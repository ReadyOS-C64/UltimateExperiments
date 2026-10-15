.setcpu "6502"
.macpack longbranch
.include "native_file_restore.inc"
.include "files.inc"
.include "uci.inc"
.include "reu.inc"
.import dos64_files_start, dos64_files_poll
.import dos64_files_target,dos64_files_owned_target
.import dos64_files_state, dos64_files_handle, dos64_files_op, dos64_files_mode
.import dos64_files_count, dos64_files_actual, dos64_files_now
.import dos64_uci_data, dos64_uci_abort, dos64_uci_now
.import dos64_reu_request, dos64_reu_transfer
.export dos64_restore_complete
.exportzp restore_stage
.export dos64_restore_cold_init, dos64_restore_cold_start, dos64_restore_cold_poll
.export dos64_restore_state, dos64_restore_error, dos64_restore_cleanup_error
.export dos64_restore_now, dos64_restore_expected_crc, dos64_restore_elapsed
.export dos64_restore_limit, dos64_restore_operation_limit
.export dos64_restore_crc, dos64_restore_sectors, dos64_restore_phase
.export dos64_restore_code_start, dos64_restore_code_end
.export dos64_restore_state_start, dos64_restore_state_end
.segment "ZEROPAGE"
restore_stage: .res 2
.segment "CODE"
dos64_restore_code_start:
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
; Internal phases: OPEN1, READ2, CRC3, DMA4, EOF5, CLOSE6,
; failed-transaction recovery7, cleanup close8. All state is cold RAM.
restore_clock:
 lda dos64_restore_now
 sta dos64_files_now
 sta dos64_uci_now
 lda dos64_restore_now+1
 sta dos64_files_now+1
 sta dos64_uci_now+1
 rts
restore_launch:
 jsr restore_clock
 jmp dos64_files_start

dos64_restore_cold_init:
 ENTER
 lda #0
 ldx #dos64_restore_state_end-dos64_restore_state_start-1
@clear:
 sta dos64_restore_state_start,x
 dex
 bpl @clear
 sta dos64_restore_complete
 lda #$c3
 sta dos64_restore_limit
 lda #$33
 sta dos64_restore_limit+1
 lda #2
 sta dos64_restore_limit+2
 lda #$5e
 sta dos64_restore_operation_limit
 lda #$2a
 sta dos64_restore_operation_limit+1
 lda #2
 sta dos64_restore_operation_limit+2
 LEAVE 0

dos64_restore_cold_start:
 ENTER
 lda dos64_restore_state
 cmp #IMPORT_BUSY
 jeq restore_reject
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq restore_reject
 lda #0
 sta dos64_restore_complete
 sta dos64_restore_error
 sta dos64_restore_cleanup_error
 sta dos64_restore_sectors
 sta dos64_restore_sectors+1
 sta restore_offset
 sta restore_offset+1
 sta restore_far
 sta restore_far+1
 sta restore_far+2
 sta restore_fill
 ldx #3
@elapsed:
 sta dos64_restore_elapsed,x
 dex
 bpl @elapsed
 lda #0
 sta restore_stage
 lda #$80
 sta restore_stage+1
 lda dos64_restore_now
 sta restore_last
 lda dos64_restore_now+1
 sta restore_last+1
 lda #$ff
 ldx #3
@crc:
 sta dos64_restore_crc,x
 dex
 bpl @crc
 ; A reset cannot establish the firmware's single-file handle ownership.
 lda dos64_files_target
 sta dos64_files_owned_target
 lda #2
 sta dos64_files_handle
 lda #FILES_CLOSE
 sta dos64_files_op
 lda #1
 sta dos64_files_mode
 lda #9
 sta dos64_restore_phase
 jsr restore_launch
 bcs @failed
 lda #IMPORT_BUSY
 sta dos64_restore_state
 LEAVE 0
@failed:
 lda #IMPORT_ERR_INPUT
 sta dos64_restore_error
 lda #IMPORT_FAILED
 sta dos64_restore_state
 LEAVE 1
restore_reject:
 LEAVE 1

dos64_restore_cold_poll:
 ENTER
 lda dos64_restore_state
 cmp #IMPORT_BUSY
 jne restore_reject
 jsr restore_clock
 ; Accumulate modulo16 elapsed units into32 bits, including cleanup.
 sec
 lda dos64_restore_now
 sbc restore_last
 sta restore_delta
 lda dos64_restore_now+1
 sbc restore_last+1
 sta restore_delta+1
 lda dos64_restore_now
 sta restore_last
 lda dos64_restore_now+1
 sta restore_last+1
 clc
 lda dos64_restore_elapsed
 adc restore_delta
 sta dos64_restore_elapsed
 lda dos64_restore_elapsed+1
 adc restore_delta+1
 sta dos64_restore_elapsed+1
 lda dos64_restore_elapsed+2
 adc #0
 sta dos64_restore_elapsed+2
 lda dos64_restore_elapsed+3
 adc #0
 sta dos64_restore_elapsed+3
 ; Hard600s PAL-nominal bound includes recovery; retain unknown ownership.
 ldx #3
