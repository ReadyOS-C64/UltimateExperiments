; C14 calls the independent R14 reader. C->R nesting is supported by resident.
.setcpu "6502"
.include "editor-api.inc"
.export se_fs_begin,se_fs_guard,se_fs_read
.segment "STYLE_CODE"
se_fs_begin:
    lda #0
    beq invoke
se_fs_guard:
    lda #1
    bne invoke
se_fs_read:
    lda #2
invoke:
    sta se_overlay_frame
    lda #14
    ldx #0
    jmp se_overlay_call

.ifndef se_mode
.import se_mode
.endif
.export se_sc_begin,se_sc_event,se_sc_finish
se_sc_begin: lda #3
 bne certificate
se_sc_event:
.ifdef SE_GRID_PRODUCER
.ifndef se_sm_kind
.import se_sm_kind
.endif
 lda se_sm_kind
 beq @call
 lda $89C3 ; owner2 live latch; absence can only suppress optional authority
 bne @call
 lda #0
 clc
 rts
@call:
.endif
 lda #4
 bne certificate
se_sc_finish: lda #5
certificate:
 ldx se_mode
 bne invoke
 lda #0
 clc
 rts
