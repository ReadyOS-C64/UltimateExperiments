.setcpu "6502"
.include "bundle.inc"
.import reu_transfer
.importzp reu_addr, reu_ram, reu_size, reu_direction
.export verify_model_image, model_crc

TILE = $8000
CHUNK = $2000
PAGES = MODEL_SIZE / CHUNK
TAIL = MODEL_SIZE .mod CHUNK

pointer = $f0
page_limit = $f2
byte_limit = $f3

.segment "PROBEBSS"
blocks:    .res 1
model_crc: .res 4

.segment "PROBE"
verify_model_image:
    lda #$ff
    .repeat 4, I
        sta model_crc+I
    .endrepeat
    lda #PAGES
    sta blocks
    lda #0
    sta reu_addr
    sta reu_addr+1
    sta reu_addr+2
verify_block:
    lda #<CHUNK
    ldx #>CHUNK
    ldy blocks
    bne stage
    lda #<TAIL
    ldx #>TAIL
stage:
    sta byte_limit
    stx page_limit
    sta reu_size
    stx reu_size+1
    ora reu_size+1
    beq final
    lda #<TILE
    sta reu_ram
    sta pointer
    lda #>TILE
    sta reu_ram+1
    sta pointer+1
    lda #1
    sta reu_direction
    jsr reu_transfer
    bcs done
    ldy #0
full_page:
    lda page_limit
    beq partial
full_byte:
    jsr update_crc
    iny
    bne full_byte
    inc pointer+1
    dec page_limit
    bne full_byte
partial:
    cpy byte_limit
    beq next_block
    jsr update_crc
    iny
    bne partial
next_block:
    lda blocks
    beq final
    dec blocks
    jmp verify_block
final:
    .repeat 4, I
        lda model_crc+I
        eor #$ff
        sta model_crc+I
    .endrepeat
    ldx #3
compare:
    lda model_crc,x
    cmp expected,x
    bne corrupt
    dex
    bpl compare
    clc
done:
    rts
corrupt:
    sec
    rts

update_crc:
    lda (pointer),y
    eor model_crc
    tax
    lda table0,x
    eor model_crc+1
    sta model_crc
    lda table1,x
    eor model_crc+2
    sta model_crc+1
    lda table2,x
    eor model_crc+3
    sta model_crc+2
    lda table3,x
    sta model_crc+3
    rts

expected:
    .dword MODEL_CRC32
.include "crc_table.inc"
