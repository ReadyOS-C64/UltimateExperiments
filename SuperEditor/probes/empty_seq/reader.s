.setcpu "6502"
.macpack longbranch
.include "fileio/api.inc"
.import fio_command,fio_command_len,fio_send_command
.export empty_begin,empty_step,empty_cancel,empty_phase,empty_result
.export empty_track,empty_sector,empty_link
.segment "BSS"
empty_phase: .res 1 ;0idle,1header,2directory,3firstfileblock
empty_result: .res 1 ;0nonempty,1empty; meaningful only afterA0 completion
empty_track: .res 1
empty_sector: .res 1
empty_link: .res 2
empty_remaining: .res 1
empty_index: .res 1
empty_entry: .res 1
empty_value: .res 1
empty_error: .res 1
.segment "CODE"
; Read-only D81/unpartitioned1581 provider probe, not a genericIEC guarantee.
; Native filename/device in existing fileio frame. No open data consumer allowed.
; Cclear/A2pending, A0completed; empty_result1 denotes exact zero bytes.
empty_begin:
    jsr se_io_validate
    bcs @return
    lda se_io_mode
    ora empty_phase
    bne @busy
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
    sta empty_result
    sta empty_sector
    lda #40
    sta empty_track
    sta empty_remaining
    lda #1
    sta empty_phase
    lda #2
    clc
@return:
    rts
@busy:
    lda #FIO_BUSY
    sec
    rts
empty_step:
    lda empty_phase
    jeq state_error
    cmp #4
    jcs state_error
    lda empty_track
    jeq format_error
    cmp #81
    jcs format_error
    lda empty_sector
    cmp #40
    jcs format_error
    ldx #11
@command:
    lda u1_text,x
    sta fio_command,x
    dex
    bpl @command
    lda empty_track
    jsr decimal
    stx fio_command+7
    sta fio_command+8
    lda empty_sector
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
    sty empty_index
    jsr $FFCF
    sta empty_value
    jsr $FFB7
    sta se_io_raw_status
    and #$BF
    jne io_error
    ldy empty_index
    lda empty_value
    sta $8000,y
    iny
    bne @read
    jsr $FFCC
    lda empty_phase
    cmp #3
    jeq first_block
    lda $8000
    sta empty_link
    lda $8001
    sta empty_link+1
    lda empty_phase
    cmp #1
    bne directory
    lda #2
    sta empty_phase
    jmp next_directory
directory:
    ldx #0
@record:
    stx empty_entry
    lda $8002,x
    and #$87
    cmp #$81 ;closedSEQ; lockedbit allowed
    bne @next
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
    inx
    iny
    cpy #16
    bcc @name
    ldx empty_entry
    lda $8003,x
    sta empty_track
    lda $8004,x
    sta empty_sector
    lda #3
    sta empty_phase
    jmp pending
@next:
    ldx empty_entry
    txa
    clc
    adc #32
    tax
    bne @record
next_directory:
    dec empty_remaining
    jeq format_error
    lda empty_link
    beq missing
    cmp #40
    jne format_error
    sta empty_track
    lda empty_link+1
    cmp #3
    jcc format_error
    cmp #40
    jcs format_error
    sta empty_sector
pending:
    lda #2
    clc
    rts
first_block:
    lda #0
    sta empty_result
    lda $8000
    bne @done ;another block implies nonempty
    lda $8001
    jeq format_error ;terminal count0 is not a valid payload length
    cmp #1
    bne @done
    inc empty_result
@done:
    jsr empty_cancel
    lda #0
    clc
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
    sta empty_error
    jsr empty_cancel
    lda empty_error
    sec
    rts
empty_cancel:
    jsr $FFCC
    lda #7
    jsr $FFC3
    lda #0
    sta empty_phase
    clc
    rts
.segment "RODATA"
buffer_name: .byte "#"
u1_text: .byte "U1:3 0 00 00"
