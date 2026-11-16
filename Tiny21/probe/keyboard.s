.setcpu "6502"
.export keyboard_init, keyboard_input, keyboard_stop

PORT_A = $dc00
PORT_B = $dc01
DIR_A = $dc02
DIR_B = $dc03
RUN_STOP = 3
SHIFT_KEY = 1

.segment "PROBEBSS"
matrix_column: .res 1
matrix_bits: .res 1
shift_down: .res 1
matrix_key: .res 1
previous_sample: .res 1
reported_sample: .res 1

.segment "PROBE"
.proc keyboard_init
    lda #0
    sta DIR_A
    sta DIR_B
    sta PORT_A
    lda #$ff
    sta previous_sample
    sta reported_sample
    rts
.endproc

; With all other columns left as inputs, only the selected pin drives low.
; Return Z clear when RUN/STOP (PA7/PB7) is held.
.proc keyboard_stop
    lda #$80
    sta DIR_A
    lda PORT_B
    ldx #0
    stx DIR_A
    eor #$ff
    and #$80
    rts
.endproc

; Call once per frame. Emit a single character after two matching samples.
; Modifier keys can coexist with one printable/editing key.
.proc keyboard_input
    jsr scan_matrix
    cmp previous_sample
    beq stable
    sta previous_sample
    lda #0
    rts
stable:
    cmp reported_sample
    beq repeat_key
    sta reported_sample
    cmp #$ff
    bne key
repeat_key:
    lda #0
key:
    rts
.endproc

.proc scan_matrix
    lda #0
    sta shift_down
    sta matrix_column
    lda #$ff
    sta matrix_key
column:
    ldx matrix_column
    lda driven_bit,x
    sta DIR_A
    lda PORT_B
    eor #$ff
    sta matrix_bits
    txa
    asl
    asl
    asl
    tax
    ldy #8
row:
    lsr matrix_bits
    bcc next
    lda plain,x
    beq next
    cmp #SHIFT_KEY
    beq modifier
    lda matrix_key
    cmp #$ff
    bne ambiguous
    stx matrix_key
    jmp next
modifier:
    inc shift_down
next:
    inx
    dey
    bne row
    inc matrix_column
    lda matrix_column
    cmp #8
    bne column
    lda #0
    sta DIR_A
    ldx matrix_key
    bmi no_key
    lda shift_down
    beq unshifted
    lda shifted,x
    rts
unshifted:
    lda plain,x
    rts
ambiguous:
    lda #0
    sta DIR_A
no_key:
    lda #$ff
    rts
.endproc

driven_bit:
    .byte $01,$02,$04,$08,$10,$20,$40,$80
; Columns PA0 through PA7, rows PB0 through PB7 within each column.
plain:
    .byte 8,13,0,0,0,0,0,0
    .byte "3wa4zse",SHIFT_KEY
    .byte "5rd6cftx"
    .byte "7yg8bhuv"
    .byte "9ij0mkon"
    .byte "+pl-.:@,"
    .byte 0,"*;",0,SHIFT_KEY,"=^/"
    .byte "1",0,0,"2 ",0,"q",RUN_STOP
shifted:
    .byte 8,13,0,0,0,0,0,0
    .byte "#WA$ZSE",SHIFT_KEY
    .byte "%RD&CFTX"
    .byte "'YG(BHUV"
    .byte ")IJ0MKON"
    .byte "+PL_>:@<"
    .byte 0,"*;",0,SHIFT_KEY,"=^?"
    .byte "!",0,0,$22," ",0,"Q",RUN_STOP
.assert shifted-plain = 64, error, "keyboard table width"
.assert *-shifted = 64, error, "shifted keyboard table width"
