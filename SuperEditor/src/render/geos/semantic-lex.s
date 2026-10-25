; Actual unchanged SuperMark lexer over a counted R14 merged-source snapshot.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/semantic-lex.inc"
.include "render/presentation.inc"
.include "supermark/api.inc"
.include "document/math24.inc"
.import se_f_owner,se_fs_state,se_fs_owned,se_fs_end,se_fs_state_size
.import se_fs_offset,se_fs_count,se_fs_buffer,se_fs_done,se_fs_length
.import se_sl_init,se_sl_feed,se_sl_finish,se_sl_next,se_sl_count
.import se_sl_pos,se_sl_start,se_sl_end,se_sl_style,se_sl_state,se_sl_state_size
.export entry
F=GSEM_FRAME
.assert se_fs_state=$8EE0,lderror,"GEOS lexical reader state moved"
.assert se_fs_state_size=86,lderror,"GEOS lexical reader size changed"
.assert se_sl_state=$8D00,lderror,"GEOS lexer phase moved"
.assert se_sl_state_size=60,lderror,"GEOS lexer aliases lexical controller"
.segment "GEOS_SEMANTIC_LEX"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 jeq begin
 cmp #GLEX_CANCEL
 jeq cancel
 cmp #GLEX_STEP
 jne argument
 lda GLEX_ACTIVE
 jeq state
 jsr frozen
 jcs fail
 lda #1
 jsr reader
 jcs fail
 lda GLEX_PHASE
 cmp #2
 jeq paint
 lda se_sl_count
 jne event
 lda GLEX_FINISHED
 jne complete
 lda #0
 sta GLEX_READS
 lda #32
 sta GLEX_BUDGET
scan:
 CMP24 se_sl_pos,GLEX_END
 jcs finish
 lda GLEX_INDEX
 cmp GLEX_USED
 bcc @feed
 lda GLEX_READS
 jne pending
 inc GLEX_READS
 COPY24 se_sl_pos,se_fs_offset
 lda #32
 sta se_fs_count
 lda #<GLEX_PACKET
 sta se_fs_buffer
 lda #>GLEX_PACKET
 sta se_fs_buffer+1
 lda #2
 jsr reader
 jcs fail
 lda se_fs_done
 jeq range
 sta GLEX_USED
 lda #0
 sta GLEX_INDEX
@feed:
 ldx GLEX_INDEX
 lda GLEX_PACKET,x
 sta GLEX_BYTE
 jsr packet_matches
 jcs fail
 lda GLEX_BYTE
 jsr se_sl_feed
 jcs fail
 inc GLEX_INDEX
 lda se_sl_count
 jne pending
 dec GLEX_BUDGET
 jne scan
 jmp pending
begin:
 lda GLEX_SOURCE_ACTIVE
 ora GLEX_CONTEXT_VALID
 ora se_fs_owned
 jne busy
 lda F+GSEM_LANGUAGE
 cmp #3
 jcs argument
 lda F+GSEM_COUNT
 cmp #161
 jcs argument
 lda #0
 sta GLEX_ACTIVE
 sta GLEX_ERROR
 sta GLEX_INDEX
 sta GLEX_USED
 sta GLEX_FINISHED
 sta GLEX_PHASE
 ldx #85
@clear:
 sta se_fs_state,x
 dex
 bpl @clear
 jsr reader ;A0 snapshot BEGIN
 jcs fail
 COPY24 se_fs_length,GLEX_LENGTH
 COPY24 F+GSEM_QUERY,GLEX_QUERY
 COPY24 F+GSEM_BODY,GLEX_BODY
 COPY24 F+GSEM_END,GLEX_END
 lda F+GSEM_LANGUAGE
 sta GLEX_LANG
 lda F+GSEM_COUNT
 sta GLEX_COUNT
 clc
 lda GLEX_QUERY
 adc GLEX_COUNT
 sta GLEX_VISIBLE_END
 lda GLEX_QUERY+1
 adc #0
 sta GLEX_VISIBLE_END+1
 lda GLEX_QUERY+2
 adc #0
 sta GLEX_VISIBLE_END+2
 jcs range
 CMP24 GLEX_BODY,GLEX_QUERY
 jcs @body_equal
 jmp @end
@body_equal:
 jne range
@end:
 CMP24 GLEX_VISIBLE_END,GLEX_END
 bcc @length
 jne range
@length:
 CMP24 GLEX_END,GLEX_LENGTH
 bcc @valid
 jne range
@valid:
 ldx GLEX_COUNT
 jeq complete
 lda #4
