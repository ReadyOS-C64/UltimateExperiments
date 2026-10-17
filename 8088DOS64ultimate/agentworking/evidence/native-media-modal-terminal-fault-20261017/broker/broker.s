.setcpu "6502"
.macpack longbranch
.include "symbols.inc"
.export modal_admit,modal_release,modal_ui_on,modal_ui_off,modal_poll
.export modal_error,modal_owned,modal_context,modal_native_zp,modal_ui_zp
.export modal_display_on,modal_display_off,modal_display_active
.segment "LOADADDR"
.word $7000
.segment "CODE"
; Component only: a resident caller must first load this matched asset while
; coherently PAUSED5. The guest bitmap may be retired; cache8000..BFFF may not.
; No disk/menu loader or end-user key binding is provided by this component.
; IRQ/NMI and RAM+I/O mapping remain owned by the native runtime.
modal_owned: .byte 0
modal_context: .byte 0             ; 1 native highZP, 2 UI highZP
modal_display_active: .byte 0
.macro ENTER
 php
 sei
 cld
.endmacro
.macro RETURN carry
 plp
 .if carry
 sec
 .else
 clc
 .endif
 rts
.endmacro
modal_admit:
 ENTER
 lda modal_owned
 jne rejected
 lda #1
 sta modal_error
 lda dos64_native_diag
 cmp #5
 jne rejected
 lda dos64_cold_open
 ora sav_borrowed
 ora sav_context_pending
 ora dos64_overlay_busy
 ora hd_uncertain
 ora hdb_active
 jne rejected
 lda dos64_overlay_ready
 cmp #$a5
 jne rejected
 lda dos64_cache_ready
 cmp #$a5
 jne rejected
 lda dos64_cache_limit
 cmp #32
 jne rejected
 ldx #31
@pins:
 lda dos64_cache_pins,x
 jne rejected
 dex
 bpl @pins
 jsr quiet
 jcs rejected
 lda hdb_online
 cmp #2
 jcs rejected
 cmp dos64_files_handle
 jne rejected
 lda hdb_online
 beq @closed
 lda hdc_target
 cmp #1
 beq @target
 cmp #2
 jne rejected
@target:
 cmp dos64_files_target
 jne rejected
 cmp dos64_files_owned_target
 jne rejected
@closed:
 lda dos64_files_state
 cmp #1
 jeq rejected
 jsr clock
 jcs rejected
 jsr dos64_cache_flush
 bcc @flushed
 lda #3
 sta modal_error
 lda #$e1
 sta dos64_native_diag
 jmp rejected
@flushed:
 ; Every dirty frame is backed before any phase byte can overwrite it.
 ldx #31
@invalidate:
 lda dos64_cache_flags,x
 and #1
 beq @clear
 lda dos64_cache_tags_lo,x
 sta dos64_mem_pointer
 lda dos64_cache_tags_hi,x
 clc
 adc #$e1
 sta dos64_mem_pointer+1
 ldy #0
 lda #$ff
 sta (dos64_mem_pointer),y
@clear:
 lda #0
 sta dos64_cache_flags,x
 dex
 bpl @invalidate
 jsr dos64_fetch_init
 lda dos64_cache_hand
 sta saved_hand
 lda hdb_online
 sta saved_online
 lda hdc_target
 sta saved_target
 ldx #24
@files:
 lda dos64_files_state_start,x
 sta saved_files,x
 dex
 bpl @files
 ldx #hd_state_end-hd_state_start-1
@hd:
 lda hd_state_start,x
 sta saved_hd,x
 dex
 bpl @hd
 ldx #hdb_state_end-hdb_state_start-1
@hdb:
 lda hdb_state_start,x
 sta saved_hdb,x
 dex
 bpl @hdb
 lda #0
 sta dos64_cache_limit
 sta dos64_cache_hand
 sta dos64_native_diag+3
 sta modal_error
 ldx #95
@zero_ui:
 sta modal_ui_zp,x
 dex
 bpl @zero_ui
 lda #8
 sta dos64_native_diag
 lda #1
 sta modal_context
 lda #$a5
 sta modal_owned
 RETURN 0
rejected:
 RETURN 1
; No UCI/FILES operation is performed here. This observation alone cannot
; certify worker completion, external durability or permission to clear dirty.
quiet:
 lda dos64_uci_recovery_failed
 bne @bad
 lda dos64_uci_state
 beq @ok
 cmp #9
 beq @ok
 cmp #10
 bne @bad
@ok:
 clc
 rts
@bad:
 sec
 rts
clock:
 jsr dos64_elapsed_poll
 bcc @ok
 lda #4
 sta modal_error
 lda dos64_host_clock_status
 cmp #4
 beq @bad                         ; deferred coherent sample; do not reset CIA
 lda #5
 sta modal_error
 lda #$e1
 sta dos64_native_diag
@bad:
 sec
 rts
@ok:
 clc
 rts
presentation_owner:
 lda modal_owned
 cmp #$a5
 bne @bad
 lda modal_context
 cmp #1
 bne @bad
 lda dos64_native_diag
 cmp #8
 beq @stage
 cmp #$e1
 bne @bad
