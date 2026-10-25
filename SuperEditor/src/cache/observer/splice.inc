; All fallible staging is finished. Observe the actual transaction tuple,
; never the mutable public request. No cache error can reject source publication.
.include "cache/observer/ring.inc"
bc_splice_prepare:
 lda se_bc_flags
 and #BC_MUTATING
 bne @rekey
 lda se_hot_pending
 bne @lost ; committed coordinates cannot stand in for an unproved merged edit
 jsr bc_reserve
 beq @done
 lda #BC_EVENT_SPLICE
 sta se_bc_ring+BC_E_KIND,y
 BC_STORE se_r_revision,BC_E_REV_BEFORE,4
 BC_STORE se_doc_generation,BC_E_GEN_BEFORE,2
 tya
 clc
 adc #(BC_E_POSITION+2)
 tay
 ldx #2
@tuple:
 lda tx_position,x
 sta se_bc_ring,y
 lda tx_insert,x
 sta se_bc_ring+(BC_E_INSERT-BC_E_POSITION),y
 dey
 dex
 bpl @tuple
 jsr bc_index
 sec
.repeat 3,I
 lda tx_end+I
 sbc tx_position+I
 sta se_bc_ring+BC_E_DELETE+I,y
.endrepeat
@done:
 rts
@lost:
 jmp bc_lost
@rekey:
 ; Only the admitted hot/history byte flush can consume a prepared REKEY.
 ; Dry-run BEGIN/CANCEL never calls this publication point.
 lda se_hot_phase
 cmp #2
 bne @lost
 lda se_h_owned_splice
 beq @lost
 lda tx_ref_mode
 bne @lost
 lda se_h_phase
 and #$FE ;H_FEEDING4/H_APPLY5
 cmp #H_FEEDING
 bne @lost
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING)
 cmp #(BC_ARMED|BC_MUTATING)
 bne @lost
 lda se_bc_head
 cmp #BC_RING_LIMIT
 bcs @lost
 jsr bc_index
 lda se_bc_ring+BC_E_KIND,y
 cmp #BC_EVENT_REKEY
 bne @lost
 tya
 clc
 adc #(BC_E_POSITION+2)
 tay
 ldx #2
@match:
 lda tx_position,x
 cmp se_bc_ring,y
 bne @lost
 lda tx_insert,x
 cmp se_bc_ring+(BC_E_INSERT-BC_E_POSITION),y
 bne @lost
 dey
 dex
 bpl @match
 jsr bc_index
 ldx #0
@revision:
 lda se_r_revision,x
 cmp se_bc_ring+BC_E_REV_BEFORE,y
 bne @lost_late
 iny
 inx
 cpx #4
 bcc @revision
 jmp @generation
@lost_late:
 jmp bc_lost
@generation:
 jsr bc_index
 lda se_doc_generation
 cmp se_bc_ring+BC_E_GEN_BEFORE,y
 bne @lost_late
 lda se_doc_generation+1
 cmp se_bc_ring+BC_E_GEN_BEFORE+1,y
 bne @lost_late
 ; Compare DELETE while preserving the24-bit subtraction carry across CMP.
 sec
.repeat 3,I
 lda tx_end+I
 sbc tx_position+I
 php
 cmp se_bc_ring+BC_E_DELETE+I,y
 beq :+
 plp
 jmp bc_lost
:
 plp
.endrepeat
 rts
