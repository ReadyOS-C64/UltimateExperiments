; C14 calls the independent R14 reader. C->R nesting is supported by resident.
.setcpu "6502"
.include "editor-api.inc"
.export se_fs_begin,se_fs_guard,se_fs_read,se_sb_init,se_sb_step
.segment "STYLE_CODE"
se_fs_begin:
    lda #0
    beq invoke
se_fs_guard:
    lda #1
    bne invoke
se_fs_read:
    lda #2
    bne invoke
se_sb_init:
    lda #3
    bne invoke
se_sb_step:
    lda #4
invoke:
    sta se_overlay_frame
    lda #14
    ldx #0
    jmp se_overlay_call
