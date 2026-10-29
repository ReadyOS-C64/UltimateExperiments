.setcpu "6502"
.macpack longbranch
.include "fileio/internal.inc"
.export se_io_directory_open, se_io_directory_next, fio_drain_line
.segment "CODE"
se_io_directory_open:
    lda se_io_mode
    bne @busy
    lda se_io_device
    cmp #8
    beq :+
    cmp #9
    bne @argument
:   lda #$24 ; $0:*=S, type-filter at drive as well as bounded local parser
    sta fio_command
    lda #$30
    sta fio_command+1
    lda #$3A
    sta fio_command+2
    lda #$2A
    sta fio_command+3
    lda #$3D
    sta fio_command+4
    lda #$53
    sta fio_command+5
    lda #6
    sta fio_command_len
    lda #3
    sta se_io_mode
    lda #0
    sta se_io_eof
    jsr fio_open ; SA0: directory BASIC stream, never LOAD
    bcs @fail
    jsr se_io_status
    bcs @fail
    jsr fio_select_in
    bcs @fail
    jsr dir_byte ; two-byte load address is data, never a destination
    bcs @fail
    jsr dir_byte
    bcs @fail
    jsr $FFCC
    jmp fio_ok
@busy:
    lda #FIO_BUSY
    sec
    rts
@argument:
    lda #FIO_ARGUMENT
    sec
    rts
@fail:
    jmp fio_fail

; One matching SEQ entry, or dir_len0/eof nonzero. Scans at most32 listing lines
; per call; FIO_LIMIT with data channel still open means call again to continue.
; A malformed/overlong line is a failure which closes owned data channel.
se_io_directory_next:
    lda se_io_mode
    cmp #3
    jne @state
    lda #0
    sta se_io_dir_len
    lda se_io_eof
    jne @ok
    lda #32
    pha
    jsr fio_select_in
    jcs @failed_stack
@line:
    jsr dir_byte
    jcs @failed_stack
    sta se_io_dir_blocks
    jsr dir_byte
    jcs @failed_stack
    ora se_io_dir_blocks
    beq @end
    jsr dir_byte
    jcs @failed_stack
    sta se_io_dir_blocks
    jsr dir_byte
    jcs @failed_stack
    sta se_io_dir_blocks+1
    jsr fio_drain_line
    jcs @failed_stack
    jsr parse_line
    lda se_io_dir_len
    bne @return
    pla
    sec
    sbc #1
    pha
    bne @line
    pla
    jsr $FFCC
    lda #FIO_LIMIT
    sec
    rts
@end:
    lda #1
    sta se_io_eof
@return:
    pla
    jsr $FFCC
@ok:
    jmp fio_ok
@failed_stack:
    tax
    pla
    txa
    jmp fio_fail
@state:
    lda #FIO_STATE
    sec
    rts
dir_byte:
    lda se_io_eof
    bne @short
    jmp fio_byte
@short:
    lda #FIO_FORMAT
    sec
    rts
fio_drain_line:
    ldx #0
@read:
    stx fio_line_len
    jsr dir_byte
    bcs @done
    ldx fio_line_len
    cmp #0
    beq @line_end
    cpx #82
    bcs @limit
    sta fio_line,x
    inx
    bne @read
@line_end:
    clc
    rts
@limit:
    lda #FIO_LIMIT
    sec
@done:
    rts
parse_line:
    ldx #0
    stx se_io_dir_flags
@quote:
    cpx fio_line_len
    bcs @reject
    lda fio_line,x
    inx
    cmp #$22
    bne @quote
    ldy #0
@name:
    cpx fio_line_len
    bcs @reject
    lda fio_line,x
    inx
    cmp #$22
    beq @type
    cpy #16
    bcs @reject
    sta se_io_dir_name,y
    iny
    bne @name
@type:
    sty se_io_dir_len
@spaces:
    cpx fio_line_len
    bcs @reject
    lda fio_line,x
    inx
    cmp #$20
    beq @spaces
    cmp #$2A
    bne :+
    inc se_io_dir_flags
    cpx fio_line_len
    bcs @reject
    lda fio_line,x
    inx
:   cmp #$53
    bne @reject
    cpx fio_line_len
    bcs @reject
    lda fio_line,x
    inx
    cmp #$45
    bne @reject
    cpx fio_line_len
    bcs @reject
    lda fio_line,x
    inx
    cmp #$51
    bne @reject
    cpx fio_line_len
    bcs @done
    lda fio_line,x
    cmp #$3C
    bne @done
    lda se_io_dir_flags
    ora #2
    sta se_io_dir_flags
@done:
    rts
@reject:
    lda #0
    sta se_io_dir_len
    rts
