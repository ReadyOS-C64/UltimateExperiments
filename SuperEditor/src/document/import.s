.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.segment "CODE"
; Initial import finalizer only. Caller has written source_length initialized
; original bytes through the object API; no live document may be replaced here.
se_doc_adopt_original:
    jsr se_doc_validate
    jcs @return
    lda se_doc_busy
    ora se_doc_read_locks
    jne @busy
    lda se_doc_root_count
    ora se_doc_length
    ora se_doc_length+1
    ora se_doc_length+2
    jne @state
    lda se_doc_generation
    cmp #1
    jne @state
    lda se_doc_generation+1
    jne @state
    ; Validate capacity before staging any metadata. Resize only after stash.
    DOC_TOKEN se_doc_original
    jsr se_object_validate
    jcs @return
    lda se_doc_source_length+2
    cmp object_banks,x
    bcc @capacity
    jne @range
    lda se_doc_source_length
    ora se_doc_source_length+1
    jne @range
@capacity:
    lda se_doc_source_length
    ora se_doc_source_length+1
    ora se_doc_source_length+2
    beq @empty
    ldx #0
    lda #0
@clear:
    .repeat 4,P
        sta DOC_LEAF+P*$100,x
    .endrepeat
    inx
    bne @clear
    lda se_doc_original
    sta DOC_LEAF
    lda se_doc_original+1
    sta DOC_LEAF+1
    lda se_doc_original+2
    sta DOC_LEAF+2
    ldx #2
@size:
    lda se_doc_source_length,x
    sta DOC_LEAF+6,x
    dex
    bpl @size
    lda #$FF
    sta DOC_LEAF+9
    sta DOC_LEAF+10
    sta DOC_LEAF+11
    DOC_TOKEN se_doc_meta
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    sta se_object_offset+2
    sta se_object_c64
    sta se_object_length
    lda #>DOC_LEAF
    sta se_object_c64+1
    lda #4
    sta se_object_length+1
    lda #0
    jsr se_object_copy
    bcs @return
@empty:
    DOC_TOKEN se_doc_original
    ldx #2
@length:
    lda se_doc_source_length,x
    sta se_object_offset,x
    dex
    bpl @length
    jsr se_object_resize
    bcs @return
    ldx #2
@publish:
    lda se_doc_source_length,x
    sta se_doc_length,x
    sta se_doc_roots+2,x
    dex
    bpl @publish
    lda se_doc_length
    ora se_doc_length+1
    ora se_doc_length+2
    beq @published
    lda #0
    sta se_doc_roots
    lda #1
    sta se_doc_roots+1
    sta se_doc_root_count
    lda #$FF
    sta se_doc_roots+5
    sta se_doc_roots+6
    sta se_doc_roots+7
@published:
    inc se_doc_generation
    jsr se_doc_invalidate
    lda #0
    clc
@return:
    rts
@state:
    lda #$40
    sec
    rts
@range:
    lda #$32
    sec
    rts
@busy:
    lda #$41
    sec
    rts
