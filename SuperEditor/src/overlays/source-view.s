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
pixel_argument:
    lda #$B0
    sec
    rts
begin:jmp se_fs_begin
guard:jmp se_fs_guard
read:jmp se_fs_read
