; Source-preserving bounded inline appearance, complete logical-body lookahead.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/semantic.inc"
.include "render/geos/source-line.inc"
.include "render/geos/inline.inc"
.include "render/geos/source-cache-api.inc"
.include "supermark/api.inc"
.include "fold/source.inc"
.ifdef SE_EDITOR_CACHED_INLINE_SOURCE
.import se_bc_flags,se_bc_count
.endif
.import se_f_owner,se_fs_state,se_fs_owned,se_fs_end,se_fs_state_size
.import se_fs_offset,se_fs_count,se_fs_buffer,se_fs_done,se_fs_length
.import se_si_init,se_si_feed,se_si_finish,se_si_at_body,se_si_pos,se_si_ready
.import se_si_kind,se_si_style,se_si_width,se_si_open,se_si_close,se_si_state,se_si_state_size
.export entry,se_gi_active
se_gi_active=GI_ACTIVE
F=GSEM_FRAME
.assert se_fs_state=$8EE0,lderror,"inline reader context moved"
.assert se_fs_state_size=86,lderror,"inline reader context size changed"
.assert se_si_state=GI_PARSER,lderror,"inline parser phase moved"
.assert se_si_state_size=68,lderror,"inline parser phase size changed"
.segment "GEOS_INLINE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 cmp #GI_BEGIN_WIDE
 jeq begin_wide
.ifdef SE_EDITOR_CACHED_INLINE_SOURCE
 cmp #GI_SOURCE_FALLBACK ;explicit legacy retry, never redelegates
 jeq source_legacy
.endif
 cmp #GI_SOURCE_BEGIN
 jeq source_begin
 cmp #GI_BEGIN
 jeq begin
 cmp #GI_CANCEL
 jeq cancel
 cmp #GI_STEP
 jne argument
 lda $9135
 cmp #GI_ID
 jne busy ;another owner4 phase must not be interpreted as this controller
 lda GI_ACTIVE
 jeq state
 jsr frozen
 jcs fail
 lda GI_PHASE
 cmp #4
 bcs @published_guard
 lda #1
 jsr reader
 jmp @guarded
@published_guard:
 jsr publish_guard
@guarded:
 jcs fail
 lda #32
 sta GI_BUDGET
 lda GI_PHASE
 cmp #1
 jeq initialize
 cmp #3
 jeq paint
 cmp #4
 jeq publish
 cmp #5
 jeq publish_hidden
 cmp #2
 jne argument_fail
 lda GI_FINISHED
 jne publication
 lda #0
 sta GI_READS
scan:
 CMP24 se_si_pos,GI_END
 jcs finish
 lda GI_INDEX
 cmp GI_USED
 bcc @feed
 lda GI_READS
 jne pending
 inc GI_READS
 COPY24 se_si_pos,se_fs_offset
 lda #32
 sta se_fs_count
 lda #<GS_PACKET
 sta se_fs_buffer
 lda #>GS_PACKET
 sta se_fs_buffer+1
 lda #2
 jsr reader
 jcs fail
 lda se_fs_done
 jeq range
 sta GI_USED
 lda #0
 sta GI_INDEX
@feed:
 ldx GI_INDEX
 lda GS_PACKET,x
 sta GI_BYTE
 cmp #13
 jeq argument_fail ;BODY..END is one logical body, excludes its CR
 lda GI_BYTE
 jsr se_si_feed
 jcs fail
 inc GI_INDEX
 lda se_si_ready
 jne event
 dec GI_BUDGET
 jne scan
 jmp pending
begin:
 ldx #0
 beq begin_common
source_begin:
.ifdef SE_EDITOR_CACHED_INLINE_SOURCE
.include "render/geos/source-cache-gate.inc"
source_legacy:
.endif
 ldx #1
 bne begin_common
begin_wide:
 ldx #2
begin_common:
 lda GS_ACTIVE
 ora GS_CONTEXT_VALID
 jne busy
 lda F+GSEM_COUNT
 cpx #2
 bne @ordinary_count
 cmp #161
 jne argument
 ldx #0 ;WIDE completion returns to its caller, never SOURCE_BEGIN handoff
 beq @count_ready
