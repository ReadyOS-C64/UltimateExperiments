.setcpu "6502"
.macpack longbranch
.include "fileio/api.inc"
.import fio_command,fio_command_len,fio_send_command
.export se_f_preflight_begin,se_f_preflight_step,se_f_preflight_cancel,se_f_exists_begin
.import se_f_preflight_phase,se_f_preflight_result,se_f_preflight_track,se_f_preflight_sector,se_f_preflight_link,se_f_preflight_remaining,se_f_preflight_index,se_f_preflight_entry,se_f_preflight_value,se_f_preflight_error,se_f_preflight_length,se_f_preflight_blocks
.import se_f_preflight_kind
.segment "CODE"
; Read-only unpartitioned1581/D81 chain preflight. Never writes disk sectors.
; Native filename/device in existing fileio frame. No open data consumer allowed.
; Cclear/A2pending, A0completed; se_f_preflight_result1 denotes exact zero bytes.
se_f_preflight_begin:
    lda #0
    beq begin_mode
; Same bounded raw directory scan, but any non-DEL entry means occupied.
; A0/Cclear occupied; DOS62/Cset definite absence; no file-chain or W-open.
se_f_exists_begin:
    lda #1
begin_mode:
    pha
    jsr se_io_validate
    bcc @available
    tax
    pla
    txa
    sec
    rts
@available:
    lda se_io_mode
    ora se_f_preflight_phase
    bne @busy
    pla
    sta se_f_preflight_kind
    lda #1
    ldx #<buffer_name
    ldy #>buffer_name
    jsr $FFBD
    lda #7
    ldx se_io_device
    ldy #3
    jsr $FFBA
    jsr $FFC0
    jcs io_error
    jsr $FFB7
    sta se_io_raw_status
    jne io_error
    lda #0
    sta se_f_preflight_result
    sta se_f_preflight_length
    sta se_f_preflight_length+1
    sta se_f_preflight_length+2
    sta se_f_preflight_blocks
    sta se_f_preflight_blocks+1
    sta se_f_preflight_sector
    lda #40
    sta se_f_preflight_track
    sta se_f_preflight_remaining
    lda #1
    sta se_f_preflight_phase
    lda #2
    clc
@return:
    rts
@busy:
    pla
    lda #FIO_BUSY
    sec
    rts
se_f_preflight_step:
    lda se_f_preflight_phase
    jeq state_error
    cmp #4
    jcs state_error
    lda se_f_preflight_track
    jeq format_error
    cmp #81
    jcs format_error
    lda se_f_preflight_sector
    cmp #40
    jcs format_error
    ldx #11
@command:
    lda u1_text,x
    sta fio_command,x
    dex
    bpl @command
    lda se_f_preflight_track
    jsr decimal
    stx fio_command+7
    sta fio_command+8
    lda se_f_preflight_sector
    jsr decimal
    stx fio_command+10
    sta fio_command+11
    lda #12
    sta fio_command_len
    jsr fio_send_command
    jcs failed
    ldx #7
    jsr $FFC6
    jcs io_error
    ldy #0
@read:
    sty se_f_preflight_index
    jsr $FFCF
    sta se_f_preflight_value
    jsr $FFB7
    sta se_io_raw_status
    and #$BF
    jne io_error
    ldy se_f_preflight_index
    lda se_f_preflight_value
    sta $8000,y
    iny
    bne @read
    jsr $FFCC
    lda se_f_preflight_phase
    cmp #3
    jeq first_block
    lda $8000
    sta se_f_preflight_link
    lda $8001
    sta se_f_preflight_link+1
    lda se_f_preflight_phase
    cmp #1
    bne directory
    lda se_f_preflight_link
    jeq format_error ;a header cannot terminate an otherwise unscanned directory
    lda #2
    sta se_f_preflight_phase
    jmp next_directory
directory:
    ldx #0
@record:
    stx se_f_preflight_entry
    lda se_f_preflight_kind
    beq @closed_seq
    lda $8002,x
    and #7 ;DEL is unused; closed, splat, locked and every other type occupy
    jeq @next
    bne @compare_name
@closed_seq:
    lda $8002,x
    and #$87
    cmp #$81 ;closedSEQ; lockedbit allowed
    jne @next
@compare_name:
    txa
    clc
    adc #5
    tax
    ldy #0
@name:
    cpy se_io_name_len
    bcc @native
    lda #$A0
    bne @compare
@native:
    lda se_io_name,y
@compare:
    cmp $8000,x
    bne @next
    lda se_f_preflight_kind
    beq @continue
    cpy se_io_name_len
    bcs @occupied ;first matching A0 ends DOS lookup, even with a raw suffix
@continue:
    inx
    iny
    cpy #16
    bcc @name
    lda se_f_preflight_kind
    bne @occupied
    ldx se_f_preflight_entry
    lda $8003,x
    sta se_f_preflight_track
    lda $8004,x
    sta se_f_preflight_sector
    lda #3
    sta se_f_preflight_phase
    jmp pending
@occupied:
    jsr se_f_preflight_cancel
    lda #0
    clc
    rts
@next:
    ldx se_f_preflight_entry
    txa
    clc
    adc #32
    tax
    bne @record
next_directory:
    dec se_f_preflight_remaining
    jeq format_error
    lda se_f_preflight_link
    jeq missing
    cmp #40
    jne format_error
    sta se_f_preflight_track
    lda se_f_preflight_link+1
    cmp #3
    jcc format_error
    cmp #40
    jcs format_error
    sta se_f_preflight_sector
pending:
    lda #2
    clc
    rts
first_block:
    ; Each call inspects exactly one payload sector. D81 has at most3200.
    inc se_f_preflight_blocks
    bne :+
    inc se_f_preflight_blocks+1
:   lda se_f_preflight_blocks+1
    cmp #>3201
    bcc @bounded
    bne @bad
    lda se_f_preflight_blocks
    cmp #<3201
    bcs @bad
@bounded:
    lda $8000
    beq @last
    sta se_f_preflight_track
    lda $8001
    sta se_f_preflight_sector
    lda #254
    jsr add_length
    jmp pending
@last:
    lda $8001
    beq @bad
    sec
    sbc #1
    jsr add_length
    lda se_f_preflight_length
    ora se_f_preflight_length+1
    ora se_f_preflight_length+2
    bne :+
    inc se_f_preflight_result
:   jsr se_f_preflight_cancel
    lda #0
    clc
    rts
@bad:
    jmp format_error
add_length:
    clc
    adc se_f_preflight_length
    sta se_f_preflight_length
    lda se_f_preflight_length+1
    adc #0
    sta se_f_preflight_length+1
    lda se_f_preflight_length+2
    adc #0
    sta se_f_preflight_length+2
    rts
decimal:
    ldx #$30
@tens:
    cmp #10
    bcc @ones
    sec
    sbc #10
    inx
    bne @tens
@ones:
    clc
    adc #$30
    rts
missing:
    lda #62
    sta se_io_dos_code
    lda #FIO_DOS
    bne failed
state_error:
    lda #FIO_STATE
    sec
    rts
format_error:
    lda #FIO_FORMAT
    bne failed
io_error:
    jsr $FFB7
    sta se_io_raw_status
    lda #FIO_IO
failed:
    sta se_f_preflight_error
    jsr se_f_preflight_cancel
    lda se_f_preflight_error
    sec
    rts
se_f_preflight_cancel:
    jsr $FFCC
    lda #7
    jsr $FFC3
    lda #0
    sta se_f_preflight_phase
    sta se_f_preflight_kind
    clc
    rts
.segment "RODATA"
buffer_name: .byte "#"
u1_text: .byte "U1:3 0 00 00"
