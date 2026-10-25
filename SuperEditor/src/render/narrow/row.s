.setcpu "6502"
.macpack longbranch
.include "render/narrow/api.inc"
.import se_petscii_screen
.export se_narrow_row
.segment "CODE"
; One complete physical hires row. Foreground-only, nonreentrant: caller loans
; both ZP pairs, owns all inputs/frame/output, and prevents competing rendering.
; No allocation, overlay, KERNAL, REU or VIC-register call; A/X/Y/P clobbered.
se_narrow_row:
    stx se_nr_context
    sty se_nr_context+1
    ldy #NR_MODE
    lda (se_nr_context),y
    cmp #60
    beq @mode_ok
    cmp #80
    jne argument
@mode_ok:
    ldy #NR_ROW
    lda (se_nr_context),y
    cmp #25
    jcs argument
    ldy #NR_ENCODING
    lda (se_nr_context),y
    cmp #2
    jcs argument
    ; Reject output ranges that could hit the shim, I/O or zero page. Matrix
    ; may startC000 (endsC3E7); bitmap may startA000 (endsBF3F), neverC000.
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
    ldy #NR_MODE
    lda (se_nr_context),y
    ldy #NR_COUNT
    cmp (se_nr_context),y
    bcc :+
    lda (se_nr_context),y
:   ldy #NR_LIMIT
    sta (se_nr_context),y
    lda #0
    ldy #NR_INDEX
    sta (se_nr_context),y
    ldy #NR_MODE
    lda (se_nr_context),y
    cmp #60
    beq @sixty
    lda #4
    ldx #$F0
    bne @pitch
@sixty:
    lda #5
    ldx #$F8
@pitch:
    ldy #NR_PITCH
    sta (se_nr_context),y
    txa
    iny
    sta (se_nr_context),y
    ldy #NR_BITMAP
    jsr pointer
    ldy #NR_ROW
    lda (se_nr_context),y
    tax
    beq @bitmap_address
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
@bitmap_address:
    ldy #NR_BITMAP_PTR
    jsr save_pointer
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
    beq @attribute_address
@attribute_row:
    lda se_nr_pointer
    clc
    adc #40
    sta se_nr_pointer
    bcc :+
    inc se_nr_pointer+1
:   dex
    bne @attribute_row
@attribute_address:
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
    ldy #NR_TEMP
    sta (se_nr_context),y
    ldy #NR_BACKGROUND
    lda (se_nr_context),y
    and #15
    ldy #NR_TEMP
    ora (se_nr_context),y
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
    lda #0
    ldy #NR_OFFSET
    sta (se_nr_context),y
    ldy #NR_TILE
    sta (se_nr_context),y
    jsr clear_histogram
    ldy #NR_MODE
    lda (se_nr_context),y
    cmp #60
    bne next_glyph
    ; Centered300-pixel60-column area:8px blank tile plus2px inset.
    jsr advance_tile
    lda #2
    ldy #NR_OFFSET
    sta (se_nr_context),y
next_glyph:
    ldy #NR_INDEX
    lda (se_nr_context),y
    ldy #NR_LIMIT
    cmp (se_nr_context),y
    jeq done
    ldy #NR_FLAGS
    jsr array
    pha
    and #NR_INVERSE
    ldy #NR_REVERSE
    sta (se_nr_context),y
    pla
    and #(NR_SELECTED|NR_CARET)
    ldy #NR_SELECT
    sta (se_nr_context),y
    ldy #NR_ROLES
    jsr array
    cmp #14
    bcc :+
    lda #0
:   ldy #NR_ROLE
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
    bpl @normal_screen
    lda #1
    ldy #NR_REVERSE
    sta (se_nr_context),y
    ldy #NR_GLYPH
    lda (se_nr_context),y
@normal_screen:
    and #$7F
    jmp @glyph
@native:
    ldy #NR_GLYPH
    lda (se_nr_context),y
    jsr se_petscii_screen
