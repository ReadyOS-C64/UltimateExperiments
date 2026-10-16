.include "render_text.inc"
.macpack longbranch
.import dos64_mem_read
.import dos64_cga_control, dos64_cga_control_valid
.importzp dos64_address
.export dos64_render_text_row, dos64_render_text_request

.segment "DEVICESTATE"
dos64_render_text_request: .res RT_SIZE
rt_sp: .res 1
rt_port: .res 1
rt_ddr: .res 1
rt_cols: .res 1
rt_stride: .res 1
rt_page: .res 1
rt_ptr: .res 2
rt_char: .res 1
rt_attr: .res 1
rt_mask_left: .res 1
rt_mask_right: .res 1
rt_bits: .res 1
rt_count: .res 1
rt_bg_mask: .res 1
rt_blank: .res 1

.segment "RENDERCODE"
; Actual 6510 bitmap presenter foundation; synchronous, nonreentrant. Requires
; writable code (self-modified font/output operands), no IRQ entry in progress.
; Native P except C, exact DDR and port output bits restored; A/X/Y clobbered.
; Latent latch bits for input-configured port pins cannot be read/restored.
; Entry may have BASIC/KERNAL visible. Code must remain in C900-CFFF while bank
; switching; port saved on native stack before accessing state under KERNAL.
; Guest BDA/VRAM read exclusively through coherent memory. No guest writes.
; Inputs: native fonts 4400-47FF (packed4x8) and 4800-4FFF (8x8), descriptor row/blink, coherent BDA text mode.
; Outputs: matrix 4000-43E7, hires bitmap 6000-7F3F, selected row only.
; 80 cols: packed four-pixel glyphs at4400; both halves share LEFT cell fg/bg. Blink
; suppresses each half independently. No cursor overlay, VIC setup or font asset.
dos64_render_text_row:
    php
    sei
    cld
    lda $00
    pha
    lda $01
    pha
    lda $00
    ora #7
    sta $00
    lda $01
    and #$F8
    ora #5
    sta $01
    pla
    sta rt_port
    pla
    sta rt_ddr
    tsx
    stx rt_sp
    lda #0
    sta dos64_render_text_request+RT_DONE
    sta dos64_render_text_request+RT_STATUS
    sta dos64_render_text_request+RT_ERROR
    lda dos64_render_text_request+RT_ROW
    cmp #25
    jcs rt_argument
    lda dos64_render_text_request+RT_BLINK
    cmp #2
    jcs rt_argument
    lda #$49
    jsr rt_bda
    cmp #4
    jcs rt_argument
    cmp #2
    lda #40
    bcc @columns
    lda #80
@columns:
    sta rt_cols
    lda #$4A
    jsr rt_bda
    cmp rt_cols
    jne rt_argument
    lda #$4B
    jsr rt_bda
    jne rt_argument
    lda #$4C
    jsr rt_bda
    jne rt_argument
    lda #8
    ldx rt_cols
    cpx #40
    beq @stride
    asl
@stride:
    sta rt_stride
    lda #$4D
    jsr rt_bda
    cmp rt_stride
    jne rt_argument
    lda #$62
    jsr rt_bda
    sta rt_page
    ldx rt_cols
    cpx #40
    bne @fourpages
    cmp #8
    jcs rt_argument
    jmp @page
@fourpages:
    cmp #4
    jcs rt_argument
@page:
    lda #0
    sta rt_ptr
    lda rt_page
    asl
    asl
    asl
    ldx rt_cols
    cpx #40
    beq @pagehi
    asl
@pagehi:
    sta rt_ptr+1
    lda #$4E
    jsr rt_bda
    jne rt_argument
    lda #$4F
    jsr rt_bda
    cmp rt_ptr+1
    jne rt_argument
    ; Native pointers row*40 (matrix) and row*320 (bitmap).
    lda #0
    sta rt_matrix+1
    sta rt_bitmap+1
    lda #$40
    sta rt_matrix+2
    lda #$60
    sta rt_bitmap+2
    ldx dos64_render_text_request+RT_ROW
    beq @rowready
@row:
    clc
    lda rt_matrix+1
    adc #40
    sta rt_matrix+1
    bcc :+
    inc rt_matrix+2
:
    clc
    lda rt_bitmap+1
    adc #$40
    sta rt_bitmap+1
    lda rt_bitmap+2
    adc #1
    sta rt_bitmap+2
    clc
    lda rt_ptr
    adc rt_cols
    sta rt_ptr
    lda rt_ptr+1
    adc #0
    sta rt_ptr+1
    clc
    lda rt_ptr
    adc rt_cols
    sta rt_ptr
    lda rt_ptr+1
    adc #0
    sta rt_ptr+1
    dex
    bne @row
@rowready:
    lda #0
    sta rt_blank
    lda #7
    sta rt_bg_mask
    lda dos64_cga_control_valid
    cmp #$A5
    bne @control_done
    lda dos64_cga_control
    and #8
    bne @enabled
    inc rt_blank
@enabled:
    lda dos64_cga_control
    and #$20
    bne @control_done
    lda #15
    sta rt_bg_mask
