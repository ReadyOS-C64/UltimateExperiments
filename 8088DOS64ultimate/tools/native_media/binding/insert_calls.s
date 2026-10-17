.setcpu "6502"
.include "insert-entry.inc"
.export mw_init,mw_build
.segment "LOADADDR"
.word $7dd0
.segment "CODE"
.macro call_c target
 php
 sei
 cld
 ldx #95
: lda $80,x
 sta $7e80,x
 lda #0
 sta $80,x
 dex
 bpl :-
 lda #$ff
 sta $80
 lda #$bf
 sta $81
 jsr target
 pha
 ldx #95
: lda $7e80,x
 sta $80,x
 dex
 bpl :-
 pla
 ldx #0
 plp
 rts
.endmacro
mw_init: call_c plan_init
mw_build: call_c plan_build

.assert * <= $7e80,error,"PLAN wrapper must not overwrite saved C/native high96"
