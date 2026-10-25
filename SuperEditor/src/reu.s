; All REU register writes belong in this service. The bootstrap probe only
; transfers one byte between its owned C64 scratch and offset FFFD of a bank.
; It saves ALL originals before tagging any bank, so aliased banks restore too.
.setcpu "6502"
.import se_probe_byte, se_probe_bank, se_probe_saved, se_probe_original, se_reu_banks
.export se_reu_probe
.ifdef SE_COLD_STARTUP
.segment "COLD"
.else
.segment "CODE"
.endif
se_reu_byte:
    pha
    lda #<se_probe_byte
    sta $DF02
    lda #>se_probe_byte
    sta $DF03
    lda #$FD
    sta $DF04
    lda #$FF
    sta $DF05
    lda se_probe_bank
    sta $DF06
    lda #1
    sta $DF07
    lda #0
    sta $DF08
    sta $DF09
    sta $DF0A
    pla
    sta $DF01
    rts

se_reu_fetch_byte:
    lda #$91
    jmp se_reu_byte
se_reu_stash_byte:
    lda #$90
    jmp se_reu_byte

se_reu_probe:
    lda #$A5
    sta se_probe_byte
    jsr se_reu_fetch_byte
    lda se_probe_byte
    sta se_probe_saved
    lda #$5A
    sta se_probe_byte
    jsr se_reu_stash_byte
    lda #$A5
    sta se_probe_byte
    jsr se_reu_fetch_byte
    lda se_probe_byte
    cmp #$5A
    bne @absent
    lda se_probe_saved
    sta se_probe_byte
    jsr se_reu_stash_byte
    ldx #0
@save:
    stx se_probe_bank
    jsr se_reu_fetch_byte
    lda se_probe_byte
    sta se_probe_original,x
    inx
    bne @save
@tag:
    stx se_probe_bank
    stx se_probe_byte
    jsr se_reu_stash_byte
    inx
    bne @tag
    stx se_probe_bank
    jsr se_reu_fetch_byte
    ; Supported REUs alias a power-of-two bank count: bank zero holds 256-N.
    lda #0
    sec
    sbc se_probe_byte
    sta se_reu_banks
    bne @restore
    inc se_reu_banks+1
@restore:
    stx se_probe_bank
    lda se_probe_original,x
    sta se_probe_byte
    jsr se_reu_stash_byte
    inx
    bne @restore
    rts
@absent:
    lda #0
    sta se_reu_banks
    sta se_reu_banks+1
    rts
