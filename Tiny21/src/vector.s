.setcpu "6502"
.importzp scale_shift, dot_columns
.import activation_lo, activation_hi, dot_prepare
.ifdef GROUP4_EXPERIMENT
    .import group4_ready
.endif
.import wide_a, wide_b, wide_product, wide_root
.import wide_multiply, wide_divide, wide_round_divide, wide_sqrt, wide_mul_byte
.export vector_source, vector_dest, vector_gains, vector_count
.export vector_add, vector_pack, vector_norm, vector_cache, vector_relu

; Packed signed Q16.16 vectors. Count zero encodes 256 elements.
.segment "ZEROPAGE"
vector_source: .res 2
vector_dest:   .res 2
vector_gains:  .res 2
source:        .res 2
dest:          .res 2
gains:         .res 2

.segment "BSS"
vector_count: .res 1
index:        .res 1
magnitude:    .res 4
peak:         .res 4
negative:     .res 1
energy:       .res 9

.segment "CODE"
.macro ADVANCE ptr, stride
    clc
    lda ptr
    adc #stride
    sta ptr
    bcc :+
    inc ptr+1
:
.endmacro

.proc reset_source
    lda vector_source
    sta source
    lda vector_source+1
    sta source+1
    lda #0
    sta index
    rts
.endproc

.proc reset_dest
    lda vector_dest
    sta dest
    lda vector_dest+1
    sta dest+1
    rts
.endproc

.proc load_magnitude
    ldy #3
    lda (source),y
    sta negative
    bmi negate
    .repeat 4
        lda (source),y
        sta magnitude,y
        dey
    .endrepeat
    rts
negate:
    ldy #0
    sec
    .repeat 4
        lda #0
        sbc (source),y
        sta magnitude,y
        iny
    .endrepeat
    rts
.endproc

; Add source to dest in place. Caller ensures the sums fit signed 32 bits.
.proc vector_add
    jsr reset_source
    jsr reset_dest
element:
    ldy #0
    clc
    .repeat 4
        lda (source),y
        adc (dest),y
        sta (dest),y
        iny
    .endrepeat
    ADVANCE source, 4
    ADVANCE dest, 4
    inc index
    lda index
    cmp vector_count
    bne element
    rts
.endproc

.proc find_peak
    jsr reset_source
    lda #0
    .repeat 4, I
        sta peak+I
    .endrepeat
scan:
    jsr load_magnitude
    ldx #3
compare:
    lda magnitude,x
    cmp peak,x
    bcc next
    bne larger
    dex
    bpl compare
    jmp next
larger:
    .repeat 4, I
        lda magnitude+I
        sta peak+I
    .endrepeat
next:
    ADVANCE source, 4
    inc index
    lda index
    cmp vector_count
    bne scan

    rts
.endproc

; Round by the smallest shared right shift that puts the largest absolute
; activation at or below 32767. Prepare the matching dot buffers once.
.proc vector_pack
    jsr find_peak
    lda #0
    sta scale_shift
    clc
choose:
    ; Save the last discarded bit for the check at an exact 32767.
    php
    lda peak+3
    ora peak+2
    bne shrink
    lda peak+1
    bmi shrink
    cmp #$7f
    bne fit
    lda peak
    cmp #$ff
    bne fit
    plp
    bcc chosen
    bcs shift_more
fit:
    plp
    jmp chosen
shrink:
    plp
shift_more:
    inc scale_shift
    lsr peak+3
    ror peak+2
    ror peak+1
    ror peak
    jmp choose
chosen:
    jsr reset_source
pack:
    jsr load_magnitude
    ldx scale_shift
    beq sign
shift:
    lsr magnitude+3
    ror magnitude+2
    ror magnitude+1
    ror magnitude
    dex
    bne shift
    bcc sign
    inc magnitude
    bne sign
    inc magnitude+1
sign:
    ldx index
    lda negative
    bmi pack_negative
    lda magnitude
    sta activation_lo,x
    lda magnitude+1
    sta activation_hi,x
    jmp stored
pack_negative:
    sec
    lda #0
    sbc magnitude
    sta activation_lo,x
    lda #0
    sbc magnitude+1
    sta activation_hi,x
stored:
    ADVANCE source, 4
    inc index
    lda index
    cmp vector_count
    bne pack
    sta dot_columns
.ifdef GROUP4_EXPERIMENT
    lda #0
    sta group4_ready
.endif
    jmp dot_prepare
.endproc

; Exact 96-channel RMS normalization with signed Q4.12 gains.
; dest may equal source. Carry reports an invalid count or arithmetic fault.
.proc vector_norm
    lda vector_count
    cmp #96
    beq start
    sec
    rts
start:
    jsr reset_source
    ; 96 * round(1e-5 * 2^32) = $003eea40.
    lda #<(96 * 42950)
    sta energy
    lda #>(96 * 42950)
    sta energy+1
    lda #^(96 * 42950)
    sta energy+2
    lda #0
    .repeat 6, I
        sta energy+3+I
    .endrepeat
