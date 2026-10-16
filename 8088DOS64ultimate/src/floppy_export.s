.setcpu "6502"
.macpack longbranch
.include "floppy_export.inc"
.include "files.inc"
.include "uci.inc"
.include "reu.inc"
.ifdef DOS64_EXPORT_INTEGRATED
.import dos64_overlay_files_start,dos64_overlay_files_poll
 dos64_files_start = dos64_overlay_files_start
 dos64_files_poll = dos64_overlay_files_poll
 EXPORT_STAGE = $B800
.else
.import dos64_files_start,dos64_files_poll
 EXPORT_STAGE = $8000
.endif
.import dos64_uci_abort
.import dos64_files_state,dos64_files_handle,dos64_files_op,dos64_files_mode
.import dos64_files_count,dos64_files_actual,dos64_files_now,dos64_files_path_len
.import dos64_files_error,dos64_files_transport_error
.import dos64_files_uncertain,dos64_uci_command,dos64_uci_data,dos64_uci_now
.import dos64_uci_state,dos64_uci_recovery_failed
.import dos64_reu_request,dos64_reu_transfer
.export dos64_export_init,dos64_export_start,dos64_export_poll
.export dos64_export_state,dos64_export_error,dos64_export_cleanup_error
.export dos64_export_verified,dos64_export_uncertain,dos64_export_sectors
.export dos64_export_now,dos64_export_elapsed,dos64_export_limit
.export dos64_export_owned,dos64_export_paused,dos64_export_bank
.export dos64_export_path_len,dos64_export_path,dos64_export_cancel
.export dos64_export_failure_phase,dos64_export_failure_sector
.export dos64_export_failure_files_error,dos64_export_failure_transport_error
.export dos64_export_phase,dos64_export_state_start,dos64_export_state_end
.export dos64_export_code_start,dos64_export_code_end
.segment "DEVICESTATE"
dos64_export_state_start:
dos64_export_state: .res 1
dos64_export_error: .res 1
dos64_export_cleanup_error: .res 1
dos64_export_verified: .res 1
dos64_export_uncertain: .res 1
dos64_export_sectors: .res 2
dos64_export_now: .res 2
dos64_export_elapsed: .res 4
dos64_export_limit: .res 4
dos64_export_owned: .res 1
dos64_export_paused: .res 1
dos64_export_bank: .res 1
dos64_export_path_len: .res 1
dos64_export_path: .res 128
dos64_export_cancel: .res 1
dos64_export_phase: .res 1
dos64_export_failure_phase: .res 1
dos64_export_failure_sector: .res 2
dos64_export_failure_files_error: .res 1
dos64_export_failure_transport_error: .res 1
export_last: .res 2
export_delta: .res 2
export_far: .res 3
export_page: .res 1
dos64_export_state_end:
.ifdef DOS64_EXPORT_INTEGRATED
.segment "SAVERCODE"
.else
.segment "CODE"
.endif
dos64_export_code_start:
.macro ENTER
 php
 sei
 cld
 lda $00
 pha
 ora #7
 sta $00
 lda $01
 pha
 and #$f8
 ora #5
 sta $01
.endmacro
.macro LEAVE c
 pla
 sta $01
 pla
 sta $00
 plp
 .if c
 sec
 .else
 clc
 .endif
 rts
.endmacro
; Phases:1OPENcreate,2DMAwrite,3WRITEwait,4CLOSEwrite,5OPENread,
; 6READwait,7DMAcompare,8comparepage,9EOFwait,10CLOSEverify,11cleanupCLOSE,12INFO.
dos64_export_init:
 ENTER
 lda #0
 ldx #dos64_export_state_end-dos64_export_state_start-1
@clear: sta dos64_export_state_start,x
 dex
 cpx #$ff
 bne @clear
 lda #$c3
 sta dos64_export_limit
 lda #$33
 sta dos64_export_limit+1
 lda #2
 sta dos64_export_limit+2
 LEAVE 0
