; Linked into mutation images, never called through an extra per-key overlay.
.include "cache/api.inc"
.global se_crc_init,se_crc_byte,se_crc_value
.macro BC_STORE source,offset,count
.if count>2
 tya
 pha
 clc
 adc #(offset+count-1)
 tay
 ldx #(count-1)
:
 lda source,x
 sta se_bc_ring,y
 dey
 dex
 bpl :-
 pla
 tay
.else
.repeat count,I
 lda source+I
 sta se_bc_ring+offset+I,y
.endrepeat
.endif
.endmacro
bc_index:
 lda se_bc_head
 asl
 asl
 asl
 asl
 asl
 tay
 rts
bc_lost:
 lda se_bc_flags
 and #($FF-BC_ARMED-BC_MUTATING)
 ora #BC_LOST
 sta se_bc_flags
bc_none:
 lda #0
 clc
 rts
; A1 reserved/Y=slot start, A0 disabled/lost. No canonical failure is returned.
bc_reserve:
 lda se_bc_flags
 and #BC_MUTATING
 bne bc_lost ; unexpected nested/abandoned producer cannot certify a chain
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING)
 cmp #BC_ARMED
 bne bc_none
 lda se_bc_head
 cmp #BC_RING_LIMIT
 bcs bc_lost
 lda se_bc_tail
 cmp #BC_RING_LIMIT
 bcs bc_lost
 lda se_bc_count
 cmp #BC_RING_LIMIT
 bcs bc_lost
 jsr bc_index
 ldx #BC_EVENT_SIZE
 lda #0
@clear:
 sta se_bc_ring,y
 iny
 dex
 bne @clear
 jsr bc_index
 lda se_bc_flags
 ora #BC_MUTATING
 sta se_bc_flags
 lda #1
 rts
; Commit only after the authoritative successful publication. Marker/count
; publish last. CRC covers1..28 and31, excludingmarker0 anditsown29/30.
bc_commit:
 lda se_bc_flags
 and #BC_MUTATING
 beq bc_none
 lda se_bc_head
 cmp #BC_RING_LIMIT
 bcs bc_lost
 lda se_bc_tail
 cmp #BC_RING_LIMIT
 bcs bc_lost
 lda se_bc_count
 cmp #BC_RING_LIMIT
 bcs bc_lost
 jsr bc_index
 lda se_bc_ring+BC_E_KIND,y
 cmp #BC_EVENT_SPLICE
 bne @ticket
 inc se_bc_ticket
 bne @ticket
 inc se_bc_ticket+1
 bne @ticket
 inc se_bc_ticket+2
 bne @ticket
 inc se_bc_ticket+3
 jeq bc_lost
@ticket:
 BC_STORE se_bc_ticket,BC_E_TICKET,4
 BC_STORE se_r_revision,BC_E_REV_AFTER,4
 BC_STORE se_doc_generation,BC_E_GEN_AFTER,2
 jsr se_crc_init
 jsr bc_index
 iny
@crc:
 lda se_bc_ring,y
 jsr se_crc_byte
 iny
 tya
 and #31
 cmp #BC_E_CRC
 bcc @crc
 lda #0 ;reserved31 iszero
 jsr se_crc_byte
 jsr bc_index
 lda se_crc_value
 sta se_bc_ring+BC_E_CRC,y
 lda se_crc_value+1
 sta se_bc_ring+BC_E_CRC+1,y
 lda #BC_EVENT_VALID
 sta se_bc_ring+BC_E_MARK,y
 inc se_bc_head
 lda se_bc_head
 cmp #BC_RING_LIMIT
 bcc :+
 lda #0
 sta se_bc_head
:
 inc se_bc_count
 lda se_bc_flags
 and #($FF-BC_MUTATING)
 sta se_bc_flags
 jmp bc_none
