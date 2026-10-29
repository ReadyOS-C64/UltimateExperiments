; C33's sealed native8 font is part of its own authenticated immutable payload.
; R25 guard requires the actual backend native font's exact bound/verified asset.
status_pixels:
 ldy #7
@row:
 lda (text_ptr),y
 cpx #128
 bcc :+
 eor #$FF
: sta (screen_ptr),y
 dey
 bpl @row
 rts
status:
 jsr tui_editor_status40
 lda #6
 sta BCOL
 lda #48
 sta screen_ptr
 lda #$7E
 sta screen_ptr+1
@cell:
 ldx BCOL
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
 ora #$BC
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
 jsr status_pixels
 clc
 lda screen_ptr
 adc #8
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: inc BCOL
 lda BCOL
 cmp #12
 bne :+
 lda #14
 sta BCOL
 lda #112
 sta screen_ptr
: lda BCOL
 cmp #22
 bcc @cell
 lda #0
 clc
 rts
