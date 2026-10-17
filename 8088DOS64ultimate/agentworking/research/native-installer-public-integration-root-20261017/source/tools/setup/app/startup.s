.setcpu "6502"
.importzp sp,ptr1
.import __HIGHBSS_RUN__,__HIGHBSS_SIZE__
.ifndef DOS64_FILE_DIAGNOSTICS
DOS64_FILE_DIAGNOSTICS=0
.endif
.if DOS64_FILE_DIAGNOSTICS
.import _ps_guard
.import __BOOT_DIAG_LOAD__,__BOOT_DIAG_RUN__,__BOOT_DIAG_SIZE__
.assert __BOOT_DIAG_LOAD__=$b000,lderror,"cold diagnostic initial source"
.assert __BOOT_DIAG_SIZE__>0 .and __BOOT_DIAG_SIZE__<=$100,lderror,"cold diagnostic copy bound"
.endif
.import zerobss
.export runtime_init,fixture_return
.segment "LOADADDR"
.word $0801
.segment "BASIC"
.word $080b,10
.byte $9e,"2061",0
.word 0
.segment "CODE"
 jmp fixture_return
fixture_return: jmp fixture_return
runtime_init:
.if DOS64_FILE_DIAGNOSTICS
 jsr _ps_guard ; trusted RAM NMI vector/masks before35 and any B000 source read
.else
 sei
 cld
.endif
 lda #$ff
 sta sp
 lda #$cf
 sta sp+1
.if DOS64_FILE_DIAGNOSTICS
 ; Trusted load-only source aliases initial BSS. Install/readback before zero.
 ldx #<(256-__BOOT_DIAG_SIZE__)
@diag:
 lda __BOOT_DIAG_LOAD__-(256-__BOOT_DIAG_SIZE__),x
 sta __BOOT_DIAG_RUN__-(256-__BOOT_DIAG_SIZE__),x
 cmp __BOOT_DIAG_RUN__-(256-__BOOT_DIAG_SIZE__),x
 bne fixture_return
 inx
 bne @diag
.endif
 jsr zerobss
 lda #<__HIGHBSS_RUN__
 sta ptr1
 lda #>__HIGHBSS_RUN__
 sta ptr1+1
 ldx #>__HIGHBSS_SIZE__
 lda #0
 tay
@page:
 cpx #0
 beq @tail
@byte:
 sta (ptr1),y
 iny
 bne @byte
 inc ptr1+1
 dex
 bne @page
@tail:
 ldy #0
@last:
 cpy #<__HIGHBSS_SIZE__
 beq @done
 sta (ptr1),y
 iny
 bne @last
@done:
 rts