@ordinary_count:
 cmp #161
 jcs argument
@count_ready:
 lda F+GSEM_ROLE
 cmp #14
 jcs argument
 txa
 pha
 lda #0
 ldx #62
@clear:
 sta GI_CONTROL,x
 dex
 bpl @clear
 sta GI_LAST_HIDDEN
 sta GI_LAST_STYLE
 sta GI_LAST_ROLE
 pla
 sta GI_SOURCE_RETURN
 lda #0
 ldx #85
@source:
 sta se_fs_state,x
 dex
 bpl @source
 jsr reader ;A0 snapshot BEGIN
 jcs fail
 COPY24 se_fs_length,GI_LENGTH
 COPY24 F+GSEM_QUERY,GI_QUERY
 COPY24 F+GSEM_START,GI_START
 COPY24 F+GSEM_BODY,GI_BODY
 COPY24 F+GSEM_END,GI_END
 lda F+GSEM_COUNT
 sta GI_COUNT
 lda F+GSEM_ROLE
 sta GI_BASE
 clc
 lda GI_QUERY
 adc GI_COUNT
 sta GI_VISIBLE_END
 lda GI_QUERY+1
 adc #0
 sta GI_VISIBLE_END+1
 lda GI_QUERY+2
 adc #0
 sta GI_VISIBLE_END+2
 jcs range
 CMP24 GI_BODY,GI_START
 jcc range
 CMP24 GI_END,GI_BODY
 jcc range
 CMP24 GI_QUERY,GI_START
 jcc range
 CMP24 GI_LENGTH,GI_VISIBLE_END
 jcc range
 CMP24 GI_LENGTH,GI_END
 jcc range
 jsr se_si_init
 COPY24 GI_BODY,se_si_pos
 SUB24 GI_BODY,GI_START,GI_TEMP
 lda GI_TEMP
 ora GI_TEMP+1
 ora GI_TEMP+2
 beq @ready
 lda GI_TEMP
 ldx GI_TEMP+1
 ldy GI_TEMP+2
 jsr se_si_at_body
@ready:
 lda #1
 sta GI_ACTIVE
 sta GI_PHASE
 lda GI_COUNT
 jeq publication_hidden
 jmp pending
initialize:
 ldx GI_PAINT
 cpx #160
 beq @last
 cpx GI_COUNT
 bcs @next
 lda #0
 sta GI_STYLES,x
 lda GI_BASE
 sta GI_ROLES,x
 jmp @next
@last:
 lda #0
 sta GI_LAST_STYLE
 lda GI_BASE
 sta GI_LAST_ROLE
@next:
 inc GI_PAINT
 lda GI_PAINT
 cmp #161
 beq @scan
 dec GI_BUDGET
 bne initialize
 jmp pending
@scan:
 lda #2
 sta GI_PHASE
 jmp pending
finish:
 jsr se_si_finish
 jcs fail
 lda #1
 sta GI_FINISHED
 lda se_si_ready
 jne event
 jmp publication
event:
 lda #0
 sta se_si_ready ;drain before accepting another native source byte
 lda se_si_kind
 cmp #SM_ESCAPE
 beq @escape
 cmp #SM_PAIR
 jne argument_fail
 COPY24 se_si_open,GI_HIDE_POS
 jsr hide_span
 COPY24 se_si_close,GI_HIDE_POS
 jsr hide_span
 jmp @interior
@escape:
 COPY24 se_si_open,GI_HIDE_POS
 jsr hide_span
 jmp pending
@interior:
 clc
 lda se_si_open
 adc se_si_width
 sta GI_FROM
 lda se_si_open+1
 adc #0
 sta GI_FROM+1
 lda se_si_open+2
 adc #0
 sta GI_FROM+2
 jcs range
 COPY24 se_si_close,GI_TO
 CMP24 GI_FROM,GI_QUERY
 bcs :+
 COPY24 GI_QUERY,GI_FROM
