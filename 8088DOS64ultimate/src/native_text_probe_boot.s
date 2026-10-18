.import dos64_native_text_probe
.export fixture_return
.segment "LOADADDR"
.word $0801
.segment "BASIC"
.word basic_end
.word 10
.byte $9E,"2061",0
basic_end: .word 0
.segment "BOOT"
    sei
    cld
    jsr dos64_native_text_probe
fixture_return:
    jmp fixture_return
.segment "FONT"
.incbin "assets/native-text/cp437-unscii8.bin"
