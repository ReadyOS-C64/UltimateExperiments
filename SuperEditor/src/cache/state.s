.setcpu "6502"
.include "cache/api.inc"
; Link LAST in both existing work segments: no existing field may move.
.segment "OBJECTS"
.export se_bc_arena,se_bc_ticket,se_bc_incarnation,se_bc_flags
.export se_bc_head,se_bc_tail,se_bc_count
se_bc_arena: .res 5
se_bc_ticket: .res 4
se_bc_incarnation: .res 4
se_bc_flags: .res 1
se_bc_head: .res 1
se_bc_tail: .res 1
se_bc_count: .res 1
.assert *-se_bc_arena=17,error,"cache descriptor size"
.assert se_bc_arena>=$9FB3,lderror,"cache moved surviving OBJECTS state"
.assert *<=$A000,lderror,"cache descriptor exceeds OBJECTS"
.segment "DOCSTATE"
.export se_bc_ring
se_bc_ring: .res BC_RING_LIMIT*BC_EVENT_SIZE
.assert se_bc_ring>=$9D85,lderror,"cache moved existing DOCSTATE state"
.assert *<=$9E00,lderror,"cache producer ring exceeds DOCSTATE"
