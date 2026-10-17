.setcpu "6502"
.macpack longbranch
.include "native.inc"
.import _ac_dma_host,_ac_dma_count,_ac_dma_reu
.export _ac_transfer,_ac_native_safe,_ac_context_closed,_ac_block
.segment "CODE"
_ac_transfer:
 ldx #1
: lda _ac_dma_host,x
 sta dos64_reu_request,x
 lda _ac_dma_count,x
 sta dos64_reu_request+5,x
 dex
 bpl :-
 ldx #2
: lda _ac_dma_reu,x
 sta dos64_reu_request+2,x
 dex
 bpl :-
 lda #1
 sta dos64_reu_request+7
 jsr dos64_reu_transfer
 bcs bad
ok:
 lda #1
 ldx #0
 rts
bad:
 lda #0
 tax
 rts
_ac_context_closed:
 lda modal_owned
 cmp #$a5
 jne bad
 lda modal_context
 cmp #1
 jne bad
 lda dos64_cache_ready
 cmp #$a5
 jne bad
 lda dos64_overlay_ready
 cmp #$a5
 jne bad
 lda dos64_cache_limit
 ora dos64_cold_open
 ora sav_context_pending
 ora sav_borrowed
 ora hdb_active
 ora hd_uncertain
 ora dos64_overlay_busy
 ora dos64_uci_recovery_failed
 jne bad
 lda dos64_uci_state
 beq :+
 cmp #9
 jne bad
: lda saved_online
 cmp hdb_online
 jne bad
 lda saved_target
 cmp hdc_target
 jne bad
 ldx #24
: lda dos64_files_state_start,x
 cmp saved_files,x
 jne bad
 dex
 bpl :-
 ldx #hd_state_end-hd_state_start-1
: lda hd_state_start,x
 cmp saved_hd,x
 jne bad
 dex
 bpl :-
 ldx #hdb_state_end-hdb_state_start-1
: lda hdb_state_start,x
 cmp saved_hdb,x
 jne bad
 dex
 bpl :-
 ldx #31
: lda dos64_cache_flags,x
 ora dos64_cache_pins,x
 jne bad
 dex
 bpl :-
 jmp ok
_ac_native_safe:
 jsr _ac_context_closed
 cmp #1
 jne bad
 lda dos64_native_diag
 cmp #8
 jne bad
 ldx #255
clock:
 txa
 pha
 jsr dos64_elapsed_poll
 pla
 tax
 jcc ok
 lda dos64_host_clock_status
 cmp #4
 jne bad
 dex
 bne clock
 jmp bad

_ac_block:
 lda #$e1
 sta dos64_native_diag
 rts

.export _ac_service,_ac_pending_error
.segment "BSS"
service_seen:.res 1
service_last:.res 4
service_ports:.res 4
service_samples:.res 1
.segment "CODE"
; Existing leaf owns FILES/UCI and its error reconciliation. Any published
; pending error must reach that leaf before caller samples a later STOP/clock.
_ac_pending_error:
 lda dos64_files_error
 ora dos64_uci_error
 ora sav_error
 ldx #0
 rts
; C ABI u8 result:0 healthy,1 physicalSTOP,2 invalid clock/ambiguous gap.
; Never FILES/engine/timer initialization. Only controller-admitted zerobss
; starts a new service history. No wrap-insensitive absolute deadline.
_ac_service:
 lda #0
 sta service_samples
@again:
 jsr dos64_elapsed_poll
 bcc @fresh
 lda dos64_host_clock_status
 cmp #4
 bne @bad
 inc service_samples
 bne @again
@bad:
 lda #2
 ldx #0
 rts
@fresh:
 lda service_seen
 beq @capture
 ; Bound the actual coherent raw32 gap, not the truncated elapsed16 delta.
 ; Four byte subtraction preserves carry across INX/DEY (never CPX).
 ldx #0
 ldy #4
 sec
@delta:
 lda dos64_host_clock_ticks,x
 sbc service_last,x
 inx
 dey
 bne @delta
 cmp #8                       ; raw gap < $08000000 = elapsed $8000
 bcs @bad
@capture:
 ldx #3
: lda dos64_host_clock_ticks,x
 sta service_last,x
 dex
 bpl :-
 lda #1
 sta service_seen
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
 beq @stop
 lda #0
 ldx #0
 rts
@stop:
 lda #1
 ldx #0
 rts
