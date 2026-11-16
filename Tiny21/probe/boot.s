.setcpu "6502"
.import probe_main
.import __PROBE_LOAD__, __PROBE_RUN__, __PROBE_SIZE__
.import __PROBEBSS_RUN__, __PROBEBSS_SIZE__
.export probe_start

src = $f0
dst = $f2
length = $f4
CIA1_ICR = $dc0d
CIA2_ICR = $dd0d

.segment "LOADADDR"
    .word $0801

.segment "STARTUP"
    .word next_line
    .word 10
    .byte $9e, "2061", 0
next_line:
    .word 0
.assert * = $080d, lderror, "SYS address does not match the probe entry"

probe_start:
    sei
    cld
    ldx #$ff
    txs
    lda #$7f
    sta CIA1_ICR
    sta CIA2_ICR
    lda CIA1_ICR
    lda CIA2_ICR
    lda #<ignore_interrupt
    sta $fffa
    sta $fffe
    lda #>ignore_interrupt
    sta $fffb
    sta $ffff
    lda $00
    ora #7
    sta $00
    lda $01
    and #$f8
    ora #5
    sta $01

    lda #<__PROBE_LOAD__
    sta src
    lda #>__PROBE_LOAD__
    sta src+1
    lda #<__PROBE_RUN__
    sta dst
    lda #>__PROBE_RUN__
    sta dst+1
    lda #<__PROBE_SIZE__
    sta length
    lda #>__PROBE_SIZE__
    sta length+1
    ldy #0
copy_page:
    lda length+1
    beq copy_tail
copy_full:
    lda (src),y
    sta (dst),y
    iny
    bne copy_full
    inc src+1
    inc dst+1
    dec length+1
    bne copy_full
copy_tail:
    cpy length
    beq clear
    lda (src),y
    sta (dst),y
    iny
    bne copy_tail

clear:
    lda #<__PROBEBSS_RUN__
    sta dst
    lda #>__PROBEBSS_RUN__
    sta dst+1
    ldx #>__PROBEBSS_SIZE__
    lda #0
    ldy #0
    cpx #0
    beq clear_tail
clear_full:
    sta (dst),y
    iny
    bne clear_full
    inc dst+1
    dex
    bne clear_full
clear_tail:
    cpy #<__PROBEBSS_SIZE__
    beq run
    sta (dst),y
    iny
    bne clear_tail
run:
    jmp probe_main

ignore_interrupt:
    rti
