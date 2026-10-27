; C6-only producer. Called at MARK after quota admission and before revision
; changes. BACK has already moved left; DELETE/INSERT retain their exact caret.
; A/X/Y and the existing hot pointer loan are scratch. No DMA/source/history
; writes. The consumer must independently authenticate its source/publication key.
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
    lda se_r_presentation
    ora se_e_ui
    ora se_sel_mark
    jne @reject
    lda se_mode
    cmp #3
    beq @geos
    jcs @reject
    ; The fixed-grid certificate is captured from the last completely
    ; published resident layout.  R25 will independently authenticate LRV3;
    ; this gate only proves that the pre-edit resident context is current.
    lda se_e_redraw
    ora se_l_need_wrap
    jne @reject
    lda se_l_valid
    cmp #1
    jne @reject
    ldx #9
@grid_tokens:
    lda se_doc_original,x
    cmp se_l_original,x
    jne @reject
    dex
    bpl @grid_tokens
    ldx #1
@grid_generation:
    lda se_doc_generation,x
    cmp se_l_generation,x
    jne @reject
    dex
    bpl @grid_generation
    ldx #3
@grid_revision:
    lda se_r_revision,x
    cmp se_l_revision,x
    jne @reject
    dex
    bpl @grid_revision
    jmp @capture
@geos:
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
    dex
    bpl @generation
    ldx #2
@geos_length:
    lda GCC_KEY+21,x
    cmp se_v_length,x
    jne @reject
    dex
    bpl @geos_length
@capture:
    ldx #3
@capture_revision:
    lda se_r_revision,x
    sta GEC_REVISION,x
    dex
    bpl @capture_revision
    ldx #1
@capture_epochs:
    lda se_doc_epoch,x
    sta GEC_DOC_EPOCH,x
    lda se_reu_epoch,x
    sta GEC_REU_EPOCH,x
    lda se_e_draw_sequence,x
    sta GEC_SEQUENCE,x
    dex
    bpl @capture_epochs
    ldx #2
@length:
    lda se_v_length,x
    sta GEC_LENGTH,x
    lda se_hot_caret,x
    sta GEC_POSITION,x
    dex
    bpl @length
    lda se_hot_delete
    sta GEC_OP
    ldx se_mode
    cpx #3
    beq @classify
    cmp #2
    jcs @reject
@classify:
    tax
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
    beq @value
@insert:
    lda #0
    sta GEC_OLD
    lda se_hot_byte
    sta GEC_NEW
@value:
    ldx se_mode
    cpx #3
    beq @publish
    lda GEC_OLD
    cmp #$0D
    jeq @reject
    lda GEC_NEW
    cmp #$0D
    jeq @reject
@publish:
    lda #1
    sta GEC_VALID
    rts
