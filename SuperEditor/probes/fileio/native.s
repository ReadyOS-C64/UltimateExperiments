.setcpu "6502"
.macpack longbranch
.include "fileio/api.inc"
.import __BSS_RUN__, __BSS_SIZE__
.export fio_native_result,fio_native_stage,fio_native_error
.export fio_native_empty_done,fio_native_empty_eof,fio_native_empty_byte
.segment "LOADADDR"
    .word $0801
.segment "BOOT"
    .word end_boot,10
    .byte $9E,"4096",0
end_boot: .word 0
.segment "BSS"
fio_native_result: .res 1
fio_native_stage: .res 1
fio_native_error: .res 1
fio_native_empty_done: .res 2
fio_native_empty_eof: .res 1
fio_native_empty_byte: .res 1
.segment "ENTRY"
native_entry:
    cld
    lda #0
    tax
@clear:
    sta __BSS_RUN__,x
    inx
    bne @clear
    ldx #<(__BSS_SIZE__-256)
@tail:
    dex
    sta __BSS_RUN__+256,x
    cpx #0
    bne @tail
    jsr se_io_init
    inc fio_native_stage ;1 create/write273 bytes
    jsr name_temp
    jsr se_io_create_temp
    jcs failed
    ldx #0
@fill:
    txa
    sta FIO_BUFFER,x
    inx
    bne @fill
    lda #0
    sta se_io_count
    jsr se_io_write_chunk
    jcs failed
    lda #17
    sta se_io_count
    jsr se_io_write_chunk
    jcs failed
    jsr se_io_close
    jcs failed
    inc fio_native_stage ;2 binary readback
    jsr se_io_open_read
    jcs failed
    lda #0
    sta se_io_count
    jsr se_io_read_chunk
    jcs failed
    lda se_io_done
    jne mismatch
    lda se_io_done+1
    cmp #1
    jne mismatch
    lda se_io_eof
    jne mismatch
    ldx #0
@compare:
    txa
    cmp FIO_BUFFER,x
    jne mismatch
    inx
    bne @compare
    jsr se_io_read_chunk
    jcs failed
    lda se_io_done
    cmp #17
    jne mismatch
    lda se_io_done+1
    jne mismatch
    lda se_io_eof
    jeq mismatch
    ldx #0
@compare_tail:
    txa
    cmp FIO_BUFFER,x
    jne mismatch
    inx
    cpx #17
    bne @compare_tail
    jsr se_io_close
    jcs failed
    inc fio_native_stage ;3 backup/promotion/exact-owned scratch
    jsr name_target
    ldx #7
@backup:
    lda backup_name,x
    sta se_io_other,x
    dex
    bpl @backup
    lda #8
    sta se_io_other_len
    jsr se_io_make_backup
    jcs failed
    jsr name_temp
    ldx #7
@target:
    lda target_name,x
    sta se_io_other,x
    dex
    bpl @target
    jsr se_io_rename
    jcs failed
    lda #1
    jsr se_io_scratch_owned
    jcs failed
    inc fio_native_stage ;4 directory includes promoted SEQ
    jsr se_io_directory_open
    jcs failed
@directory:
    jsr se_io_directory_next
    bcc @entry
    cmp #FIO_LIMIT
    jeq @directory
    jmp failed
@entry:
    lda se_io_dir_len
    jeq mismatch
    cmp #8
    bne @directory
    ldx #7
@dir_name:
    lda target_name,x
    cmp se_io_dir_name,x
    bne @directory
    dex
    bpl @dir_name
    jsr se_io_close
    jcs failed
    inc fio_native_stage ;5 missing-file refusal closes all channels
    lda #7
    sta se_io_name_len
    ldx #6
@missing:
    lda missing_name,x
    sta se_io_name,x
    dex
    bpl @missing
    jsr se_io_open_read
    jcc mismatch
    cmp #FIO_DOS
    bne failed
    lda se_io_dos_code
    cmp #62
    jne mismatch
    inc fio_native_stage ;6 refuse unproven empty SEQ and remove owned artifact
    ldx #4
@empty:
    lda empty_name,x
    sta se_io_name,x
    dex
    bpl @empty
    lda #5
    sta se_io_name_len
    jsr se_io_create_temp
    bcs failed
    jsr se_io_close
    bcc mismatch
    cmp #FIO_EMPTY
    bne failed
    sta fio_native_empty_byte
    lda #0
    jsr se_io_scratch_owned
    bcs failed
    inc fio_native_stage
    lda #1
    sta fio_native_result
    ldx #0
@passed:
    lda passed_text,x
    beq idle
    jsr $FFD2
    inx
    bne @passed
mismatch:
    lda #$FE
failed:
    sta fio_native_error
    jsr se_io_abort
    lda #$FF
    sta fio_native_result
    ldx #0
@failed:
    lda failed_text,x
    beq idle
    jsr $FFD2
    inx
    bne @failed
idle:
    jmp idle
.segment "CODE"
name_temp:
    ldx #7
@loop:
    lda temp_name,x
    sta se_io_name,x
    dex
    bpl @loop
    lda #8
    sta se_io_name_len
    rts
name_target:
    ldx #7
@loop:
    lda target_name,x
    sta se_io_name,x
    dex
    bpl @loop
    lda #8
    sta se_io_name_len
    rts
.segment "RODATA"
temp_name: .byte "SEPROBET"
backup_name: .byte "SEPROBEB"
target_name: .byte "ORIGINAL"
missing_name: .byte "MISSING"
empty_name: .byte "EMPTY"
passed_text: .byte 13,"FILEIO NATIVE PASSED",13,0
failed_text: .byte 13,"FILEIO NATIVE FAILED",13,0
.assert __BSS_SIZE__ > 256,lderror,"native clear requires>256 bytes"
.assert __BSS_SIZE__ < 512,lderror,"native clear exceeds two pages"
.assert __BSS_RUN__+__BSS_SIZE__ <= $C600,lderror,"fileIO touches reserved shim"