:
 CMP24 GI_TO,GI_VISIBLE_END
 bcc :+
 COPY24 GI_VISIBLE_END,GI_TO
:
 CMP24 GI_TO,GI_FROM
 jcc pending
 jeq pending
 SUB24 GI_FROM,GI_QUERY,GI_TEMP
 lda GI_TEMP+1
 ora GI_TEMP+2
 jne argument_fail
 lda GI_TEMP
 sta GI_PAINT
 SUB24 GI_TO,GI_QUERY,GI_TEMP
 lda GI_TEMP+1
 ora GI_TEMP+2
 jne argument_fail
 lda GI_TEMP
 sta GI_STOP
 lda se_si_style
 cmp #SM_INLINE_CODE
 beq @code
 cmp #1
 jcc argument_fail
 cmp #4
 jcs argument_fail
 lda #0
 sta GI_STYLE
 lda se_si_style
 and #SM_STRONG
 beq :+
 inc GI_STYLE
:
 lda se_si_style
 and #SM_EMPHASIS
 beq @phase
 lda GI_STYLE
 ora #2
 sta GI_STYLE
 bne @phase
@code:
 lda #$80
 sta GI_STYLE
@phase:
 lda #3
 sta GI_PHASE
 jmp pending
paint:
 ldx GI_PAINT
 cpx #160
 bne @ordinary
 lda GI_STYLE
 bmi @last_code
 lda GI_LAST_STYLE
 bmi @next
 ora GI_STYLE
 sta GI_LAST_STYLE
 jmp @next
@last_code:
 sta GI_LAST_STYLE
 lda #4
 sta GI_LAST_ROLE
 jmp @next
@ordinary:
 lda GI_STYLE
 bmi @code
 lda GI_STYLES,x
 bmi @next
 ora GI_STYLE
 sta GI_STYLES,x
 jmp @next
@code:
 sta GI_STYLES,x
 lda #4
 sta GI_ROLES,x
@next:
 inc GI_PAINT
 lda GI_PAINT
 cmp GI_STOP
 beq @scan
 dec GI_BUDGET
 bne paint
 jmp pending
@scan:
 lda #2
 sta GI_PHASE
 jmp pending
publication:
 jsr cleanup ;END before publishing derived appearance
 lda #1
 sta GI_ACTIVE ;publication remains cancellable, without a source lease
 lda #0
 sta GI_PAINT
 lda #4
 sta GI_PHASE
 jmp pending
publish:
 ldx GI_PAINT
 cpx #160
 bne @ordinary
 lda GI_LAST_STYLE
 and #3
 sta GI_OUTPUT_STYLES+160
 lda GI_LAST_ROLE
 sta GI_OUTPUT_ROLE_LAST
 jmp @next
@ordinary:
 lda GI_STYLES,x
 and #3
 sta GI_OUTPUT_STYLES,x
 lda GI_ROLES,x
 sta GI_OUTPUT_ROLES,x
@next:
 inc GI_PAINT
 lda GI_PAINT
 cmp GI_COUNT
 beq hidden_phase
 dec GI_BUDGET
 bne publish
 jmp pending
publication_hidden:
 jsr cleanup
 lda #1
 sta GI_ACTIVE
hidden_phase:
 lda #0
 sta GI_PAINT
 lda #5
 sta GI_PHASE
 jmp pending
publish_hidden:
 ldx GI_PAINT
 cpx #20
 bne @ordinary
 lda GI_LAST_HIDDEN
 jmp @store
@ordinary:
 lda GI_HIDDEN,x
@store:
 sta GI_OUTPUT_HIDDEN,x
 inc GI_PAINT
 lda GI_PAINT
 cmp #GI_HIDDEN_BYTES
 bcc publish_hidden
complete:
 jsr cleanup
 lda GI_SOURCE_RETURN
 jeq se_gp_preview_complete
 lda #20
 sta $9135
 lda #1
 sta $9136
 clc
 rts
zero:
 lda #0
 clc
 rts
