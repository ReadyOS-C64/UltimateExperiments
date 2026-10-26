; C7 production source handlers, no trampoline/old binary.
.include "cache/edit-rebase-integration/api.inc"
.include "render/geos/fold-query.inc"
.include "render/geos/source-line.inc"
.include "render/geos/semantic.inc"
.global se_f_owner,se_render_caps,se_overlay_frame,se_overlay_call
.global se_crc_value,se_crc_init,se_crc_byte
.segment "CODE"
brg_busy:lda #$B2
 sec
 rts
ebr_stale:lda #$C1
 sec
 rts
brg_queued:lda #1
 clc
 rts
brg_resume:
 lda #21
 ldx #1
 bne brg_request
brg_schedule:
 lda se_f_owner
 cmp #4
 bne brg_busy
 lda #0
 sta GS_ACTIVE
 sta GS_CONTEXT_VALID
 sta GFQ_ACTIVE
 sta GSEM_FRAME+GSEM_ACTIVE
 lda #50
 sta $9134
 lda se_render_caps
 beq brg_resume
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #BC_ARMED
 bne brg_resume
 lda se_bc_count
 beq brg_resume
 cmp #3
 bcs brg_resume
 ; The short-document branch performs no arena/source worker call or parsing.
 lda se_doc_length+2
 bne @large
 lda se_doc_length+1
 cmp #16
 bcc brg_resume
@large:
 lda #41
 ldx #0
brg_request:
 sta $9135
 stx $9136
 jmp brg_queued
brg_reader:
 CP S_READER,se_fs_state,86
 lda #1
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 CP se_fs_state,S_READER,86
 pla
 plp
 rts
brg_source_proof:
 lda se_f_owner
 cmp #4
 jne brg_busy
 EQ S_AUTH,se_bc_arena,13
 lda S_STATE
 cmp #7
 jne ebr_stale
 jsr brg_reader
 jcs @return
 EQ S_ROOT+32,S_READER+27,4
 EQ S_ROOT+38,S_READER+33,15
 EQ S_ROOT+57,S_EVENT+8,4
 EQ S_READER+52,S_EVENT+12,4
 EQ S_ROOT+36,S_EVENT+25,2
 ; The semantic ticket changes only for an actual visible SPLICE.
 CP S_AUTH+5,S_TEMP,4
 lda S_MODE
 bne @ticket
 sec
 .repeat 4,I
 lda S_TEMP+I
 .if I=0
 sbc #1
 .else
 sbc #0
 .endif
 sta S_TEMP+I
 .endrepeat
 jcc ebr_stale
@ticket:
 EQ S_TEMP,S_ROOT+22,4
 CP S_ROOT+91,S_TEMP,3
 lda S_MODE
 bne @length
 INC24 S_TEMP
@length:
 EQ S_TEMP,S_READER+10,3
 lda S_MODE
 bne @pure_rekey
 lda S_COUNT
 cmp #2
 beq @combined
 ; No representation change: actual committed graph remains identical.
 EQ S_ROOT+32,S_READER+27,25
 lda S_READER+57
 cmp #1
 jne ebr_stale
 jmp @page
@combined:
 EQ S_REKEY+25,S_EVENT+25,2
 EQ S_REKEY+8,S_EVENT+12,4
 EQ S_REKEY+12,S_EVENT+12,4
 ; Normalize the already checked second event into dead parser scratch only.
 CP S_REKEY,E,32
 jmp @flushed
@pure_rekey:
 CP S_EVENT,E,32
 ; A nonzero flush can only replace the exact cached pending representation.
 lda E+19
 ora E+20
 ora E+21
 ora E+22
 ora E+23
 ora E+24
 beq @flushed
 lda S_ROOT+62
 cmp #1
 jne ebr_stale
 lda S_ROOT+61
 cmp #1
 jne ebr_stale
@flushed:
 lda S_READER+57
 jne ebr_stale
 EQ E+27,S_READER+31,2
 lda E+19
 ora E+20
 ora E+21
 ora E+22
 ora E+23
 ora E+24
 beq @zero
 clc
 lda E+25
 adc #1
 sta S_TEMP
 lda E+26
 adc #0
 jcs ebr_stale
 sta S_TEMP+1
 EQ S_TEMP,E+27,2
 jmp @tuple
@zero:EQ E+25,E+27,2
@tuple:
 ; Complete24-bit committedBefore-delete+insert and both canonical ranges.
 sec
 .repeat 3,I
 lda S_ROOT+53+I
 sbc E+19+I
 sta S_TEMP+I
 .endrepeat
 jcc ebr_stale
 clc
 .repeat 3,I
 lda S_TEMP+I
 adc E+22+I
 sta S_TEMP+I
 .endrepeat
 jcs ebr_stale
 EQ S_TEMP,S_READER+48,3
 clc
 .repeat 3,I
 lda E+16+I
 adc E+19+I
 sta S_TEMP+I
 .endrepeat
 jcs ebr_stale
 C24 S_TEMP,S_ROOT+53
 jcc @newrange
 jne ebr_stale
@newrange:
 clc
 .repeat 3,I
 lda E+16+I
 adc E+22+I
 sta S_TEMP+I
 .endrepeat
 jcs ebr_stale
 C24 S_TEMP,S_READER+48
 jcc @page
 jne ebr_stale
@page:
 lda BCA_SELECTED
 eor #128
 sta S_DEST
 lda S_ROOT+104
 sta BCA_PAGE
 lda #1
 sta BCA_KIND
 sta BCA_GENERATION
 lda #0
 sta BCA_GENERATION+1
 sta BCA_PHASE
 sta BCA_PROOF
 lda #2
 sta se_overlay_frame
 lda #34
 ldx #0
 jsr se_overlay_call
 jcs @return
 lda #2
 sta S_STATE
 lda #41
 ldx #1
 jmp brg_request
@return:rts
