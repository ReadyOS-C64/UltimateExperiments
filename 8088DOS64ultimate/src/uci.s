.setcpu "6502"
.macpack longbranch
.include "uci.inc"
.export dos64_uci_init, dos64_uci_start, dos64_uci_poll, dos64_uci_accept, dos64_uci_abort
.export dos64_uci_code_start, dos64_uci_code_end
.export dos64_uci_state_start, dos64_uci_state_end, dos64_uci_base, dos64_uci_now
.export dos64_uci_timeout, dos64_uci_recovery_timeout, dos64_uci_state, dos64_uci_error
.export dos64_uci_last_status, dos64_uci_recovery_failed, dos64_uci_flags
.export dos64_uci_command_len, dos64_uci_data_capacity, dos64_uci_status_capacity
.export dos64_uci_data_len, dos64_uci_status_len, dos64_uci_data_seen, dos64_uci_status_seen
.export dos64_uci_blocks, dos64_uci_command, dos64_uci_data, dos64_uci_status
.export dos64_uci_buffer_start, dos64_uci_buffer_end
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
.import hdb_extension_ready,dos64_uci_trace_first,dos64_uci_trace_last_id
.endif
.segment "DEVICESTATE"
dos64_uci_state_start:
dos64_uci_base: .res 2
dos64_uci_now: .res 2
dos64_uci_timeout: .res 2
dos64_uci_recovery_timeout: .res 2
dos64_uci_command_len: .res 2
dos64_uci_data_capacity: .res 2
dos64_uci_status_capacity: .res 2
dos64_uci_state: .res 1
dos64_uci_error: .res 1
dos64_uci_recovery_failed: .res 1
dos64_uci_last_status: .res 1
dos64_uci_flags: .res 1
uci_deadline: .res 2
uci_upload_pos: .res 2
dos64_uci_data_len: .res 2
dos64_uci_status_len: .res 2
dos64_uci_data_seen: .res 3
dos64_uci_status_seen: .res 3
uci_data_raw: .res 2
uci_status_raw: .res 2
dos64_uci_blocks: .res 2
uci_more: .res 1
uci_work: .res 1
uci_work_status: .res 1
dos64_uci_state_end:
.segment "UCIBUFFER"
dos64_uci_buffer_start:
dos64_uci_command: .res 896
dos64_uci_data: .res 896
dos64_uci_status: .res 256
dos64_uci_buffer_end:
.segment "DEVICECODE"
dos64_uci_code_start:
; Save P/X/Y, expose I/O while retaining RAM under KERNAL/BASIC. Routine code
; and buffers must stay outside A000-BFFF/E000-FFFF during this mapped span.
.macro ENTER
 php
 sei
 pha
 txa
 pha
 tya
 pha
 cld
 lda $00
 pha
 ora #7
 sta $00
 lda $01
 pha
 and #$f8
 ora #$05
 sta $01
.endmacro
.macro LEAVE carry
 pla
 sta $01
 pla
 sta $00
 pla
 tay
 pla
 tax
 pla
 plp
 .if carry
 sec
 .else
 clc
 .endif
 rts
.endmacro
; Patch all native register operands once per transaction. Only allow three
; documented/established mappings; no arbitrary pointer into native memory.
uci_patch:
 lda dos64_uci_base+1
 cmp #$de
 beq @de
 cmp #$df
 bne @bad
 lda dos64_uci_base
 cmp #$fc
 beq @good
@de:
 lda dos64_uci_base
 cmp #$1c
 bne @bad
@good:
 lda dos64_uci_base
 sta uci_status_read+1
 sta uci_control_write+1
 clc
 adc #1
 sta uci_id_read+1
 sta uci_command_write+1
 clc
 adc #1
 sta uci_data_read+1
 clc
 adc #1
 sta uci_stat_read+1
 lda dos64_uci_base+1
 sta uci_status_read+2
 sta uci_control_write+2
 sta uci_id_read+2
 sta uci_command_write+2
 sta uci_data_read+2
 sta uci_stat_read+2
 clc
 rts
@bad: sec
 rts
uci_status_read: lda $df1c
 sta dos64_uci_last_status
 rts
uci_id_read: lda $df1d
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
 sta dos64_uci_trace_last_id
