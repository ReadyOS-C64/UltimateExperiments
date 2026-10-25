.setcpu "6502"
.macpack longbranch
.include "fileio/internal.inc"
.export se_io_init, se_io_validate, se_io_open_read, se_io_create_write
.export se_io_close, se_io_abort, fio_open, fio_select_in, fio_select_out
.export fio_byte, fio_fail, fio_ok, fio_cleanup
.segment "CODE"
se_io_init:
    lda #0
    sta se_io_mode
    sta se_io_owned_temp
    sta se_io_owned_backup
    sta se_io_raw_status
    sta se_io_dos_code
    sta se_io_eof
    sta se_io_wrote
    lda #8
    sta se_io_device
    jmp fio_ok

; Validate frame name without changing its native PETSCII bytes. Reject DOS
; syntax, controls, wildcards, paths and all-space names. Device is exactly8/9.
se_io_validate:
    lda se_io_device
    cmp #8
    beq :+
    cmp #9
    jne @bad
:   lda se_io_name_len
    beq @bad
    cmp #17
    bcs @bad
    ldx #0
    ldy #0
@loop:
    lda se_io_name,x
    cmp #$20
    bcc @bad
    cmp #$7F
    bcc @print
    cmp #$A1 ;A0 is DOS directory padding/end-of-name, never an exact native name
    bcc @bad
@print:
    cmp #$22
    beq @bad
    cmp #$2A
    beq @bad
    cmp #$2C
    beq @bad
    cmp #$2F
    beq @bad
    cmp #$3A
    beq @bad
    cmp #$3D
    beq @bad
    cmp #$3F
    beq @bad
    cmp #$20
    beq :+
    iny
:   inx
    cpx se_io_name_len
    bcc @loop
    tya
    beq @bad
    jmp fio_ok
@bad:
    lda #FIO_ARGUMENT
    sec
    rts

se_io_open_read:
    lda #1
    bne open_file
se_io_create_write:
    lda #2
open_file:
    pha
    jsr se_io_validate
    bcs @bad
    lda se_io_mode
    bne @busy
    lda #$30 ; force drive0; partition/path syntax is never accepted in name
    sta fio_command
    lda #$3A
    sta fio_command+1
    ldx #0
@copy:
    lda se_io_name,x
    sta fio_command+2,x
    inx
    cpx se_io_name_len
    bcc @copy
    lda #$2C
    sta fio_command+2,x
    lda #$53 ; S
    sta fio_command+3,x
    lda #$2C
    sta fio_command+4,x
    pla
    sta se_io_mode
    cmp #1
    bne @write
    lda #$52 ; R
    bne :+
@write:
    lda #$57 ; W
:   sta fio_command+5,x
    txa
    clc
    adc #6
    sta fio_command_len
    lda #2 ; secondary2 for both ordinary SEQ streams
    jsr fio_open
    bcs @fail
    jsr se_io_status
    bcs @fail
    lda #0
    sta se_io_eof
    sta se_io_wrote
    jmp fio_ok
@busy:
    lda #FIO_BUSY
    sec
@bad:
    tax
    pla
    txa
    rts
@fail:
    jmp fio_fail

; A secondary address; frame command bytes. Mode has already been published so
; every failed attempted OPEN can CLOSE LFN5. No CHRIN/CHROUT stays selected.
fio_open:
    pha
    lda fio_command_len
    ldx #<fio_command
    ldy #>fio_command
    jsr $FFBD
    pla
    tay
    lda #FIO_DATA_LFN
    ldx se_io_device
    jsr $FFBA
    jsr $FFC0
    bcs @io
    jsr $FFB7
    sta se_io_raw_status
    jeq fio_ok
@io:
    jsr $FFB7
    sta se_io_raw_status
    lda #FIO_IO
    sec
    rts
fio_select_in:
    ldx #FIO_DATA_LFN
    jsr $FFC6
    bcs @bad
    jmp fio_ok
@bad:
    lda #FIO_IO
    sec
    rts
fio_select_out:
    ldx #FIO_DATA_LFN
    jsr $FFC9
    bcs @bad
    jmp fio_ok
@bad:
    lda #FIO_IO
    sec
    rts
fio_byte:
    jsr $FFCF
    sta fio_value
    jsr $FFB7
    sta se_io_raw_status
    and #$BF
    bne @bad
    lda se_io_raw_status
    and #$40
    sta se_io_eof
    lda fio_value
    clc
    rts
@bad:
    lda #FIO_IO
    sec
    rts
se_io_close:
    lda se_io_mode
    cmp #2
    bne @normal
    lda se_io_wrote
    bne @normal
    jsr fio_cleanup
    jsr se_io_status
    bcs @done
    ; Native trapped1581 OPEN-W/CLOSE without data produced254 garbage bytes.
    ; Never publish this as a successful empty save. Owned-temp capability is
    ; retained so coordinator can scratch precisely its own rejected artifact.
    lda #FIO_EMPTY
    sec
@done:
    rts
@normal:
    jsr fio_cleanup
    jmp se_io_status ; CLOSE can report write/disk-full errors only now
se_io_abort:
    jsr fio_cleanup
    jmp fio_ok
fio_fail:
    sta fio_error
    jsr fio_cleanup
    lda fio_error
    sec
    rts
fio_cleanup:
    jsr $FFCC
    lda se_io_mode
    beq :+
    lda #FIO_DATA_LFN
    jsr $FFC3
:   lda #0
    sta se_io_mode
    rts
fio_ok:
    lda #0
    clc
    rts
