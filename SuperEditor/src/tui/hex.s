.setcpu "6502"
.export se_hex_byte
.segment "CODE"
; A -> two mixed-case screen-code hex digits; X high, A low; Y clobbered.
se_hex_byte:
    pha
    lsr
    lsr
    lsr
    lsr
    tay
    lda hex_screen,y
    tax
    pla
    and #15
    tay
    lda hex_screen,y
    rts
.segment "RODATA"
hex_screen: .byte $30,$31,$32,$33,$34,$35,$36,$37,$38,$39,$41,$42,$43,$44,$45,$46
