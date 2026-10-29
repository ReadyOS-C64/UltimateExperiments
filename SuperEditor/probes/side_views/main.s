; Isolated side preview. This is deliberately not the editor event loop.
.setcpu "6502"
.include "platform.inc"
.export se_mode,se_ink_reverse,sv_ready,sv_key_count,sv_help,sv_render_seq
.exportzp text_ptr,screen_ptr
.import sv_render
.segment "LOADADDR"
    .word $0801
.segment "BOOT"
    .word boot_end
    .word 10
    .byte $9E,$34,$30,$39,$36,0
boot_end: .word 0
.segment "ZEROPAGE"
text_ptr: .res 2
screen_ptr: .res 2
.segment "BSS"
se_mode: .res 1
se_ink_reverse: .res 1
sv_ready: .res 1
sv_help: .res 1
sv_key_count: .res 2
sv_render_seq: .res 2
.segment "ENTRY"
entry:
    sei
    lda #0
    tax
@clear:
    .repeat 6,P
        sta $C000+P*$100,x
    .endrepeat
    inx
    bne @clear
    lda #2
    sta se_mode
    cli
    jsr sv_render
    lda #1
    sta sv_ready
@idle:
    jsr K_GETIN
    beq @idle
    pha
    inc sv_key_count
    bne :+
    inc sv_key_count+1
:   pla
    cmp #$31
    beq @eighty
    cmp #$32
    beq @geos
    cmp #$8B
    bne @idle
    lda sv_help
    eor #1
    sta sv_help
    jmp @draw
@eighty:
    lda #2
    bne @mode
@geos:
    lda #3
@mode:
    sta se_mode
    lda #0
    sta sv_help
@draw:
    jsr sv_render
    jmp @idle