.endif
 rts
uci_control_write: sta $df1c
 rts
uci_command_write: sta $df1d
 rts
uci_data_read: lda $df1e
 rts
uci_stat_read: lda $df1f
 rts
; Signed modular comparison is sound for caller's <8000 tick polling bound.
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
.segment "CODE"
.endif
uci_expired:
 lda dos64_uci_now
 sec
 sbc uci_deadline
 lda dos64_uci_now+1
 sbc uci_deadline+1
 bpl @yes
 clc
 rts
@yes: sec
 rts
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
.segment "DEVICECODE"
.endif
uci_set_deadline:
 lda dos64_uci_now
 clc
 adc dos64_uci_timeout
 sta uci_deadline
 lda dos64_uci_now+1
 adc dos64_uci_timeout+1
 sta uci_deadline+1
 rts
; A=first error. Keep it through recovery; a stuck recovery has its own flag.
uci_recover:
 sta dos64_uci_error
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
 lda hdb_extension_ready
 cmp #$a5
 bne @no_trace
 jsr dos64_uci_trace_first
@no_trace:
.endif
 lda #UCI_RECOVER
 sta dos64_uci_state
 lda dos64_uci_now
 clc
 adc dos64_uci_recovery_timeout
 sta uci_deadline
 lda dos64_uci_now+1
 adc dos64_uci_recovery_timeout+1
 sta uci_deadline+1
 jsr uci_status_read
 and #4
 bne @pending
 lda #4
 jsr uci_control_write
@pending: rts
uci_quiet:
 ; Fully quiet includes no residual queue flags as well as state/control bits.
 jsr uci_status_read
 cmp #0
 rts

dos64_uci_init:
 ENTER
 lda #0
 ldx #dos64_uci_state_end-dos64_uci_state_start-1
@zero: sta dos64_uci_state_start,x
 dex
 bpl @zero
 lda #$1c
 sta dos64_uci_base
 lda #$df
 sta dos64_uci_base+1
 lda #$80
 sta dos64_uci_data_capacity
 lda #3
 sta dos64_uci_data_capacity+1
 lda #1
 sta dos64_uci_status_capacity+1
 lda #$2c
 sta dos64_uci_timeout
 lda #1
 sta dos64_uci_timeout+1
 lda #60
 sta dos64_uci_recovery_timeout
 LEAVE 0

dos64_uci_start:
 ENTER
 lda dos64_uci_state
 beq @validate
 cmp #UCI_DONE
 beq @validate
 cmp #UCI_FAILED
 jne @reject
 lda dos64_uci_recovery_failed
 jne @reject
@validate:
 jsr uci_patch
 bcs @input
 lda dos64_uci_command_len
 ora dos64_uci_command_len+1
 beq @input
 lda dos64_uci_command_len+1
 cmp #3
 bcc @cap
 bne @input
 lda dos64_uci_command_len
 cmp #$80
 bcs @input
@cap:
 lda dos64_uci_command
 bmi @input
 lda dos64_uci_data_capacity+1
 cmp #3
 bcc @stat
 bne @input
 lda dos64_uci_data_capacity
 cmp #$81
 bcs @input
@stat:
 lda dos64_uci_status_capacity+1
 beq @duration
 cmp #1
 bne @input
 lda dos64_uci_status_capacity
 bne @input
@duration:
 lda dos64_uci_timeout
 ora dos64_uci_timeout+1
 beq @input
 lda dos64_uci_timeout+1
 bmi @input
 lda dos64_uci_recovery_timeout
 ora dos64_uci_recovery_timeout+1
 beq @input
 lda dos64_uci_recovery_timeout+1
 bmi @input
 jsr uci_id_read
 and #$7f
 cmp #$49
 bne @id
 lda #0
 ldx #dos64_uci_state_end-dos64_uci_state-1
@clear: sta dos64_uci_state,x
 dex
 bpl @clear
 lda #UCI_SYNC
 sta dos64_uci_state
 jsr uci_set_deadline
 LEAVE 0
@input: lda #UCI_ERR_INPUT
 bne @failure
@id: lda #UCI_ERR_ID
@failure:
 sta dos64_uci_error
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
 lda hdb_extension_ready
 cmp #$a5
 bne @no_start_trace
 jsr dos64_uci_trace_first
