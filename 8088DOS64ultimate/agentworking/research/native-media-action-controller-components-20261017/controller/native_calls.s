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
