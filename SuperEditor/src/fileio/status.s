.setcpu "6502"
.macpack longbranch
.include "fileio/internal.inc"
.export se_io_status, fio_send_command
.segment "CODE"
; Reads at most128 response bytes, copies first39 plus terminator (CR may be included). Reads CR/EOI
; even if display text truncated. DOS code00 is success, every other code is an
; explicit FIO_DOS (including73 startup; caller can display/acknowledge it).
se_io_status:
    lda #0
    sta fio_command_len
fio_send_command:
    lda se_io_device
    cmp #8
    beq :+
    cmp #9
    beq :+
    lda #FIO_ARGUMENT
    sec
    rts
:   lda #0
    sta fio_index
    sta se_io_status_text
    lda fio_command_len
    ldx #<fio_command
    ldy #>fio_command
    jsr $FFBD
    lda #FIO_COMMAND_LFN
    ldx se_io_device
    ldy #15
    jsr $FFBA
    lda #FIO_IO
    sta fio_error
    jsr $FFC0
    jcs @close
    jsr $FFB7
    sta se_io_raw_status
    jne @close
    ldx #FIO_COMMAND_LFN
    jsr $FFC6
    jcs @close
    lda #$FF
    sta se_io_dos_code
    lda #0
    sta fio_index
    sta fio_error
@read:
    jsr $FFCF
    sta fio_value
    jsr $FFB7
    sta se_io_raw_status
    and #$BF
    bne @io
    ldx fio_index
    lda fio_value
    cpx #39
    bcs :+
    sta se_io_status_text,x
:   cpx #0
    bne @second
    cmp #$30
    bcc @format
    cmp #$3A
    bcs @format
    sec
    sbc #$30
    asl
    sta se_io_dos_code
    asl
    asl
    clc
    adc se_io_dos_code
    sta se_io_dos_code
@second:
    cpx #1
    bne @more
    cmp #$30
    bcc @format
    cmp #$3A
    bcs @format
    sec
    sbc #$30
    clc
    adc se_io_dos_code
    sta se_io_dos_code
@more:
    inc fio_index
    lda fio_value
    cmp #$0D
    beq @end
    lda se_io_raw_status
    and #$40
    bne @end
    lda fio_index
    bpl @read
    lda #FIO_LIMIT
    bne @error
@end:
    lda fio_index
    cmp #3
    bcc @format
    lda se_io_status_text+2
    cmp #$2C
    bne @format
    lda se_io_dos_code
    beq @close
    lda #FIO_DOS
    bne @error
@format:
    lda #FIO_FORMAT
    bne @error
@io:
    lda #FIO_IO
@error:
    sta fio_error
@close:
    ldx fio_index
    cpx #39
    bcc :+
    ldx #39
:   lda #0
    sta se_io_status_text,x
    jsr $FFCC
    lda #FIO_COMMAND_LFN
    jsr $FFC3
    lda fio_error
    beq @ok
    sec
    rts
@ok:
    clc
    rts
