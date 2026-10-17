.setcpu "6502"
.ifndef DOS64_BOOT_DIAGNOSTICS
DOS64_BOOT_DIAGNOSTICS=0
.endif
.if DOS64_BOOT_DIAGNOSTICS
.import __BOOT_DIAG_LOAD__,__BOOT_DIAG_RUN__,__BOOT_DIAG_SIZE__,fixture_return
.assert __BOOT_DIAG_RUN__=$c843,lderror,"diagnostic run tail"
.assert __BOOT_DIAG_SIZE__<=$bd,lderror,"diagnostic device tail bounds"
.endif
.ifndef DOS64_FILE_DIAGNOSTICS
DOS64_FILE_DIAGNOSTICS=0
.endif
.if DOS64_FILE_DIAGNOSTICS
.import __FILE_DIAG_LOAD__,__FILE_DIAG_RUN__,__FILE_DIAG_SIZE__
.assert __FILE_DIAG_RUN__=$bfa0,lderror,"file diagnostic helper run"
.assert __FILE_DIAG_SIZE__<=$60,lderror,"file diagnostic helper bound"
.endif
.importzp ptr1,ptr2,ptr3
.import __HIGH_CODE_LOAD__,__HIGH_CODE_RUN__,__HIGH_CODE_SIZE__
.import __AUX_CODE_LOAD__,__AUX_CODE_RUN__,__AUX_CODE_SIZE__,__AUX_RO_SIZE__
.export _sl_copy_code,sl_copy_check
.assert ptr2=ptr1+2,lderror,"copy pointer tuple ABI"
.assert ptr3=ptr1+4,lderror,"copy count tuple ABI"
.assert __AUX_CODE_SIZE__+__AUX_RO_SIZE__>0,lderror,"empty AUX code"
.assert __AUX_CODE_SIZE__+__AUX_RO_SIZE__<=$0460,lderror,"AUX run bounds"
.segment "UI_RO"
; Reversed tuple: copied into ptr1/ptr2/ptr3 by descending Y. X selects range.
copy_ranges:
.if DOS64_BOOT_DIAGNOSTICS .and (DOS64_FILE_DIAGNOSTICS=0)
 .byte >__BOOT_DIAG_SIZE__,<__BOOT_DIAG_SIZE__,>__BOOT_DIAG_RUN__,<__BOOT_DIAG_RUN__,>__BOOT_DIAG_LOAD__,<__BOOT_DIAG_LOAD__
.endif
.if DOS64_FILE_DIAGNOSTICS
 .byte >__FILE_DIAG_SIZE__,<__FILE_DIAG_SIZE__,>__FILE_DIAG_RUN__,<__FILE_DIAG_RUN__,>__FILE_DIAG_LOAD__,<__FILE_DIAG_LOAD__
.endif
 .byte >__HIGH_CODE_SIZE__,<__HIGH_CODE_SIZE__,>__HIGH_CODE_RUN__,<__HIGH_CODE_RUN__,>__HIGH_CODE_LOAD__,<__HIGH_CODE_LOAD__
 .byte >(__AUX_CODE_SIZE__+__AUX_RO_SIZE__),<(__AUX_CODE_SIZE__+__AUX_RO_SIZE__),>__AUX_CODE_RUN__,<__AUX_CODE_RUN__,>__AUX_CODE_LOAD__,<__AUX_CODE_LOAD__
.segment "UI_CODE"
; Setup-only C ABI, both stacks initialized, D=0/IRQs masked/bank35, no concurrent
; memory owner. No SMC: initial UI must retain its build CRC for SOprepare.
; Each store is read back against the source byte before proceeding. Caller
; grants installed authority only after BOTH complete ranges return success.
_sl_copy_code:
 ldx #0
.if DOS64_BOOT_DIAGNOSTICS .and (DOS64_FILE_DIAGNOSTICS=0)
 jsr copy_range
 bcs :+
 ; No instruction from a partially installed diagnostic is executable.
 ; The trusted permanent park remains available even if RAM cannot retain it.
 jmp fixture_return
:
.endif
.if DOS64_FILE_DIAGNOSTICS
 jsr copy_range
 bcc failed
.endif
 jsr copy_range
 bcc failed
 jsr copy_range
 bcc failed
 lda #1
 ldx #0
 rts
failed:
 lda #0
 tax
 rts
copy_range:
 ldy #5
@tuple:
 lda copy_ranges,x
 sta ptr1,y
 inx
 dey
 bpl @tuple
 ldy #0
copy_byte:
 lda (ptr1),y
 sta (ptr2),y
sl_copy_check:
 cmp (ptr2),y
 bne @bad
 iny
 bne @count
 inc ptr1+1
 inc ptr2+1
@count:
 lda ptr3
 bne @low
 dec ptr3+1
@low:
 dec ptr3
 lda ptr3
 ora ptr3+1
 bne copy_byte
 sec
 rts
@bad:
 clc
 rts
