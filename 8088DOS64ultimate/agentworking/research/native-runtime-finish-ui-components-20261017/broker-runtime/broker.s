.setcpu "6502"
.macpack longbranch
.include "symbols.inc"
.include "bridge_products.inc"
.export modal_admit,modal_release,modal_ui_on,modal_ui_off,modal_poll
.export modal_error,modal_owned,modal_context,modal_native_zp,modal_ui_zp
.export modal_display_on,modal_display_off,modal_display_active
.segment "LOADADDR"
.word $7000
.segment "CODE"
.export modal_entry,modal_view_refresh,modal_verify,verify_expected,ui_ready,modal_fault_screen
 jmp modal_entry
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

.segment "CODE"
; Actual native C frontend controller; backend dispatch is still a successor.
.include "ui_symbols.inc"
.export modal_wait
modal_entry:
 lda #0
 sta ui_ready
 sta idle_samples
 lda #255
 sta admission_retries
@admit:
 lda #0
 sta modal_error
 jsr modal_admit
 bcc @owned
 lda modal_error
 cmp #4
 jne modal_entry_failed
 dec admission_retries
 bne @admit
 jmp modal_entry_failed
@owned:
 jsr modal_colors_save
 jcs modal_entry_failed
 jsr modal_display_on
 jcs modal_entry_failed
 ldx #40
 jsr entry_dma
 jcs modal_entry_failed
 ldx #3
: lda bridge_crc,x
 sta verify_expected,x
 dex
 bpl :-
 jsr modal_verify
 jcs modal_entry_failed
 jsr $6003
 ldx #16
 jsr entry_dma
 jcs modal_entry_failed
 ldx #3
: lda initial_ui_crc,x
 sta verify_expected,x
 dex
 bpl :-
 jsr modal_verify
 jcs modal_entry_failed
 jsr modal_view_refresh
 jcs modal_entry_failed
 jsr modal_ui_on
 jcs modal_entry_failed
 jsr _mu_fixture_init
 jsr modal_ui_off
 jcs modal_entry_failed
 lda #1
 sta ui_ready
modal_wait:
 lda #0
 sta modal_error
 jsr modal_poll
 bcc @input
 lda modal_error
 cmp #4
 bne @fault
 inc idle_samples
 bne modal_wait
 lda #5
 sta modal_error
@fault:
 jmp modal_entry_failed
@input:
 lda #0
 sta idle_samples
 jsr modal_ui_on
 jcs modal_entry_failed
 jsr _mu_poll
 jsr _mu_take
 pha
 jsr modal_ui_off
 bcc :+
 pla
 jmp modal_entry_failed
: pla
 cmp #0
 beq modal_wait
 jsr $6000
 jcs modal_entry_failed
 cmp #6
 beq @resume
 cmp #7
 beq modal_finished
 jmp modal_wait
@resume:
 jsr modal_display_off
 jcs modal_entry_failed
 jsr modal_colors_restore
 jcs modal_entry_failed
 jsr modal_release
 jcs modal_entry_failed
 lda #2
 sta dos64_native_diag+3
 sta dos64_modal_pending
 sta dos64_modal_edge
 clc
 rts
.export modal_finished,modal_safe_idle
modal_finished:
 lda #0
 sta dos64_modal_pending
 sta dos64_modal_edge
modal_safe_idle:
 jmp modal_safe_idle
modal_entry_failed:
 lda #0
 sta dos64_modal_pending
 lda #$e1
 sta dos64_native_diag
 lda ui_ready
 bne @ui
 jsr modal_fault_screen
 jmp @return
@ui:
 jsr modal_ui_on
 bcs @return
 lda modal_error
 bne :+
 lda #254
: sta _mu_block_error
 jsr _mu_block
 jsr modal_ui_off
@return:
 sec
 rts
modal_colors_save:
 ldx #0
@full:
 lda $d800,x
 and #15
 sta $b800,x
 lda $d900,x
 and #15
 sta $b900,x
 lda $da00,x
 and #15
 sta $ba00,x
 inx
 bne @full
@last:
 lda $db00,x
 and #15
 sta $bb00,x
 inx
 cpx #232
 bne @last
 ldx #0
 jmp entry_dma
modal_colors_restore:
 ldx #8
 jsr entry_dma
 bcs @return
 ldx #0
@full:
 lda $b800,x
 sta $d800,x
 lda $b900,x
 sta $d900,x
 lda $ba00,x
 sta $da00,x
 inx
 bne @full
@last:
 lda $bb00,x
 sta $db00,x
 inx
 cpx #232
 bne @last
 clc
@return:
 rts
