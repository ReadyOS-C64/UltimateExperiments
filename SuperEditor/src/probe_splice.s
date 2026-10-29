.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "document/api.inc"
.include "document/math24.inc"
.import se_doc_probe, se_doc_result, se_print
.importzp text_ptr, screen_ptr
.export se_splice_probe, se_splice_probe_screen, se_splice_result, se_splice_cases, se_splice_error
.segment "BSS"
se_splice_result: .res 1
se_splice_cases: .res 1
se_splice_error: .res 1
.segment "CODE"
se_splice_probe:
    jsr se_doc_probe
    lda se_doc_result
    cmp #1
    jne @failed
    inc se_splice_cases
    lda #0
    sta se_doc_edit_position
    sta se_doc_edit_position+1
    sta se_doc_edit_delete+1
    sta se_doc_edit_delete+2
    sta se_doc_edit_insert+1
    sta se_doc_edit_insert+2
    lda #1
    sta se_doc_edit_position+2
    lda #old_end-old_text
    sta se_doc_edit_delete
    lda #new_end-new_text
    sta se_doc_edit_insert
    jsr se_doc_splice_begin
    jcs @failed
    cmp #1
    jne @failed
    inc se_splice_cases
    ldx #new_end-new_text-1
@feed:
    lda new_text,x
    sta $8000,x
    dex
    bpl @feed
    lda #new_end-new_text
    jsr set_buffer
    jsr se_doc_splice_feed
    jcs @failed
    inc se_splice_cases
    ; The UI may read old source after feeding, before root publication.
    COPY24 se_doc_edit_position,se_doc_offset
    lda #old_end-old_text
    jsr set_buffer
    jsr se_doc_read
    jcs @failed
    ldx #old_end-old_text-1
@old:
    lda old_text,x
    cmp $8000,x
    jne @failed
    dex
    bpl @old
    inc se_splice_cases
    jsr finish
    jcs @failed
    inc se_splice_cases
    jsr read_new
    jcs @failed
    inc se_splice_cases
    ; Pure insertion at EOF, then delete that exact source character.
    COPY24 se_doc_length,se_doc_edit_position
    lda #0
    sta se_doc_edit_delete
    lda #1
    sta se_doc_edit_insert
    jsr se_doc_splice_begin
    jcs @failed
    lda #$0D
    sta $8000
    lda #1
    jsr set_buffer
    jsr se_doc_splice_feed
    jcs @failed
    jsr finish
    jcs @failed
    COPY24 se_doc_edit_position,se_doc_offset
    lda #1
    jsr set_buffer
    jsr se_doc_read
    jcs @failed
    lda $8000
    cmp #$0D
    jne @failed
    inc se_splice_cases
    lda #1
    sta se_doc_edit_delete
    lda #0
    sta se_doc_edit_insert
    jsr se_doc_splice_begin
    jcs @failed
    jsr finish
    jcs @failed
    lda se_doc_length
    cmp #<FINAL_LENGTH
    jne @failed
    lda se_doc_length+1
    cmp #>FINAL_LENGTH
    jne @failed
    lda se_doc_length+2
    cmp #^FINAL_LENGTH
    jne @failed
    inc se_splice_cases
    ; Private canceled append bytes are never published into source/size.
    lda #0
    sta se_doc_edit_position
    sta se_doc_edit_position+1
    sta se_doc_edit_position+2
    sta se_doc_edit_delete
    lda #2
    sta se_doc_edit_insert
    jsr se_doc_splice_begin
    jcs @failed
    lda #$21
    sta $8000
    sta $8001
    lda #2
    jsr set_buffer
    jsr se_doc_splice_feed
    jcs @failed
    jsr se_doc_splice_cancel
    jsr read_new
    jcs @failed
    inc se_splice_cases
    lda #1
    sta se_doc_edit_insert
    jsr se_doc_splice_begin
    jcs @failed
    jsr se_doc_splice_step
    jcc @failed
    cmp #$45
    jne @failed
    jsr se_doc_splice_cancel
    jsr read_new
    jcs @failed
    inc se_splice_cases
    lda #0
    sta $8000+new_end-new_text
    lda #1
    sta se_splice_result
    rts
@failed:
    sta se_splice_error
    lda #$EE
    sta se_splice_result
    rts
finish:
    jsr se_doc_splice_step
    bcs @return
    cmp #1
    beq finish
@return:
    rts
set_buffer:
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    rts
read_new:
    lda #0
    sta se_doc_offset
    sta se_doc_offset+1
    lda #1
    sta se_doc_offset+2
    lda #new_end-new_text
    jsr set_buffer
    jsr se_doc_read
    bcs @return
    ldx #new_end-new_text-1
@compare:
    lda new_text,x
    cmp $8000,x
    bne @error
    dex
    bpl @compare
    clc
@return:
    rts
@error:
    lda #$EF
    sec
    rts
se_splice_probe_screen:
    lda se_splice_result
    cmp #1
    bne @return
    PRINT_AT $8000,18,1
@return:
    rts
.segment "RODATA"
old_text: .byte "Beyond 64 KiB: PETSCII source survives"
old_end:
new_text: .byte "Edited beyond 64 KiB. Old text safe."
new_end:
FINAL_LENGTH = $11000-(old_end-old_text)+(new_end-new_text)
