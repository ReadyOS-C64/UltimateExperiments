.setcpu "6502"
.macpack longbranch
.include "render/geos/caret-ui.inc"
.import se_f_owner,tui_editor_status40
.importzp text_ptr,screen_ptr
.export se_gcc_status
.segment "CODE"
pixels:
    ldy #7
@row:
    lda (text_ptr),y
    cpx #128
    bcc :+
    eor #$FF
:
    sta (screen_ptr),y
    dey
    bpl @row
    lda #0
    clc
    rts

se_gcc_status:
    lda se_f_owner
    cmp #4
    jne foreign
    jsr tui_editor_status40
    lda #6
    sta GCC_UI_COLUMN
    lda #48
    sta screen_ptr
    lda #$7E
    sta screen_ptr+1
@cell:
    ldx GCC_UI_COLUMN
    lda $43C0,x
    pha
    asl
    asl
    asl
    sta text_ptr
    pla
    pha
    lsr
    lsr
    lsr
    lsr
    lsr
    and #3
    ora #$48
    sta text_ptr+1
    lda $DBC0,x
    and #15
    asl
    asl
    asl
    asl
    ora #6
    sta $43C0,x
    pla
    tax
    jsr pixels
    clc
    lda screen_ptr
    adc #8
    sta screen_ptr
    bcc :+
    inc screen_ptr+1
:
    inc GCC_UI_COLUMN
    lda GCC_UI_COLUMN
    cmp #12
    bne :+
    lda #14
    sta GCC_UI_COLUMN
    lda #112
    sta screen_ptr
:   lda GCC_UI_COLUMN
    cmp #22
    bcc @cell
    lda #0
    clc
    rts
foreign:
 lda #$B2
 sec
 rts
