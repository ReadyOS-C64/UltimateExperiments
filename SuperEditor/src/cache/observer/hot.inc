; C6-only producer. Quota/boundary admission precedes PREPARE. The mutation
; suffix is nonfallible; COMMIT runs after source length/caret are updated.
.include "cache/observer/ring.inc"
bc_hot_prepare:
 jsr bc_reserve
 beq @done
 lda #BC_EVENT_SPLICE
 sta se_bc_ring+BC_E_KIND,y
 BC_STORE se_hot_caret,BC_E_POSITION,3
 BC_STORE se_r_revision,BC_E_REV_BEFORE,4
 BC_STORE se_doc_generation,BC_E_GEN_BEFORE,2
 lda se_hot_delete
 sta se_bc_ring+BC_E_DELETE,y
 eor #1
 sta se_bc_ring+BC_E_INSERT,y
@done:
 rts