entry_dma:
 ldy #7
@copy:
 lda entry_requests,x
 sta dos64_reu_request,y
 inx
 dey
 bpl @copy
 jmp dos64_reu_transfer
entry_requests:
.macro ENTRY_DMA host, far, count, direction
 .byte direction,>(count),<(count),^(far),>(far),<(far),>(host),<(host)
.endmacro
 ENTRY_DMA $b800,$3e2000,1000,0
 ENTRY_DMA $b800,$3e2000,1000,1
 ENTRY_DMA $8000,$3daa00,UI_BYTES,1
 ENTRY_DMA _mu_view+1,$3ff0a8,128,1
 ENTRY_DMA _mu_view+130,$3ff128,128,1
 ENTRY_DMA $6000,BRIDGE_REU,BRIDGE_BYTES,1
ui_ready: .byte 0
entry_flags: .byte 0
admission_retries: .byte 0

modal_view_refresh:
 lda #0
 ldx #0
@view:
 sta _mu_view,x
 inx
 bne @view
 ldx #43
@tail:
 sta _mu_view+256,x
 dex
 bpl @tail
 lda dos64_native_diag
 cmp #8
 bne :+
 lda #1
 sta _mu_view+258
:
 ldx #0
@drive:
 lda dos64_disk_exhausted,x
 and #1
 asl
 asl
 asl
 sta entry_flags
 lda dos64_disk_dirty,x
 and #1
 asl
 asl
 ora entry_flags
 sta entry_flags
 lda dos64_disk_readonly,x
 and #1
 asl
 ora entry_flags
 sta entry_flags
 lda dos64_disk_loaded
 cpx #0
 beq :+
 lda dos64_disk_b_descriptor+9
: and #1
 ora entry_flags
 ldy #0
 cpx #0
 beq :+
 ldy #129
: sta _mu_view,y
 inx
 cpx #2
 bne @drive
 ldx #24
 jsr entry_dma
 jcs @failed
 ldx #32
 jsr entry_dma
 jcs @failed
 clc
 rts
@failed:
 sec
 rts

; Pure CPU CRC of the just-completed fixed request. The exact expected value
; comes from source-bound products; preserve native high ZP around all reads.
modal_verify:
 ENTER
 lda $80
 sta verify_saved
 lda $81
 sta verify_saved+1
 ldx #1
: lda dos64_reu_request,x
 sta $80,x
 lda dos64_reu_request+5,x
 sta verify_count,x
 dex
 bpl :-
 lda #$ff
 ldx #3
: sta verify_crc,x
 dex
 bpl :-
@next:
 lda verify_count
 ora verify_count+1
 beq @done
 ldy #0
 lda ($80),y
 eor verify_crc
 sta verify_crc
 ldx #8
@bit:
 lsr verify_crc+3
 ror verify_crc+2
 ror verify_crc+1
 ror verify_crc
 bcc @skip
 lda verify_crc
 eor #$20
 sta verify_crc
 lda verify_crc+1
 eor #$83
 sta verify_crc+1
 lda verify_crc+2
 eor #$b8
 sta verify_crc+2
 lda verify_crc+3
 eor #$ed
 sta verify_crc+3
@skip:
 dex
 bne @bit
 inc $80
 bne :+
 inc $81
: lda verify_count
 bne :+
 dec verify_count+1
: dec verify_count
 jmp @next
@done:
 ldx #3
: lda verify_crc,x
 eor #$ff
 cmp verify_expected,x
 bne @bad
 dex
 bpl :-
 lda verify_saved
 sta $80
 lda verify_saved+1
 sta $81
 RETURN 0
@bad:
 lda verify_saved
 sta $80
 lda verify_saved+1
 sta $81
 RETURN 1
bridge_crc:.dword BRIDGE_CRC
initial_ui_crc:.dword UI_CRC
.segment "STATE"
verify_crc:.res 4
verify_expected:.res 4
verify_saved:.res 2
verify_count:.res 2
idle_samples:.res 1

.segment "CODE"
; No jump into an incomplete frontend: this display needs only verified broker
; instructions. It cannot grant closure or resume and leaves all files alone.
modal_fault_screen:
 ldx #0
 lda #32
@pages:
 sta $0400,x
 sta $0500,x
 sta $0600,x
 inx
 bne @pages
@tail:
 sta $0700,x
 inx
 cpx #232
 bne @tail
 ldx #39
@line:
 lda fault_text,x
 sta $0400,x
 lda #1
 sta $d800,x
 dex
 bpl @line
 rts
fault_text:
 .byte "DISK CONTROL FAILED. KEEP POWER ON.      "
