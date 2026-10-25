.setcpu "6502"
.export se_input_init, se_input_restore, se_input_irq, se_input_nmi
.export se_input_head, se_input_tail, se_input_chars, se_input_mods, se_input_matrix
.export se_input_nmi_pending, se_input_irq_ticks, se_input_backpressure

.segment "BSS"
se_input_head: .res 1
se_input_tail: .res 1
se_input_chars: .res 64
se_input_mods: .res 64
se_input_matrix: .res 64
se_input_nmi_pending: .res 1
se_input_irq_ticks: .res 2
se_input_backpressure: .res 1
input_old_irq: .res 2
input_old_nmi: .res 2
input_old_repeat: .res 1

.segment "CODE"
; Caller masks IRQ. Uses normal ROM SCNKEY tables, then latches modifiers with
; the character on that same scan. It still consumes the standard KERNAL FIFO
; so the established automation route is compatible and separately identifiable.
se_input_init:
    lda $0314
    sta input_old_irq
    lda $0315
    sta input_old_irq+1
    lda $0318
    sta input_old_nmi
    lda $0319
    sta input_old_nmi+1
    lda $028A
    sta input_old_repeat
    lda #$80
    sta $028A ; native repeat for editor keys
    lda #<se_input_irq
    sta $0314
    lda #>se_input_irq
    sta $0315
    lda #<se_input_nmi
    sta $0318
    lda #>se_input_nmi
    sta $0319
    lda #0
    sta $D01A
    lda #$0F
    sta $D019
    rts

se_input_restore:
    php
    sei
    lda input_old_irq
    sta $0314
    lda input_old_irq+1
    sta $0315
    lda input_old_nmi
    sta $0318
    lda input_old_nmi+1
    sta $0319
    lda input_old_repeat
    sta $028A
    plp
    rts

; KERNAL IRQ dispatcher already stacked A/X/Y. All helpers are resident.
; No REU, overlays, app ZP or document state is touched here.
se_input_irq:
    cld
    jsr $FFEA ; UDTIM
    jsr $FF9F ; SCNKEY, including native modifier detection and repeat
    inc se_input_irq_ticks
    bne @drain
    inc se_input_irq_ticks+1
@drain:
    lda $C6
    beq @exit
    lda se_input_head
    clc
    adc #1
    and #63
    cmp se_input_tail
    beq @full
    ldx se_input_head
    lda $0277
    sta se_input_chars,x
    lda $028D
    sta se_input_mods,x
    lda $CB
    sta se_input_matrix,x
    inx
    txa
    and #63
    sta se_input_head ; publish only after all event fields are present
    ldx #0
@shift:
    lda $0278,x
    sta $0277,x
    inx
    cpx #9
    bcc @shift
    dec $C6
    jmp @drain
@full:
    inc se_input_backpressure ; leave KERNAL bytes pending; no overwrite
@exit:
    lda $DC0D
    jmp $EA81 ; verified ROM restore-Y/X/A + RTI sequence

; KERNAL NMI vector arrives with registers unstacked. RESTORE becomes a pending
; cancel event, never a ROM jump into BASIC. No shared ring write races with IRQ.
se_input_nmi:
    pha
    txa
    pha
    tya
    pha
    lda $DD0D
    lda #1
    sta se_input_nmi_pending
    pla
    tay
    pla
    tax
    pla
    rti
