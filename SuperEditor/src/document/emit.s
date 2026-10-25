.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.include "document/splice.inc"
.include "document/math24.inc"
.include "document/frames/emit.inc"
.ifndef ENGINE_STATE_ONLY
.segment "CODE"
doc_emit_reset:
    lda #0
    sta emit_root_count
    sta emit_records
    sta emit_total
    sta emit_total+1
    sta emit_total+2
    sta pending+6
    sta pending+7
    sta pending+8
    ldx #7
@bits:
    sta emit_used,x
    dex
    bpl @bits
    ldx #0
@roots:
    sta se_doc_next_roots,x
    inx
    bne @roots
    lda #0
    sta emit_scan
@active:
    lda emit_scan
    cmp se_doc_root_count
    bcs @ready
    asl
    asl
    asl
    tay
    lda se_doc_roots,y
    jsr claim_slot
    bcs @return
    inc emit_scan
    jmp @active
@ready:
    jsr clear_leaf
    clc
@return:
    rts
; Input se_doc_emit. Delay one record so adjacent source runs coalesce even
; across output leaf boundaries. Newline fields are invalidated explicitly.
doc_emit_piece:
    lda se_doc_emit+6
    ora se_doc_emit+7
    ora se_doc_emit+8
    jeq @ok
    lda pending+6
    ora pending+7
    ora pending+8
    beq @pending
    ldx #2
@identity:
    lda se_doc_emit,x
    cmp pending,x
    bne @separate
    dex
    bpl @identity
    ADD24 pending+3,pending+6,emit_end
    bcs @corrupt
    CMP24 emit_end,se_doc_emit+3
    bne @separate
    ADD24 pending+6,se_doc_emit+6,pending+6
    bcs @corrupt
    clc
    rts
@separate:
    jsr flush_pending
    bcs @return
@pending:
    ldx #15
@copy:
    lda se_doc_emit,x
    sta pending,x
    dex
    bpl @copy
    lda #$FF
    sta pending+9
    sta pending+10
    sta pending+11
@ok:
    clc
@return:
    rts
@corrupt:
    lda #$42
    sec
    rts

doc_emit_finish:
    lda pending+6
    ora pending+7
    ora pending+8
    beq @tail
    jsr flush_pending
    bcs @return
    lda #0
    sta pending+6
    sta pending+7
    sta pending+8
@tail:
    lda emit_records
    jeq @ok
    jmp flush_leaf
@ok:
    clc
@return:
    rts

; X=old root. Seal any newly built leaf, then retain this immutable active
; leaf by copying only its8-byte root. Active slots were reserved at reset.
doc_emit_reuse_root:
    stx emit_scan
    jsr doc_emit_finish
    bcs @return
    lda emit_root_count
    cmp #DOC_ROOTS
    jcs full
    asl
    asl
    asl
    tax
    lda emit_scan
    asl
    asl
    asl
    tay
    .repeat 8,N
        lda se_doc_roots+N,y
        sta se_doc_next_roots+N,x
    .endrepeat
    .repeat 3,N
        lda se_doc_roots+2+N,y
        sta emit_end+N
    .endrepeat
    ADD24 emit_total,emit_end,emit_total
    bcs @corrupt
    inc emit_root_count
    clc
@return:
    rts
@corrupt:
    lda #$42
    sec
    rts

flush_pending:
    lda emit_root_count
    cmp #DOC_ROOTS
    jcs full
    lda emit_records
    asl
    asl
    asl
    asl
    sta emit_ptr
    lda emit_records
    lsr
    lsr
    lsr
    lsr
    clc
    adc #>DOC_BUILD
    sta emit_ptr+1
    ldy #15
@record:
    lda pending,y
    sta (emit_ptr),y
    dey
    bpl @record
    ADD24 emit_leaf_sum,pending+6,emit_leaf_sum
    bcs @corrupt
    ADD24 emit_total,pending+6,emit_total
    bcs @corrupt
    inc emit_records
    lda emit_records
    cmp #64
    beq flush_leaf
    clc
    rts
@corrupt:
    lda #$42
    sec
    rts

flush_leaf:
    lda emit_root_count
    cmp #DOC_ROOTS
    jcs full
    lda #0
    sta emit_slot
@find:
    lda emit_slot
    and #7
    tax
    lda bit_masks,x
    sta emit_mask
    lda emit_slot
    lsr
    lsr
    lsr
    tax
    lda emit_used,x
    and emit_mask
    beq @free
    inc emit_slot
    lda emit_slot
    cmp #64
    bcc @find
    jcs full
@free:
    lda emit_used,x
    ora emit_mask
    sta emit_used,x
    DOC_TOKEN se_doc_meta
    lda #0
    sta se_object_offset
    sta se_object_offset+2
    sta se_object_c64
    sta se_object_length
    lda emit_slot
    asl
    asl
    sta se_object_offset+1
    lda #>DOC_BUILD
    sta se_object_c64+1
    lda #4
    sta se_object_length+1
    lda #0
    jsr se_object_copy
    bcs @return
    lda emit_root_count
    asl
    asl
    asl
    tay
    lda emit_slot
    sta se_doc_next_roots,y
    lda emit_records
    sta se_doc_next_roots+1,y
    .repeat 3,N
        lda emit_leaf_sum+N
        sta se_doc_next_roots+2+N,y
    .endrepeat
    lda #$FF
    sta se_doc_next_roots+5,y
    sta se_doc_next_roots+6,y
    sta se_doc_next_roots+7,y
    inc emit_root_count
    jsr clear_leaf
    clc
@return:
    rts
full:
    lda #$43
    sec
    rts
clear_leaf:
    lda #0
    sta emit_records
    sta emit_leaf_sum
    sta emit_leaf_sum+1
    sta emit_leaf_sum+2
    ldx #0
@clear:
    .repeat 4,N
        sta DOC_BUILD+N*$100,x
    .endrepeat
    inx
    bne @clear
    rts
claim_slot:
    cmp #64
    bcs @corrupt
    pha
    and #7
    tax
    lda bit_masks,x
    sta emit_mask
    pla
    lsr
    lsr
    lsr
    tax
    lda emit_used,x
    and emit_mask
    bne @corrupt
    lda emit_used,x
    ora emit_mask
    sta emit_used,x
    clc
    rts
@corrupt:
    lda #$42
    sec
    rts
.segment "RODATA"
bit_masks: .byte 1,2,4,8,16,32,64,128

.endif
