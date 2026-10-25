.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "document/api.inc"
.include "object/api.inc"
.import se_reu_provider_init, se_reu_bind, se_petscii_screen, se_print
.importzp text_ptr, screen_ptr
.export se_doc_probe, se_doc_probe_screen, se_doc_result, se_doc_cases, se_doc_error
.segment "BSS"
se_doc_result: .res 1
se_doc_cases: .res 1
se_doc_error: .res 1
doc_seed_count: .res 1
.segment "COLD"
se_doc_probe:
    jsr se_reu_provider_init
    jcs @failed
    jsr se_object_init
    jcs @failed
    lda #7
    ldx #190
    ldy #1
    jsr se_reu_bind
    jcs @failed
    lda #7
    ldx #191
    ldy #4
    jsr se_reu_bind
    jcs @failed
    lda #2
    jsr se_doc_init
    jcs @failed
    inc se_doc_cases
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    sta se_object_offset+2
    sta se_object_c64
    sta se_object_length
    lda #$80
    sta se_object_c64+1
    lda #$10
    sta se_object_length+1
    lda #17
    sta doc_seed_count
    ldx #0
@fill:
    txa
    eor #$A5
    .repeat 16,P
        sta $8000+P*$100,x
    .endrepeat
    inx
    bne @fill
@seed:
    DOC_TOKEN se_doc_original
    lda doc_seed_count
    cmp #1
    bne @write
    ldx #tail_end-tail-1
@tail:
    lda tail,x
    sta $8000,x
    dex
    bpl @tail
@write:
    lda #0
    jsr se_object_copy
    jcs @failed
    clc
    lda se_object_offset+1
    adc #$10
    sta se_object_offset+1
    bcc :+
    inc se_object_offset+2
:
    dec doc_seed_count
    bne @seed
    inc se_doc_cases
    lda #0
    sta se_doc_source_length
    lda #$10
    sta se_doc_source_length+1
    lda #1
    sta se_doc_source_length+2
    jsr se_doc_adopt_original
    jcs @failed
    inc se_doc_cases
    lda #$80
    sta se_doc_offset
    lda #$FF
    sta se_doc_offset+1
    lda #0
    sta se_doc_offset+2
    sta se_doc_count
    sta se_doc_c64
    lda #4
    sta se_doc_count+1
    lda #$80
    sta se_doc_c64+1
    jsr se_doc_read
    jcs @failed
    ldx #0
@first:
    txa
    ora #$80
    eor #$A5
    cmp $8000,x
    jne @failed
    inx
    bpl @first
    ldx #tail_end-tail-1
@compare_tail:
    lda tail,x
    cmp $8080,x
    jne @failed
    dex
    bpl @compare_tail
    lda $83FF
    cmp #$DA
    jne @failed
    ldx #0
@retain:
    .repeat 4,P
        lda $8000+P*$100,x
        sta $9000+P*$100,x
    .endrepeat
    inx
    bne @retain
    inc se_doc_cases
    lda #$0F
    sta se_doc_offset+1
    lda #1
    sta se_doc_offset+2
    lda #$80
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    jsr se_doc_read
    jcs @failed
    ldx #0
@last:
    txa
    ora #$80
    eor #$A5
    cmp $8000,x
    jne @failed
    inx
    bpl @last
    inc se_doc_cases
    lda #0
    sta se_doc_offset
    lda #$10
    sta se_doc_offset+1
    lda #1
    sta se_doc_count
    jsr se_doc_read
    jcc @failed
    cmp #$32
    jne @failed
    inc se_doc_cases
    lda #0
    sta se_doc_offset+1
    lda #$9A
    sta se_doc_c64+1
    jsr se_doc_read
    jcc @failed
    cmp #$33
    jne @failed
    inc se_doc_cases
    lda #0
    sta se_doc_count
    jsr se_doc_read
    jcc @failed
    cmp #$36
    jne @failed
    inc se_doc_cases
    lda #$80
    sta se_doc_c64+1
    lda #tail_end-tail
    sta se_doc_count
    jsr se_doc_read
    jcs @failed
    ldx #tail_end-tail-1
@render_check:
    lda tail,x
    cmp $8000,x
    jne @failed
    dex
    bpl @render_check
    lda #0
    sta $8000+tail_end-tail
    inc se_doc_cases
    lda #1
    sta se_doc_result
    rts
@failed:
    sta se_doc_error
    lda #$EE
    sta se_doc_result
    rts
se_doc_probe_screen:
    lda se_doc_result
    cmp #1
    bne @done
    PRINT_AT $8000,18,1
@done:
    rts
.segment "COLD"
tail: .byte "Beyond 64 KiB: PETSCII source survives"
tail_end:
