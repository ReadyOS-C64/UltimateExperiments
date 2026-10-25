; C6-only producer. Called at MARK after quota admission and before revision
; changes. BACK has already moved left; DELETE/INSERT retain their exact caret.
; A/X/Y and the existing hot pointer loan are scratch. No DMA/source/history
; writes. The consumer must independently authenticate the full FE/source key.
.include "render/geos/edit-certificate.inc"
se_gec_capture:
    lda GEC_VALID
    beq @eligible
    ldx #1
@prior:
    lda GEC_SEQUENCE,x
    cmp se_e_draw_sequence,x
    bne @eligible
    dex
    bpl @prior
    ; A second mutation before publication cannot be represented by this ABI.
@reject:
    lda #0
    sta GEC_VALID
    rts
@eligible:
    lda #0
    sta GEC_VALID
    lda se_mode
    cmp #3
    jne @reject
    lda se_r_presentation
    ora se_e_ui
    ora se_sel_mark
    jne @reject
    lda GCC_VALID
    cmp #1
    jne @reject
    ldx #1
@published:
    lda GCC_SEQUENCE,x
    cmp se_e_draw_sequence,x
    jne @reject
    lda GCC_EPOCH,x
    cmp se_reu_epoch,x
    jne @reject
    dex
    bpl @published
    ldx #3
@revision:
    lda GCC_KEY+17,x
    cmp se_r_revision,x
    jne @reject
    sta GEC_REVISION,x
    dex
    bpl @revision
    ldx #14
@tokens:
    lda GCC_KEY,x
    cmp se_doc_meta,x
    jne @reject
    dex
    bpl @tokens
    ldx #1
@generation:
    lda GCC_KEY+15,x
    cmp se_doc_generation,x
    jne @reject
    lda GCC_KEY+26,x
    cmp se_doc_epoch,x
    jne @reject
    sta GEC_DOC_EPOCH,x
    lda se_reu_epoch,x
    sta GEC_REU_EPOCH,x
    lda se_e_draw_sequence,x
    sta GEC_SEQUENCE,x
    dex
    bpl @generation
    ldx #2
@length:
    lda GCC_KEY+21,x
    cmp se_v_length,x
    jne @reject
    sta GEC_LENGTH,x
    lda se_hot_caret,x
    sta GEC_POSITION,x
    dex
    bpl @length
    lda se_hot_delete
    sta GEC_OP
    beq @insert
    lda se_hot_right
    sta se_hot_ptr
    lda se_hot_right+1
    clc
    adc #>HOT_FIRST
    sta se_hot_ptr+1
    ldy #0
    lda (se_hot_ptr),y
    sta GEC_OLD
    lda #0
    sta GEC_NEW
    beq @publish
@insert:
    lda #0
    sta GEC_OLD
    lda se_hot_byte
    sta GEC_NEW
@publish:
    lda #1
    sta GEC_VALID
    rts
