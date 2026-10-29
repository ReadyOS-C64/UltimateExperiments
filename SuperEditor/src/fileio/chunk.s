.setcpu "6502"
.macpack longbranch
.include "fileio/internal.inc"
.export se_io_read_chunk, se_io_write_chunk
.segment "CODE"
se_io_read_chunk:
    lda #0
    sta se_io_done
    sta se_io_done+1
    lda se_io_mode
    cmp #1
    bne state_error
    lda se_io_eof
    bne @done
    jsr fio_select_in
    bcs @fail
    ldy #0
@loop:
    sty fio_index
    jsr fio_byte
    bcs @fail
    ldy fio_index
    sta FIO_BUFFER,y
    inc se_io_done
    bne :+
    inc se_io_done+1
:   iny
    lda se_io_eof
    bne @clear
    cpy se_io_count
    bne @loop
@clear:
    jsr $FFCC
@done:
    jmp fio_ok
@fail:
    jmp fio_fail
se_io_write_chunk:
    lda #0
    sta se_io_done
    sta se_io_done+1
    lda se_io_mode
    cmp #2
    bne state_error
    jsr fio_select_out
    bcs @fail
    ldy #0
@loop:
    sty fio_index
    lda FIO_BUFFER,y
    jsr $FFD2
    jsr $FFB7
    sta se_io_raw_status
    bne @io
    lda #1
    sta se_io_wrote
    inc se_io_done
    bne :+
    inc se_io_done+1
:   ldy fio_index
    iny
    cpy se_io_count
    bne @loop
    jsr $FFCC
    jmp fio_ok
@io:
    lda #FIO_IO
@fail:
    jmp fio_fail
state_error:
    lda #FIO_STATE
    sec
    rts
