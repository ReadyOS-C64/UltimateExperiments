.setcpu "6502"
.macpack longbranch
.include "floppy_export.inc"
.include "native_save.inc"
.include "memory.inc"
.include "reu.inc"
.include "host_clock.inc"
.ifndef DOS64_SAVE_HD_CONTEXT
DOS64_SAVE_HD_CONTEXT=0
.endif
.if DOS64_SAVE_HD_CONTEXT
.include "files.inc"
.include "uci.inc"
.import dos64_files_state_start,dos64_files_state_end,dos64_files_owned_target
.import dos64_files_now,dos64_files_op,dos64_files_error,dos64_files_transport_error
.import dos64_export_verified
.import dos64_uci_state,dos64_uci_recovery_failed,dos64_uci_now,dos64_uci_abort
.import dos64_overlay_files_start,dos64_overlay_files_poll,hdc_target
.export sav_context_pending,sav_context_snapshot,sav_context_phase,sav_expected_handle
.import dos64_disk_b_descriptor,dos64_disk_readonly,dos64_disk_content_generation
.assert dos64_disk_loaded-dos64_disk_reu_base=9,lderror,"SAVE A descriptor layout changed"
.assert dos64_disk_readonly-dos64_disk_b_descriptor=10,lderror,"SAVE B descriptor layout changed"
.assert dos64_disk_content_generation+8-dos64_disk_b_descriptor=32,lderror,"SAVE metadata snapshot layout changed"
.export sav_drive,sav_selected_drive,sav_media_snapshot
.assert dos64_files_state_end-dos64_files_state_start=25,lderror,"SAVE FILES snapshot changed"
.endif
.import __SAVERCODE_SIZE__,dos64_native_diag,dos64_export_init,dos64_export_start,dos64_export_poll
.import dos64_export_state,dos64_export_cleanup_error,dos64_export_uncertain,dos64_export_cancel
.import dos64_export_now,dos64_export_owned,dos64_export_paused,dos64_export_bank
.import dos64_export_path_len,dos64_export_path,dos64_export_limit
.import dos64_elapsed_poll,dos64_elapsed_now,dos64_host_clock_status
.import dos64_fetch_init
.import dos64_cache_limit,dos64_cache_ready,dos64_cache_flush,dos64_cache_pins,dos64_cache_flags
.import dos64_cache_tags_lo,dos64_cache_tags_hi,dos64_cache_map,dos64_cache_hand
.importzp dos64_mem_pointer
.import dos64_overlay_busy,dos64_overlay_ready
.import dos64_files_handle,dos64_files_state,dos64_files_target
.import hdb_online,hdb_active,hd_uncertain
.import dos64_disk_loaded,dos64_disk_reu_base,dos64_disk_sectors
.import dos64_reu_request,dos64_reu_transfer,dos64_cold_open
.export sav_boot,sav_header,sav_borrowed,sav_begin,sav_dispatch
.export sav_ready,sav_error,sav_state_start,sav_state_end
.segment "DEVICESTATE"
sav_state_start:
sav_borrowed: .res 1
sav_ready: .res 1
sav_error: .res 1
sav_hand: .res 1
.if DOS64_SAVE_HD_CONTEXT
sav_context_pending: .res 1
sav_context_phase: .res 1
sav_expected_handle: .res 1
sav_close_drain: .res 1
sav_context_leaf: .res 1
sav_context_transport: .res 1
sav_context_snapshot: .res 25
sav_drive: .res 1
sav_selected_drive: .res 1
sav_media_snapshot: .res 42
.endif
sav_state_end:
.segment "HDBIOS"
; Resident continuations only. B000-BFFF is never active code before flush.
.if DOS64_SAVE_HD_CONTEXT
sav_early_reject:
 jmp sav_reject
