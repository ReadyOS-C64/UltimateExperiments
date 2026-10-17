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

.export _sr_worker_spec,_sr_worker_call
.segment "DATA"
_sr_worker_spec:
.byte "D64F",1,16
.word 0
.dword 0
.word $a000,$a000
.segment "CODE"
_sr_worker_call:
 pha
 lda _sr_worker_spec+14
 sta ptr1
 lda _sr_worker_spec+15
 sta ptr1+1
 pla
 jmp (ptr1)
