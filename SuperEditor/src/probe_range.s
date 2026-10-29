.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "document/api.inc"
.include "object/api.inc"
.import se_local_result, se_print, se_hex_byte
.importzp text_ptr, screen_ptr
.export se_range_probe, se_range_screen, se_range_result, se_range_cases, se_range_error
.segment "BSS"
se_range_result: .res 1
se_range_cases: .res 1
se_range_error: .res 1
.segment "COLD"
se_range_probe:
    lda se_local_result
    cmp #1
    jne failed
    inc se_range_cases
    lda #6
    ldx #1
    jsr se_object_create
    jcs failed
    ldy #4
@token:
    lda se_object_id,y
    sta se_range_token,y
    dey
    bpl @token
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    lda #1
    sta se_object_offset+2
    jsr se_object_resize
    jcs failed
    inc se_range_cases
    lda #$4C
    sta se_range_offset
    lda #$FF
    sta se_range_offset+1
    lda #0
    sta se_range_offset+2
    sta se_range_position+1
    sta se_range_position+2
    sta se_range_length+1
    sta se_range_length+2
    lda #60
    sta se_range_position
    lda #20
    sta se_range_length
    jsr se_range_begin
    jcs failed
@capture:
    jsr se_range_step
    jcs failed
    cmp #1
    beq @capture
    lda se_range_pieces
    cmp #20
    jne failed
    lda se_range_bytes
    cmp #180
    jne failed
    inc se_range_cases
    lda se_doc_read_locks
    ora se_snapshot_busy
    jne failed
    inc se_range_cases
    DOC_TOKEN se_range_token
    lda #$4C
    sta se_object_offset
    lda #$FF
    sta se_object_offset+1
    lda #0
    sta se_object_offset+2
    sta se_object_length+1
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    lda #180
    sta se_object_length
    lda #1
    jsr se_object_copy
    jcs failed
    lda $8000+90
    cmp se_doc_append
    jne failed
    lda $8000+96
    cmp #1
    jne failed
    inc se_range_cases
    lda #1
    sta se_range_result
    rts
failed:
    sta se_range_error
    lda #$EE
    sta se_range_result
    rts
se_range_screen:
    lda #$20
    ldx #39
@clear:
    sta VIC_SCREEN+16*40,x
    sta VIC_SCREEN+18*40,x
    sta VIC_SCREEN+20*40,x
    sta VIC_SCREEN+22*40,x
    dex
    bpl @clear
    PRINT_AT result,16,1
    lda se_range_result
    jsr se_hex_byte
    stx VIC_SCREEN+16*40+25
    sta VIC_SCREEN+16*40+26
    PRINT_AT packed,18,1
    PRINT_AT selection,20,1
    PRINT_AT scope,22,1
    rts
result: .asciiz "Range capture result: "
packed: .asciiz "20 refs / 180 bytes / source unchanged"
selection: .asciiz "Selection60..79 includes PETSCII X"
scope: .asciiz "Delta primitive; undo UI comes later"
