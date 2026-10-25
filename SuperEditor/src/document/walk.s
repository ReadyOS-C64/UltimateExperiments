.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.include "document/math24.inc"
.export walk_root, walk_record, walk_total
.segment "ZEROPAGE"
walk_ptr: .res 2
.segment "DOCSTATE"
se_doc_walk_piece: .res 16
walk_root: .res 1
walk_record: .res 1
walk_generation: .res 2
walk_sum: .res 3
walk_total: .res 3
walk_expected: .res 3
.segment "CODE"
; Private single foreground iterator. Reads may evict the leaf between calls.
se_doc_walk_reset:
    lda #0
    sta walk_root
    sta walk_record
    .repeat 3,N
        sta walk_sum+N
        sta walk_total+N
    .endrepeat
    lda se_doc_generation
    sta walk_generation
    lda se_doc_generation+1
    sta walk_generation+1
    rts
; A1/Cclear=record copied, A0/Cset=EOF, Anonzero/Cset=error.
; Validates source lifetime/range, nonzero lengths, reserved fields and sums.
se_doc_walk_next:
    jsr se_doc_validate
    jcs @return
    lda se_doc_generation
    cmp walk_generation
    jne @state
    lda se_doc_generation+1
    cmp walk_generation+1
    jne @state
    lda walk_root
    cmp se_doc_root_count
    bcc @root
    CMP24 walk_total,se_doc_length
    jne @corrupt
    lda #0
    sec
    rts
@root:
    lda walk_root
    asl
    asl
    asl
    tay
    lda se_doc_roots+1,y
    jeq @corrupt
    cmp #65
    jcs @corrupt
    lda se_doc_roots,y
    tax
    jsr se_doc_leaf_load
    jcs @return
    lda walk_record
    asl
    asl
    asl
    asl
    sta walk_ptr
    lda walk_record
    lsr
    lsr
    lsr
    lsr
    clc
    adc #>DOC_LEAF
    sta walk_ptr+1
    ldy #15
@copy:
    lda (walk_ptr),y
    sta se_doc_walk_piece,y
    dey
    bpl @copy
    jsr se_doc_piece_validate
    jcs @return
    ADD24 walk_sum,se_doc_walk_piece+6,walk_sum
    bcs @corrupt
    ADD24 walk_total,se_doc_walk_piece+6,walk_total
    bcs @corrupt
    inc walk_record
    lda walk_root
    asl
    asl
    asl
    tay
    lda walk_record
    cmp se_doc_roots+1,y
    bcc @piece
    .repeat 3,N
        lda se_doc_roots+2+N,y
        sta walk_expected+N
    .endrepeat
    CMP24 walk_sum,walk_expected
    bne @corrupt
    lda #0
    sta walk_record
    sta walk_sum
    sta walk_sum+1
    sta walk_sum+2
    inc walk_root
@piece:
    lda #1
    clc
@return:
    rts
@corrupt:
    lda #$42
    sec
    rts
@state:
    lda #$40
    sec
    rts
