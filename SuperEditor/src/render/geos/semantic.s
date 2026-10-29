; Native merged-source block context. Root enters C24 before C20 BEGIN only.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/checkpoint/codec.inc"
.include "render/geos/semantic.inc"
.include "render/geos/source-line.inc"
.include "supermark/api.inc"
.include "document/math24.inc"
.import se_f_owner,se_fs_state,se_fs_owned,se_fs_end,se_fs_state_size
.import se_fs_offset,se_fs_count,se_fs_buffer,se_fs_done,se_fs_length
.import se_sm_init,se_sm_feed,se_sm_finish,se_sm_state,se_sm_state_size
.import se_sm_pos,se_sm_ready,se_sm_kind,se_sm_language,se_sm_level,se_sm_marker
.import se_sm_start,se_sm_end,se_sm_body,se_sm_fence
.import se_doc_meta,se_doc_generation,se_doc_epoch,se_reu_epoch,se_r_revision,se_l_mode
.export entry,se_gsem_frame
se_gsem_frame=GSEM_FRAME
F=GSEM_FRAME
.macro KEY_FIELDS action
 action se_doc_meta,0,15
 action se_doc_generation,15,2
 action se_r_revision,17,4
 action F+GSEM_LENGTH,21,3
 action se_reu_epoch,24,2
 action se_doc_epoch,26,2
.endmacro
.macro capture source,offset,size
 ldx #size-1
: lda source,x
 sta F+GSEM_CP_KEY+offset,x
 dex
 bpl :-
.endmacro
.macro compare source,offset,size
 ldx #size-1
: lda source,x
 cmp F+GSEM_CP_KEY+offset,x
 jne restart
 dex
 bpl :-
.endmacro
.assert se_fs_state=$8EE0,lderror,"semantic source context moved"
.assert se_fs_state_size=86,lderror,"semantic source context size changed"
.assert se_sm_state=GSEM_BLOCK_STATE,lderror,"semantic block state moved"
.assert se_sm_state_size=79,lderror,"semantic block state size changed"
.segment "GEOS_SEMANTIC"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 jeq begin
 cmp #3
 jeq gsc_begin
 cmp #GSEM_CANCEL
 jeq cancel
 cmp #GSEM_STEP
 jne argument
 lda F+GSEM_ACTIVE
 cmp #2
 jeq gpc_step
 lda F+GSEM_ACTIVE
 jeq state
 ; Source guard and READ are sequential R14 entries, never another C leaf.
 lda #1
 jsr reader
 jcs fail
 COPY24 se_sm_pos,se_fs_offset
 lda #32
 sta se_fs_count
 lda #<GS_PACKET
 sta se_fs_buffer
 lda #>GS_PACKET
 sta se_fs_buffer+1
 lda #2
 jsr reader
 jcs fail
 inc F+GSEM_READS
 bne :+
 inc F+GSEM_READS+1
 bne :+
 inc F+GSEM_READS+2
:
 lda se_fs_done
 jeq eof
 sta F+GSEM_USED
 lda #0
 sta F+GSEM_INDEX
@feed:
 ldx F+GSEM_INDEX
 lda GS_PACKET,x
 cmp #'*'
 beq @inline
 cmp #'@'
 bne @literal
@inline:
 lda #1
 sta F+GSEM_INLINE
@literal:
 lda GS_PACKET,x
 cmp #13
 bne @gsc_literal
 jsr gsc_boundary
 lda #13
@gsc_literal:
 jsr se_sm_feed
 jcs fail
 inc F+GSEM_INDEX
 lda se_sm_ready
 beq @next
 jsr contains
 jcs publish
 lda #0
 sta F+GSEM_INLINE ;the next physical line has a fresh inline context
@next:
 lda F+GSEM_INDEX
 cmp F+GSEM_USED
 bcc @feed
 jmp pending
begin:
 lda #0
 sta GSC_TRY
 jmp gsc_begin_common
gsc_begin:
 lda GSC_SELECTOR
 cmp #2
 jcs argument
 lda #1
 sta GSC_TRY
gsc_begin_common:
 lda GS_ACTIVE
 ora GS_CONTEXT_VALID
 jne busy
 lda #0
 sta F+GSEM_ACTIVE
 sta GSC_CAPTURED
 sta GSC_PROOF
 sta GSC_PREVIOUS_VALID
 sta F+GSEM_ERROR
 sta F+GSEM_READS
 sta F+GSEM_READS+1
 sta F+GSEM_READS+2
 ldx #85
@clear:
 sta se_fs_state,x
 dex
 bpl @clear
 jsr reader ;A0 BEGIN
 jcs fail
 COPY24 se_fs_length,F+GSEM_LENGTH
 CMP24 F+GSEM_QUERY,F+GSEM_LENGTH
 bcc @valid
 jne range
@valid:
 lda GSC_TRY
 jne gsc_try
 lda #1
 sta F+GSEM_ACTIVE
 lda F+GSEM_CP_VALID
 cmp #1
 beq :+
 cmp #2
 jne restart
: lda se_l_mode
 cmp F+GSEM_CP_MODE
 jne restart
 lda F+GSEM_CP_VALID
 cmp #2
 jeq gsc_restore_seed
 CMP24 F+GSEM_QUERY,F+GSEM_CP_QUERY
 jcc restart
 KEY_FIELDS compare
 CMP24 F+GSEM_QUERY,F+GSEM_CP_EVENT+4 ;cached START
 jcc restart
 CMP24 F+GSEM_CP_EVENT+7,F+GSEM_QUERY ;cached END
 bcc gsc_later
 ldx #15