@no_start_trace:
.endif
 lda #UCI_FAILED
 sta dos64_uci_state
@reject:
 LEAVE 1

dos64_uci_abort:
 ENTER
 lda dos64_uci_state
 beq @reject
 cmp #UCI_RECOVER
 bcs @reject
 lda #UCI_ERR_CANCEL
 jsr uci_recover
 LEAVE 0
@reject: LEAVE 1

dos64_uci_accept:
 ENTER
 lda dos64_uci_state
 cmp #UCI_BLOCK
 bne @reject
 jsr uci_expired
 bcs @timeout
 lda #2
 jsr uci_control_write
 ; The FPGA clears state bit5 on this write. For MORE it sets handshake bit1.
 ; Firmware validates the next response and subsequently clears handshake1.
 ; Qualification on state+handshake is safe even if BUSY was never sampled.
 lda uci_more
 beq @last
 lda #UCI_ACK
 bne @store
@last: lda #UCI_FINAL
@store: sta dos64_uci_state
 LEAVE 0
@timeout:
 lda #UCI_ERR_TIMEOUT
 jsr uci_recover
 LEAVE 0
@reject: LEAVE 1

dos64_uci_poll:
 ENTER
 lda dos64_uci_state
 jeq @return
 cmp #UCI_DONE
 jcs @return
 cmp #UCI_RECOVER
 jeq @recovery
 jsr uci_expired
 bcc @alive
 lda #UCI_ERR_TIMEOUT
 jsr uci_recover
 jmp @return
@alive:
 jsr uci_status_read
 and #8
 beq @dispatch
 lda #UCI_ERR_PROTOCOL
 jsr uci_recover
 jmp @return
@dispatch:
 lda dos64_uci_state
 cmp #UCI_SYNC
 bne @not_sync
 jsr uci_quiet
 beq @synced
 lda #UCI_ERR_STALE
 jsr uci_recover
 jmp @return
@synced:
 lda #UCI_UPLOAD
 sta dos64_uci_state
@not_sync:
 lda dos64_uci_state
 cmp #UCI_UPLOAD
 bne @not_upload
 jsr uci_upload
 jmp @return
@not_upload:
 cmp #UCI_BLOCK
 beq @return
 cmp #UCI_FINAL
 bne @not_final
 jsr uci_quiet
 bne @return
 lda #UCI_DONE
 sta dos64_uci_state
 jmp @return
@not_final:
 ; WAIT/ACK only accepts published LAST/MORE with DATA_ACC clear. CMD_BUSY
 ; and ABORT_PENDING must also clear. Stale immediate idle is not completion.
 cmp #UCI_DRAIN
 beq @drain
 jsr uci_status_read
 and #$0f
 bne @return
 lda dos64_uci_last_status
 and #$30
 cmp #$20
 bcc @return
 sta uci_more
 cmp #$20
 bne @more
 lda #0
 sta uci_more
@more:
 lda #0
 sta dos64_uci_data_len
 sta dos64_uci_data_len+1
 sta dos64_uci_status_len
 sta dos64_uci_status_len+1
 sta uci_data_raw
 sta uci_data_raw+1
 sta uci_status_raw
 sta uci_status_raw+1
 lda #UCI_DRAIN
 sta dos64_uci_state
@drain:
 jsr uci_drain
 jmp @return
@recovery:
 jsr uci_status_read
 and #8
 beq @recover_clean
 lda #8
 jsr uci_control_write
@recover_clean:
 jsr uci_quiet
 bne @still_recover
 lda #UCI_FAILED
 sta dos64_uci_state
 jmp @return
@still_recover:
 jsr uci_expired
 bcc @return
 lda #1
 sta dos64_uci_recovery_failed
 lda #UCI_FAILED
 sta dos64_uci_state
@return:
 LEAVE 0

.proc uci_upload
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
 jsr uci_quiet
 bne stale
.endif
 lda #16
 sta uci_work
loop:
 lda uci_upload_pos
 cmp dos64_uci_command_len
 bne byte
 lda uci_upload_pos+1
 cmp dos64_uci_command_len+1
 beq push
