.setcpu "6502"
.export se_narrow_font5
.ifdef SE_FIXED_NARROW_FONT
.segment "NARROW_FONT"
.else
.segment "RODATA"
.endif
se_narrow_font5: .incbin "assets/fonts/generated/narrow5.bin"
