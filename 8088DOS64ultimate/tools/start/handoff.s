.setcpu "6502"
.import _d64_release_output,_lc_consume_handoff
.import __TRAMPOLINE_LOAD__,__TRAMPOLINE_SIZE__
.export _sf_handoff,trampoline_start,trampoline_loaded,trampoline_success,trampoline_failed
.export dma_fields,main_start_operand,main_loop_operand,checked_main_idle
.segment "CODE"
_sf_handoff:
 ldx #<(__TRAMPOLINE_SIZE__-1)
@copy:
 lda __TRAMPOLINE_LOAD__,x
 sta trampoline_start,x
 dex
 cpx #$ff
 bne @copy
 ldx #1
@patch:
 lda _d64_release_output+16,x
 sta dma_fields,x
 lda _d64_release_output+18,x
 sta dma_fields+5,x
 lda _d64_release_output+20,x
 sta main_start_operand,x
 lda _d64_release_output+22,x
 sta main_loop_operand,x
 lda _d64_release_output+24,x
 sta checked_main_idle,x
 dex
 bpl @patch
 ; Last call validates prepared metadata/closed quiet ownership and consumes
 ; private one-shot authority. No C frame survives trampoline's TXS.
 jsr _lc_consume_handoff
 cmp #1
 bne @refused
 jmp trampoline_start
@refused:
 rts
.segment "TRAMPOLINE"
trampoline_start:
 sei
 cld
 ldx #$ff
 txs
 lda #$2f
 sta $00
 lda #$37
 sta $01
 lda #$40
 sta $5882
 lda #$82
 sta $fffa
 lda #$58
 sta $fffb
 lda #$7f
 sta $dc0d
 sta $dd0d
 lda $dc0d
 lda $dd0d
 lda #0
 sta $d01a
 lda #15
 sta $d019
 lda #$35
 sta $01
 ldx #8
@program:
 lda dma_fields,x
 sta $df02,x
 dex
 bpl @program
 lda #$91
 sta $df01
 ldx #0
@poll:
 lda $df00
 and #$60
 cmp #$40
 beq trampoline_loaded
 and #$20
 bne trampoline_failed
 dex
 bne @poll
trampoline_failed:
 jmp trampoline_failed
trampoline_loaded:
 .byte $20
main_start_operand: .word 0
 bcs trampoline_failed
trampoline_success:
 .byte $4c
main_loop_operand: .word 0
; All varying fields come from checked release metadata. Source bank/offset
; and RTI5882 are fixed ABI1 values validated by release.c; idle metadata is
; retained without ever jumping into a partial main payload on failure.
dma_fields:
 .byte 0,0,$02,$00,$3e,0,0,0,0
checked_main_idle: .word 0
.assert __TRAMPOLINE_SIZE__ <= $100,lderror,"low trampoline must fit0200 page"
