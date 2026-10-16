.setcpu "6502"
.macpack longbranch
.include "floppy_export.inc"
.include "native_save.inc"
.include "memory.inc"
.include "reu.inc"
.include "host_clock.inc"
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
sav_state_end:
.segment "HDBIOS"
; Resident continuations only. B000-BFFF is never active code before flush.
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
 lda dos64_overlay_busy
 ora hdb_online
 ora hd_uncertain
 ora dos64_files_handle
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
 ; No file target or existing handle is stolen. Only floppy-only save accepted.
 jsr sav_clock
 jsr dos64_export_start
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
; Modal control lives with SAVER, separate from replaceable FILE at C900.
sav_clock:
 lda dos64_elapsed_now
 sta dos64_export_now
 lda dos64_elapsed_now+1
 sta dos64_export_now+1
 rts
sav_dispatch:
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
 lda #2
 sta sav_error
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
 jsr dos64_export_poll
 lda dos64_export_state
 cmp #EXPORT_BUSY
 beq @return
 cmp #EXPORT_DONE
 bne @failed
 lda #$a5
 jmp sav_finish
@failed:
 lda #$e1
 jmp sav_finish
@return:
 clc
 rts
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