cancel:
 lda $9135
 cmp #GI_ID
 jne zero
 lda GI_ACTIVE
 jeq zero ;do not release a later C20/C24/C25 source snapshot
 jsr cleanup
 jmp zero
; A complete-body parser event certifies at most3 delimiter bytes. Clip each
; byte against the canonical query window before touching its private bitset.
; No source read, output publication, or unbounded loop occurs here.
hide_span:
 lda se_si_width
 sta GI_HIDE_LEFT
@byte:
 CMP24 GI_HIDE_POS,GI_QUERY
 bcc @next
 CMP24 GI_HIDE_POS,GI_VISIBLE_END
 bcs @next
 SUB24 GI_HIDE_POS,GI_QUERY,GI_TEMP
 lda GI_TEMP
 and #7
 tay
 lda GI_TEMP
 lsr
 lsr
 lsr
 tax
 lda hidden_bits,y
 cpx #20
 bne @ordinary
 ora GI_LAST_HIDDEN
 sta GI_LAST_HIDDEN
 jmp @next
@ordinary:
 ora GI_HIDDEN,x
 sta GI_HIDDEN,x
@next:
 inc GI_HIDE_POS
 bne :+
 inc GI_HIDE_POS+1
 bne :+
 inc GI_HIDE_POS+2
:
 dec GI_HIDE_LEFT
 jne @byte
 rts
hidden_bits:
 .byte $80,$40,$20,$10,$08,$04,$02,$01
frozen:
 CMP24 F+GSEM_QUERY,GI_QUERY
 jne changed
 CMP24 F+GSEM_BODY,GI_BODY
 jne changed
 CMP24 F+GSEM_END,GI_END
 jne changed
 CMP24 F+GSEM_START,GI_START
 jne changed
 lda F+GSEM_COUNT
 cmp GI_COUNT
 jne changed
 lda F+GSEM_ROLE
 cmp GI_BASE
 jne changed
 clc
 rts
.macro GI_CHECK source,offset,n
 ldx #n-1
: lda source,x
 cmp GS_FS+27+offset,x
 jne changed
 dex
 bpl :-
.endmacro
; Publication uses metadata-only guards; the role result is outside DOC_LEAF.
; Compare the full frozen59B source identity and validate all typed tokens using
; resident metadata-only services after END, before every bounded output slice.
publish_guard:
 FS_FIELDS GI_CHECK
 lda se_doc_busy
 ora se_hot_phase
 ora se_hot_owned
 ora se_h_phase
 ora se_b_phase
 ora se_clip_busy
 ora se_snapshot_busy
 jne changed
 DOC_TOKEN se_doc_meta
 jsr se_object_validate
 bcs @return
 DOC_TOKEN se_doc_original
 jsr se_object_validate
 bcs @return
 DOC_TOKEN se_doc_append
 jmp se_object_validate
@return:
 rts
reader:
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 ldx #85
@save:
 lda se_fs_state,x
 sta GS_FS,x
 dex
 bpl @save
 lda se_fs_owned
 sta GS_CONTEXT_VALID
 sta GS_ACTIVE
 pla
 plp
 rts
cleanup:
 lda GS_CONTEXT_VALID
 beq @clear
 ldx #85
@restore:
 lda GS_FS,x
 sta se_fs_state,x
 dex
 bpl @restore
 jsr se_fs_end
 ldx #85
@save:
 lda se_fs_state,x
 sta GS_FS,x
 dex
 bpl @save
@clear:
 lda #0
 sta GS_ACTIVE
 sta GS_CONTEXT_VALID
 sta GI_ACTIVE
 rts
pending:
 lda #26
 sta $9135
 lda #1
 sta $9136
 clc
 rts
fail:
 sta GI_ERROR
 pha
 jsr cleanup
 pla
 sec
 rts
argument_fail:
 lda #$90
 jmp fail
range:
 lda #$7B
 jmp fail
changed:
 lda #$74
 sec
 rts
busy:
 lda #$B2
 sec
 rts
state:
 lda #$70
 sec
 rts
argument:
 lda #$90
 sec
 rts

.include "render/geos/preview-handoff.inc"
