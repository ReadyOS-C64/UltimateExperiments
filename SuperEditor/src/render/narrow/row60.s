; Specialized strict 60-column renderer. Retains the public NR68 frame and
; output contract, but rejects every mode except60. Foreground-only and
; nonreentrant, as is the generic source leaf. The fused scanline loop patches
; and restores one operand while inside fragment; no IRQ/NMI path enters this
; overlay leaf, and the caller excludes a second foreground renderer.
.setcpu "6502"
.macpack longbranch
.include "render/narrow/api.inc"
.import se_petscii_screen
.export se_narrow_row,se_narrow_row60
.segment "CODE"
se_narrow_row:
se_narrow_row60:
    stx se_nr_context
    sty se_nr_context+1
    ldy #NR_MODE
    lda (se_nr_context),y
    cmp #60
    jne argument
    ldy #NR_ROW
    lda (se_nr_context),y
    cmp #25
    jcs argument
    ldy #NR_ENCODING
    lda (se_nr_context),y
    cmp #2
    jcs argument
    ; Preserve the generic leaf's output-range validation exactly.
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
    cmp #60
    bcc :+
    lda #60
:   ldy #NR_LIMIT
    sta (se_nr_context),y
    lda #0
    ldy #NR_INDEX
    sta (se_nr_context),y
    lda #5
    ldy #NR_PITCH
    sta (se_nr_context),y
    lda #$F8
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
    ; Always clear the complete 320-byte row.
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
    ; Centered 300-pixel 60-column area: one blank tile plus two pixels.
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
    ; Bias source so the same Y addresses font glyph and caller cache.
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
    clc
    adc #5
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
    ; A 60-column row always finishes inside the final physical tile.
    jsr se_narrow_resolve_tile
    lda #0
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
    ; Selection/caret is a separate clipped fragment and never changes the
    ; base-ink histogram used for color arbitration.
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
    ; Select one of two same-low-byte tables once for the whole fragment.
    ; The operand is restored before return, preserving the full-RAM oracle.
    ldy #NR_SIDE
    lda (se_nr_context),y
    beq @scanline
    lda #>shifted_left
    sta @shifted+2
@scanline:
    ldy #NR_Y
    lda (se_nr_context),y
    tay
    lda (se_nr_context),y
    ; Existing 5-pixel glyph rows occupy only their top five bits. OR the
    ; output phase to form the 32-pattern x 8-phase table index.
    ldy #NR_OFFSET
    ora (se_nr_context),y
    tax
@shifted:
    lda shifted_right,x
    tax
    lda popcount,x
    ldy #NR_INK
    clc
    adc (se_nr_context),y
    sta (se_nr_context),y
    txa
    ldy #NR_FRAGMENT_MASK
    eor (se_nr_context),y
    tax
    ldy #NR_Y
    lda (se_nr_context),y
    tay
    txa
    ora (se_nr_pointer),y
    sta (se_nr_pointer),y
    iny
    tya
    ldy #NR_Y
    sta (se_nr_context),y
    cmp #NR_CACHE+8
    bcc @scanline
    lda #>shifted_right
    sta @shifted+2
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

.segment "RODATA"
popcount:
.repeat 256,I
    .byte ((I>>0)&1)+((I>>1)&1)+((I>>2)&1)+((I>>3)&1)+((I>>4)&1)+((I>>5)&1)+((I>>6)&1)+((I>>7)&1)
.endrepeat
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
.assert <shifted_right=<shifted_left,error,"fragment tables must share low byte"
