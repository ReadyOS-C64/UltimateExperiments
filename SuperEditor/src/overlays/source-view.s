.setcpu "6502"
.include "editor-api.inc"
.ifndef se_f_owner
.import se_f_owner
.endif
.import se_fs_begin,se_fs_guard,se_fs_read,se_sb_init,se_sb_step
.segment "FOLD_SOURCE_CODE"
    OVL_BINDING
entry:
    ldx se_overlay_frame
    beq begin
    dex
    beq guard
    dex
    beq read
    dex
    beq block_init
    dex
    beq block_step
pixel_argument:
    lda #$B0
    sec
    rts
begin:jmp se_fs_begin
guard:jmp se_fs_guard
; Frame2 keeps the public authenticated-read contract.  se_sb_step enters the
; private reader directly after C14 authenticated the same uninterrupted STEP.
read:
    jsr se_fs_guard
    bcc :+
    rts
:   jmp se_fs_read
block_init:jmp se_sb_init
block_step:jmp se_sb_step