export_clock:
 lda dos64_export_now
 sta dos64_files_now
 sta dos64_uci_now
 lda dos64_export_now+1
 sta dos64_files_now+1
 sta dos64_uci_now+1
 rts
export_launch:
 jsr export_clock
 jmp dos64_files_start
export_open:
 ldx dos64_export_path_len
 stx dos64_files_path_len
 dex
@copy: lda dos64_export_path,x
 sta dos64_uci_command+3,x
 dex
 bpl @copy
 lda #FILES_OPEN
 sta dos64_files_op
 jmp export_launch
export_reset_position:
 lda #0
 sta dos64_export_sectors
 sta dos64_export_sectors+1
 sta export_far
 sta export_far+1
 lda dos64_export_bank
 sta export_far+2
 rts
dos64_export_start:
 ENTER
 lda dos64_export_state
 cmp #EXPORT_BUSY
 jeq export_reject
 lda dos64_export_owned
 cmp #$a5
 jne export_reject
 lda dos64_export_paused
 cmp #$a5
 jne export_reject
 lda dos64_export_bank
 cmp #$10
 beq @bank
 cmp #$18
 jne export_reject
@bank:
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq export_reject
 lda dos64_files_handle
 jne export_reject
 lda dos64_uci_state
 cmp #UCI_IDLE
 beq @quiet
 cmp #UCI_DONE
 beq @quiet
 cmp #UCI_FAILED
 jne export_reject
 lda dos64_uci_recovery_failed
 jne export_reject
@quiet:
 lda dos64_export_path_len
 cmp #2
 jcc export_reject
 cmp #129
 jcs export_reject
 tax
 dex
 lda dos64_export_path,x
 jne export_reject
 dex
@path:
 lda dos64_export_path,x
 jeq export_reject
 dex
 bpl @path
 lda dos64_export_path
 cmp #'/'
 jne export_reject
 lda dos64_export_limit
 ora dos64_export_limit+1
 ora dos64_export_limit+2
 ora dos64_export_limit+3
 jeq export_reject
 lda #0
 sta dos64_export_error
 sta dos64_export_cleanup_error
 sta dos64_export_verified
 sta dos64_export_cancel
 sta dos64_export_failure_phase
 sta dos64_export_failure_sector
 sta dos64_export_failure_sector+1
 sta dos64_export_failure_files_error
 sta dos64_export_failure_transport_error
 ldx #3
@elapsed: sta dos64_export_elapsed,x
 dex
 bpl @elapsed
 lda dos64_export_now
 sta export_last
 lda dos64_export_now+1
 sta export_last+1
 jsr export_reset_position
 lda #1
 sta dos64_export_uncertain
 sta dos64_export_state
 sta dos64_export_phase
 lda #6                         ; WRITE | CREATE_NEW; no truncate bit
 sta dos64_files_mode
 jsr export_open
 jcs export_file_error
 LEAVE 0
export_reject:
 LEAVE 1
; Fixed512-byte REU->RAM only. No path can write the authoritative REU image.
export_dma:
 sta dos64_reu_request+R_HOST
 stx dos64_reu_request+R_HOST+1
 ldx #2
@far: lda export_far,x
 sta dos64_reu_request+R_REU,x
 dex
 bpl @far
 lda #0
 sta dos64_reu_request+R_LENGTH
 lda #2
 sta dos64_reu_request+R_LENGTH+1
 lda #1
 sta dos64_reu_request+R_DIRECTION
 jmp dos64_reu_transfer
export_advance:
 inc dos64_export_sectors
 bne @far
 inc dos64_export_sectors+1
@far:
 clc
 lda export_far+1
 adc #2
 sta export_far+1
 bcc @done
 inc export_far+2
@done:
 lda dos64_export_sectors+1
 cmp #2
 bne @more
 lda dos64_export_sectors
 cmp #$d0
 bne @more
 sec
 rts
@more: clc
 rts
export_read:
 lda #0
 sta dos64_files_count
 lda #2
 sta dos64_files_count+1
 lda #FILES_READ
 sta dos64_files_op
 jmp export_launch