@control_done:
    lda #40
    sta rt_count
rt_cell:
    jsr rt_read
    sta rt_char
    jsr rt_read
    sta rt_attr
    jsr rt_blink_mask
    sta rt_mask_left
    lda rt_char
    jsr rt_font_pointer
    sta rt_font_left+1
    stx rt_font_left+2
    sta rt_narrow_left+1
    stx rt_narrow_left+2
    lda rt_cols
    cmp #40
    beq @draw
    jsr rt_read
    sta rt_char
    jsr rt_read
    ; Right attribute affects blink only; palette comes from the left.
    jsr rt_blink_mask
    sta rt_mask_right
    lda rt_char
    jsr rt_font_pointer
    sta rt_font_right+1
    stx rt_font_right+2
@draw:
    lda rt_attr
    and #15
    tax
    lda rt_palette,x
    asl
    asl
    asl
    asl
    sta rt_bits
    lda rt_attr
    lsr
    lsr
    lsr
    lsr
    and rt_bg_mask
    tax
    lda rt_palette,x
    ora rt_bits
    ldx rt_blank
    beq :+
    lda #0                 ; both bitmap colors black; guest glyphs unchanged
:
rt_matrix:
    sta $4000
    ldy #0
rt_scanline:
    lda rt_cols
    cmp #40
    bne rt_narrow_scanline
rt_font_left:
    lda $4800,y
    and rt_mask_left
    jmp rt_store
rt_narrow_scanline:
    tya
    lsr
    tax
rt_narrow_left:
    lda $4400,x
    and rt_mask_left
    sta rt_bits
    tya
    and #1
    beq rt_narrow_even
    lda rt_bits
    asl
    asl
    asl
    asl
    sta rt_bits
    jmp rt_narrow_right
rt_narrow_even:
    lda rt_bits
    and #$F0
    sta rt_bits
rt_narrow_right:
rt_font_right:
    lda $4400,x
    and rt_mask_right
    tax
    tya
    and #1
    bne rt_narrow_odd_right
    txa
    lsr
    lsr
    lsr
    lsr
    jmp rt_narrow_combine
rt_narrow_odd_right:
    txa
    and #$0F
rt_narrow_combine:
    ora rt_bits
rt_store:
rt_bitmap:
    sta $6000,y
    iny
    cpy #8
    bne rt_scanline
    inc dos64_render_text_request+RT_DONE
    inc rt_matrix+1
    bne :+
    inc rt_matrix+2
:
    clc
    lda rt_bitmap+1
    adc #8
    sta rt_bitmap+1
    bcc :+
    inc rt_bitmap+2
:
    dec rt_count
    jne rt_cell
    lda #RT_OK
    sta dos64_render_text_request+RT_STATUS
    lda rt_port
    ldx rt_ddr
    sta $01
    stx $00
    plp
    clc
    rts
rt_argument:
    lda #RT_ERR_ARGUMENT
    bne rt_failed
rt_cache:
    lda #RT_ERR_CACHE
rt_failed:
    sta dos64_render_text_request+RT_ERROR
    lda #RT_FAILED
    sta dos64_render_text_request+RT_STATUS
    ldx rt_sp
    txs
    lda rt_port
    ldx rt_ddr
    sta $01
    stx $00
    plp
    sec
    rts

rt_bda:
    sta dos64_address
    lda #4
    sta dos64_address+1
    lda #0
    sta dos64_address+2
    jsr dos64_mem_read
    jcs rt_cache
    cmp #0
    rts
rt_read:
    lda rt_ptr
    sta dos64_address
    clc
    lda rt_ptr+1
    adc #$80
    sta dos64_address+1
    lda #$0B
    sta dos64_address+2
    jsr dos64_mem_read
    jcs rt_cache
    inc rt_ptr
    bne :+
    inc rt_ptr+1
:
    rts
rt_blink_mask:
    ; A=attribute. Physical mode latch selects blink or background intensity.
    ldx rt_bg_mask
    cpx #15
    beq @visible
    and #$80
    beq @visible
    lda dos64_render_text_request+RT_BLINK
    bne @visible
    lda #0
    rts
@visible:
    lda #$FF
    rts
rt_font_pointer:
    ldx rt_cols
    cpx #40
    beq rt_wide_pointer
    ; Packed narrow index*4 at4400, always four bytes per glyph.
    ldx #$44
    asl
    bcc :+
    inx
    inx
:   asl
    bcc :+
    inx
:   rts
rt_wide_pointer:
    ldx #$48
    asl
    bcc :+
    inx
    inx
    inx
    inx
:   asl
    bcc :+
    inx
    inx
:   asl
    bcc :+
    inx
:   rts
; IBM RGBI -> deterministic C64 palette: black, blue, green, cyan, red,
; purple, brown, light gray, gray, light blue, light green, cyan, light red,
; purple, yellow, white. Bright cyan/magenta use closest selected C64 hue.
rt_palette:
    .byte 0,6,5,3,2,4,9,15,12,14,13,3,10,4,7,1