.endif
.if DOS64_SAVE_HD_CONTEXT
sav_begin:
 lda dos64_native_diag
 cmp #5
 bne sav_early_reject
 lda sav_ready
 cmp #$a5
 bne sav_early_reject
 lda dos64_cache_ready
 cmp #$a5
 bne sav_early_reject
 lda dos64_cache_limit
 cmp #32
 bne sav_early_reject
.if DOS64_SAVE_HD_CONTEXT
 lda dos64_files_handle
 eor hdb_online
 ora dos64_overlay_busy
 ora hd_uncertain
.else
 lda dos64_overlay_busy
 ora hdb_online
 ora hd_uncertain
 ora dos64_files_handle
.endif
 bne sav_early_reject
 lda hdb_active
 and #$fd
 cmp #1
 beq sav_early_reject
 lda dos64_files_state
 cmp #1
 beq sav_early_reject
 ldx #31
@pins:
 lda dos64_cache_pins,x
 bne sav_early_reject
 dex
 bpl @pins
 jsr sav_capture_media
 bcs sav_early_reject
.else
sav_begin:
 lda dos64_native_diag
 cmp #5
 jne sav_reject
 lda sav_ready
 cmp #$a5
 jne sav_reject
 lda dos64_cache_ready
 cmp #$a5
 jne sav_reject
 lda dos64_cache_limit
 cmp #32
 jne sav_reject
.if DOS64_SAVE_HD_CONTEXT
 lda dos64_files_handle
 eor hdb_online
 ora dos64_overlay_busy
 ora hd_uncertain
.else
 lda dos64_overlay_busy
 ora hdb_online
 ora hd_uncertain
 ora dos64_files_handle
.endif
 jne sav_reject
 lda hdb_active
 cmp #1
 jeq sav_reject
 cmp #3
 jeq sav_reject
 lda dos64_files_state
 cmp #1
 jeq sav_reject
 ldx #31
@pins:
 lda dos64_cache_pins,x
 jne sav_reject
 dex
 bpl @pins
.endif
 jsr dos64_elapsed_poll
 bcc @clock
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 jeq sav_return                   ; pending original SAVE, no mutation
 jmp sav_clock_terminal
@clock:
 jsr dos64_cache_flush
 jcs sav_flush_fail               ; no code borrow on incomplete writeback
 ; Unpublish only eight borrowed frames; retain epochs/mode/lower24frames.
 ldx #24
@invalidate:
 lda dos64_cache_flags,x
 and #MEM_VALID
 beq @clear
 lda dos64_cache_tags_lo,x
 sta dos64_mem_pointer
 lda dos64_cache_tags_hi,x
 clc
 adc #>MEM_MAP_BASE
 sta dos64_mem_pointer+1
 ldy #0
 lda #$ff
 sta (dos64_mem_pointer),y
@clear:
 lda #0
 sta dos64_cache_flags,x
 inx
 cpx #32
 bne @invalidate
 lda dos64_cache_hand
 sta sav_hand
 lda #0
 sta dos64_cache_hand
 sta sav_error
 jsr dos64_fetch_init
 lda #24
 sta dos64_cache_limit
 lda #1
 sta sav_borrowed
 lda #NATIVE_SAVE_STAGE
 sta dos64_native_diag
 ; Entire slot, including immutable header, loaded while caller stays resident.
 ldx #7
@descriptor:
 lda sav_load,x
 sta dos64_reu_request,x
 dex
 bpl @descriptor
 jsr dos64_reu_transfer
 jcs sav_load_fail
 ldx #15
@header:
 lda $b000,x
 cmp sav_header,x
 jne sav_load_fail
 dex
 bpl @header
 jsr sav_validate_media
 jcs sav_known_fail
 ; Validate selected snapshot before borrowing an alternate FILES target.
 jsr sav_clock
.if DOS64_SAVE_HD_CONTEXT
 jsr sav_context_begin
.else
 jsr dos64_export_start
.endif
 jcs sav_known_fail
 jmp sav_return
