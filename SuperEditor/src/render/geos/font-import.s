; C28 cold-only actual KERNAL stream into two FD-owned logical data banks.
.setcpu "6502"
.macpack longbranch
.include "render/geos/font-store.inc"
.include "geos-font-pack.inc"
.import se_reu_alloc,se_reu_free,se_reu_epoch,se_reu_logical_owner
.import se_reu_copy,se_reu_logical,se_reu_offset,se_reu_length,se_reu_c64
.import se_crc_init,se_crc_byte,se_crc_value
.export se_gf_import_begin,se_gf_import_step,se_gf_import_cancel
S=se_gf_state
.segment "CODE"
se_gf_import_begin:
    cmp #8
    beq :+
    cmp #9
    jne argument
:
    pha
    lda S+GF_READY
    ora S+GF_BUSY
    ora S+GF_HANDLE0
    ora S+GF_HANDLE1
    ora $98
    bne @busy
    pla
    sta S+GF_TEMP+8 ;frozen device until SETLFS
    ldx #1
@epoch:
    lda se_reu_epoch,x
    sta S+GF_EPOCH,x
    dex
    bpl @epoch
    lda #0
    ldx #6
@clear:
    sta S+GF_POSITION,x ;position3,done2,CRC2
    dex
    bpl @clear
    sta S+GF_ERROR
    sta S+GF_VALID
    lda #1
    sta S+GF_BUSY
    lda #GF_OWNER
    jsr se_reu_alloc
    jcs fail
    sta S+GF_HANDLE0
    lda #GF_OWNER
    jsr se_reu_alloc
    jcs fail
    sta S+GF_HANDLE1
    lda #15
    ldx #<filename
    ldy #>filename
    jsr $FFBD
    lda #GF_DATA_LFN
    ldx S+GF_TEMP+8
    ldy #2
    jsr $FFBA
    lda #1
    sta S+GF_OWNED ;an attempted OPEN owns its cleanup responsibility
    jsr $FFC0
    jcs io_fail
    jsr $FFB7
    sta S+GF_RAW_STATUS
    jne io_fail
    jsr se_crc_init
    lda se_crc_value
    sta S+GF_CRC
    lda se_crc_value+1
    sta S+GF_CRC+1
    jmp pending
@busy:
    pla
    lda #GF_BUSY_ERROR
    sec
    rts
se_gf_import_step:
    lda S+GF_BUSY
    cmp #1
    jne state
    ldx #1
@guard:
    lda S+GF_EPOCH,x
    cmp se_reu_epoch,x
    jne stale
    lda S+GF_HANDLE0,x
    jeq stale
    tay
    lda se_reu_logical_owner,y
    cmp #GF_OWNER
    jne stale
    dex
    bpl @guard
    lda #0
    sta S+GF_DONE
    sta S+GF_DONE+1
    lda S+GF_CRC
    sta se_crc_value
    lda S+GF_CRC+1
    sta se_crc_value+1
    ldx #GF_DATA_LFN
    jsr $FFC6
    jcs io_fail
read_byte:
    jsr $FFCF
    sta S+GF_TEMP+7
    jsr $FFB7
    sta S+GF_RAW_STATUS
    and #$BF
    jne io_fail
    ldy S+GF_DONE
    lda S+GF_TEMP+7
    sta GF_BUFFER,y
    jsr se_crc_byte
    lda S+GF_POSITION+2
    ora S+GF_POSITION+1
    ora S+GF_POSITION
    bne @count
    cpy #32
    bcs @count
    lda S+GF_TEMP+7
    cmp gf_pack_header,y
    jne format
@count:
    inc S+GF_DONE
    bne :+
    inc S+GF_DONE+1
:
    clc
    lda S+GF_POSITION
    adc S+GF_DONE
    sta S+GF_TEMP
    lda S+GF_POSITION+1
    adc S+GF_DONE+1
    sta S+GF_TEMP+1
    lda S+GF_POSITION+2
    adc #0
    sta S+GF_TEMP+2
    lda S+GF_RAW_STATUS
    and #$40
    bne @last
    lda S+GF_TEMP+2
    cmp #^GF_PACK_BYTES
    bcc @more
    jne format
    lda S+GF_TEMP+1
    cmp #>GF_PACK_BYTES
    bcc @more
    jne format
    lda S+GF_TEMP
    cmp #<GF_PACK_BYTES
    jcs format ;expected lastbyte MUST carry EOI, no extra data accepted
