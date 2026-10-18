.export _codec_init, fixture_return
.importzp sp
.import zerobss
.segment "LOADADDR"
.word $0801
.segment "CODE"
_codec_init:
    lda #<$c000
    sta sp
    lda #>$c000
    sta sp+1
    jsr zerobss
    rts
fixture_return:
    brk
