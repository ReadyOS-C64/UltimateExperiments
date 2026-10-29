; Private C24 TRY_SEED3. Exact typedFE read, real R14 lease, no BOF on miss.
.include "render/geos/semantic-checkpoint-candidate/codec.inc"
.import se_gc_handle,se_gc_epoch,se_gc_width,se_reu_retired
.import se_reu_logical_owner,se_reu_physical_owner,se_reu_map
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.import se_doc_invalidate,se_gsc_restore
.import se_sm_regions
.segment "GEOS_SEMANTIC"
gsc_try:
 lda #0
 sta F+GSEM_CP_VALID
 sta GSC_PROOF
 KEY_FIELDS capture
 jsr gsc_read
 bcs @miss
 jsr se_gsc_restore
 bcs @miss
 cmp #1
 bne @miss
 lda GSC_PROOF
 cmp #1
 bne @accepted
 lda GCC_VALID
 cmp #1
 bne @reject
 ldx #27
@published:
 lda GCC_KEY,x
 cmp GSC_CURRENT,x
 bne @reject
 dex
 bpl @published
@accepted:
 ; Save incoming state under current fullkey, distinct from post-event valid1.
 ldx #78
@state:
 lda se_sm_state,x
 sta F+GSEM_CP_STATE,x
 dex
 bpl @state
 COPY24 se_sm_pos,F+GSEM_CP_NEXT
 COPY24 se_sm_pos,GSC_INCOMING
 lda se_l_mode
 sta F+GSEM_CP_MODE
 lda #2
 sta F+GSEM_CP_VALID
 jmp @miss
@reject:
 lda #0
 sta GSC_PROOF
@miss:
 jsr cleanup
 jmp zero

gsc_read:
 lda se_gc_width
 cmp #$FF
 bne @bad
 lda se_reu_retired
 bne @bad
 ldx #1
@epoch:
 lda se_gc_epoch,x
 cmp se_reu_epoch,x
 bne @bad
 cmp GCC_EPOCH,x
 bne @bad
 dex
 bpl @epoch
 lda se_reu_epoch
 ora se_reu_epoch+1
 beq @bad
 lda se_gc_handle
 cmp GCC_HANDLE
 bne @bad
 tax
 beq @bad
 lda se_reu_logical_owner,x
 cmp #$FE
 bne @bad
 lda se_reu_map,x
 cmp GCC_PHYSICAL
 bne @bad
 tay
 beq @bad
 lda se_reu_physical_owner,y
 cmp #$FE
 bne @bad
 stx se_reu_logical
 jsr se_doc_invalidate
 lda #0
 sta se_reu_offset
 sta se_reu_c64
 sta se_reu_length+1
 lda #6
 sta se_reu_offset+1
 lda #>GSC_RECORD
 sta se_reu_c64+1
 lda #64
 sta se_reu_length
 lda #1
 jmp se_reu_copy
@bad:
 sec
 rts

; The producer copies these9B only when CAPTURED1 after successful real query.
; Capture is before classification: parser fields may change on this very CR.
gsc_incoming:
 COPY24 se_sm_state+20,GSC_INCOMING
 lda se_sm_fence
 sta GSC_INCOMING+3
 lda se_sm_language
 sta GSC_INCOMING+4
 lda se_sm_regions
 sta GSC_INCOMING+5
 COPY24 se_sm_state+76,GSC_INCOMING+6
 lda #1
 sta GSC_CAPTURED
 rts
