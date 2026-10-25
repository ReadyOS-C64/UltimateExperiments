.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.include "document/math24.inc"
.segment "DOCSTATE"
piece_end: .res 3
.segment "CODE"
se_doc_piece_validate:
    lda se_doc_walk_piece+6
    ora se_doc_walk_piece+7
    ora se_doc_walk_piece+8
    beq @corrupt
    lda se_doc_walk_piece+12
    ora se_doc_walk_piece+13
    ora se_doc_walk_piece+14
    ora se_doc_walk_piece+15
    bne @corrupt
    lda se_doc_walk_piece
    cmp se_doc_original
    beq @source
    cmp se_doc_append
    bne @corrupt
@source:
    sta se_object_id
    lda se_doc_walk_piece+1
    sta se_object_generation
    lda se_doc_walk_piece+2
    sta se_object_generation+1
    lda se_doc_epoch
    sta se_object_token_epoch
    lda se_doc_epoch+1
    sta se_object_token_epoch+1
    jsr se_object_validate
    bcs @return
    ADD24 se_doc_walk_piece+3,se_doc_walk_piece+6,piece_end
    bcs @corrupt
    lda piece_end+2
    cmp object_size_hi,x
    bcc @range_ok
    bne @corrupt
    lda piece_end+1
    cmp object_size_mid,x
    bcc @range_ok
    bne @corrupt
    lda piece_end
    cmp object_size_lo,x
    bcc @range_ok
    bne @corrupt
@range_ok:
    lda #0
    clc
@return:
    rts
@corrupt:
    lda #$42
    sec
    rts
