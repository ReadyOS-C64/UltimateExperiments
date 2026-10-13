        .importzp ptr1
        .import pushax, _cputs, _readyfs_content_parse_count
        .export _readyfs_utility_test

RF_U_VALUE_LOW = 10
RF_U_WORKSPACE = 12

        .segment "OVERLAY9"

callptr: .res 2
passed:  .res 1
value:   .res 1
crc:     .res 4

count_255: .byte "255",0
count_0:   .byte "0",0
count_256: .byte "256",0
crc_text:  .byte "123456789"
msg_head:  .byte "rft1 suites",13,10,"core",13,10,0
msg_pass:  .byte "rft1 core pass 4/4",13,10,0
msg_fail:  .byte "fail",13,10,0

_readyfs_utility_test:
        sta callptr
        stx callptr+1
        sta ptr1
        stx ptr1+1
        ldy #RF_U_VALUE_LOW
        lda #0
        sta (ptr1),y
        lda #<msg_head
        ldx #>msg_head
        jsr _cputs
        lda callptr
        sta ptr1
        lda callptr+1
        sta ptr1+1
        ldy #RF_U_WORKSPACE
        lda (ptr1),y
        iny
        ora (ptr1),y
        bne @workspace_ok
        lda #<msg_fail
        ldx #>msg_fail
        jsr _cputs
        lda #1
        ldx #0
        rts
@workspace_ok:
        lda #1
        sta passed
        lda #<count_255
        ldx #>count_255
        jsr pushax
        lda #<value
        ldx #>value
        jsr _readyfs_content_parse_count
        beq :+
        lda value
        cmp #255
        bne :+
        inc passed
:
        lda #<count_0
        ldx #>count_0
        jsr pushax
        lda #<value
        ldx #>value
        jsr _readyfs_content_parse_count
        bne @crc
        lda #<count_256
        ldx #>count_256
        jsr pushax
        lda #<value
        ldx #>value
        jsr _readyfs_content_parse_count
        bne @crc
        inc passed

@crc:  lda #$ff
        ldx #3
@init: sta crc,x
        dex
        bpl @init
        ldy #0
@byte: lda crc_text,y
        eor crc
        sta crc
        ldx #8
@bit:  lsr crc+3
        ror crc+2
        ror crc+1
        ror crc
        bcc @plain
        lda crc
        eor #$20
        sta crc
        lda crc+1
        eor #$83
        sta crc+1
        lda crc+2
        eor #$b8
        sta crc+2
        lda crc+3
        eor #$ed
        sta crc+3
@plain:dex
        bne @bit
        iny
        cpy #9
        bne @byte
        lda crc
        eor #$ff
        cmp #$26
        bne @report
        lda crc+1
        eor #$ff
        cmp #$39
        bne @report
        lda crc+2
        eor #$ff
        cmp #$f4
        bne @report
        lda crc+3
        eor #$ff
        cmp #$cb
        bne @report
        inc passed

@report:
        lda passed
        cmp #4
        bne @failed
        lda #<msg_pass
        ldx #>msg_pass
        bne @print
@failed:
        lda #<msg_fail
        ldx #>msg_fail
@print: jsr _cputs
        lda #1
        ldx #0
        rts