sav_flush_fail:
 lda #3
 sta sav_error
 lda #$e1
 sta dos64_native_diag
 jmp sav_reject
sav_load_fail:
 lda #4
 sta sav_error
sav_known_fail:
 lda #$e1
 jmp sav_finish
sav_reject:
 lda #$e1
 sta dos64_native_diag+4
 lda #0
 sta dos64_native_diag+3
sav_return:
 clc
 rts
sav_clock_terminal:
 lda #2
 sta sav_error
 lda #$e1
 sta dos64_native_diag
 jmp sav_reject
; A=final command acknowledgement. Returning code is permanently resident.
sav_finish:
 sta dos64_native_diag+4
 lda sav_hand
 sta dos64_cache_hand
 lda #32
 sta dos64_cache_limit
 lda #0
 sta sav_borrowed
 sta dos64_native_diag+3
 lda #5
 ldx dos64_files_handle
.if DOS64_SAVE_HD_CONTEXT
 cpx sav_expected_handle
.endif
 bne @blocked
 ldx dos64_export_cleanup_error
 bne @blocked
 ldx sav_error
 beq @stage
@blocked:
 lda #$e1
@stage:
 sta dos64_native_diag
 clc
 rts
.if DOS64_SAVE_HD_CONTEXT
sav_context_clock:
 ldx #1
@copy:
 lda dos64_export_now,x
 sta dos64_files_now,x
 sta dos64_uci_now,x
 dex
 bpl @copy
 rts
.endif
sav_load:
 .word $b000
 .byte $00,$30,$34
 .word $800
 .byte 1
sav_header:
 .byte "D64O",1,7
 .word __SAVERCODE_SIZE__,$b010,0
 .byte "SAVE"
.segment "SAVERCODE"

.if DOS64_SAVE_HD_CONTEXT
.segment "CODE"
sav_capture_media:
 lda sav_drive
 cmp #2
 bcs @bad
 sta sav_selected_drive
 ldx #9
@a:
 lda dos64_disk_reu_base,x
 sta sav_media_snapshot,x
 dex
 bpl @a
 ldx #31
@b:
 lda dos64_disk_b_descriptor,x
 sta sav_media_snapshot+10,x
 dex
 bpl @b
 clc
 rts
@bad:
 sec
 rts
sav_clock:
 lda dos64_elapsed_now
 sta dos64_export_now
 lda dos64_elapsed_now+1
 sta dos64_export_now+1
 rts
.segment "SAVERCODE"
.endif
.if DOS64_SAVE_HD_CONTEXT
sav_validate_media:
 ldx #9
@a:
 lda dos64_disk_reu_base,x
 cmp sav_media_snapshot,x
 bne @bad
 dex
 bpl @a
 ldx #31
@b:
 lda dos64_disk_b_descriptor,x
 cmp sav_media_snapshot+10,x
 bne @bad
 dex
 bpl @b
 ldx #9
 lda sav_selected_drive
 beq @selected
 ldx #19
@selected:
 lda sav_media_snapshot-9,x
 ora sav_media_snapshot-8,x
 bne @bad
 lda sav_media_snapshot-7,x
 cmp dos64_export_bank
 bne @bad
 ldy #6
@geometry:
 lda sav_media_snapshot,x
 cmp sav_geometry,y
 bne @bad
 dex
 dey
 bpl @geometry
 clc
 rts
@bad:
 lda #6
 sta sav_error
 sec
 rts
sav_geometry:
 .byte $d0,2,40,0,2,9,1
.else
sav_validate_media:
 lda dos64_disk_loaded
 cmp #1
 jne @bad
 lda dos64_disk_reu_base
 ora dos64_disk_reu_base+1
 jne @bad
 lda dos64_disk_reu_base+2
 cmp dos64_export_bank
 jne @bad
 lda dos64_disk_sectors
 cmp #$d0
 jne @bad
 lda dos64_disk_sectors+1
 cmp #2
 jne @bad
 clc
 rts