@base:
 dex
 sta GLEX_ROLES,x
 bne @base ;STA preserves DEX Z for count up to160
 lda se_render_caps
 and #RENDER_CODE_COLOR
 jeq complete ;uniform code roles; no lexical init, feed or finish
 lda GLEX_LANG
 jsr se_sl_init
 COPY24 GLEX_BODY,se_sl_pos
 lda #1
 sta GLEX_ACTIVE
 sta GLEX_SOURCE_ACTIVE
 jmp pending
finish:
 jsr se_sl_finish
 jcs fail
 lda #1
 sta GLEX_FINISHED
 jmp pending
event:
 jsr se_sl_next
 jcs fail
 lda se_sl_style
 cmp #7
 jcc argument_fail
 cmp #14
 jcs argument_fail
 sta GLEX_ROLE
 COPY24 se_sl_start,GLEX_FROM
 COPY24 se_sl_end,GLEX_TO
 CMP24 GLEX_FROM,GLEX_QUERY
 bcs :+
 COPY24 GLEX_QUERY,GLEX_FROM
:
 CMP24 GLEX_TO,GLEX_VISIBLE_END
 bcc :+
 COPY24 GLEX_VISIBLE_END,GLEX_TO
:
 CMP24 GLEX_FROM,GLEX_TO
 jcs pending
 SUB24 GLEX_FROM,GLEX_QUERY,GLEX_FROM
 SUB24 GLEX_TO,GLEX_QUERY,GLEX_TO
 lda GLEX_FROM
 sta GLEX_PAINT
 lda GLEX_TO
 sta GLEX_PAINT_END
 lda #2
 sta GLEX_PHASE
 jmp pending
paint:
 lda #32
 sta GLEX_BUDGET
@byte:
 ldx GLEX_PAINT
 cpx GLEX_PAINT_END
 beq @done
 lda GLEX_ROLE
 sta GLEX_ROLES,x
 inc GLEX_PAINT
 dec GLEX_BUDGET
 bne @byte
 jmp pending
@done:
 lda #0
 sta GLEX_PHASE
 jmp pending
complete:
 jsr cleanup
 lda #0
 sta GLEX_ACTIVE
 jmp se_gp_preview_complete
cancel:
 lda GLEX_ACTIVE
 beq @done
 jsr cleanup
 lda #0
 sta GLEX_ACTIVE
 sta GLEX_ERROR
@done:
 lda #0
 clc
 rts
pending:
 lda #GLEX_ID
 sta $9135
 lda #1
 sta $9136
 clc
 rts
frozen:
 lda F+GSEM_LANGUAGE
 cmp GLEX_LANG
 jne changed
 lda F+GSEM_COUNT
 cmp GLEX_COUNT
 jne changed
 ldx #2
@fields:
 lda F+GSEM_QUERY,x
 cmp GLEX_QUERY,x
 jne changed
 lda F+GSEM_BODY,x
 cmp GLEX_BODY,x
 jne changed
 lda F+GSEM_END,x
 cmp GLEX_END,x
 jne changed
 dex
 bpl @fields
 clc
 rts
; Visible cached bytes must be the same canonical bytes the lexer consumes.
packet_matches:
 CMP24 se_sl_pos,GLEX_QUERY
 bcc @outside
 CMP24 se_sl_pos,GLEX_VISIBLE_END
 bcs @outside
 sec
 lda se_sl_pos
 sbc GLEX_QUERY
 tax
 lda GLEX_SOURCE,x
 cmp GLEX_BYTE
 bne changed
@outside:
 clc
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
 sta GLEX_SAVED_FS,x
 dex
 bpl @save
 lda se_fs_owned
 sta GLEX_CONTEXT_VALID
 pla
 plp
 rts
cleanup:
 lda GLEX_CONTEXT_VALID
 beq @done
 jsr se_fs_end ;always resident; no cleanup depends on R14 admission
 ldx #85
@save:
 lda se_fs_state,x
 sta GLEX_SAVED_FS,x
 dex
 bpl @save
@done:
 lda #0
 sta GLEX_SOURCE_ACTIVE
 sta GLEX_CONTEXT_VALID
 rts
argument:
 lda #$90
 sec
 rts
argument_fail:
 lda #$90
 bne fail
range:
 lda #$7B
 bne fail
changed:
 lda #$B1
 sec
 rts
state:
 lda #$70
 sec
 rts
busy:
 lda #$B2
 sec
 rts
fail:
 sta GLEX_ERROR
 pha
 jsr cleanup
 lda #0
 sta GLEX_ACTIVE
 pla
 sec
 rts

.include "render/geos/preview-handoff.inc"
