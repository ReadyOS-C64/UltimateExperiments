.setcpu "6502"
.macpack longbranch
.import se_reu_provider_init, se_overlay_init, se_overlay_read
.import se_overlay_import, se_overlay_call, se_overlay_frame
.export se_overlay_probe, se_overlay_result, se_overlay_cases
.segment "BSS"
se_overlay_result: .res 1
se_overlay_cases: .res 1
.segment "CODE"
se_overlay_probe:
    jsr se_reu_provider_init
    jcs @failed
    jsr se_overlay_init
    jcs @failed
    inc se_overlay_cases
    lda #4
    ldx #<rone
    ldy #>rone
    jsr import_file
    jcs @failed
    lda #4
    ldx #<rtwo
    ldy #>rtwo
    jsr import_file
    jcs @failed
    lda #4
    ldx #<cone
    ldy #>cone
    jsr import_file
    jcs @failed
    lda #5
    ldx #<rnest
    ldy #>rnest
    jsr import_file
    jcs @failed
    lda #1
    ldx #0
    jsr se_overlay_call
    jcs @failed
    cmp #$41
    jne @failed
    inc se_overlay_cases
    lda #1
    ldx #0
    jsr se_overlay_call
    jcs @failed
    cmp #$41
    jne @failed
    inc se_overlay_cases
    lda #2
    ldx #0
    jsr se_overlay_call
    jcs @failed
    cmp #$42
    jne @failed
    inc se_overlay_cases
    lda #1
    ldx #1
    jsr se_overlay_call
    jcc @failed
    cmp #$43
    jne @failed
    lda se_overlay_frame+3
    cmp #$19 ; same-slot nested command rejected
    jne @failed
    inc se_overlay_cases
    lda #3
    ldx #0
    jsr se_overlay_call
    jcs @failed
    cmp #$44
    jne @failed
    lda se_overlay_frame+4
    cmp #$19 ; renderer->command rejected
    jne @failed
    inc se_overlay_cases
    ; Failed file/header/checksum cases must not discard already cached images.
    lda #7
    ldx #<missing
    ldy #>missing
    jsr se_overlay_read
    jcc @failed
    inc se_overlay_cases
    lda #5
    ldx #<short_file
    ldy #>short_file
    jsr se_overlay_read
    jcc @failed
    cmp #$21
    jne @failed
    inc se_overlay_cases
    lda #5
    ldx #<extra_file
    ldy #>extra_file
    jsr se_overlay_read
    jcc @failed
    cmp #$22
    jne @failed
    inc se_overlay_cases
    lda #6
    ldx #<bad_crc
    ldy #>bad_crc
    jsr se_overlay_read
    jcs @failed
    jsr se_overlay_import
    jcc @failed
    cmp #$14
    jne @failed
    inc se_overlay_cases
    lda #6
    ldx #<bad_header
    ldy #>bad_header
    jsr se_overlay_read
    jcc @failed
    cmp #$10
    jne @failed
    inc se_overlay_cases
    lda #7
    ldx #<bad_binding
    ldy #>bad_binding
    jsr se_overlay_read
    jcc @failed
    cmp #$11
    jne @failed
    inc se_overlay_cases
    lda #6
    ldx #<bad_payload_binding
    ldy #>bad_payload_binding
    jsr se_overlay_read
    jcs @failed
    jsr se_overlay_import
    jcc @failed
    cmp #$11
    jne @failed
    inc se_overlay_cases
    lda #1
    ldx #0
    jsr se_overlay_call
    jcs @failed
    cmp #$41
    jne @failed
    inc se_overlay_cases
    lda #1
    sta se_overlay_result
    rts
@failed:
    sta se_overlay_result ; retain error, EE if unexpected success/A0
    bne :+
    lda #$EE
    sta se_overlay_result
:
    rts
import_file:
    jsr se_overlay_read
    bcs @done
    jsr se_overlay_import
    bcs @done
    inc se_overlay_cases
@done:
    rts
.segment "RODATA"
; literal bytes avoid source PETSCII mapping: filenames are uppercase PETSCII.
rone: .byte $52,$4F,$4E,$45
rtwo: .byte $52,$54,$57,$4F
cone: .byte $43,$4F,$4E,$45
rnest: .byte $52,$4E,$45,$53,$54
missing: .byte $4D,$49,$53,$53,$49,$4E,$47
short_file: .byte $53,$48,$4F,$52,$54
extra_file: .byte $45,$58,$54,$52,$41
bad_crc: .byte $42,$41,$44,$43,$52,$43
bad_header: .byte $42,$41,$44,$48,$44,$52

bad_binding: .byte $42,$49,$4E,$44,$45,$52,$52
bad_payload_binding: .byte $50,$41,$59,$45,$52,$52