@stage:
 lda dos64_cache_limit
 bne @bad
 lda dos64_cache_ready
 cmp #$a5
 bne @bad
 lda dos64_overlay_ready
 cmp #$a5
 bne @bad
 clc
 rts
@bad:
 sec
 rts
; E1 presentation does not authorize native work, release or display-off.
native_owner:
 jsr presentation_owner
 bcs @bad
 lda dos64_native_diag
 cmp #8
 bne @bad
 clc
 rts
@bad:
 sec
 rts
modal_poll:
 ENTER
 jsr native_owner
 jcs rejected
 jsr clock
 jcs rejected
 RETURN 0
modal_ui_on:
 ENTER
 jsr presentation_owner
 jcs rejected
 ; Only the overlapping high ZP is exchanged. Native20..7F is untouched by
 ; the cc65 phase. A worker cannot run until UI has returned through ui_off.
 ldx #95
@swap:
 lda $80,x
 sta modal_native_zp,x
 lda modal_ui_zp,x
 sta $80,x
 dex
 bpl @swap
 lda #2
 sta modal_context
 RETURN 0
modal_ui_off:
 ENTER
 lda modal_owned
 cmp #$a5
 jne rejected
 lda modal_context
 cmp #2
 jne rejected
 ldx #95
@swap:
 lda $80,x
 sta modal_ui_zp,x
 lda modal_native_zp,x
 sta $80,x
 dex
 bpl @swap
 lda #1
 sta modal_context
 RETURN 0
modal_release:
 ENTER
 jsr native_owner
 jcs rejected
 lda modal_display_active
 jne rejected
 jsr quiet
 jcs rejected
 lda dos64_overlay_busy
 ora sav_borrowed
 ora sav_context_pending
 ora hd_uncertain
 ora hdb_active
 jne rejected
 lda saved_online
 cmp hdb_online
 jne rejected
 lda saved_target
 cmp hdc_target
 jne rejected
 ldx #24
@context:
 lda saved_files,x
 cmp dos64_files_state_start,x
 jne rejected
 dex
 bpl @context
 ldx #hd_state_end-hd_state_start-1
@hd:
 lda hd_state_start,x
 cmp saved_hd,x
 jne rejected
 dex
 bpl @hd
 ldx #hdb_state_end-hdb_state_start-1
@hdb:
 lda hdb_state_start,x
 cmp saved_hdb,x
 jne rejected
 dex
 bpl @hdb
 ldx #31
@empty:
 lda dos64_cache_flags,x
 ora dos64_cache_pins,x
 jne rejected
 dex
 bpl @empty
 jsr clock
 jcs rejected
 jsr dos64_fetch_init
 lda saved_hand
 sta dos64_cache_hand
 lda #32
 sta dos64_cache_limit
 lda #0
 sta modal_owned
 sta modal_context
 sta modal_error
 sta dos64_native_diag+3
 lda #5
 sta dos64_native_diag
 ; Return to permanent resident code BEFORE rendering the bitmap over7000.
 RETURN 0
; Select the same lower/upper text ROM charset as the standalone native UI,
; without its startup clock/ICR/vector takeover. IRQ raster compare is caller
; owned and disabled; the unreadable D011 compare highbit is not reconstructed.
modal_display_on:
 ENTER
 jsr presentation_owner
 jcs rejected
 lda modal_display_active
 jne rejected
 lda $d011
 and #$7f
 sta saved_display
 lda $d016
 sta saved_display+1
 lda $d018
 sta saved_display+2
 lda $d015
 sta saved_display+3
 lda $d020
 sta saved_display+4
 lda $d021
 sta saved_display+5
 lda $dd00
 sta saved_display+6
 lda $dd02
 sta saved_display+7
 lda $dd00
 ora #3
 sta $dd00
 lda $dd02
 ora #3
 sta $dd02
 lda #$1b
 sta $d011
 lda #8
 sta $d016
 lda #$16
 sta $d018
 lda #0
 sta $d015
 sta $d020
 sta $d021
 lda #1
 sta modal_display_active
 RETURN 0
modal_display_off:
 ENTER
 jsr native_owner
 jcs rejected
 lda modal_display_active
 cmp #1
 jne rejected
 lda saved_display+6
 sta $dd00
 lda saved_display+7
 sta $dd02
 lda saved_display
 sta $d011
 lda saved_display+1
 sta $d016
 lda saved_display+2
 sta $d018
 lda saved_display+3
 sta $d015
 lda saved_display+4
 sta $d020
 lda saved_display+5
 sta $d021
 lda #0
 sta modal_display_active
 RETURN 0
; Private snapshots share the broker asset's owned bitmap slice. They are
; writable data, not executable instructions; no UI BSS or cache overlaps.
saved_hd: .res hd_state_end-hd_state_start,0
saved_hdb: .res hdb_state_end-hdb_state_start,0
saved_display: .res 8,0
.segment "STATE"
modal_native_zp: .res 96
modal_ui_zp: .res 96
saved_files: .res 25
saved_hand: .res 1
saved_online: .res 1
saved_target: .res 1
modal_error: .res 1
