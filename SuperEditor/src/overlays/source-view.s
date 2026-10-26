.import se_sc_begin,se_sc_event,se_sc_finish,se_sc_close,se_sc_scan
.import se_lp_shift_row
.setcpu "6502"
.include "editor-api.inc"
.ifndef se_f_owner
.import se_f_owner
.endif
.import se_fs_begin,se_fs_guard,se_fs_read
.segment "FOLD_SOURCE_CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    beq begin
    cmp #1
    beq guard
    cmp #2
    beq read
    cmp #3
    beq sc_begin
    cmp #4
    beq sc_event
    cmp #5
    beq sc_finish
    cmp #7
    beq pixel_owner
    cmp #6
    bne pixel_argument
pixel_owner:
    ldx se_f_owner
    cpx #4
    bne pixel_argument
    cmp #6
    beq pixel_prime
    jmp se_lp_shift_row
pixel_prime:
    lda #0
    clc
    rts
pixel_argument:
    lda #$B0
    sec
    rts
sc_begin:jmp se_sc_begin
sc_event:jmp se_sc_event
sc_finish:jmp se_sc_finish
begin:jmp se_fs_begin
guard:jmp se_fs_guard
read:jsr se_fs_read
 bcs :+
 jmp se_sc_scan
: rts
