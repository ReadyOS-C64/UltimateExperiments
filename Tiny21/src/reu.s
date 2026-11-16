.setcpu "6502"
.export reu_transfer, reu_addr, reu_ram, reu_size, reu_banks, reu_direction
.export REU_TILE, REU_TILE_SIZE

REU_TILE = $8000
REU_TILE_SIZE = $2000
.ifdef GROUP8_EXPERIMENT
    .import group4_ready
    .importzp IMAGE_END_LO, IMAGE_END_MID, IMAGE_END_HI
    .export reu_group8_read, REU_GROUP8_TILE
REU_GROUP8_TILE = $c400
REU_GROUP8_TILE_END = $cb00
.endif
STATUS = $df00
COMMAND = $df01
.ifndef REU_READ_PAGE_CHUNKS
REU_READ_PAGE_CHUNKS = 0
.endif

.segment "ZEROPAGE"
reu_addr: .res 3
reu_ram: .res 2
reu_size: .res 2
reu_banks: .res 1            ; configured capacity in 512 KiB units, 1..32
reu_direction: .res 1        ; 0=write, 1=read
chunk: .res 2
bound: .res 2
last_bank: .res 1
.ifdef GROUP8_EXPERIMENT
tile_start_page: .res 1
tile_end_page: .res 1
.endif

.segment "CODE"
; Carry clear on success. Zero logical length is a no-op.
; Accept only the owned tile and a single contiguous logical REU span.
; Advances reu_addr/reu_ram and consumes reu_size on success.
; Caller keeps I/O mapped and owns the REU registers through completion.
.ifdef GROUP8_EXPERIMENT
reu_transfer:
    ldx #>REU_TILE
    lda #>(REU_TILE+REU_TILE_SIZE)
    bne validate_tile
reu_group8_read:
    lda reu_direction
    cmp #1
    beq :+
    sec
    rts
:
    ldx #>REU_GROUP8_TILE
    lda #>REU_GROUP8_TILE_END
.proc validate_tile
    stx tile_start_page
    sta tile_end_page
.else
.proc reu_transfer
.endif
    lda reu_size
    ora reu_size+1
    bne :+
    jmp ok
:
    lda reu_direction
    cmp #2
    bcs error
    ldx reu_banks
    beq error
    cpx #33
    bcs error
    lda reu_ram+1
.ifdef GROUP8_EXPERIMENT
    cmp tile_start_page
.else
    cmp #>REU_TILE
.endif
    bcc error
    ; Validate inclusive last CPU address and REU address before DMA.
    sec
    lda reu_size
    sbc #1
    sta bound
    lda reu_size+1
    sbc #0
    sta bound+1
    clc
    lda reu_ram
    adc bound
    lda reu_ram+1
    adc bound+1
    bcs error
.ifdef GROUP8_EXPERIMENT
    cmp tile_end_page
.else
    cmp #>(REU_TILE+REU_TILE_SIZE)
.endif
    bcs error
    clc
    lda reu_addr
    adc bound
.ifdef GROUP8_EXPERIMENT
    sta chunk
.endif
    lda reu_addr+1
    adc bound+1
.ifdef GROUP8_EXPERIMENT
    sta chunk+1
.endif
    lda reu_addr+2
    adc #0
    bcs error
.ifdef GROUP8_EXPERIMENT
    ldx tile_end_page
    cpx #>REU_GROUP8_TILE_END
    bne regular_tile
    ; The alternate window can read only the admitted model image.
    cmp #IMAGE_END_HI
    bcc check_bank
    bne error
    ldx chunk+1
    cpx #IMAGE_END_MID
    bcc check_bank
    bne error
    ldx chunk
    cpx #IMAGE_END_LO
    bcs error
    bcc check_bank
regular_tile:
    ; The normal tile may overwrite a live group-eight lookup table.
    ldx group4_ready
    cpx #2
    bne check_bank
    ldx #0
    stx group4_ready
check_bank:
.endif
    lsr
    lsr
    lsr
    cmp reu_banks
    bcs error
    sta last_bank
    jmp transfer
ok:
    clc
    rts
error:
    sec
    rts

transfer:
    lda reu_size
    sta chunk
    lda reu_size+1
    sta chunk+1
    lda reu_addr+2
    lsr
    lsr
    lsr
    cmp last_bank
    beq issue
    ; This tile spans a 512 KiB boundary. First send only up to it.
    sec
    lda #0
    sbc reu_addr
    sta chunk
    lda #0
    sbc reu_addr+1
    sta chunk+1
issue:
.if ::REU_READ_PAGE_CHUNKS
    ; Benchmark build: cap each read at 256 bytes after applying the bank limit.
    lda reu_direction
    beq program_registers
    lda chunk+1
    beq program_registers
    lda #0
    sta chunk
    lda #1
    sta chunk+1
program_registers:
.endif
    lda STATUS
    lda reu_ram
    sta $df02
    lda reu_ram+1
    sta $df03
    lda reu_addr
    sta $df04
    lda reu_addr+1
    sta $df05
    lda reu_addr+2
    sta $df06
    lda chunk
    sta $df07
    lda chunk+1
    sta $df08
    lda #0
    sta $df09
    sta $df0a
    lda reu_direction
    ora #$90
    sta COMMAND
    lda STATUS
    and #$40
    beq error
    clc
    lda reu_addr
    adc chunk
    sta reu_addr
    lda reu_addr+1
    adc chunk+1
    sta reu_addr+1
    bcc :+
    inc reu_addr+2
:
    clc
    lda reu_ram
    adc chunk
    sta reu_ram
    lda reu_ram+1
    adc chunk+1
    sta reu_ram+1
    sec
    lda reu_size
    sbc chunk
    sta reu_size
    lda reu_size+1
    sbc chunk+1
    sta reu_size+1
    ora reu_size
    bne :+
    jmp ok
:
    jmp transfer
.endproc
