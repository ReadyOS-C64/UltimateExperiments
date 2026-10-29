.setcpu "6502"
.export se_ef_suspended
.segment "BSS"
; Published records stay owned and immutable while FILE owns the phase union.
se_ef_suspended: .res 1