@event:
 lda F+GSEM_CP_EVENT,x
 sta F+GSEM_KIND,x
 dex
 bpl @event
 COPY24 F+GSEM_QUERY,F+GSEM_CP_QUERY
 jsr cleanup
 jmp gpc_complete
gsc_later:
 CMP24 F+GSEM_QUERY,F+GSEM_CP_NEXT
 jcc restart
gsc_restore_seed:
 CMP24 F+GSEM_QUERY,F+GSEM_CP_NEXT
 jcc restart
 ldx #78
@restore:
 lda F+GSEM_CP_STATE,x
 sta se_sm_state,x
 dex
 bpl @restore
 lda #0
 sta F+GSEM_INLINE
 jmp pending
restart:
 lda #0
 sta F+GSEM_CP_VALID
 sta F+GSEM_INLINE
 jsr se_sm_init
 jmp pending
eof:
 jsr gsc_incoming
 jsr se_sm_finish
 jcs fail
 lda se_sm_ready
 beq @blank
 jsr contains
 jcs publish
 jmp range
@blank:
 CMP24 F+GSEM_QUERY,F+GSEM_LENGTH
 jne range
 ; Block finish emits no invented line. A real EOF boundary after CR still
 ; needs its current fence context and an empty canonical descriptor.
 COPY24 F+GSEM_LENGTH,se_sm_start
 COPY24 F+GSEM_LENGTH,se_sm_end
 COPY24 F+GSEM_LENGTH,se_sm_body
 lda #0
 sta se_sm_level
 sta se_sm_marker
 lda #SM_BLANK
 ldx se_sm_fence
 bne @code
 ldx #SM_TEXT
 stx se_sm_language
 beq :+
@code:
 lda #SM_CODE_LINE
:
 sta se_sm_kind
 jmp publish
contains:
 CMP24 F+GSEM_QUERY,se_sm_start
 bcc @no
 CMP24 se_sm_end,F+GSEM_QUERY
 rts ;Cset query<=END, includes its literal CR source cell
@no:
 clc
 rts
publish:
 lda se_sm_kind
 sta F+GSEM_KIND
 lda se_sm_language
 sta F+GSEM_LANG
 lda se_sm_level
 sta F+GSEM_LEVEL
 lda se_sm_marker
 sta F+GSEM_MARKER
 COPY24 se_sm_start,F+GSEM_START
 COPY24 se_sm_end,F+GSEM_END
 COPY24 se_sm_body,F+GSEM_BODY
 lda #0
 sta F+GSEM_REVERSE
 sta F+GSEM_ROLE
 lda #9
 sta F+GSEM_HEIGHT
 lda se_sm_kind
 cmp #SM_CODE_LINE
 bne :+
 lda #8
 sta F+GSEM_HEIGHT
 lda #4
 bne @role
:
 cmp #SM_HEADING
 bne :+
 inc F+GSEM_REVERSE
 lda #2
 bne @role
:
 cmp #SM_LIST
 bne :+
 lda #1
 bne @role
:
 cmp #SM_CODE_OPEN
 beq @code
 cmp #SM_CODE_CLOSE
 bne @done
@code:
 lda #4
@role:
 sta F+GSEM_ROLE
@done:
 jsr checkpoint
 jsr cleanup
 jmp gpc_complete
zero:
 lda #0
 clc
 rts
cancel:
 lda F+GSEM_ACTIVE
 jeq zero ;a later C20 may now own the shared GS source context
 lda #0
 sta F+GSEM_CP_VALID
 jsr cleanup
 jmp zero
checkpoint:
 KEY_FIELDS capture
 COPY24 se_sm_pos,F+GSEM_CP_NEXT
 COPY24 F+GSEM_QUERY,F+GSEM_CP_QUERY
 ldx #78
@state:
 lda se_sm_state,x
 sta F+GSEM_CP_STATE,x
 dex
 bpl @state
 ldx #15
@event:
 lda F+GSEM_KIND,x
 sta F+GSEM_CP_EVENT,x
 dex
 bpl @event
 lda se_l_mode
 sta F+GSEM_CP_MODE
 lda #1
 sta F+GSEM_CP_VALID
 rts
reader:
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 ldx #85
@snapshot:
 lda se_fs_state,x
 sta GS_FS,x
 dex
 bpl @snapshot
 lda se_fs_owned
 sta GS_CONTEXT_VALID
 sta GS_ACTIVE
 pla
 plp
 rts
cleanup:
 lda GS_CONTEXT_VALID
 beq @clear
 ; Keep cleanup correct even after a missing R14 or context/epoch change.
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
 sta GS_CONTEXT_VALID
 sta GS_ACTIVE
 sta F+GSEM_ACTIVE
 rts
pending:
 lda #24
 sta $9135
 lda #1
 sta $9136
 clc
 rts
fail:
 sta F+GSEM_ERROR
 pha
 lda #0
 sta F+GSEM_CP_VALID
 jsr cleanup
 pla
 sec
 rts
range:
 lda #$7B
 jmp fail
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

.include "render/geos/checkpoint/seed.inc"
.include "render/geos/preview-handoff.inc"

.include "render/geos/preview-prepare.inc"