@bad:
 sec
 rts
.endif
; Modal control lives with SAVER, separate from replaceable FILE at C900.
.if !DOS64_SAVE_HD_CONTEXT
sav_clock:
 lda dos64_elapsed_now
 sta dos64_export_now
 lda dos64_elapsed_now+1
 sta dos64_export_now+1
 rts
.endif
sav_dispatch:
.if DOS64_SAVE_HD_CONTEXT
 jsr sav_context_observe
.endif
 lda dos64_native_diag+3
 cmp #NATIVE_SAVE_CANCEL
 bne @request
 lda #1
 sta dos64_export_cancel
 lda #NATIVE_SAVE_COMMAND
 sta dos64_native_diag+3
@request:
 lda dos64_native_diag+3
 cmp #NATIVE_SAVE_COMMAND
 beq @poll
 lda #$e1
 sta dos64_native_diag+4
 lda #0
 sta dos64_native_diag+3
@poll:
 jsr dos64_elapsed_poll
 bcc @clock
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 beq @return
 ; Force the core's hard deadline path once if the real clock becomes invalid.
.if DOS64_SAVE_HD_CONTEXT
 lda sav_error
 bne :+
.endif
 lda #2
 sta sav_error
.if DOS64_SAVE_HD_CONTEXT
:
.endif
 lda #1
 sta dos64_export_limit
 lda #0
 sta dos64_export_limit+1
 sta dos64_export_limit+2
 sta dos64_export_limit+3
 inc dos64_export_now
 bne @step
 inc dos64_export_now+1
 jmp @step
@clock:
 jsr sav_clock
@step:
.if DOS64_SAVE_HD_CONTEXT
 lda sav_context_phase
 jne sav_context_poll
.endif
 jsr dos64_export_poll
 lda dos64_export_state
 cmp #EXPORT_BUSY
 beq @return
 cmp #EXPORT_DONE
 bne @failed
.if DOS64_SAVE_HD_CONTEXT
 jsr sav_validate_media
 bcs @failed
.endif
 lda #$a5
.if DOS64_SAVE_HD_CONTEXT
 jmp sav_context_finish
.else
 jmp sav_finish
.endif
@failed:
 lda #$e1
.if DOS64_SAVE_HD_CONTEXT
 jmp sav_context_finish
.else
 jmp sav_finish
.endif
@return:
 clc
 rts

.if DOS64_SAVE_HD_CONTEXT
; All modal frames return to permanent sav_finish before restoring32 frames.
sav_context_begin:
 lda #0
 sta sav_expected_handle
 sta sav_context_phase
 sta sav_close_drain
 sta sav_context_leaf
 sta sav_context_transport
 sta dos64_export_verified
 lda sav_context_pending
 bne @bad
 lda hdb_online
 beq @plain
 cmp #1
 bne @bad
 lda hdb_active
 bne @bad
 lda dos64_files_handle
 cmp #1
 bne @bad
 lda hdc_target
 cmp #1
 beq @target
 cmp #2
 bne @bad
@target:
 cmp dos64_files_target
 bne @bad
 cmp dos64_files_owned_target
 bne @bad
 jsr sav_context_quiet
 bcs @bad
 ldx #24
@save:
 lda dos64_files_state_start,x
 sta sav_context_snapshot,x
 dex
 bpl @save
 lda #1
 sta sav_context_pending
 sta sav_context_phase
 lda #0
 sta hdb_online
 ldx #24
@clear:
 sta dos64_files_state_start,x
 dex
 bpl @clear
 lda #3
 sec
 sbc hdc_target
 sta dos64_files_target
 sta dos64_files_owned_target
 lda #2
 sta dos64_files_handle
 lda #FILES_CLOSE
 sta dos64_files_op
 jsr sav_context_clock
 jsr dos64_overlay_files_start
 bcs @bad
 ; A new accepted safety-close job owns cancellation from this point.
 ; Command9 published during/after admission is consumed by sav_dispatch.
 lda #0
 sta dos64_export_cancel
 clc
 rts
