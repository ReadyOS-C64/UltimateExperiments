; Independently authored cold-only IEC/D81 proof. ROM/KERNAL stays mapped.
; Mailbox $6000: stage,error,ST,closed, byte countLE24, chunk countLE16,
; CRC32LE, loaded, guard reject, EOI count, final-byte, initial logical count,
; final logical count. Runtime integration is explicitly absent.
.ifdef DOS64_IEC_SMALL
IEC_LENGTH_MID = 2
IEC_LENGTH_HI = 0
.else
IEC_LENGTH_MID = $A0
IEC_LENGTH_HI = 5
.endif
.include "reu.inc"
.macpack longbranch
.import dos64_reu_request, dos64_reu_transfer
.export entry, finished, started, filename, expected_crc, code_end
MB = $6000
BUF = $C000
SETLFS=$FFBA
SETNAM=$FFBD
OPEN=$FFC0
CLOSE=$FFC3
CHKIN=$FFC6
CLRCHN=$FFCC
CHRIN=$FFCF
READST=$FFB7
.segment "LOADADDR"
.word $0801
.segment "BASIC"
.word next
.word 10
.byte $9E,"2061",0
next: .word 0
.segment "CODE"
entry:
    lda started
    beq fresh
    inc MB+14
    rts
fresh:
    inc started
    sei
    cld
    lda #$2F
    sta $00
    lda #$37
    sta $01
    lda #$7F
    sta $DC0D
    sta $DD0D
    lda $DC0D
    lda $DD0D
    lda #0
    sta $D01A
    lda #$FF
    sta $D019
    ; Writes under visible ROM establish complete RAM vectors before the
    ; shared REU primitive temporarily maps RAM at $E000-$FFFF.
    lda #<ram_interrupt
    sta $FFFA
    sta $FFFE
    lda #>ram_interrupt
    sta $FFFB
    sta $FFFF
    ; Model the planned F000-FDFF host extension under KERNAL ROM. Every
    ; byte is independently checked after import; ROM reads must preserve it.
    ldx #0
shadow_guard:
    txa
    eor #$A5
    .repeat 14, page
        sta $F000+page*$100,x
    .endrepeat
    inx
    bne shadow_guard
    ldx #31
clear:
    lda #0
    sta MB,x
    dex
    bpl clear
    lda $98
    sta MB+17
    lda #1
    sta MB
    lda #$FF
    sta MB+9
    sta MB+10
    sta MB+11
    sta MB+12
    lda #$A7
    sta BUF-1
    lda #$5A
    sta BUF+$200
    lda #0
    sta pos
    sta pos+1
    sta dos64_reu_request+R_REU
    sta dos64_reu_request+R_REU+1
    lda #$10
    sta dos64_reu_request+R_REU+2
    lda #filename_end-filename
    ldx #<filename
    ldy #>filename
    jsr SETNAM
    lda #2
    ldx #8
    ldy #2
    jsr SETLFS
    jsr OPEN
    bcc open_ok
    lda #1
    jmp fail
open_ok:
    ldx #2
    jsr CHKIN
    bcc read_loop
    lda #2
    jmp fail
read_loop:
    jsr CHRIN
    sta byte_value
    jsr READST
    sta MB+2
    and #$BF
    beq status_ok
    lda #3
    jmp fail
status_ok:
    ; Consume the returned byte before processing EOI: EOI belongs to last byte.
    lda byte_value
    sta MB+16
    ldx pos
    ldy pos+1
    bne second_page
    sta BUF,x
    jmp crc
second_page:
    sta BUF+$100,x
crc:
    eor MB+9
    sta MB+9
    ldx #8
crc_bit:
    lsr MB+12
    ror MB+11
    ror MB+10
    ror MB+9
    bcc crc_next
    lda MB+9
    eor #$20
    sta MB+9
    lda MB+10
    eor #$83
    sta MB+10
    lda MB+11
    eor #$B8
    sta MB+11
    lda MB+12
    eor #$ED
    sta MB+12
crc_next:
    dex
    bne crc_bit
    inc MB+4
    bne counted
    inc MB+5
    bne counted
    inc MB+6
counted:
    inc pos
    bne eoi
    inc pos+1
eoi:
    lda MB+2
    and #$40
    beq not_eoi
    inc MB+15
    ; Exactly 360 KiB, with EOI on that byte (no extra read/phantom byte).
    lda MB+4
    bne length_error
    lda MB+5
    cmp #IEC_LENGTH_MID
    bne length_error
    lda MB+6
    cmp #IEC_LENGTH_HI
    bne length_error
    jsr flush
    bcs dma_error
    jmp crc_check
not_eoi:
    ; Reaching exact length without EOI is an overlong file: reject before
    ; another CHRIN or DMA; imported bytes never become published media.
    lda MB+6
    cmp #IEC_LENGTH_HI
    bne under_length
    lda MB+5
    cmp #IEC_LENGTH_MID
    bcs length_error
