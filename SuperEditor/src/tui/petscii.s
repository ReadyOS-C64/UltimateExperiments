.setcpu "6502"
.export se_petscii_screen
.segment "CODE"
; A = native PETSCII, returns normal mixed-case screen code; controls show '?'.
se_petscii_screen:
    cmp #$20
    bcc @control
    cmp #$40
    bcc @done
    cmp #$60
    bcc @low
    cmp #$80
    bcc @alias
    cmp #$A0
    bcc @control
    cmp #$C0
    bcc @graphic
    cmp #$E0
    bcc @upper
    cmp #$FF
    beq @pi
@graphic:
    and #$3F
    ora #$60
    rts
@upper:
    and #$3F
    ora #$40
    rts
@alias:
    and #$1F
    ora #$40
    rts
@pi:
    lda #$5E
    rts
@low:
    and #$3F
@done:
    rts
@control:
    lda #$3F
    rts
