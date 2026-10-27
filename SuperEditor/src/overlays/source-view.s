.setcpu "6502"
.include "editor-api.inc"
.ifndef se_f_owner
.import se_f_owner
.endif
.import se_fs_begin,se_fs_guard,se_fs_read,se_sb_init,se_sb_step
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
    beq block_init
    cmp #4
    beq block_step
pixel_argument:
    lda #$B0
    sec
    rts
begin:jmp se_fs_begin
guard:jmp se_fs_guard
read:jmp se_fs_read
block_init:jmp se_sb_init
block_step:jmp se_sb_step
