.segment "CODE"
se_boot_screen:
    lda #$80
    sta se_ink_reverse
    PRINT_AT boot_title,0,0
    PRINT_AT boot_footer,24,0
    lda #0
    sta se_ink_reverse
    PRINT_AT boot_subtitle,3,2
    PRINT_AT boot_version,5,2
    PRINT_AT boot_ram,8,2
    PRINT_AT boot_reu,10,2
    lda se_reu_banks+1
    beq @small
    lda #$32
    sta VIC_SCREEN+10*40+16
    lda #$35
    sta VIC_SCREEN+10*40+17
    lda #$36
    sta VIC_SCREEN+10*40+18
    jmp @bank_unit
@small:
    lda #$24 ; explicitly label small count as hex for this boot probe
    sta VIC_SCREEN+10*40+15
    lda se_reu_banks
    jsr se_hex_byte
    stx VIC_SCREEN+10*40+16
    sta VIC_SCREEN+10*40+17
@bank_unit:
    PRINT_AT boot_banks,10,20
    lda se_status
    cmp #1
    bne @error
    PRINT_AT boot_ready,13,2
    jmp @details
@error:
    PRINT_AT boot_failed,13,2
@details:
    PRINT_AT boot_pending,16,2
.ifdef MEMORY_PROBE
    lda se_memory_result
    jsr se_hex_byte
    stx VIC_SCREEN+16*40+24
    sta VIC_SCREEN+16*40+25
.endif
.ifdef OVERLAY_PROBE
    lda se_overlay_result
    jsr se_hex_byte
    stx VIC_SCREEN+16*40+24
    sta VIC_SCREEN+16*40+25
.endif
.ifdef OBJECT_PROBE
    lda se_object_result
    jsr se_hex_byte
    stx VIC_SCREEN+16*40+24
    sta VIC_SCREEN+16*40+25
.endif
.ifdef DOCUMENT_PROBE
    lda se_doc_result
    jsr se_hex_byte
    stx VIC_SCREEN+16*40+26
    sta VIC_SCREEN+16*40+27
.endif
.ifdef SPLICE_PROBE
    lda se_splice_result
    jsr se_hex_byte
    stx VIC_SCREEN+16*40+26
    sta VIC_SCREEN+16*40+27
.endif
.ifdef CLIPBOARD_PROBE
    lda se_clip_result
    jsr se_hex_byte
    stx VIC_SCREEN+16*40+27
    sta VIC_SCREEN+16*40+28
.endif
    PRINT_AT boot_key,20,2
    rts

se_show_key:
    lda se_last_key
    jsr se_petscii_screen
    sta VIC_SCREEN+20*40+19
    lda se_last_key
    jsr se_hex_byte
    stx VIC_SCREEN+20*40+23
    sta VIC_SCREEN+20*40+24
    rts

.segment "RODATA"
boot_banks: .asciiz "x 64 KiB banks"