sum:
    jsr load_magnitude
    .repeat 4, I
        lda magnitude+I
        sta wide_a+I
        sta wide_b+I
    .endrepeat
    lda #0
    .repeat 8, I
        sta wide_a+4+I
        sta wide_b+4+I
    .endrepeat
    jsr wide_multiply
    clc
    .repeat 9, I
        lda energy+I
        adc wide_product+I
        sta energy+I
    .endrepeat
    ADVANCE source, 4
    inc index
    lda index
    cmp #96
    beq mean
    jmp sum
mean:
    lda #0
    sta wide_a
    sta wide_a+1
    sta wide_a+11
    sta wide_b+1
    sta wide_b+2
    sta wide_b+3
    lda #96
    sta wide_b
    .repeat 9, I
        lda energy+I
        sta wide_a+2+I
    .endrepeat
    jsr wide_divide
    jsr wide_sqrt
    jsr reset_source
    jsr reset_dest
    lda vector_gains
    sta gains
    lda vector_gains+1
    sta gains+1

apply:
    jsr load_magnitude
    ldy #1
    lda (gains),y
    bmi negative_gain
    sta wide_b+1
    dey
    lda (gains),y
    sta wide_b
    jmp operands
negative_gain:
    eor #$ff
    sta wide_b+1
    lda negative
    eor #$80
    sta negative
    dey
    sec
    lda #0
    sbc (gains),y
    sta wide_b
    bcc operands
    inc wide_b+1
operands:
    lda #0
    ldx #11
clear:
    sta wide_b,x
    sta wide_a,x
    dex
    cpx #1
    bne clear
    sta wide_a+1
    sta wide_a
    .repeat 4, I
        lda magnitude+I
        sta wide_a+3+I
    .endrepeat
    jsr wide_multiply
    lda #0
    sta wide_b
    clc
    .repeat 6, I
        lda wide_root+I
        sta wide_b+1+I
    .endrepeat
    lda #0
    sta wide_b+7
    .repeat 4
        asl wide_b+1
        .repeat 6, I
            rol wide_b+2+I
        .endrepeat
    .endrepeat
    ldx #11
dividend:
    lda wide_product,x
    sta wide_a,x
    dex
    bpl dividend
    jsr wide_round_divide
    bcc store
    rts
store:
    ldy #0
    lda negative
    bmi store_negative
    .repeat 4, I
        lda wide_a+I
        sta (dest),y
        iny
    .endrepeat
    jmp applied
store_negative:
    sec
    .repeat 4, I
        lda #0
        sbc wide_a+I
        sta (dest),y
        iny
    .endrepeat
applied:
    ADVANCE source, 4
    ADVANCE dest, 4
    ADVANCE gains, 2
    inc index
    lda index
    cmp #96
    beq complete
    jmp apply
complete:
    clc
    rts
.endproc

; Encode a 96-element cache record at vector_dest. The first four bytes
; contain the unsigned Q16.16 peak. The next 96 contain signed bytes.
.proc vector_cache
    lda vector_count
    cmp #96
    beq start
    sec
    rts
start:
    jsr find_peak
    jsr reset_dest
    ldy #0
    .repeat 4, I
        lda peak+I
        sta (dest),y
        iny
    .endrepeat
    ADVANCE dest, 4
    lda peak
    ora peak+1
    ora peak+2
    ora peak+3
    bne prepare
    ldy #95
zero:
    sta (dest),y
    dey
    bpl zero
    clc
    rts
prepare:
    jsr reset_source
convert:
    jsr load_magnitude
    lda #0
    ldx #11
clear:
    sta wide_a,x
    sta wide_b,x
    dex
    bpl clear
    .repeat 4, I
        lda magnitude+I
        sta wide_a+I
    .endrepeat
    lda #127
    sta wide_b
    jsr wide_mul_byte
    .repeat 4, I
        lda peak+I
        sta wide_b+I
    .endrepeat
    ldx #11
copy_product:
    lda wide_product,x
    sta wide_a,x
    dex
    bpl copy_product
    jsr wide_round_divide
    bcs done
    lda negative
    bmi signed_negative
    lda wide_a
    jmp put
signed_negative:
    sec
    lda #0
    sbc wide_a
put:
    ldy index
    sta (dest),y
    ADVANCE source, 4
    inc index
    lda index
    cmp #96
    beq :+
    jmp convert
:
    clc
done:
    rts
.endproc


; Clamp negative packed elements to zero in place at vector_dest.
.proc vector_relu
    jsr reset_dest
    lda #0
    sta index
element:
    ldy #3
    lda (dest),y
    bpl next
    lda #0
    .repeat 4
        sta (dest),y
        dey
    .endrepeat
next:
    ADVANCE dest, 4
    inc index
    lda index
    cmp vector_count
    bne element
    rts
.endproc
