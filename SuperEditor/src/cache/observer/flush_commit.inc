; A nonzero flush was observed already at R2 publication. Only a zero/zero
; flush can reach W_COMMIT with its REKEY intent still outstanding.
bc_flush_commit:
 lda se_bc_flags
 and #BC_MUTATING
 beq @done
 lda se_bc_head
 cmp #BC_RING_LIMIT
 bcs @lost
 jsr bc_index
 lda se_bc_ring+BC_E_KIND,y
 cmp #BC_EVENT_REKEY
 bne @lost
 lda se_bc_ring+BC_E_DELETE,y
 ora se_bc_ring+BC_E_DELETE+1,y
 ora se_bc_ring+BC_E_DELETE+2,y
 ora se_bc_ring+BC_E_INSERT,y
 ora se_bc_ring+BC_E_INSERT+1,y
 ora se_bc_ring+BC_E_INSERT+2,y
 bne @lost
 lda se_bc_ring+BC_E_GEN_BEFORE,y
 cmp se_doc_generation
 bne @lost
 lda se_bc_ring+BC_E_GEN_BEFORE+1,y
 cmp se_doc_generation+1
 bne @lost
 jmp bc_commit
@lost:
 jmp bc_lost
@done:
 rts
