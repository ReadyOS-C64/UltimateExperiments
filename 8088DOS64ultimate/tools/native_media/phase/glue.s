.setcpu "6502"
.include "runtime.inc"
.importzp sp
.import __BSS_RUN__,__BSS_SIZE__
.assert __BSS_SIZE__ > 0,lderror,"phase BSS must not be empty"
.assert __BSS_SIZE__ < 256,lderror,"8-bit init must cover entire phase BSS"
.assert __BSS_RUN__+__BSS_SIZE__ <= $7dd0,lderror,"PLAN state overlaps active C wrapper"
.export _mp_buffer:=$b800,_mp_compare:=$ba40,_mp_ledger:=$7f00
.export _mp_service
.import _mp_cancel
.export _mp_dma,_mp_dma_address,_mp_dma_count,_mp_dma_write,_mp_fixture_init
.segment "LOADADDR"
.word $a000
.segment "BSS"
_mp_dma_address:.res 4
_mp_dma_count:.res 2
_mp_dma_write:.res 1
service_ports:.res 4
service_samples:.res 1
.segment "CODE"
_mp_fixture_init:
 lda #$ff
 sta sp
 lda #$bf
 sta sp+1
 lda #0
 ldx #<__BSS_SIZE__
: sta __BSS_RUN__-1,x
 dex
 bne :-
 rts
_mp_dma:
 lda #<$b800
 sta dos64_reu_request
 lda #>$b800
 sta dos64_reu_request+1
 ldx #2
: lda _mp_dma_address,x
 sta dos64_reu_request+2,x
 dex
 bpl :-
 lda _mp_dma_count
 sta dos64_reu_request+5
 lda _mp_dma_count+1
 sta dos64_reu_request+6
 lda _mp_dma_write
 eor #1
 sta dos64_reu_request+7
 jsr dos64_reu_transfer
 ldx #0
 lda #0
 bcs :+
 lda #1
: rts

; Mandatory cooperative runtime service. Native clock before physical Stop.
; No ICR/TOD/platform initialization, second engine or UI context replacement.
_mp_service:
 lda #0
 sta service_samples
@clock:
 jsr dos64_elapsed_poll
 bcc @key
 lda dos64_host_clock_status
 cmp #4
 bne @failed
 inc service_samples
 bne @clock
@failed:
 lda #0
 ldx #0
 rts
@key:
 ldx #3
: lda $dc00,x
 sta service_ports,x
 dex
 bpl :-
 lda #$ff
 sta $dc02
 lda #0
 sta $dc03
 lda #$7f
 sta $dc00
 nop
 nop
 lda $dc01
 and #$80
 pha
 ldx #3
: lda service_ports,x
 sta $dc00,x
 dex
 bpl :-
 pla
 bne @ok
 lda #1
 sta _mp_cancel
 lda #0
 ldx #0
 rts
@ok:
 lda #1
 ldx #0
 rts
