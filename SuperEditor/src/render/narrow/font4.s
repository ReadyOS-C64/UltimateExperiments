.setcpu "6502"
.export se_narrow_font4
.ifdef SE_FIXED_NARROW_FONT
.segment "NARROW_FONT"
.else
.segment "RODATA"
.endif
se_narrow_font4: .incbin "assets/fonts/generated/narrow4.bin"
