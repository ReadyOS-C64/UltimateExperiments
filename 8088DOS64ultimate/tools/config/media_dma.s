.setcpu "6502"
.export _rm_dma
.import _rm_dma_c64,_rm_dma_reu,_rm_dma_length,_rm_dma_direction
.segment "RM_CODE"
; Exclusive launcher RAM+I/O mapping. No NMI/IRQ/caller-port transition here.
_rm_dma:
 lda _rm_dma_length
 ora _rm_dma_length+1
 beq @fail
 lda _rm_dma_length+1
 cmp #2
 bcc @setup
 bne @fail
 lda _rm_dma_length
 bne @fail
@setup:
 lda $df00
 lda #0
 sta $df09
 sta $df0a
 lda _rm_dma_c64
 sta $df02
 lda _rm_dma_c64+1
 sta $df03
 lda _rm_dma_reu
 sta $df04
 lda _rm_dma_reu+1
 sta $df05
 lda _rm_dma_reu+2
 sta $df06
 lda _rm_dma_length
 sta $df07
 lda _rm_dma_length+1
 sta $df08
 lda _rm_dma_direction
 ora #$90
 sta $df01
 ldx #0
@poll:
 lda $df00
 and #$60
 cmp #$40
 beq @ok
 cmp #0
 bne @fail
 dex
 bne @poll
@fail:
 lda #0
 ldx #0
 rts
@ok:
 lda #1
 ldx #0
 rts
