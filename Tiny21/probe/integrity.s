.setcpu "6502"
.include "bundle.inc"
.import reu_transfer
.importzp reu_addr, reu_ram, reu_size, reu_direction
.export verify_model_image, model_crc
.if DUAL_MODEL
    .import requested_model, slot_banks
.endif

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
.if DUAL_MODEL
tail_lo:   .res 1
tail_hi:   .res 1
.endif

.segment "PROBE"
verify_model_image:
    lda #$ff
    .repeat 4, I
        sta model_crc+I
    .endrepeat
    lda #0
    sta reu_addr
    sta reu_addr+1
.if DUAL_MODEL
    ldx requested_model
    lda slot_banks,x
    sta reu_addr+2
    lda pages_by_model,x
    sta blocks
    lda tail_low_by_model,x
    sta tail_lo
    lda tail_high_by_model,x
    sta tail_hi
.else
    sta reu_addr+2
    lda #PAGES
    sta blocks
.endif
verify_block:
    lda #<CHUNK
    ldx #>CHUNK
    ldy blocks
    bne stage
.if DUAL_MODEL
    lda tail_lo
    ldx tail_hi
.else
    lda #<TAIL
    ldx #>TAIL
.endif
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
.if DUAL_MODEL
    lda requested_model
    asl
    asl
    ora #3
    tay
.endif
compare:
    lda model_crc,x
.if DUAL_MODEL
    cmp expected,y
    bne corrupt
    dey
.else
    cmp expected,x
    bne corrupt
.endif
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
.if DUAL_MODEL
    .dword SECOND_MODEL_CRC
.if THIRD_MODEL
    .dword THIRD_MODEL_CRC
.endif
pages_by_model:
    .byte PAGES, SECOND_MODEL_SIZE / CHUNK
.if THIRD_MODEL
    .byte THIRD_MODEL_SIZE / CHUNK
.endif
tail_low_by_model:
    .byte <TAIL, <(SECOND_MODEL_SIZE .mod CHUNK)
.if THIRD_MODEL
    .byte <(THIRD_MODEL_SIZE .mod CHUNK)
.endif
tail_high_by_model:
    .byte >TAIL, >(SECOND_MODEL_SIZE .mod CHUNK)
.if THIRD_MODEL
    .byte >(THIRD_MODEL_SIZE .mod CHUNK)
.endif
.endif
.include "crc_table.inc"