; Record primary error once, then try exactly one known/unknown-handle CLOSE.
export_record:
 sta dos64_export_error
 lda dos64_export_phase
 sta dos64_export_failure_phase
 lda dos64_export_sectors
 sta dos64_export_failure_sector
 lda dos64_export_sectors+1
 sta dos64_export_failure_sector+1
 lda dos64_files_error
 sta dos64_export_failure_files_error
 lda dos64_files_transport_error
 sta dos64_export_failure_transport_error
 rts
export_file_error:
 lda #EXPORT_ERR_FILES
export_fail:
 ldx dos64_export_error
 bne @recorded
 jsr export_record
@recorded:
 lda dos64_files_handle
 beq export_failed
 lda dos64_uci_recovery_failed
 bne export_unclean
 lda #11
 sta dos64_export_phase
 lda #FILES_CLOSE
 sta dos64_files_op
 jsr export_launch
 bcs export_unclean
 LEAVE 0
export_unclean:
 lda #1
 sta dos64_export_cleanup_error
export_failed:
 lda #EXPORT_FAILED
 sta dos64_export_state
 LEAVE 0
export_time_fail:
 lda dos64_export_error
 bne @have
 lda #EXPORT_ERR_TIME
 jsr export_record
@have:
 lda dos64_files_state
 cmp #FILES_BUSY
 bne @handle
 jsr export_clock
 jsr dos64_uci_abort
 lda #2
 sta dos64_files_handle
@handle:
 lda dos64_files_handle
 bne export_unclean
 jmp export_failed

dos64_export_poll:
 ENTER
 lda dos64_export_state
 cmp #EXPORT_BUSY
 jne export_reject
 ; Total elapsed uses caller clock, not iteration counts. Gap>=8000 is fatal.
 sec
 lda dos64_export_now
 sbc export_last
 sta export_delta
 lda dos64_export_now+1
 sbc export_last+1
 sta export_delta+1
 jmi export_time_fail
 lda dos64_export_now
 sta export_last
 lda dos64_export_now+1
 sta export_last+1
 clc
 lda dos64_export_elapsed
 adc export_delta
 sta dos64_export_elapsed
 lda dos64_export_elapsed+1
 adc export_delta+1
 sta dos64_export_elapsed+1
 lda dos64_export_elapsed+2
 adc #0
 sta dos64_export_elapsed+2
 lda dos64_export_elapsed+3
 adc #0
 sta dos64_export_elapsed+3
 jcs export_time_fail
 ldx #3
@deadline:
 lda dos64_export_elapsed,x
 cmp dos64_export_limit,x
 jcc @time_ok
 jne export_time_fail
 dex
 bpl @deadline
 jmp export_time_fail
@time_ok:
 lda dos64_export_cancel
 beq @work
 lda dos64_export_error
 bne @work                        ; cleanup proceeds despite latched cancel
 lda #EXPORT_ERR_CANCEL
 jsr export_record
 lda dos64_files_state
 cmp #FILES_BUSY
 bne @cancel_quiet
 jsr export_clock
 jsr dos64_uci_abort
@cancel_quiet:
 ; FILE poll must finish abort recovery before cleanup launch.
@work:
 lda dos64_files_state
 cmp #FILES_BUSY
 bne @ready
 jsr export_clock
 jsr dos64_files_poll
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq export_return
@ready:
 lda dos64_export_phase
 cmp #11
 jeq @cleanup
 lda dos64_export_error
 jne export_fail
 lda dos64_files_state
 cmp #FILES_FAILED
 jeq export_file_error
 lda dos64_export_phase
 cmp #1
 beq @opened_write
 cmp #2
 jeq @dma_write
 cmp #3
 jeq @wrote
 cmp #4
 jeq @closed_write
 cmp #5
 jeq @opened_read
 cmp #6
 jeq @read
 cmp #7
 jeq @dma_compare
 cmp #8
 jeq @compare
 cmp #9
 jeq @eof
 cmp #10
 jeq @closed_verify
 cmp #12
 jeq @info
 lda #EXPORT_ERR_FILES
 jmp export_fail
