.setcpu "6502"
.import se_input_head, se_input_tail, se_input_chars, se_input_mods, se_input_matrix
.import se_input_nmi_pending
.export se_input_get
.segment "CODE"
; A = native byte, X = modifier flags, Y = physical matrix identity ($40 none).
; Zero A means no event. IRQ publishes head last; main publishes tail last.
se_input_get:
    lda se_input_nmi_pending
    beq @queue
    lda #0
    sta se_input_nmi_pending
    ldx #0
    ldy #$40
    lda #3
    rts
@queue:
    ldx se_input_tail
    cpx se_input_head
    beq @empty
    lda se_input_chars,x
    pha
    lda se_input_mods,x
    pha
    lda se_input_matrix,x
    tay
    inx
    txa
    and #63
    sta se_input_tail
    pla
    tax
    pla
    rts
@empty:
    ldx #0
    ldy #$40
    lda #0
    rts