under_length:
    lda pos+1
    cmp #2
    bne read_again
    jsr flush
    bcs dma_error
read_again:
    jmp read_loop
length_error:
    lda #4
    jmp fail
dma_error:
    lda #5
    jmp fail
crc_check:
    ldx #3
crc_final:
    lda MB+9,x
    eor #$FF
    sta MB+9,x
    cmp expected_crc,x
    bne crc_error
    dex
    bpl crc_final
    jsr close_owned
    bcs close_error
    ; Real re-entry rejection while KERNAL is hidden: a cold restart would
    ; immediately corrupt the ownership/mapping contract and cannot pass.
    lda #$35
    sta $01
    tsx
    stx saved_sp
    jsr entry
    tsx
    cpx saved_sp
    bne guard_error
    lda $01
    and #7
    sta MB+19
    cmp #5
    bne guard_error
    lda BUF-1
    cmp #$A7
    bne guard_error
    lda BUF+$200
    cmp #$5A
    bne guard_error
    lda #1
    sta MB+13
    lda #$A5
    sta MB
    jmp finished
guard_error:
    lda #0
    sta MB+13
    lda #8
    sta MB+1
    lda #$E1
    sta MB
    jmp finished
crc_error:
    lda #6
    jmp fail
close_error:
    lda #7
fail:
    sta MB+1
    lda #0
    sta MB+13
    jsr close_owned
    lda #$E1
    sta MB
finished:
    jmp finished
flush:
    lda pos
    sta dos64_reu_request+R_LENGTH
    lda pos+1
    sta dos64_reu_request+R_LENGTH+1
    lda #<BUF
    sta dos64_reu_request+R_HOST
    lda #>BUF
    sta dos64_reu_request+R_HOST+1
    lda #0
    sta dos64_reu_request+R_DIRECTION
    jsr dos64_reu_transfer
    bcs flush_return
    ; Advance by actual transferred count, explicitly handling each bank seam.
    clc
    lda dos64_reu_request+R_REU
    adc pos
    sta dos64_reu_request+R_REU
    lda dos64_reu_request+R_REU+1
    adc pos+1
    sta dos64_reu_request+R_REU+1
    bcc no_bank
    inc dos64_reu_request+R_REU+2
no_bank:
    inc MB+7
    bne chunks
    inc MB+8
chunks:
    lda #0
    sta pos
    sta pos+1
    clc
flush_return:
    rts
close_owned:
    jsr CLRCHN
    lda #0
    sta $90
    lda #2
    jsr CLOSE
    jcs bad_close
    jsr READST
    sta close_status
    jne bad_close
    ; Prove LFN2 is absent from all remaining KERNAL table entries.
    lda $98
    sta MB+18
    tax
    beq closed
scan:
    dex
    lda $259,x
    cmp #2
    jeq bad_close
    cpx #0
    bne scan
closed:
    ; The serial handshake plus LFN removal is checked above; independently
    ; read the drive command channel and require DOS status 00 after CLOSE.
    lda #0
    jsr SETNAM
    lda #15
    ldx #8
    ldy #15
    jsr SETLFS
    jsr OPEN
    jcs bad_close
    ldx #15
    jsr CHKIN
    jcs bad_close
    lda #0
    sta status_count
status_loop:
    jsr CHRIN
    ldx status_count
    cpx #40
    jcs bad_close
    sta drive_status,x
    inc status_count
    jsr READST
    sta close_status
    and #$BF
    jne bad_close
    lda close_status
    and #$40
    bne status_done
    ldx status_count
    lda drive_status-1,x
    cmp #13
    bne status_loop
status_done:
    lda drive_status
    sta MB+20
    cmp #$30
    jne bad_close
    lda drive_status+1
    sta MB+21
    cmp #$30
    jne bad_close
    jsr CLRCHN
    lda #0
    sta $90
    lda #15
    jsr CLOSE
    jcs bad_close
    jsr READST
    jne bad_close
    lda $98
    sta MB+18
    jne bad_close
    lda #1
    sta MB+3
    clc
    rts
bad_close:
    ; Retain the primary error, read status and unpublished state. KERNAL
    ; removes each owned LFN even if the drive handshake/status failed.
    ; Cleanup is best effort: never set known-closed on this failure path.
    jsr CLRCHN
    lda #0
    sta $90
    lda #15
    jsr CLOSE
    lda #0
    sta $90
    lda #2
    jsr CLOSE
    sec
    rts
ram_interrupt:
    rti
code_end:
.segment "RODATA"
filename: .byte "PCDISK,S,R"
filename_end:
expected_crc:
.ifdef DOS64_IEC_SMALL
.byte $76,$35,$61,$1C
.else
.byte $37,$0A,$77,$30
.endif
.segment "DATA"
started: .byte 0
.segment "BSS"
pos: .res 2
byte_value: .res 1
close_status: .res 1
status_count: .res 1
drive_status: .res 40
saved_sp: .res 1
