.setcpu "6502"
.import reu_transfer, REU_TILE
.importzp reu_addr, reu_ram, reu_size, reu_direction
.ifdef GROUP4_BENCHMARK
    .import group4_dot
    MATRIX_DOT = group4_dot
.else
    .import dot_w8a16
    MATRIX_DOT = dot_w8a16
.endif
.ifdef GROUP4_EXPERIMENT
    .import group4_dot, group4_tile
    .export matrix_project_group4
.endif
.ifdef GROUP8_EXPERIMENT
    .import reu_group8_read, REU_GROUP8_TILE
    .import group8_dot
    .export matrix_project_group8
.endif
.importzp dot_weights, dot_columns, dot_result
.export matrix_tile, matrix_rows, matrix_dots

.segment "ZEROPAGE"
matrix_rows: .res 1
row_bytes: .res 2
rows_left: .res 1
output_index: .res 1

.segment "BSS"
matrix_dots: .res 16 * 4

.segment "CODE"
; Read and execute one tile, up to 16 rows. Activations are already prepared.
; Pass its 24-bit REU offset, row count and the number of columns (0 = 256).
; Produces unpacked little-endian signed 32-bit row sums in matrix_dots.
; Row-scale bytes follow tile weights at dot_weights on return.
; Carry set if the request or DMA fails. reu_addr advances to the next tile.
.ifdef GROUP4_EXPERIMENT
matrix_tile:
    lda #0
    sta group4_tile
.proc tile_for_layout
.else
.proc matrix_tile
.endif
    lda matrix_rows
    beq invalid
    cmp #17
    bcc valid
invalid:
    sec
    rts
valid:
    sta rows_left
.ifdef GROUP8_EXPERIMENT
    lda group4_tile
    cmp #2
    bne :+
    lda dot_columns
    cmp #96
    bne invalid
:
.endif
    lda dot_columns
    sta row_bytes
    lda #0
    ldx dot_columns
    bne :+
    lda #1
:
    sta row_bytes+1

    ; Include the three scale bytes per row. A tile uses at most 4144 bytes.
    lda #0
    sta reu_size
    sta reu_size+1
    ldx matrix_rows
size:
    clc
    lda reu_size
    adc row_bytes
    sta reu_size
    lda reu_size+1
    adc row_bytes+1
    sta reu_size+1
    clc
    lda reu_size
    adc #3
    sta reu_size
    bcc :+
    inc reu_size+1
:
    dex
    bne size
    lda #<REU_TILE
    sta reu_ram
    sta dot_weights
    lda #>REU_TILE
.ifdef GROUP8_EXPERIMENT
    ldx group4_tile
    cpx #2
    bne :+
    .assert <REU_GROUP8_TILE = <REU_TILE, lderror, "DMA tile low bytes must match"
    lda #>REU_GROUP8_TILE
:
.endif
    sta reu_ram+1
    sta dot_weights+1
    lda #0
    sta reu_direction
    inc reu_direction
    sta output_index
.ifdef GROUP8_EXPERIMENT
    cpx #2
    bne :+
    jsr reu_group8_read
    jmp dma_status
:
.endif
    jsr reu_transfer
.ifdef GROUP8_EXPERIMENT
dma_status:
.endif
    bcs error
row:
.ifdef GROUP4_EXPERIMENT
    lda group4_tile
    beq raw
.ifdef GROUP8_EXPERIMENT
    cmp #2
    bne :+
    jsr group8_dot
    jmp collect
:
.endif
    jsr group4_dot
    jmp collect
raw:
.endif
    jsr MATRIX_DOT
.ifdef GROUP4_EXPERIMENT
collect:
.endif
    ldx output_index
    .repeat 4, I
        lda dot_result+I
        sta matrix_dots,x
        inx
    .endrepeat
    stx output_index
    clc
    lda dot_weights
    adc row_bytes
    sta dot_weights
    lda dot_weights+1
    adc row_bytes+1
    sta dot_weights+1
    dec rows_left
    bne row
    clc
    rts
error:
    sec
    rts
.endproc

.import scale_dot
.importzp scale_factor, scale_value
.export matrix_project

.segment "ZEROPAGE"
scale_index: .res 1
scaled_rows: .res 1

.segment "CODE"
; Read, dot and rescale a tile. scale_shift is the input vector exponent.
; Overwrites matrix_dots with signed working-unit outputs on success.
.ifdef GROUP4_EXPERIMENT
matrix_project:
    lda #0
    beq project_with_layout
.ifdef GROUP8_EXPERIMENT
matrix_project_group8:
    lda #2
    bne project_with_layout
.endif
matrix_project_group4:
    lda #1
project_with_layout:
    sta group4_tile
.proc project_rows
    jsr tile_for_layout
.else
.proc matrix_project
    jsr matrix_tile
.endif
    bcs failed
    lda matrix_rows
    sta scaled_rows
    lda #0
    sta scale_index
row:
    ldy #0
    .repeat 3, I
        lda (dot_weights),y
        sta scale_factor+I
        iny
    .endrepeat
    clc
    lda dot_weights
    adc #3
    sta dot_weights
    bcc :+
    inc dot_weights+1
:
    ldx scale_index
    .repeat 4, I
        lda matrix_dots+I,x
        sta dot_result+I
    .endrepeat
    jsr scale_dot
    bcs failed
    ldx scale_index
    .repeat 4, I
        lda scale_value+I
        sta matrix_dots+I,x
    .endrepeat
    txa
    clc
    adc #4
    sta scale_index
    dec scaled_rows
    bne row
    clc
failed:
    rts
.endproc