byte:
 ; Self-modified absolute indexed access avoids consuming scarce zero page.
 lda #<dos64_uci_command
 clc
 adc uci_upload_pos
 sta read+1
 lda #>dos64_uci_command
 adc uci_upload_pos+1
 sta read+2
read: lda $ffff
 jsr uci_command_write
 inc uci_upload_pos
 bne next
 inc uci_upload_pos+1
next: dec uci_work
 bne loop
 rts
push:
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
 jsr uci_quiet
 bne stale
.endif
 lda #1
 jsr uci_control_write
 lda #UCI_WAIT
 sta dos64_uci_state
 rts
.ifdef DOS64_NATIVE_UCI_DIAGNOSTIC
stale:
 lda #UCI_ERR_STALE
 jmp uci_recover
.endif
.endproc
.export dos64_uci_upload_operand := uci_upload::read+1

.proc uci_drain
 lda #16
 sta uci_work
loop:
 jsr uci_status_read
 and #8
 beq ok
 lda #UCI_ERR_PROTOCOL
 jmp uci_recover
ok:
 lda dos64_uci_last_status
 and #$3f
 sta uci_work_status
 lda uci_more
 ora #$20
 cmp uci_work_status
 beq valid_state
 lda #UCI_ERR_PROTOCOL
 jmp uci_recover
valid_state:
 lda dos64_uci_last_status
 and #$80
 beq status
 lda uci_data_raw+1
 cmp #3
 bcc data_allowed
 lda uci_data_raw
 cmp #$80
 bcc data_allowed
 lda #UCI_ERR_PROTOCOL
 jmp uci_recover
data_allowed:
 inc uci_data_raw
 bne data_read
 inc uci_data_raw+1
data_read:
 jsr uci_data_read
 pha
 inc dos64_uci_data_seen
 bne counted
 inc dos64_uci_data_seen+1
 bne counted
 inc dos64_uci_data_seen+2
 bne counted
 pla
 lda #UCI_ERR_OVERFLOW
 jmp uci_recover
counted:
 lda dos64_uci_data_len+1
 cmp dos64_uci_data_capacity+1
 bcc data_store
 bne data_discard
 lda dos64_uci_data_len
 cmp dos64_uci_data_capacity
 bcs data_discard
data_store:
 lda #<dos64_uci_data
 clc
 adc dos64_uci_data_len
 sta store+1
 lda #>dos64_uci_data
 adc dos64_uci_data_len+1
 sta store+2
 pla
store: sta $ffff
 inc dos64_uci_data_len
 bne next
 inc dos64_uci_data_len+1
 jmp next
data_discard:
 pla
 lda dos64_uci_flags
 ora #1
 sta dos64_uci_flags
 jmp next
status:
 lda dos64_uci_last_status
 and #$40
 beq empty
 lda uci_status_raw+1
 beq status_allowed
 lda #UCI_ERR_PROTOCOL
 jmp uci_recover
status_allowed:
 inc uci_status_raw
 bne status_read
 inc uci_status_raw+1
status_read:
 jsr uci_stat_read
 pha
 inc dos64_uci_status_seen
 bne stat_counted
 inc dos64_uci_status_seen+1
 bne stat_counted
 inc dos64_uci_status_seen+2
 bne stat_counted
 pla
 lda #UCI_ERR_OVERFLOW
 jmp uci_recover
stat_counted:
 lda dos64_uci_status_len+1
 cmp dos64_uci_status_capacity+1
 bcc stat_store
 bne stat_discard
 lda dos64_uci_status_len
 cmp dos64_uci_status_capacity
 bcs stat_discard
stat_store:
 ldx dos64_uci_status_len
 pla
 sta dos64_uci_status,x
 inc dos64_uci_status_len
 bne next
 inc dos64_uci_status_len+1
 jmp next
stat_discard:
 pla
 lda dos64_uci_flags
 ora #2
 sta dos64_uci_flags
next:
 dec uci_work
 beq return
 jmp loop
empty:
 inc dos64_uci_blocks
 bne block
 inc dos64_uci_blocks+1
 bne block
 lda #UCI_ERR_OVERFLOW
 jmp uci_recover
block:
 lda #UCI_BLOCK
 sta dos64_uci_state
return: rts
.endproc
.export dos64_uci_drain_operand := uci_drain::store+1

dos64_uci_code_end:
