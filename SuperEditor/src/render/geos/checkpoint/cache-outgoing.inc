; Explicit verified retained-CR carry type, never a79-byte parser checkpoint.
; Entry after actual owner4, checked FE/source guard and sealed C24 capability.
; Carry9 was copied by C21 immediately after a complete checked query result.
; GP_HEADER is actual current guarded source; helper never aliases BCQP source.
.include "cache/query/proof-api.inc"
.include "cache/api.inc"
.import se_bc_flags,se_bc_count,se_bc_arena
.assert se_bc_ticket=se_bc_arena+5,lderror,"cache AUTH ticket adjacency"
.assert se_bc_incarnation=se_bc_arena+9,lderror,"cache AUTH incarnation adjacency"
gsc_cached_carry:
 lda se_bc_flags
 eor #(BC_ARMED|BCQ_PAGE_PROOF)
 and #($FF-BC_REBUILD_TRIED-BC_LEX_ATTEMPT) ;onlydefined optionalTRIEDbit isignored
 ora se_bc_count
 bne @miss
 jsr se_crc_init
 ldy #82
@crc:
 lda BCQP,y
 jsr se_crc_byte
 dey
 bpl @crc
 lda se_crc_value
 cmp BCQP_CRC
 bne @miss
 lda se_crc_value+1
 cmp BCQP_CRC+1
 bne @miss
 ldy #12
@auth:
 lda se_bc_arena,y
 cmp BCQP_AUTH,y
 bne @miss
 dey
 bpl @auth
 clc
 rts
@miss:
 sec
 rts
