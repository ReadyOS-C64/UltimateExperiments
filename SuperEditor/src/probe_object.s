.setcpu "6502"
.macpack longbranch
.import se_reu_provider_init, se_reu_bind, se_reu_free
.include "object/api.inc"
.export se_object_probe, se_object_result, se_object_cases, se_object_error
.segment "BSS"
se_object_result: .res 1
se_object_cases: .res 1
seed_count: .res 1
se_object_error: .res 1
.segment "CODE"
se_object_probe:
    jsr se_reu_provider_init
    jcs @failed
    jsr se_object_init
    jcs @failed
    inc se_object_cases
    lda #7
    ldx #20
    ldy #1
    jsr se_reu_bind
    jcs @failed
    lda #7
    ldx #21
    ldy #2
    jsr se_reu_bind
    jcs @failed
    lda #7
    ldx #22
    ldy #4
    jsr se_reu_bind
    jcs @failed
    inc se_object_cases
    lda #4
    ldx #2
    jsr se_object_create
    jcs @failed
    cmp #0
    jne @failed
    inc se_object_cases
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
    sta seed_count
    ldx #0
@seed:
    txa
    eor #$A5
    .repeat 16,P
        sta $8000+P*$100,x
    .endrepeat
    inx
    bne @seed
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
    dec seed_count
    bne @write
    inc se_object_cases
    jsr se_object_resize ; 69632 initialized bytes, not an uninitialized gap
    jcs @failed
    inc se_object_cases
    ldx #0
@patch:
    txa
    eor #$5A
    .repeat 4,P
        sta $8000+P*$100,x
    .endrepeat
    inx
    bne @patch
    lda #$80
    sta se_object_offset
    lda #$FF
    sta se_object_offset+1
    lda #0
    sta se_object_offset+2
    lda #4
    sta se_object_length+1
    lda #0
    jsr se_object_copy
    jcs @failed
    inc se_object_cases
    lda #$90
    sta se_object_c64+1
    lda #1
    jsr se_object_copy
    jcs @failed
    ldx #0
@verify:
    txa
    eor #$5A
    .repeat 4,P
        cmp $9000+P*$100,x
        jne @failed
    .endrepeat
    inx
    bne @verify
    inc se_object_cases
    lda #$FF
    sta se_object_c64
    lda #$9D
    sta se_object_c64+1
    lda #2
    sta se_object_length
    lda #0
    sta se_object_length+1
    lda #1
    jsr se_object_copy
    jcc @failed
    cmp #$33
    jne @failed
    inc se_object_cases
    lda #0
    sta se_object_c64
    sta se_object_offset
    lda #$90
    sta se_object_c64+1
    lda #$10
    sta se_object_offset+1
    lda #1
    sta se_object_offset+2
    sta se_object_length
    jsr se_object_copy
    jcc @failed
    cmp #$32
    jne @failed
    inc se_object_cases
    lda #0
    sta se_object_length
    lda #1
    jsr se_object_copy
    jcc @failed
    cmp #$36
    jne @failed
    inc se_object_cases
    jsr se_object_release
    jcs @failed
    inc se_object_cases
    jsr se_object_validate
    jcc @failed
    cmp #$31
    jne @failed
    inc se_object_cases
    lda #4
    ldx #1
    jsr se_object_create
    jcs @failed
    cpx #2
    jne @failed
    cpy #0
    jne @failed
    lda #1
    sta se_object_generation
    jsr se_object_validate
    jcc @failed
    cmp #$31
    jne @failed
    inc se_object_cases
    lda #2
    sta se_object_generation
    jsr se_object_release
    jcs @failed
    ldx #20
    jsr se_reu_free
    jcs @failed
    ldx #21
    jsr se_reu_free
    jcs @failed
    ldx #22
    jsr se_reu_free
    jcs @failed
    inc se_object_cases
    lda #1
    sta se_object_result
    rts
@failed:
    sta se_object_error
    lda #$EE
    sta se_object_result
    rts
