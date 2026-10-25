.setcpu "6502"
.macpack longbranch
.include "fileio/internal.inc"
.export se_io_rename, se_io_create_temp, se_io_make_backup, se_io_scratch_owned
.segment "CODE"
; Create-new semantics are mandatory: no @ replace shortcut. DOS63 means the
; candidate was occupied, never authorizes scratching it. Caller selects another
; collision-checked candidate and retries. Successful OPEN alone grants ownership.
se_io_create_temp:
    lda se_io_owned_temp
    jne busy
    jsr se_io_create_write
    bcs @done
    ldx #15
@copy:
    lda se_io_name,x
    sta se_io_temp_name,x
    dex
    bpl @copy
    lda se_io_name_len
    sta se_io_temp_len
    lda #1
    sta se_io_owned_temp
    jmp fio_ok
@done:
    rts
; name=old target,other=backup candidate. Rename fails if destination exists;
; only successful rename grants capability to the exact resulting backup name.
se_io_make_backup:
    lda se_io_owned_backup
    jne busy
    jsr se_io_rename
    bcs @done
    ldx #15
@copy:
    lda se_io_other,x
    sta se_io_backup_name,x
    dex
    bpl @copy
    lda se_io_other_len
    sta se_io_backup_len
    lda #1
    sta se_io_owned_backup
    jmp fio_ok
@done:
    rts
; name=source,other=destination. Exact names only, no wildcards/replace. Caller
; chooses this user-visible filesystem mutation; this routine never guesses.
se_io_rename:
    lda se_io_mode
    jne busy
    jsr se_io_validate
    bcs @done
    jsr swap_names
    jsr se_io_validate
    php
    pha
    jsr swap_names
    pla
    plp
    bcs @done
    lda #$52 ; R0:destination=source
    sta fio_command
    lda #$30
    sta fio_command+1
    lda #$3A
    sta fio_command+2
    ldx #0
@dest:
    lda se_io_other,x
    sta fio_command+3,x
    inx
    cpx se_io_other_len
    bcc @dest
    lda #$3D
    sta fio_command+3,x
    txa
    clc
    adc #4
    tay
    ldx #0
@source:
    lda se_io_name,x
    sta fio_command,y
    iny
    inx
    cpx se_io_name_len
    bcc @source
    sty fio_command_len
    jsr fio_send_command
    bcs @done
    ; Consuming a known source invalidates only that exact capability. Arbitrary
    ; source rename cannot manufacture ownership of an existing destination.
    jsr source_is_temp
    bne :+
    lda #0
    sta se_io_owned_temp
:   jsr source_is_backup
    bne :+
    lda #0
    sta se_io_owned_backup
:   jmp fio_ok
@done:
    rts
busy:
    lda #FIO_BUSY
    sec
    rts
swap_names:
    ldx #15
@loop:
    lda se_io_name,x
    pha
    lda se_io_other,x
    sta se_io_name,x
    pla
    sta se_io_other,x
    dex
    bpl @loop
    lda se_io_name_len
    pha
    lda se_io_other_len
    sta se_io_name_len
    pla
    sta se_io_other_len
    rts
; A=0 scratch exact owned temporary; A=1 scratch exact owned backup. Input
; name is deliberately ignored. Never infer ownership from filename prefix.
se_io_scratch_owned:
    cmp #2
    bcs @ownership
    sta fio_index
    tax
    lda se_io_owned_temp,x ; two adjacent capability bytes
    beq @ownership
    lda se_io_mode
    bne busy
    lda #$53
    sta fio_command
    lda #$30
    sta fio_command+1
    lda #$3A
    sta fio_command+2
    ldx #0
    lda fio_index
    bne @backup
@temp:
    lda se_io_temp_name,x
    sta fio_command+3,x
    inx
    cpx se_io_temp_len
    bcc @temp
    bcs @send
@backup:
    lda se_io_backup_name,x
    sta fio_command+3,x
    inx
    cpx se_io_backup_len
    bcc @backup
@send:
    txa
    clc
    adc #3
    sta fio_command_len
    lda fio_index
    pha ; status reader owns fio_index
    jsr fio_send_command
    php
    tax
    pla ; status flags
    sta fio_value
    pla
    tay
    txa
    pha
    lda fio_value
    pha
    plp
    pla
    bcc @consume
    cmp #FIO_DOS
    bne @done
    ldx se_io_dos_code
    cpx #1 ; DOS01 FILES SCRATCHED is the successful scratch response
    bne @done
@consume:
    lda #0
    sta se_io_owned_temp,y
    jmp fio_ok
@ownership:
    lda #FIO_OWNERSHIP
    sec
@done:
    rts
source_is_temp:
    lda se_io_owned_temp
    beq mismatch
    lda se_io_name_len
    cmp se_io_temp_len
    bne mismatch
    ldx #0
@loop:
    lda se_io_name,x
    cmp se_io_temp_name,x
    bne mismatch
    inx
    cpx se_io_name_len
    bcc @loop
    lda #0
    rts
source_is_backup:
    lda se_io_owned_backup
    beq mismatch
    lda se_io_name_len
    cmp se_io_backup_len
    bne mismatch
    ldx #0
@loop:
    lda se_io_name,x
    cmp se_io_backup_name,x
    bne mismatch
    inx
    cpx se_io_name_len
    bcc @loop
    lda #0
    rts
mismatch:
    lda #1
    rts
