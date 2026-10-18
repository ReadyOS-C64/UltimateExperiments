.setcpu "6502"
.export fixture_return
.segment "LOADADDR"
.word $0801
.segment "BASIC"
.word $080b,10
.byte $9e
.asciiz "2061"
.word 0
.segment "CODE"
; Disabled fixture entry, never runs any storage action on LOAD/RUN.
fixture_return: jmp fixture_return
