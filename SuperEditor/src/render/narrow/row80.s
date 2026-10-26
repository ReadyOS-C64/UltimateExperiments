; Specialized80-column tile-pair renderer. Same NR68 caller contract as row.s,
; strict mode80 only. No storage/ZP allocation, source/DMA/overlay/VIC calls.
; Each tile has at most two roles, so compare their base-ink counts directly.
.setcpu "6502"
.macpack longbranch
.include "render/narrow/api.inc"
.import se_petscii_screen
.export se_narrow_row,se_narrow_row80
.segment "CODE"
se_narrow_row:
se_narrow_row80:
    stx se_nr_context
    sty se_nr_context+1
    ldy #NR_MODE
    lda (se_nr_context),y
    cmp #80
    jne argument
    iny
    lda (se_nr_context),y
    cmp #25
    jcs argument
    ldy #NR_ENCODING
    lda (se_nr_context),y
    cmp #2
    jcs argument
    ldy #NR_BITMAP
    lda (se_nr_context),y
    jne argument
    iny
    lda (se_nr_context),y
    cmp #$20
    jcc argument
    cmp #$C0
    jcs argument
    and #$1F
    jne argument
    ldy #NR_ATTRIBUTES
    lda (se_nr_context),y
    jne argument
    iny
    lda (se_nr_context),y
    cmp #4
    jcc argument
    cmp #$C1
    jcs argument
    and #3
    jne argument
    ldy #NR_COUNT
    lda (se_nr_context),y
    cmp #80
    bcc :+
    lda #80
:   ldy #NR_LIMIT
    sta (se_nr_context),y
    lda #0
    iny
    sta (se_nr_context),y ;index
    ; Effective normal roles share palette0 regardless of inverse/selection.
    jsr detect_normal
    ldy #NR_TILE
    sta (se_nr_context),y
    ; Derive both row addresses, retaining them in caller scratch.
    ldy #NR_BITMAP
    jsr pointer
    ldy #NR_ROW
    lda (se_nr_context),y
    tax
    beq @bitmap_ready
@bitmap_row:
    lda se_nr_pointer
    clc
    adc #$40
    sta se_nr_pointer
    lda se_nr_pointer+1
    adc #1
    sta se_nr_pointer+1
    dex
    bne @bitmap_row
@bitmap_ready:
    ldy #NR_BITMAP_PTR
    jsr save_pointer
    ; Clear exactly320bytes; missing/clipped cells remain base-normal blank.
    lda #0
    tay
@clear_page:
    sta (se_nr_pointer),y
    iny
    bne @clear_page
    inc se_nr_pointer+1
@clear_tail:
    sta (se_nr_pointer),y
    iny
    cpy #64
    bcc @clear_tail
    ldy #NR_ATTRIBUTES
    jsr pointer
    ldy #NR_ROW
    lda (se_nr_context),y
    tax
    beq @attribute_ready
@attribute_row:
    lda se_nr_pointer
    clc
    adc #40
    sta se_nr_pointer
    bcc :+
    inc se_nr_pointer+1
:   dex
    bne @attribute_row
@attribute_ready:
    ldy #NR_ATTRIBUTE_PTR
    jsr save_pointer
    ldy #NR_PALETTE
    jsr pointer
    ldy #0
    lda (se_nr_pointer),y
    and #15
    asl
    asl
    asl
    asl
    ; Mask both palette and background to their low nibbles.
    ldy #NR_TEMP
    sta (se_nr_context),y
    ldy #NR_BACKGROUND
    lda (se_nr_context),y
    and #15
    ldy #NR_SELECT
    sta (se_nr_context),y
    ldy #NR_TEMP
    lda (se_nr_context),y
    and #$F0
    ldy #NR_SELECT
    ora (se_nr_context),y
    ldy #NR_TEMP
    sta (se_nr_context),y
    ldy #NR_ATTRIBUTE_PTR
    jsr pointer
    ldy #NR_TEMP
    lda (se_nr_context),y
    ldy #0
@clear_attributes:
    sta (se_nr_pointer),y
    iny
    cpy #40
    bcc @clear_attributes
next_tile:
    ldy #NR_INDEX
    lda (se_nr_context),y
    ldy #NR_LIMIT
    cmp (se_nr_context),y
    jcs done
    jsr glyph
    ldy #NR_TILE
    lda (se_nr_context),y
    jne normal_tile
    ; The first glyph occupies the high nibble. Cached base ink excludes the
    ; separate selection/caret union, so it cannot affect tile color choice.
    ldy #NR_ROLE
    lda (se_nr_context),y
    ldy #NR_BEST_ROLE
    sta (se_nr_context),y
    ldy #NR_SELECT
    lda (se_nr_context),y
    beq :+
    lda #$F0
