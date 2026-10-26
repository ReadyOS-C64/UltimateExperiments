.setcpu "6502"
.export se_geos_packed,se_geos_widths
.segment "LITERAL_FIXED_FONT"
; Existing local extraction only. No media extraction/regeneration here.
se_geos_packed: .incbin "assets/fonts/generated/bsw9-original.bin"
se_geos_widths: .incbin "assets/fonts/generated/bsw9-widths.bin"
