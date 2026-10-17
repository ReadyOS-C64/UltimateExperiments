.setcpu "6502"
.import __PRELAUNCH_SIZE__,__PRELAUNCH_RO_SIZE__
.export _so_overlay_spec
.segment "DATA"
_so_overlay_spec:
 .byte "D64I",1,16
 .word __PRELAUNCH_SIZE__+__PRELAUNCH_RO_SIZE__
 .byte "CRC?"
 .word $6000,0
