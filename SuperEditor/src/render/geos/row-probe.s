.setcpu "6502"
.exportzp se_gg_context,se_gg_pointer
; Four existing caller-loaned pointer bytes, no resident allocation.
se_gg_context=$F0
se_gg_pointer=$F2