:   ldy #NR_PAINT
    sta (se_nr_context),y
    ; Eight fixed scanlines trade a small, measured code budget for avoiding
    ; per-pixel fragment shifts and per-scanline scratch-index/helper traffic.
.repeat 8,I
    ldy #NR_CACHE+I
    lda (se_nr_pointer),y
    and #$F0
    tax
    ldy #NR_REVERSE
    txa
    eor (se_nr_context),y
    tax
    lda high_popcount,x
    ldy #NR_INK
    clc
    adc (se_nr_context),y
    sta (se_nr_context),y
    txa
    ldy #NR_CACHE+I
    sta (se_nr_context),y
.endrepeat
    ldy #NR_INK
    lda (se_nr_context),y
    ldy #NR_BEST_WEIGHT
    sta (se_nr_context),y
    jsr increment
    ldy #NR_LIMIT
    cmp (se_nr_context),y
    jcs resolve_left
    jsr glyph
    ldy #NR_SELECT
    lda (se_nr_context),y
    beq :+
    ldy #NR_PAINT
    lda (se_nr_context),y
    ora #$0F
    sta (se_nr_context),y
:
.repeat 8,I
    ldy #NR_CACHE+I
    lda (se_nr_pointer),y
    and #$F0
    tax
    ldy #NR_REVERSE
    txa
    eor (se_nr_context),y
    tax
    lda high_popcount,x
    ldy #NR_INK
    clc
    adc (se_nr_context),y
    sta (se_nr_context),y
    txa
    lsr
    lsr
    lsr
    lsr
    ldy #NR_CACHE+I
    ora (se_nr_context),y
    sta (se_nr_context),y
.endrepeat
    jsr increment
    ; Zero ink always chooses normal, even if selection makes visible pixels.
    ldy #NR_BEST_WEIGHT
    lda (se_nr_context),y
    ldy #NR_INK
    ora (se_nr_context),y
    beq choose_normal
    ; Equal roles combine their weights and trivially win over all other0s.
    ldy #NR_ROLE
    lda (se_nr_context),y
    ldy #NR_BEST_ROLE
    cmp (se_nr_context),y
    beq choose_left_role
    ldy #NR_INK
    lda (se_nr_context),y
    ldy #NR_BEST_WEIGHT
    cmp (se_nr_context),y
    bcc resolve_left
    bne choose_right
    ldy #NR_ROLE
    lda (se_nr_context),y
    tax
    lda priority,x
    ldy #NR_TEMP
    sta (se_nr_context),y
    ldy #NR_BEST_ROLE
    lda (se_nr_context),y
    tax
    lda priority,x
    ldy #NR_TEMP
    cmp (se_nr_context),y
    bcc choose_right
    bne resolve_left
    ; Stable same-priority tie chooses lower semantic ID.
    txa
    ldy #NR_ROLE
    cmp (se_nr_context),y
    bcc resolve_left
choose_right:
    ldy #NR_ROLE
    lda (se_nr_context),y
    jmp chosen
resolve_left:
    ldy #NR_BEST_WEIGHT
    lda (se_nr_context),y
    beq choose_normal
choose_left_role:
    ldy #NR_BEST_ROLE
    lda (se_nr_context),y
    bne chosen
choose_normal:
    lda #0
chosen:
    pha
    ldy #NR_PALETTE
    jsr pointer
    pla
    tay
    lda (se_nr_pointer),y
    and #15
    asl
    asl
    asl
    asl
    ldy #NR_SELECT
    sta (se_nr_context),y
    ldy #NR_BACKGROUND
    lda (se_nr_context),y
    and #15
    ldy #NR_SELECT
    ora (se_nr_context),y
    pha
    ldy #NR_ATTRIBUTE_PTR
    jsr pointer
    pla
    ldy #0
    sta (se_nr_pointer),y
    inc se_nr_pointer
    bne :+
    inc se_nr_pointer+1
:   ldy #NR_ATTRIBUTE_PTR
    jsr save_pointer
paint_bitmap:
    ldy #NR_BITMAP_PTR
    jsr pointer
    ; Bias output pointer so oneY indexes both the cache and destination.
    lda se_nr_pointer
    sec
    sbc #NR_CACHE
    sta se_nr_pointer
    bcs :+
    dec se_nr_pointer+1
:   ldy #NR_PAINT
    lda (se_nr_context),y
    tax
    ldy #NR_CACHE
@pixels:
    txa
    eor (se_nr_context),y
    sta (se_nr_pointer),y
    iny
    cpy #NR_CACHE+8
    bcc @pixels
    ; The biased pointer advanced8 means next physical tile.
    lda se_nr_pointer
    clc
    adc #NR_CACHE+8
    sta se_nr_pointer
    bcc :+
    inc se_nr_pointer+1
:   ldy #NR_BITMAP_PTR
    jsr save_pointer
    jmp next_tile
done:
    lda #0
    clc
    rts
argument:
    lda #NR_ARGUMENT
    sec
    rts

; All-normal-role row specialization. Caller scratch only; no
; color arbitration is needed because the precleared attributes are palette0.
detect_normal:
    ldy #NR_LIMIT
    lda (se_nr_context),y
    beq @normal
    tax
    ldy #NR_ROLES
    jsr pointer
    ldy #0
@scan:
    lda (se_nr_pointer),y
    beq @next
    cmp #14
    bcc @mixed
@next:
    iny
    dex
    bne @scan
@normal:
    lda #1
    rts
@mixed:
    lda #0
    rts
normal_mask:
    ldy #NR_SELECT
    lda (se_nr_context),y
    beq :+
    lda #$F0
:   ldy #NR_REVERSE
    eor (se_nr_context),y
    tax
    rts
normal_tile:
    jsr normal_mask
    .repeat 8,I
    ldy #NR_CACHE+I
    txa
    eor (se_nr_pointer),y
    and #$F0
    sta (se_nr_context),y
    .endrepeat
    jsr increment
    ldy #NR_LIMIT
    cmp (se_nr_context),y
    jcs @paint
    jsr glyph
    jsr normal_mask
    .repeat 8,I
    ldy #NR_CACHE+I
    txa
    eor (se_nr_pointer),y
    and #$F0
    lsr
    lsr
    lsr
    lsr
    ora (se_nr_context),y
    sta (se_nr_context),y
    .endrepeat
    jsr increment
@paint:
    lda #0
    ldy #NR_PAINT
    sta (se_nr_context),y
    jmp paint_bitmap

; Consume one source cell and prepare a biased glyph pointer, role and flags.
glyph:
    ldy #NR_ROLES
    jsr array
    cmp #14
    bcc :+
    lda #0
:   ldy #NR_ROLE
    sta (se_nr_context),y
    ldy #NR_FLAGS
    jsr array
    pha
    and #NR_INVERSE
    beq :+
    lda #$F0
:   ldy #NR_REVERSE
    sta (se_nr_context),y
    pla
    and #(NR_SELECTED|NR_CARET)
    ldy #NR_SELECT
    sta (se_nr_context),y
    ldy #NR_CHARACTERS
    jsr array
    ldy #NR_GLYPH
    sta (se_nr_context),y
    ldy #NR_ENCODING
    lda (se_nr_context),y
    beq @native
    ldy #NR_GLYPH
    lda (se_nr_context),y
    bpl @raw
    pha
    lda #$F0
    ldy #NR_REVERSE
    sta (se_nr_context),y
    pla
@raw:
    and #127
    jmp @font
@native:
    ldy #NR_GLYPH
    lda (se_nr_context),y
    jsr se_petscii_screen
@font:
    sta se_nr_pointer
    lda #0
    sta se_nr_pointer+1
    .repeat 3
        asl se_nr_pointer
        rol se_nr_pointer+1
    .endrepeat
    ldy #NR_FONT
    lda (se_nr_context),y
    clc
    adc se_nr_pointer
    sta se_nr_pointer
    iny
    lda (se_nr_context),y
    adc se_nr_pointer+1
    sta se_nr_pointer+1
    ; Bias font soY58..65 is shared by glyph and caller cache.
    lda se_nr_pointer
    sec
    sbc #NR_CACHE
    sta se_nr_pointer
    bcs :+
    dec se_nr_pointer+1
:   lda #0
    ldy #NR_INK
    sta (se_nr_context),y
    rts

pointer:
    lda (se_nr_context),y
    sta se_nr_pointer
    iny
    lda (se_nr_context),y
    sta se_nr_pointer+1
    rts
save_pointer:
    lda se_nr_pointer
    sta (se_nr_context),y
    iny
    lda se_nr_pointer+1
    sta (se_nr_context),y
    rts
array:
    jsr pointer
    ldy #NR_INDEX
    lda (se_nr_context),y
    tay
    lda (se_nr_pointer),y
    rts
increment:
    ldy #NR_INDEX
    lda (se_nr_context),y
    clc
    adc #1
    sta (se_nr_context),y
    rts
.segment "RODATA"
high_popcount:
.repeat 256,I
    .byte ((I>>4)&1)+((I>>5)&1)+((I>>6)&1)+((I>>7)&1)
.endrepeat
priority: .byte 0,6,7,8,0,0,0,5,3,4,1,5,2,0
