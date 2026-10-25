.setcpu "6502"
.macpack longbranch
.include "fileio/api.inc"
.import empty_begin,empty_step,empty_phase,empty_result
.import __BSS_RUN__,__BSS_SIZE__
.export empty_native_result,empty_native_stage,empty_native_error
.export empty_native_done,empty_native_eof,empty_native_byte
.segment "LOADADDR"
    .word $0801
.segment "BOOT"
    .word boot_end,10
    .byte $9E,"4096",0
boot_end:.word 0
.segment "BSS"
empty_native_result:.res 1
empty_native_stage:.res 1
empty_native_error:.res 1
empty_native_done:.res 2
empty_native_eof:.res 1
empty_native_byte:.res 1
target_index:.res 1
.segment "ENTRY"
native:
    cld
    lda #0
    tax
@page:
    sta __BSS_RUN__,x
    inx
    bne @page
    ldx #<(__BSS_SIZE__-256)
@tail:
    dex
    sta __BSS_RUN__+256,x
    cpx #0
    bne @tail
    jsr se_io_init
    inc empty_native_stage ;1 create empty by OPEN/CLOSE, no CHROUT at all
    lda #0
    jsr name
    jsr se_io_create_temp
    jcs failed
    jsr $FFCC
    lda #5
    jsr $FFC3 ;probe bypasses existing conservative writer98 guard
    lda #0
    sta se_io_mode
    jsr se_io_status
    jcs failed
    inc empty_native_stage ;2 preflight+real OPEN-read of native empty
    jsr safe_open
    jcs failed
    lda empty_result
    cmp #1
    jne mismatch
    jsr empty_read
    jcs failed
    inc empty_native_stage ;3 promote owned verified empty without touching others
    ldx #9
@final:
    lda final_name,x
    sta se_io_other,x
    dex
    bpl @final
    lda #10
    sta se_io_other_len
    jsr se_io_rename
    jcs failed
    inc empty_native_stage ;4 host-imported empty, not only a file we just wrote
    lda #1
    jsr name
    jsr safe_open
    jcs failed
    lda empty_result
    cmp #1
    jne mismatch
    jsr empty_read
    jcs failed
    inc empty_native_stage ;5 one NUL byte is nonempty and retained exactly
    lda #2
    jsr name
    jsr safe_open
    jcs failed
    lda empty_result
    jne mismatch
    lda #0
    sta se_io_count
    jsr se_io_read_chunk
    jcs failed
    lda se_io_done
    cmp #1
    jne mismatch
    lda se_io_done+1
    jne mismatch
    lda $8000
    jne mismatch
    jsr se_io_close
    jcs failed
    inc empty_native_stage ;6 original binary control file stays64 bytes
    lda #3
    jsr name
    jsr safe_open
    jcs failed
    lda empty_result
    jne mismatch
    lda #0
    sta se_io_count
    jsr se_io_read_chunk
    jcs failed
    lda se_io_done
    cmp #64
    jne mismatch
    lda se_io_done+1
    jne mismatch
    ldx #0
@binary:
    txa
    cmp $8000,x
    jne mismatch
    inx
    cpx #64
    bcc @binary
    jsr se_io_close
    jcs failed
    inc empty_native_stage
    lda #1
    sta empty_native_result
    ldx #0
@passed:
    lda passed,x
    beq idle
    jsr $FFD2
    inx
    bne @passed
mismatch:
    lda #$FE
failed:
    sta empty_native_error
    jsr se_io_abort
    lda #$FF
    sta empty_native_result
    ldx #0
@failed:
    lda failed_text,x
    beq idle
    jsr $FFD2
    inx
    bne @failed
idle:jmp idle
.segment "CODE"
; Probe coordinator: each empty_step reads only one256-byte sector. Production
; integration yields between these calls rather than blocking a whole directory.
safe_open:
    jsr empty_begin
    bcs @return
@step:
    jsr empty_step
    bcs @return
    cmp #2
    beq @step
    jsr se_io_open_read ;actual logicalfile and DOS status remain the real API
    bcs @return
    lda empty_result
    beq @ok
    lda #$40
    sta se_io_eof ;metadata proves zero payload; do not consume a phantom byte
@ok:
    lda #0
    clc
@return:
    rts
empty_read:
    lda #$A7
    sta $8000
    lda #0
    sta se_io_count
    jsr se_io_read_chunk
    bcs @return
    lda se_io_done
    sta empty_native_done
    ora se_io_done+1
    bne @bad
    lda se_io_done+1
    sta empty_native_done+1
    lda se_io_eof
    sta empty_native_eof
    beq @bad
    lda $8000
    sta empty_native_byte
    cmp #$A7
    bne @bad
    jmp se_io_close
@bad:
    lda #$FE
    sec
@return:
    rts
name:
    tax
    lda names_lo,x
    sta name_load+1
    lda names_hi,x
    sta name_load+2
    lda names_length,x
    sta se_io_name_len
    tay
copy_name:
    dey
name_load:
    lda $FFFF,y
    sta se_io_name,y
    cpy #0
    bne copy_name
    rts
.segment "RODATA"
names_lo:.byte <created_name,<imported_name,<nul_name,<control_name
names_hi:.byte >created_name,>imported_name,>nul_name,>control_name
names_length:.byte 10,8,3,7
created_name:.byte "EMPTYPROBE"
final_name:.byte "EMPTYFINAL"
imported_name:.byte "IMPORTED"
nul_name:.byte "NUL"
control_name:.byte "CONTROL"
passed:.byte 13,"EMPTY SEQ NATIVE PASSED",13,0
failed_text:.byte 13,"EMPTY SEQ NATIVE FAILED",13,0
.assert __BSS_SIZE__>256,lderror,"clear requires two pages"
.assert __BSS_SIZE__<512,lderror,"clear exceeds two pages"
.assert __BSS_RUN__+__BSS_SIZE__<=$C600,lderror,"shim must remain unmapped"