@glyph:
    ldy #NR_GLYPH
    sta (se_nr_context),y
    lda #0
    sta se_nr_pointer+1
    lda (se_nr_context),y
    asl
    rol se_nr_pointer+1
    asl
    rol se_nr_pointer+1
    asl
    rol se_nr_pointer+1
    sta se_nr_pointer
    ldy #NR_FONT
    lda (se_nr_context),y
    clc
    adc se_nr_pointer
    sta se_nr_pointer
    iny
    lda (se_nr_context),y
    adc se_nr_pointer+1
    sta se_nr_pointer+1
    ldy #NR_FONT_PTR
    jsr save_pointer
    ; Bias the source pointer so the sameY addresses source glyph and cache.
    lda se_nr_pointer
    sec
    sbc #NR_CACHE
    sta se_nr_pointer
    bcs :+
    dec se_nr_pointer+1
:   ldy #NR_CACHE
@cache:
    lda (se_nr_pointer),y
    sta (se_nr_context),y
    iny
    cpy #NR_CACHE+8
    bcc @cache
    ldy #NR_REVERSE
    lda (se_nr_context),y
    beq @not_inverse
    ldy #NR_MASK
    lda (se_nr_context),y
@not_inverse:
    sta se_nr_pointer
    ldy #NR_MASK
    lda (se_nr_context),y
    sta se_nr_pointer+1
    ldy #NR_CACHE
@base_ink:
    lda (se_nr_context),y
    and se_nr_pointer+1
    eor se_nr_pointer
    sta (se_nr_context),y
    iny
    cpy #NR_CACHE+8
    bcc @base_ink
    ldy #NR_OFFSET
    lda (se_nr_context),y
    ldy #NR_SHIFT
    sta (se_nr_context),y
    ldy #NR_PITCH
    clc
    adc (se_nr_context),y
    ldy #NR_NEXT
    sta (se_nr_context),y
    lda #0
    ldy #NR_SIDE
    sta (se_nr_context),y
    jsr fragment
    ldy #NR_NEXT
    lda (se_nr_context),y
    cmp #8
    bcc @offset
    jsr se_narrow_resolve_tile
    jsr advance_tile
    jsr clear_histogram
    ldy #NR_NEXT
    lda (se_nr_context),y
    cmp #8
    beq @offset
    lda #8
    ldy #NR_OFFSET
    sec
    sbc (se_nr_context),y
    ldy #NR_SHIFT
    sta (se_nr_context),y
    lda #1
    ldy #NR_SIDE
    sta (se_nr_context),y
    jsr fragment
    ldy #NR_NEXT
    lda (se_nr_context),y
@offset:
    and #7
    ldy #NR_OFFSET
    sta (se_nr_context),y
    ldy #NR_INDEX
    lda (se_nr_context),y
    clc
    adc #1
    sta (se_nr_context),y
    jmp next_glyph
done:
    ; At exact80-column end the pointer is already one tile beyond this row.
    ldy #NR_TILE
    lda (se_nr_context),y
    cmp #40
    bcs :+
    jsr se_narrow_resolve_tile
:   lda #0
    clc
    rts
argument:
    lda #NR_ARGUMENT
    sec
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
clear_histogram:
    lda #0
    ldy #NR_HISTOGRAM
@loop:
    sta (se_nr_context),y
    iny
    cpy #NR_HISTOGRAM+14
    bcc @loop
    rts
advance_tile:
    ldy #NR_BITMAP_PTR
    lda (se_nr_context),y
    clc
    adc #8
    sta (se_nr_context),y
    bcc :+
    iny
    lda (se_nr_context),y
    adc #0
    sta (se_nr_context),y
:   ldy #NR_ATTRIBUTE_PTR
    lda (se_nr_context),y
    clc
    adc #1
    sta (se_nr_context),y
    bcc :+
    iny
    lda (se_nr_context),y
    adc #0
    sta (se_nr_context),y