@hard:
 lda dos64_restore_elapsed,x
 cmp dos64_restore_limit,x
 bcc @phase
 bne @hard_timeout
 dex
 bpl @hard
@hard_timeout:
 lda #IMPORT_ERR_TIMEOUT
 sta dos64_restore_error
 lda #1
 sta dos64_restore_cleanup_error
 lda dos64_files_handle
 beq :+
 lda #2
 sta dos64_files_handle
: jmp restore_failed
@phase:
 lda dos64_restore_phase
 cmp #9
 beq @operation
 cmp #7
 jcs restore_cleanup
@operation:
 ldx #3
@deadline:
 lda dos64_restore_elapsed,x
 cmp dos64_restore_operation_limit,x
 bcc @active
 bne @timeout
 dex
 bpl @deadline
@timeout:
 lda #IMPORT_ERR_TIMEOUT
 sta dos64_restore_error
 lda dos64_files_state
 cmp #FILES_BUSY
 jne restore_begin_cleanup
 jsr dos64_uci_abort
 lda #7
 sta dos64_restore_phase
 jmp restore_return
@active:
 lda dos64_restore_phase
 cmp #3
 jeq restore_crc_work
 cmp #4
 jeq restore_dma
 jsr dos64_files_poll
 jcs restore_files_failed
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq restore_return
 cmp #FILES_DONE
 beq @file_done
 lda dos64_restore_phase
 cmp #9
 jne restore_files_failed
 lda dos64_files_handle
 jne restore_files_failed
 jmp restore_open_start
@file_done:
 lda dos64_restore_phase
 cmp #9
 jeq restore_open_start
 cmp #1
 beq restore_read_start
 cmp #2
 jeq restore_read_done
 cmp #5
 jeq restore_eof_done
 ; successful close must establish known closed ownership.
 lda dos64_files_handle
 jne restore_close_failed
 lda #IMPORT_DONE
 sta dos64_restore_state
 lda #1
 sta dos64_restore_complete
 jmp restore_return
restore_open_start:
 lda #1
 sta dos64_restore_phase
 lda #FILES_OPEN
 sta dos64_files_op
 jsr restore_launch
 jcs restore_files_failed
 jmp restore_return
restore_read_start:
 lda #2
 sta dos64_restore_phase
 lda #0
 sta dos64_files_count
 lda #2
 sta dos64_files_count+1
 lda #FILES_READ
 sta dos64_files_op
 jsr restore_launch
 jcs restore_files_failed
 jmp restore_return
restore_read_done:
 lda dos64_files_actual
 jne restore_short
 lda dos64_files_actual+1
 cmp #2
 jne restore_short
 lda #0
 sta restore_offset
 sta restore_offset+1
 lda #3
 sta dos64_restore_phase
 jmp restore_return
restore_crc_work:
 lda #16
 sta restore_work
@byte:
 ldx restore_offset
 txa
 tay
 lda restore_offset+1
 bne @copy_upper
 lda dos64_uci_data,x
 jmp @copy
@copy_upper:
 lda dos64_uci_data+$100,x
@copy:
 sta (restore_stage),y
 eor dos64_restore_crc
 sta dos64_restore_crc
 ldy #8
@bit:
 lsr dos64_restore_crc+3
 ror dos64_restore_crc+2
 ror dos64_restore_crc+1
 ror dos64_restore_crc
 bcc @next
 lda dos64_restore_crc
 eor #$20
 sta dos64_restore_crc
 lda dos64_restore_crc+1
 eor #$83
 sta dos64_restore_crc+1
 lda dos64_restore_crc+2
 eor #$b8
 sta dos64_restore_crc+2
 lda dos64_restore_crc+3
 eor #$ed
 sta dos64_restore_crc+3
@next:
 dey
 bne @bit
 inc restore_offset
 bne :+
 inc restore_offset+1
 inc restore_stage+1
: dec restore_work
 bne @byte
 lda restore_offset+1
 cmp #2
 jne restore_return
 inc dos64_restore_sectors
 bne :+
 inc dos64_restore_sectors+1
: inc restore_fill
 inc restore_fill
 lda restore_fill
 cmp #8
 jne restore_read_start
 lda #4
 sta dos64_restore_phase
 jmp restore_return
restore_dma:
 lda #0
 sta dos64_reu_request+R_HOST
 lda #$80
 sta dos64_reu_request+R_HOST+1
 ldx #2
@far:
 lda restore_far,x
 sta dos64_reu_request+R_REU,x
 dex
 bpl @far
 lda #0
 sta dos64_reu_request+R_DIRECTION
 sta dos64_reu_request+R_LENGTH
 lda #8
 sta dos64_reu_request+R_LENGTH+1
 jsr dos64_reu_transfer
 jcs restore_dma_failed
 clc
 lda restore_far+1
 adc #8
 sta restore_far+1
 bcc :+
 inc restore_far+2
: lda #0
 sta restore_fill
 sta restore_stage
 lda #$80
 sta restore_stage+1
 lda dos64_restore_sectors+1
 cmp #$20
 jne restore_read_start
 lda dos64_restore_sectors
 cmp #0
 jne restore_read_start
 lda #5
 sta dos64_restore_phase
 lda #1
 sta dos64_files_count
 lda #0
 sta dos64_files_count+1
 lda #FILES_READ
 sta dos64_files_op
 jsr restore_launch
 jcs restore_files_failed
 jmp restore_return
restore_eof_done:
 lda dos64_files_actual
 ora dos64_files_actual+1
 bne restore_extra
 ldx #3
@finalize:
 lda dos64_restore_crc,x
 eor #$ff
 sta dos64_restore_crc,x
 dex
 bpl @finalize
 ldx #3
@compare:
 lda dos64_restore_crc,x
 cmp dos64_restore_expected_crc,x
 bne restore_crc_failed
 dex
 bpl @compare
 lda #6
 sta dos64_restore_phase
 lda #FILES_CLOSE
 sta dos64_files_op
 jsr restore_launch
 bcs restore_close_failed
 jmp restore_return
restore_short:
 lda #IMPORT_ERR_SHORT
 bne restore_error
restore_extra:
 lda #IMPORT_ERR_EXTRA
 bne restore_error
restore_crc_failed:
 lda #IMPORT_ERR_CRC
 bne restore_error
restore_dma_failed:
 lda #IMPORT_ERR_DMA
 bne restore_error
restore_close_failed:
 lda #IMPORT_ERR_CLOSE
 bne restore_error
restore_files_failed:
 lda dos64_restore_phase
 cmp #6
 beq restore_close_failed
 lda #IMPORT_ERR_FILES
restore_error:
 sta dos64_restore_error
restore_begin_cleanup:
 lda #7
 sta dos64_restore_phase
restore_cleanup:
 lda dos64_restore_phase
 cmp #8
 beq @closing
 lda dos64_files_state
 cmp #FILES_BUSY
 bne @close
 jsr dos64_files_poll
 jmp restore_return
@close:
 lda dos64_files_handle
 beq restore_failed
 lda #FILES_CLOSE
 sta dos64_files_op
 jsr restore_launch
 bcs @cleanup_failed
 lda #8
 sta dos64_restore_phase
 jmp restore_return
@closing:
 jsr dos64_files_poll
 bcs @cleanup_failed
 lda dos64_files_state
 cmp #FILES_BUSY
 beq restore_return
 cmp #FILES_DONE
 beq @closed_check
 lda dos64_files_handle
 beq restore_failed
 bne @cleanup_failed
@closed_check:
 lda dos64_files_handle
 bne @cleanup_failed
 beq restore_failed
@cleanup_failed:
 lda #1
 sta dos64_restore_cleanup_error
restore_failed:
 lda #IMPORT_FAILED
 sta dos64_restore_state
 lda #0
 sta dos64_restore_complete
restore_return:
 LEAVE 0

.segment "DEVICESTATE"
dos64_restore_state_start:
dos64_restore_complete: .res 1
dos64_restore_state: .res 1
dos64_restore_error: .res 1
dos64_restore_cleanup_error: .res 1
dos64_restore_now: .res 2
dos64_restore_elapsed: .res 4
dos64_restore_limit: .res 4
dos64_restore_operation_limit: .res 4
dos64_restore_expected_crc: .res 4
dos64_restore_crc: .res 4
dos64_restore_sectors: .res 2
dos64_restore_phase: .res 1
restore_last: .res 2
restore_delta: .res 2
restore_fill: .res 1
restore_far: .res 3
restore_offset: .res 2
restore_work: .res 1
dos64_restore_state_end:
.segment "CODE"
dos64_restore_code_end:
