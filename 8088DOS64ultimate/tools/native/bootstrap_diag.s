.ifndef DOS64_BOOT_DIAGNOSTICS
DOS64_BOOT_DIAGNOSTICS=0
.endif
.if DOS64_BOOT_DIAGNOSTICS
.ifndef BD_SETUP
BD_SETUP=0
.endif
.setcpu "6502"
.segment "BOOT_DIAG"
.export bd_end
.import __BOOT_DIAG_LOAD__,__BOOT_DIAG_RUN__,__BOOT_DIAG_SIZE__
.if BD_SETUP
.assert __BOOT_DIAG_RUN__=$c843,lderror,"SETUP diagnostic tail"
.assert __BOOT_DIAG_RUN__+__BOOT_DIAG_SIZE__<=$c900,lderror,"SETUP diagnostic excludes tables"
.assert __BOOT_DIAG_LOAD__>= $6000,lderror,"SETUP diagnostic serialized UI source"
.ifndef DOS64_FILE_DIAGNOSTICS
DOS64_FILE_DIAGNOSTICS=0
.endif
.if DOS64_FILE_DIAGNOSTICS
.assert __BOOT_DIAG_LOAD__=$b000 .and __BOOT_DIAG_SIZE__<=$100,lderror,"SETUP cold diagnostic source strip"
.else
.assert __BOOT_DIAG_LOAD__+__BOOT_DIAG_SIZE__<=$b000,lderror,"SETUP diagnostic source below state"
.endif
.else
.assert __BOOT_DIAG_LOAD__=$b000,lderror,"CONFIG trusted cold strip load"
.assert __BOOT_DIAG_RUN__=$b000,lderror,"CONFIG trusted cold strip executes before BSSzero"
.assert __BOOT_DIAG_SIZE__<=$100,lderror,"CONFIG cold strip extent"
.endif
.export bd_render,bd_park
.importzp ptr1
.if BD_SETUP
.import failure_closed,dos64_files_state_end
.assert dos64_files_state_end<=$c843,lderror,"diagnostic excludes full FILES state"
.endif
bd_render:
 sta ptr1+1
 sei
.if !BD_SETUP
 lda #$1b
 sta $d011
 lda #8
 sta $d016
 lda #$14
 sta $d018
 lda #0
 sta $d015
 sta $d021
 lda #2
 sta $d020
 lda $dd02
 ora #3
 sta $dd02
 lda $dd00
 ora #3
 sta $dd00
.endif
 ldx #0
@clear:
 lda #32
 sta $0400,x
 sta $0500,x
 sta $0600,x
 cpx #232
 bcs :+
 sta $0700,x
:
 lda #1
 sta $d800,x
 sta $d900,x
 sta $da00,x
 cpx #232
 bcs :+
 sta $db00,x
:
 inx
 bne @clear
 lda #40
 sta ptr1
 ldx #0
 ldy #0
@text:
 lda bd_text,y
 beq bd_code
 cmp #13
 beq @line
 and #$3f
 sta $0400,x
 inx
@next:
 iny
 bne @text
@line:
 ldx ptr1
 txa
 clc
 adc #40
 sta ptr1
 jmp @next
bd_code:
 lda ptr1+1
 lsr
 lsr
 lsr
 lsr
 tax
 lda bd_hex,x
 sta $040c
 lda ptr1+1
 and #15
 tax
 lda bd_hex,x
 sta $040d
.if BD_SETUP
 lda failure_closed
 beq :+
 lda #25 ; screen-code Y; '?' remains when closure was not privately proven
 sta $0457
:
.endif
bd_park:
 jmp bd_park
bd_text:
.byte "START ERROR 00",13
.if BD_SETUP
.byte "FILE SETUP.PRG",13
.else
.byte "FILE: CONFIG.PRG",13
.endif
.byte "CLOSED:?",13
.byte "RESTART,RELOAD",0
bd_hex:.byte 48,49,50,51,52,53,54,55,56,57,1,2,3,4,5,6
bd_end:

.endif
