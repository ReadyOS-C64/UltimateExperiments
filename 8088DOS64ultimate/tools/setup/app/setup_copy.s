.setcpu "6502"
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
 .byte >__HIGH_CODE_SIZE__,<__HIGH_CODE_SIZE__,>__HIGH_CODE_RUN__,<__HIGH_CODE_RUN__,>__HIGH_CODE_LOAD__,<__HIGH_CODE_LOAD__
 .byte >(__AUX_CODE_SIZE__+__AUX_RO_SIZE__),<(__AUX_CODE_SIZE__+__AUX_RO_SIZE__),>__AUX_CODE_RUN__,<__AUX_CODE_RUN__,>__AUX_CODE_LOAD__,<__AUX_CODE_LOAD__
.segment "UI_CODE"
; Setup-only C ABI, both stacks initialized, D=0/IRQs masked/bank35, no concurrent
; memory owner. No SMC: initial UI must retain its build CRC for SOprepare.
; Each store is read back against the source byte before proceeding. Caller
; grants installed authority only after BOTH complete ranges return success.
_sl_copy_code:
 ldx #0
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
