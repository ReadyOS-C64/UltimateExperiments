.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.export doc_cache_slot, doc_cache_generation
.segment "DOCSTATE"
doc_cache_slot: .res 1
doc_cache_generation: .res 2
leaf_requested: .res 1
.segment "CODE"
se_doc_validate:
    jsr object_service_valid
    bcs @return
    lda se_doc_epoch
    cmp se_object_epoch
    bne @state
    lda se_doc_epoch+1
    cmp se_object_epoch+1
    bne @state
    lda se_doc_ready
    cmp #1
    bne @state
    lda se_doc_root_count
    cmp #DOC_ROOTS+1
    bcs corrupt
    lda #0
    clc
@return:
    rts
@state:
    lda #$40
    sec
    rts
se_doc_invalidate:
    lda #$FF
    sta doc_cache_slot
    rts
corrupt:
    lda #$42
    sec
    rts


; X metadata slot. Shared by byte-reader and piece walker; either may evict it
; between transaction steps. No caller keeps a pointer to an evictable leaf.
se_doc_leaf_load:
    cpx #64
    bcs corrupt
    stx leaf_requested
    txa
    cmp doc_cache_slot
    bne @load
    lda doc_cache_generation
    cmp se_doc_generation
    bne @load
    lda doc_cache_generation+1
    cmp se_doc_generation+1
    beq @ok
@load:
    DOC_TOKEN se_doc_meta
    lda #0
    sta se_object_offset
    sta se_object_offset+2
    sta se_object_length
    sta se_object_c64
    lda leaf_requested
    asl
    asl
    sta se_object_offset+1
    lda #4
    sta se_object_length+1
    lda #>DOC_LEAF
    sta se_object_c64+1
    lda #1
    jsr se_object_copy
    bcs @return
    lda leaf_requested
    sta doc_cache_slot
    lda se_doc_generation
    sta doc_cache_generation
    lda se_doc_generation+1
    sta doc_cache_generation+1
@ok:
    lda #0
    clc
@return:
    rts