:   ldy #NR_TILE
    lda (se_nr_context),y
    clc
    adc #1
    sta (se_nr_context),y
    rts

fragment:
    ; Selection/caret is the union of their cell mask, applied once. Compute
    ; its clipped fragment separately from base ink used for tile arbitration.
    lda #0
    ldy #NR_FRAGMENT_MASK
    sta (se_nr_context),y
    ldy #NR_SELECT
    lda (se_nr_context),y
    beq @mask_ready
    ldy #NR_SHIFT
    lda (se_nr_context),y
    tax
    ldy #NR_SIDE
    lda (se_nr_context),y
    bne @mask_left
    ldy #NR_MASK
    lda (se_nr_context),y
    cpx #0
    beq @store_mask
@mask_right:
    lsr
    dex
    bne @mask_right
    beq @store_mask
@mask_left:
    ldy #NR_MASK
    lda (se_nr_context),y
@shift_mask_left:
    asl
    dex
    bne @shift_mask_left
@store_mask:
    ldy #NR_FRAGMENT_MASK
    sta (se_nr_context),y
@mask_ready:
    ldy #NR_BITMAP_PTR
    jsr pointer
    lda se_nr_pointer
    sec
    sbc #NR_CACHE
    sta se_nr_pointer
    bcs :+
    dec se_nr_pointer+1
:   lda #NR_CACHE
    ldy #NR_Y
    sta (se_nr_context),y
    lda #0
    ldy #NR_INK
    sta (se_nr_context),y
    ldy #NR_SIDE
    lda (se_nr_context),y
    bne @left
@right:
    jsr cached_byte
    lda shifted_right,x
    jsr fragment_byte
    jsr next_scanline
    bcc @right
    bcs @count
@left:
    jsr cached_byte
    lda shifted_left,x
    jsr fragment_byte
    jsr next_scanline
    bcc @left
@count:
    ldy #NR_INK
    lda (se_nr_context),y
    tax
    ldy #NR_ROLE
    lda (se_nr_context),y
    clc
    adc #NR_HISTOGRAM
    tay
    txa
    clc
    adc (se_nr_context),y
    sta (se_nr_context),y
    rts
cached_byte:
    ldy #NR_Y
    lda (se_nr_context),y
    tay
    lda (se_nr_context),y
    ; Existing narrow glyphs and inverse masks occupy only the top5bits.
    ; A already equals pattern*8; OR the pixel phase to index32x8 fragments.
    ldy #NR_OFFSET
    ora (se_nr_context),y
    tax
    rts
fragment_byte:
    pha
    tax
    lda popcount,x
    ldy #NR_INK
    clc
    adc (se_nr_context),y
    sta (se_nr_context),y
    pla
    ldy #NR_FRAGMENT_MASK
    eor (se_nr_context),y
    pha
    ldy #NR_Y
    lda (se_nr_context),y
    tay
    pla
    ora (se_nr_pointer),y
    sta (se_nr_pointer),y
    rts
next_scanline:
    ldy #NR_Y
    lda (se_nr_context),y
    clc
    adc #1
    sta (se_nr_context),y
    cmp #NR_CACHE+8
    rts
.segment "RODATA"
popcount:
.repeat 256,I
    .byte ((I>>0)&1)+((I>>1)&1)+((I>>2)&1)+((I>>3)&1)+((I>>4)&1)+((I>>5)&1)+((I>>6)&1)+((I>>7)&1)
.endrepeat
; Small phase tables replace variable shifts in every glyph scanline. These
; are bit-composition tables, not another font or a source-code translation.
shifted_right:
.repeat 256,I
    .byte ((I&$F8)>>(I&7))
.endrepeat
shifted_left:
.repeat 256,I
 .if (I&7)=0
    .byte 0
 .else
    .byte (((I&$F8)<<(8-(I&7)))&255)
 .endif
.endrepeat
