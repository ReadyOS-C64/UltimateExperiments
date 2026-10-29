.setcpu "6502"
.macpack longbranch
.import se_reu_provider_init, se_reu_alloc, se_reu_bind, se_reu_free
.import se_reu_copy, se_reu_c64, se_reu_offset, se_reu_length, se_reu_logical
.export se_memory_probe, se_memory_result, se_memory_cases
.segment "BSS"
se_memory_result: .res 1
se_memory_cases: .res 1
memory_first_handle: .res 1

.macro EXPECT_COPY_ERROR direction, error
    lda #direction
    jsr se_reu_copy
    jcc @failed
    cmp #error
    jne @failed
    inc se_memory_cases
.endmacro

.segment "CODE"
; Real-machine integration probe, executed from resident code. All REU writes
; use fresh standalone allocations and all C64 buffers live in the scratch area.
se_memory_probe:
    jsr se_reu_provider_init
    jcs @failed
    lda #4
    jsr se_reu_alloc
    jcs @failed
    sta memory_first_handle
    inc se_memory_cases
    lda #4
    ldx #20
    ldy #3
    jsr se_reu_bind
    jcs @failed
    inc se_memory_cases
    lda #4
    ldx #21
    ldy #6
    jsr se_reu_bind
    jcs @failed
    inc se_memory_cases
    ldx #0
@fill:
    txa
    eor #$A5
    .repeat 4, P
        sta $5000+P*$100,x
    .endrepeat
    lda #$CC
    .repeat 4, P
        sta $5400+P*$100,x
    .endrepeat
    inx
    bne @fill
    lda #20
    sta se_reu_logical
    lda #0
    sta se_reu_c64
    sta se_reu_length
    sta se_reu_offset
    lda #$50
    sta se_reu_c64+1
    lda #4
    sta se_reu_length+1
    lda #$FC
    sta se_reu_offset+1
    lda #0
    jsr se_reu_copy
    jcs @failed
    lda #$54
    sta se_reu_c64+1
    lda #1
    jsr se_reu_copy
    jcs @failed
    ldx #0
@compare:
    txa
    eor #$A5
    .repeat 4, P
        cmp $5400+P*$100,x
        jne @failed
    .endrepeat
    inx
    bne @compare
    inc se_memory_cases
    ; 257-byte transfer at a different noncontiguous logical allocation.
    lda #21
    sta se_reu_logical
    lda #$50
    sta se_reu_c64+1
    lda #1
    sta se_reu_length
    sta se_reu_length+1
    sta se_reu_offset+1
    lda #0
    jsr se_reu_copy
    jcs @failed
    ldx #0
    lda #$CC
@clear_destination:
    sta $5400,x
    sta $5500,x
    inx
    bne @clear_destination
    lda #$54
    sta se_reu_c64+1
    lda #1
    jsr se_reu_copy
    jcs @failed
    ldx #0
@compare_short:
    txa
    eor #$A5
    cmp $5400,x
    jne @failed
    inx
    bne @compare_short
    lda $5500
    cmp #$A5
    jne @failed
    lda $5501
    cmp #$CC
    jne @failed
    inc se_memory_cases
    ; Zero is never sent to REU as the hardware's dangerous 64 KiB encoding.
    lda #0
    sta se_reu_length
    sta se_reu_length+1
    EXPECT_COPY_ERROR 1,2
    lda #1
    sta se_reu_length+1
    lda #$C6
    sta se_reu_c64+1
    EXPECT_COPY_ERROR 1,3
    lda #$10
    sta se_reu_c64+1
    EXPECT_COPY_ERROR 1,3
    lda #$50
    sta se_reu_c64+1
    lda #22
    sta se_reu_logical
    EXPECT_COPY_ERROR 1,4
    lda #21
    sta se_reu_logical
    EXPECT_COPY_ERROR 2,5
    lda #$FF
    sta se_reu_offset+1
    lda #1
    sta se_reu_length
    EXPECT_COPY_ERROR 1,3
    ; Exact bank-end transfer is valid (FF00 + 0100 = 10000 exclusive).
    lda #0
    sta se_reu_length
    jsr se_reu_copy
    jcs @failed
    lda #$54
    sta se_reu_c64+1
    lda #1
    jsr se_reu_copy
    jcs @failed
    ldx #0
@compare_end:
    txa
    eor #$A5
    cmp $5400,x
    jne @failed
    inx
    bne @compare_end
    inc se_memory_cases
    ldx #20
    jsr se_reu_free
    jcs @failed
    lda #20
    sta se_reu_logical
    EXPECT_COPY_ERROR 1,4
    ldx #21
    jsr se_reu_free
    jcs @failed
    ldx memory_first_handle
    jsr se_reu_free
    jcs @failed
    inc se_memory_cases
    lda #1
    sta se_memory_result
    rts
@failed:
    lda #$EE
    sta se_memory_result
    rts
