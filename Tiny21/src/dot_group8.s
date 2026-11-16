.setcpu "6502"
.macpack longbranch
.import activation_lo, activation_hi, group4_ready
.importzp dot_weights, dot_result
.export group8_prepare, group8_dot

; 96 columns, with 12 page-aligned groups in each of three byte planes.
; $8000-$9FFF and $C000-$C3FF are reused during 96-column projections.
; The 16-row projection tile stages at $C400 while these tables are live.
lut_lo = $60
lut_mid = $62
lut_hi = $64
lane_value = $66
lane_count = $69
half = $6a
upper = $6c
weights = $6d
plane = $6f
mask_index = $70
plane_sum = $71
lower = $75

.segment "CODE"

; All three indirect pointers have their low byte at zero.
.proc next_group
    inc lut_lo+1
    inc lut_mid+1
    inc lut_hi+1
    lda lut_hi+1
    cmp #$a0
    bne ready
    lda #$c0
    sta lut_hi+1
ready:
    rts
.endproc

.proc start_groups
    lda #0
    sta lut_lo
    sta lut_mid
    sta lut_hi
    lda #$80
    sta lut_lo+1
    lda #$8c
    sta lut_mid+1
    lda #$98
    sta lut_hi+1
    rts
.endproc

.proc group8_prepare
    jsr start_groups
    ldx #0
group_loop:
    ldy #0
    lda #0
    sta (lut_lo),y
    sta (lut_mid),y
    sta (lut_hi),y
    lda #1
    sta half
    lda #8
    sta lane_count
lane:
    lda activation_lo,x
    sta lane_value
    lda activation_hi,x
    sta lane_value+1
    lda #0
    bit lane_value+1
    bpl positive
    lda #$ff
positive:
    sta lane_value+2
    lda #0
    sta lower
    lda half
    sta upper
append:
    ldy lower
    clc
    lda (lut_lo),y
    adc lane_value
    ldy upper
    sta (lut_lo),y
    ldy lower
    lda (lut_mid),y
    adc lane_value+1
    ldy upper
    sta (lut_mid),y
    ldy lower
    lda (lut_hi),y
    adc lane_value+2
    ldy upper
    sta (lut_hi),y
    inc upper
    inc lower
    lda lower
    cmp half
    bne append
    asl half
    inx
    dec lane_count
    bne lane
    jsr next_group
    cpx #96
    bne group_loop
    lda #2
    sta group4_ready
    clc
    rts
.endproc

.proc group8_dot
    lda dot_weights
    sta weights
    lda dot_weights+1
    sta weights+1
    lda #0
    sta mask_index
    .repeat 4, I
        sta dot_result+I
    .endrepeat
    lda #8
    sta plane
bit_plane:
    jsr start_groups
    lda #0
    sta plane_sum
    sta plane_sum+1
    sta plane_sum+2
    ldx #12
next_mask:
    ldy mask_index
    lda (weights),y
    tay
    clc
    lda plane_sum
    adc (lut_lo),y
    sta plane_sum
    lda plane_sum+1
    adc (lut_mid),y
    sta plane_sum+1
    lda plane_sum+2
    adc (lut_hi),y
    sta plane_sum+2
    inc mask_index
    inc lut_lo+1
    inc lut_mid+1
    inc lut_hi+1
    ; The high plane jumps from $9F to $C0 after the eighth group.
    cpx #5
    bne same_region
    lda #$c0
    sta lut_hi+1
same_region:
    dex
    bne next_mask

    lda #0
    bit plane_sum+2
    bpl sum_positive
    lda #$ff
sum_positive:
    sta plane_sum+3
    lda plane
    cmp #8
    bne unsigned
    sec
    .repeat 4, I
        lda dot_result+I
        sbc plane_sum+I
        sta dot_result+I
    .endrepeat
    jmp advance
unsigned:
    asl dot_result
    .repeat 3, I
        rol dot_result+1+I
    .endrepeat
    clc
    .repeat 4, I
        lda dot_result+I
        adc plane_sum+I
        sta dot_result+I
    .endrepeat
advance:
    dec plane
    jne bit_plane
    rts
.endproc
