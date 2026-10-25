.setcpu "6502"
.macpack longbranch
.include "fileio/api.inc"
.include "editor_file/api.inc"
.import se_f_preflight_begin,se_f_preflight_step,se_f_preflight_cancel
.import se_f_exists_begin
.import fio_cleanup
.export se_file_transport
.segment "CODE"
; Called directly by C10 opcode branch. No overlay call anywhere in this module.
se_file_transport:
    cmp #FT_INIT
    jeq se_io_init
    cmp #FT_PREFLIGHT_BEGIN
    jeq se_f_preflight_begin
    cmp #FT_EXISTS_BEGIN
    jeq se_f_exists_begin
    cmp #FT_PREFLIGHT_STEP
    jeq se_f_preflight_step
    cmp #FT_PREFLIGHT_CANCEL
    jeq se_f_preflight_cancel
    cmp #FT_VALIDATE
    jeq se_io_validate
    cmp #FT_OPEN
    beq open
    cmp #FT_READ
    jeq se_io_read_chunk
    cmp #FT_CREATE
    jeq se_io_create_temp
    cmp #FT_WRITE
    jeq se_io_write_chunk
    cmp #FT_CLOSE
    jeq se_io_close
    cmp #FT_RENAME
    jeq se_io_rename
    cmp #FT_BACKUP
    jeq se_io_make_backup
    cmp #FT_SCRATCH_TEMP
    beq temp
    cmp #FT_SCRATCH_BACKUP
    beq backup
    cmp #FT_ABORT
    jeq se_io_abort
    cmp #FT_DIRECTORY
    jeq se_io_directory_open
    cmp #FT_NEXT
    jeq se_io_directory_next
    cmp #FT_EMPTY_CLOSE
    beq empty_close
    lda #FIO_ARGUMENT
    sec
    rts
open:
    jsr se_io_open_read
    bcs @done
    lda se_f_preflight_result
    beq @done
    lda #$40 ; only after exact zero-length on-disk chain preflight
    sta se_io_eof
@done:
    rts
temp:
    lda #0
    jmp se_io_scratch_owned
backup:
    lda #1
    jmp se_io_scratch_owned
empty_close:
    ; Explicit, narrow editor/D81 path. Provider's generic98 guard stays intact.
    lda se_f_length
    ora se_f_length+1
    ora se_f_length+2
    bne invalid
    lda se_io_owned_temp
    beq invalid
    lda se_io_mode
    cmp #2
    bne invalid
    lda se_io_wrote
    bne invalid
    jsr fio_cleanup
    jmp se_io_status
invalid:
    lda #FIO_STATE
    sec
    rts
