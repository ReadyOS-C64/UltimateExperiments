.setcpu "6502"
.importzp sp,sreg,ptr1
.import incsp4
.export _mp_crc
.segment "BSS"
crc:.res 4
count:.res 2
.segment "CODE"
; cc65 fastcall CRC(pointer,u16 count,u32 raw). Last arg EAX, stack count/pointer.
; Nonreentrant phase-owned helper; no tables, phase/state callbacks or DMA.
_mp_crc:
 sta crc
 stx crc+1
 lda sreg
 sta crc+2
 lda sreg+1
 sta crc+3
 ldy #0
 lda (sp),y
 sta count
 iny
 lda (sp),y
 sta count+1
 iny
 lda (sp),y
 sta ptr1
 iny
 lda (sp),y
 sta ptr1+1
@next:
 lda count
 ora count+1
 beq @done
 ldy #0
 lda (ptr1),y
 eor crc
 sta crc
 ldx #8
@bit:
 lsr crc+3
 ror crc+2
 ror crc+1
 ror crc
 bcc @skip
 lda crc
 eor #$20
 sta crc
 lda crc+1
 eor #$83
 sta crc+1
 lda crc+2
 eor #$b8
 sta crc+2
 lda crc+3
 eor #$ed
 sta crc+3
@skip:
 dex
 bne @bit
 inc ptr1
 bne :+
 inc ptr1+1
: lda count
 bne :+
 dec count+1
: dec count
 jmp @next
@done:
 lda crc+2
 sta sreg
 lda crc+3
 sta sreg+1
 lda crc
 ldx crc+1
 jmp incsp4
