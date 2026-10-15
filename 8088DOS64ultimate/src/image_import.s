.setcpu "6502"
.macpack longbranch
.include "image_import.inc"
.include "files.inc"
.include "uci.inc"
.include "reu.inc"
.include "overlays.inc"
.import dos64_overlay_files_start, dos64_overlay_files_poll
.import dos64_overlay_ready, dos64_overlay_busy
.import dos64_files_state, dos64_files_handle, dos64_files_op, dos64_files_mode
.import dos64_files_count, dos64_files_actual, dos64_files_now
.import dos64_uci_data, dos64_uci_abort, dos64_uci_now
.import dos64_reu_request, dos64_reu_transfer, dos64_disk_loaded
.export dos64_import_init, dos64_import_start, dos64_import_poll
.export dos64_import_state, dos64_import_error, dos64_import_cleanup_error
.export dos64_import_now, dos64_import_timeout, dos64_import_expected_crc
.export dos64_import_crc, dos64_import_sectors, dos64_import_phase
.export dos64_import_code_start, dos64_import_code_end
.export dos64_import_state_start, dos64_import_state_end
.segment "IMPORTCODE"
dos64_import_code_start:
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
import_clock:
 lda dos64_import_now
 sta dos64_files_now
 sta dos64_uci_now
 lda dos64_import_now+1
 sta dos64_files_now+1
 sta dos64_uci_now+1
 rts
import_launch:
 jsr import_clock
 jmp dos64_overlay_files_start

dos64_import_init:
 ENTER
 lda #0
 ldx #dos64_import_state_end-dos64_import_state_start-1
@clear:
 sta dos64_import_state_start,x
 dex
 bpl @clear
 sta dos64_disk_loaded
 LEAVE 0

dos64_import_start:
 ENTER
 lda dos64_import_state
 cmp #IMPORT_BUSY
 jeq import_reject
 lda dos64_overlay_ready
 cmp #OV_READY
 jne import_reject
 lda dos64_overlay_busy
 ora dos64_files_handle
 jne import_reject
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq import_reject
 lda dos64_import_timeout
 ora dos64_import_timeout+1
 jeq import_reject
 lda dos64_import_timeout+1
 jmi import_reject
 lda #0
 sta dos64_disk_loaded
 sta dos64_import_error
 sta dos64_import_cleanup_error
 sta dos64_import_sectors
 sta dos64_import_sectors+1
 sta import_offset
 sta import_offset+1
 sta import_far
 sta import_far+1
 lda #$10
 sta import_far+2
 lda dos64_import_now
 sta import_started
 lda dos64_import_now+1
 sta import_started+1
 lda #$ff
 ldx #3
@crc:
 sta dos64_import_crc,x
 dex
 bpl @crc
 lda #FILES_OPEN
 sta dos64_files_op
 lda #1
 sta dos64_files_mode
 sta dos64_import_phase
 jsr import_launch
 bcs @failed
 lda #IMPORT_BUSY
 sta dos64_import_state
 LEAVE 0
@failed:
 lda #IMPORT_ERR_INPUT
 sta dos64_import_error
 lda #IMPORT_FAILED
 sta dos64_import_state
 LEAVE 1
import_reject:
 LEAVE 1

dos64_import_poll:
 ENTER
 lda dos64_import_state
 cmp #IMPORT_BUSY
 jne import_reject
 jsr import_clock
 lda dos64_import_phase
 cmp #7
 jcs import_cleanup
 ; modular elapsed deadline, recovery has independent transport deadline.
 sec
 lda dos64_import_now
 sbc import_started
 tax
 lda dos64_import_now+1
 sbc import_started+1
 cmp dos64_import_timeout+1
 bcc @active
 bne @timeout
 cpx dos64_import_timeout
 bcc @active
@timeout:
 lda #IMPORT_ERR_TIMEOUT
 sta dos64_import_error
 lda dos64_files_state
 cmp #FILES_BUSY
 jne import_begin_cleanup
 jsr dos64_uci_abort
 lda #7
 sta dos64_import_phase
 jmp import_return
@active:
 lda dos64_import_phase
 cmp #3
 jeq import_crc_work
 cmp #4
 jeq import_dma
 jsr dos64_overlay_files_poll
 jcs import_files_failed
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq import_return
 cmp #FILES_DONE
 jne import_files_failed
 lda dos64_import_phase
 cmp #1
 beq import_read_start
 cmp #2
 jeq import_read_done
 cmp #5
 jeq import_eof_done
 ; successful close must establish known closed ownership.
 lda dos64_files_handle
 jne import_close_failed
 lda #IMPORT_DONE
 sta dos64_import_state
 lda #1
 sta dos64_disk_loaded
 jmp import_return
import_read_start:
 lda #2
 sta dos64_import_phase
 lda #0
 sta dos64_files_count
 lda #2
 sta dos64_files_count+1
 lda #FILES_READ
 sta dos64_files_op
 jsr import_launch
 jcs import_files_failed
 jmp import_return
import_read_done:
 lda dos64_files_actual
 jne import_short
 lda dos64_files_actual+1
 cmp #2
 jne import_short
 lda #0
 sta import_offset
 sta import_offset+1
 lda #3
 sta dos64_import_phase
 jmp import_return
