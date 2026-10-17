.export _sj_gate_spec
.segment "DATA"
_sj_gate_spec:
.byte "D64G",1,24
.word 0
.dword 0
.word $6000,$6546,$9000
.res 6,0

.importzp ptr1
.export _sj_gate_call
.segment "CODE"
_sj_gate_call:
 pha
 lda _sj_gate_spec+14
 sta ptr1
 lda _sj_gate_spec+15
 sta ptr1+1
 pla
 jmp (ptr1)
