; R27 native8 caret/status UI without loading another renderer overlay.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/caret-ui.inc"
.import tui_editor_status40
.export se_gcc_row
.ifndef se_f_owner
.import se_f_owner
.endif
.ifndef se_overlay_frame
.import se_overlay_frame
.endif
.ifndef text_ptr
.importzp text_ptr
.endif
.ifndef screen_ptr
.importzp screen_ptr
.endif
.assert text_ptr<$FF .and screen_ptr<$FF,lderror,"UI pointer loans must be zero page"
.segment "CODE"
se_gcc_cell:
    lda se_f_owner
    cmp #2
    bcc cell_frame
foreign:
    lda #GCC_UI_OWNER
    sec
    rts
cell_frame:
    lda se_overlay_frame+1
    sta text_ptr
    lda se_overlay_frame+2
    sta text_ptr+1
    ldy #BC_ROW
    lda (text_ptr),y
    cmp #25
    bcs argument
    iny
    lda (text_ptr),y
    cmp #40
    bcs argument
    ldy #BC_FOREGROUND
    lda (text_ptr),y
    iny
    ora (text_ptr),y
    cmp #16
    bcs argument
    iny
    lda (text_ptr),y
    bne argument
    iny
    lda (text_ptr),y
    cmp #$AC
    bne argument
    iny
    lda (text_ptr),y
    bne argument
    iny
    lda (text_ptr),y
    cmp #$60
    bne argument
    iny
    lda (text_ptr),y
    bne argument
    iny
    lda (text_ptr),y
    cmp #$40
    beq cell_draw
argument:
    lda #BC_ARGUMENT
    sec
    rts
cell_draw:
    ; Save glyph pointer on stack while the two loans still address the frame
    ; and attribute. All frame fields are consumed before either output write.
    ldy #BC_SCREEN
    lda (text_ptr),y
    asl
    asl
    asl
    pha
    lda (text_ptr),y
    lsr
    lsr
    lsr
    lsr
    lsr
    and #3
    ora #$48
    pha
    lda #$40
    sta screen_ptr+1
    ldy #BC_ROW
    lda (text_ptr),y
    tax
    beq @column
    lda #0
@row:
    clc
    adc #40
    bcc :+
    inc screen_ptr+1
:
    dex
    bne @row
@column:
    ldy #BC_COLUMN
    clc
    adc (text_ptr),y
    sta screen_ptr
    bcc :+
    inc screen_ptr+1
:
    ldy #BC_SCREEN
    lda (text_ptr),y
    tax
    ldy #BC_FOREGROUND
    lda (text_ptr),y
    asl
    asl
    asl
    asl
    iny
    ora (text_ptr),y
    ldy #0
    sta (screen_ptr),y
    lda screen_ptr+1
    and #3
    sta screen_ptr+1
    .repeat 3
        asl screen_ptr
        rol screen_ptr+1
    .endrepeat
    lda screen_ptr+1
    ora #$60
    sta screen_ptr+1
    pla
    sta text_ptr+1
    pla
    sta text_ptr
    jsr rounded_pointer
pixels:
    ldy #7
@row:
    lda (text_ptr),y
    cpx #128
    bcc :+
    eor #$FF
:
    sta (screen_ptr),y
    dey
    bpl @row
    lda #0
    clc
    rts

se_gcc_status:
    lda se_f_owner
    cmp #4
    jne foreign
    jsr tui_editor_status40
    ldx #2
    bne row_setup
; Internal opcode4; owner0/1 and only physicalchrome rows0,1,24.
se_gcc_row:
    lda se_f_owner
    cmp #2
    jcs foreign
    ldx se_overlay_frame+1
    cpx #2
    bcc row_setup
    cpx #24
    jne argument
    ldx #2
row_setup:
    lda row_matrix_lo,x
    sta GCC_UI_COLUMN+1
    lda row_matrix_hi,x
    sta GCC_UI_COLUMN+2
    lda row_bitmap_lo,x
    sta screen_ptr
    lda row_bitmap_hi,x
    sta screen_ptr+1
    lda #0
    sta GCC_UI_COLUMN
@cell:
    ; Commonhotcaretstatus keeps its directabsolute accesses. Generalheader
    ; rows share the exact glyph/inverse/pixels loop below.
    lda GCC_UI_COLUMN+2
    cmp #$43
    bne @matrix_cell
    ldx GCC_UI_COLUMN
    lda $43C0,x
    pha
    lda $DBC0,x
    and #15
    asl
    asl
    asl
    asl
    ora #6
    sta $43C0,x
    jmp @glyph
@matrix_cell:
    lda GCC_UI_COLUMN+1
    sta text_ptr
    lda GCC_UI_COLUMN+2
    sta text_ptr+1
    ldy GCC_UI_COLUMN
    lda (text_ptr),y
    pha
    lda text_ptr+1
    clc
    adc #$98
    sta text_ptr+1
    lda (text_ptr),y
    and #15
    asl
    asl
    asl
    asl
    ora #6
    tax
    lda GCC_UI_COLUMN+2
    sta text_ptr+1
    txa
    sta (text_ptr),y
@glyph:
    pla
    tax
    pha
    asl
    asl
    asl
    sta text_ptr
    pla
    lsr
    lsr
    lsr
    lsr
    lsr
    and #3
    ora #$48
    sta text_ptr+1
    jsr rounded_pointer
    jsr pixels
    clc
    lda screen_ptr
    adc #8
    sta screen_ptr
    bcc :+
    inc screen_ptr+1
:
    inc GCC_UI_COLUMN
    lda GCC_UI_COLUMN
    cmp #40
    jcc @cell
    lda #0
    clc
    rts
rounded_pointer:
    cpx #$6D
    bne :+
    lda #<gcc_rounded_bl
    sta text_ptr
    lda #>gcc_rounded_bl
    sta text_ptr+1
:
    cpx #$7D
    bne :+
    lda #<gcc_rounded_br
    sta text_ptr
    lda #>gcc_rounded_br
    sta text_ptr+1
:
    rts
.segment "RODATA"
row_matrix_lo: .byte $00,$28,$C0
row_matrix_hi: .byte $40,$40,$43
row_bitmap_lo: .byte $00,$40,$00
row_bitmap_hi: .byte $60,$61,$7E
gcc_rounded_bl: .byte $18,$18,$1C,$0F,$07,$00,$00,$00
gcc_rounded_br: .byte $18,$18,$38,$F0,$E0,$00,$00,$00
