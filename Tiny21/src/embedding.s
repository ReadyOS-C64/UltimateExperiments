.setcpu "6502"
.import reu_transfer, REU_TILE
.importzp reu_addr, reu_ram, reu_size, reu_direction
.importzp dot_result, scale_factor, scale_shift, scale_value
.import scale_dot
.export embedding_row, embedding_index, embedding_rows, embedding_result

ROWS_PER_TILE = 16
ROW_WIDTH = 96
SCALE_WIDTH = 3
TILE_BYTES = ROWS_PER_TILE * (ROW_WIDTH + SCALE_WIDTH)
.assert TILE_BYTES < $2000, error, "embedding tile fits REU window"

.segment "ZEROPAGE"
embedding_index: .res 1
embedding_rows:  .res 1
row_ptr:         .res 2
scale_ptr:       .res 2
column:          .res 1
dest:            .res 2

.segment "BSS"
embedding_result: .res ROW_WIDTH * 4

.segment "CODE"
; Read a token or position embedding in one logical DMA and dequantize
; to 96 packed signed Q16.16 words. Caller supplies the table's REU base.
.proc embedding_row
    lda embedding_rows
    cmp #97
    beq valid_rows
    cmp #128
    beq valid_rows
invalid:
    sec
    rts
valid_rows:
    lda embedding_index
    cmp embedding_rows
    bcs invalid
    and #$f0
    sta column
    lsr
    lsr
    lsr
    lsr
    tax
    beq selected
next_tile:
    clc
    lda reu_addr
    adc #<TILE_BYTES
    sta reu_addr
    lda reu_addr+1
    adc #>TILE_BYTES
    sta reu_addr+1
    lda reu_addr+2
    adc #0
    sta reu_addr+2
    bcs invalid
    dex
    bne next_tile
selected:
    lda embedding_rows
    sec
    sbc column
    cmp #ROWS_PER_TILE
    bcc :+
    lda #ROWS_PER_TILE
:
    tax
    lda #<REU_TILE
    sta reu_ram
    sta scale_ptr
    sta row_ptr
    lda #>REU_TILE
    sta reu_ram+1
    sta scale_ptr+1
    sta row_ptr+1
    lda #0
    sta reu_size
    sta reu_size+1
size:
    clc
    lda scale_ptr
    adc #ROW_WIDTH
    sta scale_ptr
    bcc :+
    inc scale_ptr+1
:
    clc
    lda reu_size
    adc #(ROW_WIDTH + SCALE_WIDTH)
    sta reu_size
    bcc :+
    inc reu_size+1
:
    dex
    bne size
    lda #1
    sta reu_direction
    jsr reu_transfer
    bcc :+
    rts
:
    lda embedding_index
    and #$0f
    tax
    beq row_start
seek_row:
    clc
    lda row_ptr
    adc #ROW_WIDTH
    sta row_ptr
    bcc :+
    inc row_ptr+1
:
    clc
    lda scale_ptr
    adc #SCALE_WIDTH
    sta scale_ptr
    bcc :+
    inc scale_ptr+1
:
    dex
    bne seek_row
row_start:
    ldy #0
    .repeat 3, I
        lda (scale_ptr),y
        sta scale_factor+I
        iny
    .endrepeat
    lda #16
    sta scale_shift
    lda #<embedding_result
    sta dest
    lda #>embedding_result
    sta dest+1
    lda #0
    sta column
convert:
    ldy column
    lda (row_ptr),y
    sta dot_result
    lda #0
    bit dot_result
    bpl :+
    lda #$ff
:
    sta dot_result+1
    sta dot_result+2
    sta dot_result+3
    jsr scale_dot
    bcs done
    ldy #0
    .repeat 4, I
        lda scale_value+I
        sta (dest),y
        iny
    .endrepeat
    clc
    lda dest
    adc #4
    sta dest
    bcc :+
    inc dest+1
:
    inc column
    lda column
    cmp #ROW_WIDTH
    bne convert
    clc
done:
    rts
.endproc