@plain:
 jmp dos64_export_start
@bad:
 lda sav_error
 bne :+
 lda #5
 sta sav_error
: sec
 rts
sav_context_quiet:
 lda dos64_uci_recovery_failed
 bne @bad
 lda dos64_uci_state
 cmp #UCI_IDLE
 beq @ok
 cmp #UCI_DONE
 beq @ok
 cmp #UCI_FAILED
 bne @bad
@ok:
 clc
 rts
@bad:
 sec
 rts
sav_context_observe:
 lda sav_context_phase
 beq @return
 lda sav_error
 bne @return
 lda dos64_files_error
 beq @return
 cmp #FILES_ERR_STATUS
 bne @latch
 ; CLOSE exact84 is accepted by FILES and can be ACK/FINAL before terminal.
 lda dos64_uci_state
 cmp #UCI_ACK
 beq @return
 cmp #UCI_FINAL
 beq @return
 cmp #UCI_DONE
 beq @return
@latch:
 lda dos64_files_error
 sta sav_context_leaf
 lda dos64_files_transport_error
 sta sav_context_transport
 lda #5
 sta sav_error
@return:
 rts
sav_context_poll:
 ; Caller already sampled clock; no second engine, init, or HD dispatch.
 lda sav_error
 beq @poll
 inc sav_close_drain
 beq @failed
 jsr sav_context_clock
 jsr dos64_uci_abort
@poll:
 jsr sav_context_clock
 jsr dos64_overlay_files_poll
 bcs @failed
 lda dos64_files_state
 cmp #FILES_BUSY
 beq @return
 lda dos64_files_handle
 bne @failed
 jsr sav_context_quiet
 bcs @failed
 lda dos64_files_state
 cmp #FILES_DONE
 beq @closed
 ; Unchanged FILES parser alone grants exact84 known-closed exception.
 cmp #FILES_FAILED
 bne @failed
 lda dos64_files_error
 cmp #FILES_ERR_STATUS
 bne @failed
@closed:
 lda #0
 sta sav_context_phase
 lda sav_error
 ora dos64_export_cancel
 bne @failed
 jsr dos64_export_start
 bcc @return
 lda #5
 sta sav_error
 jmp @failed
@return:
 clc
 rts
@failed:
 lda #$e1
 jmp sav_context_finish
sav_context_finish:
 pha
 lda sav_context_pending
 beq @done
 lda dos64_files_handle
 bne @blocked
 jsr sav_context_quiet
 bcs @blocked
 ldx #24
@restore:
 lda sav_context_snapshot,x
 sta dos64_files_state_start,x
 dex
 bpl @restore
 lda #0
 sta sav_context_pending
 sta sav_context_phase
 lda #1
 sta sav_expected_handle
 sta hdb_online
 jmp @done
@blocked:
 lda sav_error
 bne @done
 lda #5
 sta sav_error
@done:
 pla
 jmp sav_finish
.endif
.segment "COLDINIT"
; Startup commit before any27source-overlapped cache frames can be reused.
sav_boot:
 ldx #7
@descriptor:
 lda sav_store,x
 sta dos64_reu_request,x
 dex
 bpl @descriptor
 jsr dos64_reu_transfer
 bcs @return
 jsr dos64_export_init
 lda #0
 sta sav_borrowed
 sta sav_error
.if DOS64_SAVE_HD_CONTEXT
 sta sav_context_pending
 sta sav_context_phase
 sta sav_expected_handle
 sta sav_drive
.endif
 lda #$a5
 sta sav_ready
 clc
@return:
 rts
sav_store:
 .word $b000
 .byte $00,$30,$34
 .word $800
 .byte 0
.assert __SAVERCODE_SIZE__ <= $7f0,lderror,"SAVER exceeds modal source payload"
