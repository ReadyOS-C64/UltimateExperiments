.include "render_graphics.inc"
.macpack longbranch
.import dos64_mem_read
.importzp dos64_address
.export dos64_present_graphics_line
.import dos64_native_text_state
.export dos64_render_graphics_line, dos64_render_graphics_request
.segment "DEVICESTATE"
dos64_render_graphics_request: .res RG_SIZE
rg_sp: .res 1
rg_ddr: .res 1
rg_port: .res 1
rg_mode: .res 1
rg_color: .res 1
rg_palette: .res 1
rg_matrix_color: .res 1
rg_color_ram: .res 1
rg_background: .res 1
rg_ptr: .res 2
rg_bits: .res 1
rg_count: .res 1
.segment "GFXCODE"
; Writable C900-CFFF overlay; nonreentrant, IRQs excluded during call.
; Native P except C and readable DDR/output bits preserved; A/X/Y clobbered.
; Every guest read is coherent. No guest writes, CIA access or VIC setup.
; CGA modes4/5: 320x200 four-color source -> 160x200 multicolor output.
; Horizontal pair chooses left nonzero index, otherwise right (never invents
; a palette index). Mode5 RGBI palette cyan/red/white, bit5 ignored.
; Mode6: 640x200 one-bit source -> 320x200 foreground-preserving pair OR.
; Outputs bitmap6000-7F3F, matrix4000-43E7, colorRAM D800-DBE7 (MC only).
; Palette can change only at scanline granularity; shared cells/D021 mean
; racing guest palette changes require caller-controlled frame scheduling.
dos64_render_graphics_line:
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
    sta rg_port
    pla
    sta rg_ddr
    tsx
    stx rg_sp
    lda #0
    sta dos64_render_graphics_request+RG_DONE
    sta dos64_render_graphics_request+RG_STATUS
    sta dos64_render_graphics_request+RG_ERROR
    lda dos64_render_graphics_request+RG_LINE
    cmp #200
    jcs rg_argument
    lda #$49
    jsr rg_bda
    cmp #4
    jcc rg_argument
    cmp #7
    jcs rg_argument
    sta rg_mode
    lda #$62
    jsr rg_bda
    jne rg_argument
    lda #$4E
    jsr rg_bda
    jne rg_argument
    lda #$4F
    jsr rg_bda
    jne rg_argument
    lda #$66
    jsr rg_bda
    sta rg_color
    and #15
    tax
    lda rg_rgb,x
    sta rg_background
    lda rg_mode
    cmp #6
    bne @multi
    lda rg_background
    asl
    asl
    asl
    asl
    sta rg_matrix_color
    lda #0
    sta rg_background
    jmp @pointers
@multi:
    lda rg_color
    and #$10
    lsr
    sta rg_palette             ; RGBI intensity 0 or 8
    lda rg_mode
    cmp #5
    beq @alternate
    lda rg_color
    and #$20
    beq @set0
    lda #3                    ; palette1: cyan/magenta/white
    bne @set
@set0:
    lda #2                    ; palette0: green/red/brown
    bne @set
@alternate:
    lda #3                    ; mode5: cyan/red/white
@set:
    ora rg_palette
    tax
    lda rg_rgb,x
    asl
    asl
    asl
    asl
    sta rg_matrix_color
    txa
    and #8
    ora #4
    sta rg_palette
    lda rg_mode
    cmp #5
    beq @red
    lda rg_color
    and #$20
    beq @red
    inc rg_palette
@red:
    ldx rg_palette
    lda rg_rgb,x
    ora rg_matrix_color
    sta rg_matrix_color
    lda rg_mode
    cmp #5
    beq @white
    lda rg_color
    and #$20
    bne @white
    lda #6
    bne @third
@white:
    lda #7
@third:
    sta rg_palette
    lda rg_color
    and #$10
    lsr
    ora rg_palette
    tax
    lda rg_rgb,x
    sta rg_color_ram
@pointers:
    lda #0
    sta rg_ptr
    lda dos64_render_graphics_request+RG_LINE
    lsr
    sta rg_count
    lda #0
    bcc :+
    lda #$20
:
    sta rg_ptr+1
    ldx rg_count
    beq @source
@source_add:
    clc
    lda rg_ptr
    adc #80
    sta rg_ptr
    bcc :+
    inc rg_ptr+1
:
    dex
    bne @source_add
@source:
    lda dos64_render_graphics_request+RG_LINE
    and #7
    sta rg_bitmap+1
    lda #$60
    sta rg_bitmap+2
    lda #0
    sta rg_matrix+1
    sta rg_colors+1
    lda #$40
    sta rg_matrix+2
    lda #$D8
    sta rg_colors+2
    lda dos64_render_graphics_request+RG_LINE
    lsr
    lsr
    lsr
    tax
    beq @ready
@output_add:
    clc
    lda rg_bitmap+1
    adc #$40
    sta rg_bitmap+1
    lda rg_bitmap+2
    adc #1
    sta rg_bitmap+2
    clc
    lda rg_matrix+1
    adc #40
    sta rg_matrix+1
    sta rg_colors+1
    bcc :+
    inc rg_matrix+2
    inc rg_colors+2
:
    dex
    bne @output_add
@ready:
    lda #40
    sta rg_count
rg_cell:
    jsr rg_read
    tax
    lda rg_mode
    cmp #6
    beq @hi_left
    lda rg_multi_reduce,x
    jmp @left
@hi_left:
    lda rg_hires_reduce,x
@left:
    asl
    asl
    asl
    asl
    sta rg_bits
    jsr rg_read
    tax
    lda rg_mode
    cmp #6
    beq @hi_right
    lda rg_multi_reduce,x
    jmp @right
@hi_right:
    lda rg_hires_reduce,x
@right:
    ora rg_bits
rg_bitmap:
    sta $6000
    lda rg_matrix_color
rg_matrix:
    sta $4000
    lda rg_mode
    cmp #6
    beq rg_committed
    lda rg_color_ram
rg_colors:
    sta $D800
rg_committed:
    lda rg_background
    sta dos64_render_graphics_request+RG_BACKGROUND
    lda #0
    ldx rg_mode
    cpx #6
    beq :+
    lda #1
:
    sta dos64_render_graphics_request+RG_MULTICOLOR
    inc dos64_render_graphics_request+RG_DONE
    clc
    lda rg_bitmap+1
    adc #8
    sta rg_bitmap+1
    bcc :+
    inc rg_bitmap+2
:
    inc rg_matrix+1
    inc rg_colors+1
    bne :+
    inc rg_matrix+2
    inc rg_colors+2
:
    dec rg_count
    jne rg_cell
    lda #RG_OK
    sta dos64_render_graphics_request+RG_STATUS
    lda rg_port
    ldx rg_ddr
    sta $01
    stx $00
    plp
    clc
    rts
rg_argument:
    lda #RG_ERR_ARGUMENT
    bne rg_failed
rg_cache:
    lda #RG_ERR_CACHE
rg_failed:
    sta dos64_render_graphics_request+RG_ERROR
    lda #RG_FAILED
    sta dos64_render_graphics_request+RG_STATUS
    ldx rg_sp
    txs
    lda rg_port
    ldx rg_ddr
    sta $01
    stx $00
    plp
    sec
    rts
rg_bda:
    sta dos64_address
    lda #4
    sta dos64_address+1
    lda #0
    sta dos64_address+2
    jsr dos64_mem_read
    jcs rg_cache
    cmp #0
    rts
rg_read:
    lda rg_ptr
    sta dos64_address
    clc
    lda rg_ptr+1
    adc #$80
    sta dos64_address+1
    lda #$0B
    sta dos64_address+2
    jsr dos64_mem_read
    jcs rg_cache
    inc rg_ptr
    bne :+
    inc rg_ptr+1
:
    rts
rg_rgb:
    .byte 0,6,5,3,2,4,9,15,12,14,13,3,10,4,7,1
rg_multi_reduce:
.repeat 256, I
    .byte (((I >> 6) * ((I & $C0) <> 0) + (((I >> 4) & 3) * ((I & $C0) = 0))) << 2) | (((I >> 2) & 3) * ((I & $0C) <> 0) + ((I & 3) * ((I & $0C) = 0)))
.endrepeat
rg_hires_reduce:
.repeat 256, I
    .byte (((I & $C0) <> 0) * 8) | (((I & $30) <> 0) * 4) | (((I & $0C) <> 0) * 2) | ((I & $03) <> 0)
.endrepeat

; Leased presenter owns native banking for its complete call. Original VIC
; owner is saved once by TEXT setup; never overwrite that snapshot here.
dos64_present_graphics_line:
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
    and #$f8
    ora #5
    sta $01
    lda dos64_native_text_state
    beq @ownership
    jsr dos64_render_graphics_line
    bcs @failed
    lda $dd00
    and #$fc
    ora #2
    sta $dd00
    lda $dd02
    ora #3
    sta $dd02
    lda #$3b
    sta $d011
    lda #$08
    sta $d018
    lda #0
    sta $d015
    sta $d020
    lda dos64_render_graphics_request+RG_BACKGROUND
    sta $d021
    lda #$c8
    ldx dos64_render_graphics_request+RG_MULTICOLOR
    beq :+
    ora #$10
:   sta $d016
    pla
    sta $01
    pla
    sta $00
    plp
    clc
    rts
@ownership:
    lda #0
    sta dos64_render_graphics_request+RG_DONE
    lda #RG_FAILED
    sta dos64_render_graphics_request+RG_STATUS
    lda #RG_ERR_ARGUMENT
    sta dos64_render_graphics_request+RG_ERROR
@failed:
    pla
    sta $01
    pla
    sta $00
    plp
    sec
    rts
