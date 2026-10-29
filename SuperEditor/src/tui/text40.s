.setcpu "6502"
.importzp text_ptr, screen_ptr
.import se_petscii_screen, se_ink_reverse
.export se_print
.segment "CODE"
; NUL-terminated native PETSCII, <=255 bytes. No CHROUT or screen-editor effects.
se_print:
    ldy #0
@next:
    lda (text_ptr),y
    beq @done
    jsr se_petscii_screen
    eor se_ink_reverse
    sta (screen_ptr),y
    iny
    bne @next
@done:
    rts
