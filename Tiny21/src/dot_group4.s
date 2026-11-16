.setcpu "6502"
.macpack longbranch
.import activation_lo, activation_hi
.importzp dot_columns, dot_weights, dot_result
.export group4_prepare, group4_dot
.export group4_ready, group4_tile

; The mixed packed build links this workspace alongside the compact kernel.
; Each of four input channels selects one bit of a 16-entry subset table.
TABLE_LO = $c000
TABLE_MI = $c400
TABLE_HI = $c800
lut_lo = $60
lut_mi = $62
lut_hi = $64
lane_lo = $66
lane_mi = $67
lane_hi = $68
groups = $69
pair_index = $6a
weights = $6b
packed = $6d
low_sum = $6e       ; three signed bytes, plus sign extension
high_sum = $72      ; three signed bytes, plus sign extension

.segment "BSS"
group4_ready: .res 1
group4_tile:  .res 1

.segment "CODE"
.macro RESET_TABLES
    lda #0
    sta lut_lo
    sta lut_mi
    sta lut_hi
    lda #>TABLE_LO
    sta lut_lo+1
    lda #>TABLE_MI
    sta lut_mi+1
    lda #>TABLE_HI
    sta lut_hi+1
.endmacro

.macro NEXT_TABLE
    .local within_page
    clc
    lda lut_lo
    adc #16
    sta lut_lo
    sta lut_mi
    sta lut_hi
    bcc within_page
    inc lut_lo+1
    inc lut_mi+1
    inc lut_hi+1
within_page:
.endmacro

; Fill all supersets of this lane from the subsets of the earlier lanes.
.macro ADD_LANE BIT_NUMBER
    .local sign_ready
    lda activation_lo,x
    sta lane_lo
    lda activation_hi,x
    sta lane_mi
    lda #0
    bit lane_mi
    bpl sign_ready
    lda #$ff
sign_ready:
    sta lane_hi
    .repeat (1 << BIT_NUMBER), SUBSET
        clc
        ldy #SUBSET
        lda (lut_lo),y
        adc lane_lo
        ldy #(SUBSET + (1 << BIT_NUMBER))
        sta (lut_lo),y
        ldy #SUBSET
        lda (lut_mi),y
        adc lane_mi
        ldy #(SUBSET + (1 << BIT_NUMBER))
        sta (lut_mi),y
        ldy #SUBSET
        lda (lut_hi),y
        adc lane_hi
        ldy #(SUBSET + (1 << BIT_NUMBER))
        sta (lut_hi),y
    .endrepeat
    inx
.endmacro

.proc group4_prepare
    lda dot_columns
    and #3
    jne unsupported
    lda dot_columns
    lsr
    lsr
    bne count
    lda #64
count:
    sta groups
    RESET_TABLES
    ldx #0
group:
    ldy #0
    lda #0
    sta (lut_lo),y
    sta (lut_mi),y
    sta (lut_hi),y
    .repeat 4, LANE
        ADD_LANE LANE
    .endrepeat
    NEXT_TABLE
    cpx dot_columns
    jne group
    lda #1
    sta group4_ready
    clc
    rts
unsupported:
    sec
    rts
.endproc

.macro SUM_SUBSET DEST
    clc
    lda DEST
    adc (lut_lo),y
    sta DEST
    lda DEST+1
    adc (lut_mi),y
    sta DEST+1
    lda DEST+2
    adc (lut_hi),y
    sta DEST+2
.endmacro

.macro EXTEND_SUM SUM
    .local positive
    ldy #0
    lda SUM+2
    bpl positive
    dey
positive:
    sty SUM+3
.endmacro

; Rows contain four runs of masks for bit pairs 6/7, 4/5, 2/3, 0/1.
; Low nibble selects the lower bit of a pair. The first high bit is signed.
.proc group4_dot
    lda dot_weights
    sta weights
    lda dot_weights+1
    sta weights+1
    lda #0
    sta pair_index
    .repeat 4, I
        sta dot_result+I
    .endrepeat
pair:
    RESET_TABLES
    lda #0
    .repeat 3, I
        sta low_sum+I
        sta high_sum+I
    .endrepeat
    ldx #0
group:
    txa
    tay
    lda (weights),y
    sta packed
    and #15
    tay
    SUM_SUBSET low_sum
    ldy packed
    lda high_nibble,y
    tay
    SUM_SUBSET high_sum
    NEXT_TABLE
    inx
    cpx groups
    bne group

    ; Sum over at most 256 signed words fits in signed 24 bits. Widen
    ; before multiplying the upper plane by two and adding/subtracting.
    EXTEND_SUM low_sum
    EXTEND_SUM high_sum
    asl high_sum
    .repeat 3, I
        rol high_sum+1+I
    .endrepeat
    .repeat 2
        asl dot_result
        .repeat 3, I
            rol dot_result+1+I
        .endrepeat
    .endrepeat
    lda pair_index
    beq signed_pair
    clc
    .repeat 4, I
        lda dot_result+I
        adc high_sum+I
        sta dot_result+I
    .endrepeat
    jmp lower_pair
signed_pair:
    sec
    .repeat 4, I
        lda dot_result+I
        sbc high_sum+I
        sta dot_result+I
    .endrepeat
lower_pair:
    clc
    .repeat 4, I
        lda dot_result+I
        adc low_sum+I
        sta dot_result+I
    .endrepeat
    clc
    lda weights
    adc groups
    sta weights
    bcc :+
    inc weights+1
:
    inc pair_index
    lda pair_index
    cmp #4
    jne pair
    rts
.endproc

.segment "RODATA"
.align 256
high_nibble:
.repeat 256, I
    .byte I >> 4
.endrepeat