@more:
    lda S+GF_DONE+1
    jeq read_byte
    bne stash
@last:
    lda S+GF_TEMP
    cmp #<GF_PACK_BYTES
    jne format
    lda S+GF_TEMP+1
    cmp #>GF_PACK_BYTES
    jne format
    lda S+GF_TEMP+2
    cmp #^GF_PACK_BYTES
    jne format
stash:
    jsr $FFCC
    lda se_crc_value
    sta S+GF_CRC
    lda se_crc_value+1
    sta S+GF_CRC+1
    ldx S+GF_POSITION+2
    cpx #2
    jcs format
    lda S+GF_HANDLE0,x
    sta se_reu_logical
    lda S+GF_POSITION
    sta se_reu_offset
    lda S+GF_POSITION+1
    sta se_reu_offset+1
    lda S+GF_DONE
    sta se_reu_length
    lda S+GF_DONE+1
    sta se_reu_length+1
    lda #0
    sta se_reu_c64
    lda #>GF_BUFFER
    sta se_reu_c64+1
    lda #0
    jsr se_reu_copy
    jcs fail
    ldx #2
@progress:
    lda S+GF_TEMP,x
    sta S+GF_POSITION,x
    dex
    bpl @progress
    lda S+GF_RAW_STATUS
    and #$40
    beq pending
    lda S+GF_CRC
    cmp #<GF_PACK_CRC
    jne format
    lda S+GF_CRC+1
    cmp #>GF_PACK_CRC
    jne format
    jsr close
    bcs io_fail
    lda #0
    sta S+GF_BUSY
    lda #GF_READY_VALUE
    sta S+GF_READY
    lda #0
    clc
    rts
pending:
    lda #1
    clc
    rts
se_gf_import_cancel:
    lda S+GF_BUSY
    beq @done
    lda #0
    sta S+GF_ERROR
    jsr cleanup
@done:
    lda #0
    clc
    rts
io_fail:
    lda #GF_IO_ERROR
    bne fail
format:
    lda #GF_FORMAT
    bne fail
stale:
    lda #GF_STALE
    bne fail
state:
    lda #$97
    sec
    rts
argument:
    lda #GF_ARGUMENT
    sec
    rts
fail:
    sta S+GF_ERROR
    jsr cleanup
    lda S+GF_ERROR
    sec
    rts
close:
    lda S+GF_OWNED
    beq @ok
    jsr $FFCC
    lda #GF_DATA_LFN
    jsr $FFC3
    jsr $FFB7
    sta S+GF_RAW_STATUS
    lda #0
    sta S+GF_OWNED
    lda S+GF_RAW_STATUS
    and #$BF
    bne @bad
@ok:
    clc
    rts
@bad:
    sec
    rts
cleanup:
    jsr close
    lda #0
    sta S+GF_READY
    sta S+GF_BUSY
    sta S+GF_VALID
    ldx #1
@epoch:
    lda S+GF_EPOCH,x
    cmp se_reu_epoch,x
    bne @forget
    dex
    bpl @epoch
    lda #1
    sta S+GF_TEMP+6
@free:
    ldx S+GF_TEMP+6
    lda S+GF_HANDLE0,x
    beq @next
    tax
    lda se_reu_logical_owner,x
    cmp #GF_OWNER
    bne @clear
    jsr se_reu_free ;validates selected physical ownership before mutation
    bcs @next ;retain refused sameepoch FD capability for explicit diagnosis
@clear:
    ldx S+GF_TEMP+6
    lda #0
    sta S+GF_HANDLE0,x
@next:
    dec S+GF_TEMP+6
    bpl @free
    rts
@forget:
    lda #0
    sta S+GF_HANDLE0
    sta S+GF_HANDLE1
    rts
.segment "RODATA"
filename: .byte "0:GEOSFONTS,S,R"
GF_IMPORT_METADATA