import_crc_work:
 lda #16
 sta import_work
@byte:
 ldx import_offset
 lda import_offset+1
 bne @upper
 lda dos64_uci_data,x
 jmp @xor
@upper:
 lda dos64_uci_data+$100,x
@xor:
 eor dos64_import_crc
 sta dos64_import_crc
 ldy #8
@bit:
 lsr dos64_import_crc+3
 ror dos64_import_crc+2
 ror dos64_import_crc+1
 ror dos64_import_crc
 bcc @next
 lda dos64_import_crc
 eor #$20
 sta dos64_import_crc
 lda dos64_import_crc+1
 eor #$83
 sta dos64_import_crc+1
 lda dos64_import_crc+2
 eor #$b8
 sta dos64_import_crc+2
 lda dos64_import_crc+3
 eor #$ed
 sta dos64_import_crc+3
@next:
 dey
 bne @bit
 inc import_offset
 bne :+
 inc import_offset+1
: dec import_work
 bne @byte
 lda import_offset+1
 cmp #2
 jne import_return
 lda #4
 sta dos64_import_phase
 jmp import_return
import_dma:
 lda #<dos64_uci_data
 sta dos64_reu_request+R_HOST
 lda #>dos64_uci_data
 sta dos64_reu_request+R_HOST+1
 ldx #2
@far:
 lda import_far,x
 sta dos64_reu_request+R_REU,x
 dex
 bpl @far
 lda #0
 sta dos64_reu_request+R_DIRECTION
 sta dos64_reu_request+R_LENGTH
 lda #2
 sta dos64_reu_request+R_LENGTH+1
 jsr dos64_reu_transfer
 jcs import_dma_failed
 clc
 lda import_far+1
 adc #2
 sta import_far+1
 bcc :+
 inc import_far+2
: inc dos64_import_sectors
 bne :+
 inc dos64_import_sectors+1
: lda dos64_import_sectors+1
 cmp #2
 jne import_read_start
 lda dos64_import_sectors
 cmp #$d0
 jne import_read_start
 lda #5
 sta dos64_import_phase
 lda #1
 sta dos64_files_count
 lda #0
 sta dos64_files_count+1
 lda #FILES_READ
 sta dos64_files_op
 jsr import_launch
 jcs import_files_failed
 jmp import_return
import_eof_done:
 lda dos64_files_actual
 ora dos64_files_actual+1
 bne import_extra
 ldx #3
@finalize:
 lda dos64_import_crc,x
 eor #$ff
 sta dos64_import_crc,x
 dex
 bpl @finalize
 ldx #3
@compare:
 lda dos64_import_crc,x
 cmp dos64_import_expected_crc,x
 bne import_crc_failed
 dex
 bpl @compare
 lda #6
 sta dos64_import_phase
 lda #FILES_CLOSE
 sta dos64_files_op
 jsr import_launch
 bcs import_close_failed
 jmp import_return
import_short:
 lda #IMPORT_ERR_SHORT
 bne import_error
import_extra:
 lda #IMPORT_ERR_EXTRA
 bne import_error
import_crc_failed:
 lda #IMPORT_ERR_CRC
 bne import_error
import_dma_failed:
 lda #IMPORT_ERR_DMA
 bne import_error
import_close_failed:
 lda #IMPORT_ERR_CLOSE
 bne import_error
import_files_failed:
 lda dos64_import_phase
 cmp #6
 beq import_close_failed
 lda #IMPORT_ERR_FILES
import_error:
 sta dos64_import_error
import_begin_cleanup:
 lda #7
 sta dos64_import_phase
import_cleanup:
 lda dos64_import_phase
 cmp #8
 beq @closing
 lda dos64_files_state
 cmp #FILES_BUSY
 bne @close
 jsr dos64_overlay_files_poll
 jmp import_return
@close:
 lda dos64_files_handle
 beq import_failed
 lda #FILES_CLOSE
 sta dos64_files_op
 jsr import_launch
 bcs @cleanup_failed
 lda #8
 sta dos64_import_phase
 jmp import_return
@closing:
 jsr dos64_overlay_files_poll
 bcs @cleanup_failed
 lda dos64_files_state
 cmp #FILES_BUSY
 beq import_return
 cmp #FILES_DONE
 bne @cleanup_failed
 lda dos64_files_handle
 bne @cleanup_failed
 beq import_failed
@cleanup_failed:
 lda #1
 sta dos64_import_cleanup_error
import_failed:
 lda #IMPORT_FAILED
 sta dos64_import_state
 lda #0
 sta dos64_disk_loaded
import_return:
 LEAVE 0

dos64_import_state_start:
dos64_import_state: .byte 0
dos64_import_error: .byte 0
dos64_import_cleanup_error: .byte 0
dos64_import_now: .word 0
dos64_import_timeout: .word 0
dos64_import_expected_crc: .dword 0
dos64_import_crc: .dword 0
dos64_import_sectors: .word 0
dos64_import_phase: .byte 0
import_started: .word 0
import_far: .byte 0,0,0
import_offset: .word 0
import_work: .byte 0
dos64_import_state_end:
dos64_import_code_end:
.assert dos64_import_code_end-dos64_import_code_start <= $1000, error, "import exceeds cold startup window"
