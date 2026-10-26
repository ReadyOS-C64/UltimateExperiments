; NEW private one-viewport CR page proof. This RAM certificate may survive only
; C20/C25/C26 read-only GSEM lifetimes. Parent clears bit32 on freshviewport,
; legacyC24/painter transition and BEFORE any checked typed53 CPU→REU write.
.include "cache/query/api.inc"
.include "cache/arena/api.inc"
.include "render/geos/semantic.inc"
.include "cache/query/proof-api.inc"
.ifdef BCQ_PROOF_RESTORE
bcq_restore_page:
 lda se_bc_flags
 and #BCQ_PAGE_PROOF
 jeq @miss
 jsr se_crc_init
 ldy #82
@crc:lda BCQP,y
 jsr se_crc_byte
 dey
 bpl @crc
 lda se_crc_value
 cmp BCQP_CRC
 bne @miss
 lda se_crc_value+1
 cmp BCQP_CRC+1
 bne @miss
 lda BQ_CLASS
 cmp #1
 bne @miss
 lda BCQP_CACHE+3
 cmp #1
 bne @miss
 lda BQ_REF
 cmp BCQP_CACHE
 bne @miss
 ldy #1
@gen:lda BQ_REF+2,y
 cmp BCQP_CACHE+1,y
 bne @miss
 dey
 bpl @gen
 ldy #58
@source:lda BQ_SOURCE,y
 cmp BCQP_SOURCE,y
 bne @miss
 dey
 bpl @source
 ldy #12
@auth:lda BQ_AUTH,y
 cmp BCQP_AUTH,y
 bne @miss
 dey
 bpl @auth
 ldy #3
@request:lda BCA_PAGE,y
 sta BCA_TEMP+4,y
 dey
 bpl @request
 ldy #1
@used:lda BCQP_USED,y
 sta BCA_USED,y
 dey
 bpl @used
 ldy #4
@links:lda BCQP_NEXT,y
 sta BQ_PAGE_NEXT,y
 dey
 bpl @links
 ldy #3
@cache:lda BCQP_CACHE,y
 sta BQ_CACHE,y
 dey
 bpl @cache
 lda #$A5
 sta BCA_PROOF
 clc
 rts
@miss:sec
 rts
.endif
.ifdef BCQ_PROOF_CAPTURE
; Called by newC21hook only after queryA0 withERROR0, before any otherphasejob.
; No fakeparser checkpoint; source59 and request13 come fromactualquery.
; Cclear means an85Bcertificate was committed; Cset means no new certificate.
; Revoke immediately after admissionbit check; publishVALID last withoutDMA/yield.
bcq_capture_page:
 lda se_bc_flags
 and #BCQ_PAGE_PROOF
 beq @miss
 lda se_bc_flags
 and #($FF-BCQ_PAGE_PROOF)
 sta se_bc_flags
 lda GSEM_FRAME+GSEM_ERROR
 ora BQ_STATE
 ora BQ_LIVE
 bne @miss
 lda BQ_PROOF_VALID
 cmp #$A5
 bne @miss
 lda BQ_CACHE+3
 cmp #1
 bne @miss
 ldy #58
@source:lda BQ_SOURCE,y
 sta BCQP_SOURCE,y
 dey
 bpl @source
 ldy #12
@auth:lda BQ_AUTH,y
 sta BCQP_AUTH,y
 dey
 bpl @auth
 ldy #3
@cache:lda BQ_CACHE,y
 sta BCQP_CACHE,y
 dey
 bpl @cache
 ldy #1
@used:lda BCA_USED,y
 sta BCQP_USED,y
 dey
 bpl @used
 ldy #4
@links:lda BQ_PAGE_NEXT,y
 sta BCQP_NEXT,y
 dey
 bpl @links
 jsr se_crc_init
 ldy #82
@crc:lda BCQP,y
 jsr se_crc_byte
 dey
 bpl @crc
 lda se_crc_value
 sta BCQP_CRC
 lda se_crc_value+1
 sta BCQP_CRC+1
 lda se_bc_flags
 ora #BCQ_PAGE_PROOF
 sta se_bc_flags
 clc
 rts
@miss:sec
 rts
.endif