@cleanup:
 lda dos64_files_state
 cmp #FILES_DONE
 jne export_unclean
 lda dos64_files_handle
 jne export_unclean
 jmp export_failed
@opened_write:
 lda #2
 sta dos64_export_phase
 jmp export_return
@dma_write:
 lda #<(dos64_uci_command+4)
 ldx #>(dos64_uci_command+4)
 jsr export_dma
 jcs export_dma_error
 lda #FILES_WRITE
 sta dos64_files_op
 lda #0
 sta dos64_files_count
 lda #2
 sta dos64_files_count+1
 jsr export_launch
 jcs export_file_error
 lda #3
 sta dos64_export_phase
 jmp export_return
@wrote:
 jsr export_advance
 bcs @close_write
 lda #2
 sta dos64_export_phase
 jmp export_return
@close_write:
 lda #4
 sta dos64_export_phase
 jmp export_close
@closed_write:
 lda #1
 sta dos64_files_mode
 lda #5
 sta dos64_export_phase
 jsr export_open
 jcs export_file_error
 jmp export_return
@opened_read:
 lda #12
 sta dos64_export_phase
 lda #FILES_INFO
 sta dos64_files_op
 jsr export_launch
 jcs export_file_error
 jmp export_return
@info:
 ; Consume the freshly validated metadata before a READ overwrites UCI data.
 lda dos64_uci_data
 jne export_length_error
 lda dos64_uci_data+1
 cmp #$a0
 jne export_length_error
 lda dos64_uci_data+2
 cmp #5
 jne export_length_error
 lda dos64_uci_data+3
 jne export_length_error
 jsr export_reset_position
 lda #6
 sta dos64_export_phase
 jsr export_read
 jcs export_file_error
 jmp export_return
@read:
 lda dos64_files_actual
 jne export_short
 lda dos64_files_actual+1
 cmp #2
 jne export_short
 lda #7
 sta dos64_export_phase
 jmp export_return
@dma_compare:
 lda #0
 ldx #>EXPORT_STAGE
 jsr export_dma
 jcs export_dma_error
 lda #0
 sta export_page
 lda #8
 sta dos64_export_phase
 jmp export_return
@compare:
 ldy #0
 lda export_page
 bne @second
@first:
 lda EXPORT_STAGE,y
 cmp dos64_uci_data,y
 jne export_compare_error
 iny
 bne @first
 inc export_page
 jmp export_return
@second:
 lda EXPORT_STAGE+$100,y
 cmp dos64_uci_data+$100,y
 jne export_compare_error
 iny
 bne @second
 jsr export_advance
 bcs @read_eof
 lda #6
 sta dos64_export_phase
 jsr export_read
 jcs export_file_error
 jmp export_return
@read_eof:
 lda #9
 sta dos64_export_phase
 lda #1
 sta dos64_files_count
 lda #0
 sta dos64_files_count+1
 lda #FILES_READ
 sta dos64_files_op
 jsr export_launch
 jcs export_file_error
 jmp export_return
@eof:
 lda dos64_files_actual
 ora dos64_files_actual+1
 jne export_extra
 lda #10
 sta dos64_export_phase
 jmp export_close
@closed_verify:
 lda dos64_files_handle
 jne export_file_error
 lda #0
 sta dos64_export_uncertain
 sta dos64_files_uncertain
 lda #1
 sta dos64_export_verified
 lda #EXPORT_DONE
 sta dos64_export_state
 jmp export_return
export_dma_error:
 lda #EXPORT_ERR_DMA
 jmp export_fail
export_short:
 lda #EXPORT_ERR_SHORT
 jmp export_fail
export_compare_error:
 lda #EXPORT_ERR_COMPARE
 jmp export_fail
export_length_error:
 lda #EXPORT_ERR_LENGTH
 jmp export_fail
export_extra:
 lda #EXPORT_ERR_EXTRA
 jmp export_fail
export_close:
 lda #FILES_CLOSE
 sta dos64_files_op
 jsr export_launch
 jcs export_file_error
export_return:
 LEAVE 0
dos64_export_code_end:
