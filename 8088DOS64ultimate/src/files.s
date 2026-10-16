; Native command adapter, independently implemented from the pinned protocol.
; Primary: GideonZ/1541ultimate v3.14 830665cd9b41bc34b868f5c1a1179c5baa4989af
; software/filemanager/dos.{cc,h}, software/filesystem/fs_errors_flags.h and
; software/io/command_interface/command_intf.cc. No firmware code copied.
.setcpu "6502"
; Preserve exact reviewed standalone recovery adapter unless explicitly enabled.
.ifndef DOS64_FILES_INFO
DOS64_FILES_INFO=0
.endif
.assert DOS64_FILES_INFO=0 || DOS64_FILES_INFO=1,error,"FILES_INFO flag must be0or1"
.macpack longbranch
.include "files.inc"
.include "uci.inc"
.import dos64_uci_start, dos64_uci_poll, dos64_uci_accept, dos64_uci_abort
.import dos64_uci_state, dos64_uci_error, dos64_uci_recovery_failed, dos64_uci_now
.import dos64_uci_command, dos64_uci_command_len, dos64_uci_data, dos64_uci_status
.import dos64_uci_data_capacity, dos64_uci_status_capacity
.import dos64_uci_data_len, dos64_uci_status_len, dos64_uci_last_status, dos64_uci_flags
.export dos64_files_init, dos64_files_start, dos64_files_poll
.export dos64_files_state_start, dos64_files_state_end, dos64_files_code_start, dos64_files_code_end
.export dos64_files_owned_target := files_owned_target ; development CLOSE owner claim; no target bytes
.export dos64_files_state, dos64_files_error, dos64_files_transport_error
.export dos64_files_now, dos64_files_target, dos64_files_op, dos64_files_mode
.export dos64_files_count, dos64_files_path_len, dos64_files_offset
.export dos64_files_handle, dos64_files_actual, dos64_files_count_known
.export dos64_files_short, dos64_files_uncertain
.segment "DEVICESTATE"
dos64_files_state_start:
dos64_files_state: .res 1
dos64_files_error: .res 1
dos64_files_transport_error: .res 1
dos64_files_now: .res 2
dos64_files_target: .res 1
dos64_files_op: .res 1
dos64_files_mode: .res 1
dos64_files_count: .res 2
dos64_files_path_len: .res 1
dos64_files_offset: .res 4
dos64_files_handle: .res 1
dos64_files_actual: .res 2
dos64_files_count_known: .res 1
dos64_files_short: .res 1
dos64_files_uncertain: .res 1
files_owned_target: .res 1
files_seen: .res 1
files_path_start: .res 1
files_path_remaining: .res 1
dos64_files_state_end:
.segment "FILECODE"
dos64_files_code_start:
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
.macro LEAVE c
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
 .if c
 sec
 .else
 clc
 .endif
 rts
.endmacro
files_clock:
 lda dos64_files_now
 sta dos64_uci_now
 lda dos64_files_now+1
 sta dos64_uci_now+1
 rts
files_quiet:
 lda dos64_uci_state
 cmp #UCI_IDLE
 beq @yes
 cmp #UCI_DONE
 beq @yes
 cmp #UCI_FAILED
 bne @no
 lda dos64_uci_recovery_failed
 bne @no
@yes: clc
 rts
@no: sec
 rts
dos64_files_init:
 ENTER
 lda #0
 ldx #dos64_files_state_end-dos64_files_state_start-1
@clear: sta dos64_files_state_start,x
 dex
 bpl @clear
 lda #1
 sta dos64_files_target
 LEAVE 0

dos64_files_start:
 ENTER
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq @reject
 jsr files_quiet
 jcs @reject
 lda dos64_files_target
 cmp #1
 beq @target
 cmp #2
 jne @reject
@target:
 lda dos64_files_handle
 beq @operation
 lda dos64_files_target
 cmp files_owned_target
 jne @reject
 lda dos64_files_handle
 cmp #2
 bne @operation
 lda dos64_files_op
 cmp #FILES_CLOSE
 jne @reject
@operation:
 lda #0
 sta dos64_uci_command_len+1
 lda #2
 sta dos64_uci_command_len
 lda dos64_files_op
.if DOS64_FILES_INFO
 cmp #FILES_INFO
 jeq @need_open
.endif
 cmp #FILES_CLOSE
 jeq @need_open
 cmp #FILES_READ
 jeq @count
 cmp #FILES_WRITE
 jeq @count
 cmp #FILES_SEEK
 jeq @seek
 lda dos64_files_handle
 jne @reject
 lda dos64_files_op
 cmp #FILES_IDENTIFY
 jeq @launch
 cmp #FILES_OPEN
 beq @open
 cmp #FILES_CD
 jne @reject
 lda #2
 bne @path
@open:
 lda dos64_files_mode
 cmp #1
 beq @mode
 cmp #2
 beq @mode
 cmp #3
 beq @mode
 cmp #6
 beq @mode
 cmp #7
 jne @reject
@mode: sta dos64_uci_command+2
 lda #3
@path:
 sta files_path_start
 tax
 lda dos64_files_path_len
 sta files_path_remaining
 cmp #2
 jcc @reject
 cmp #253
 jcs @reject
 clc
 adc files_path_start
 sta dos64_uci_command_len
 bcc @path_loop
 inc dos64_uci_command_len+1
@path_loop:
 lda dos64_uci_command,x
 inx
 dec files_path_remaining
 beq @path_last
 cmp #0
 jeq @reject
 jmp @path_loop
@path_last:
 cmp #0
 jne @reject
 jmp @launch
@count:
 lda dos64_files_count
 ora dos64_files_count+1
 jeq @reject
 lda dos64_files_count+1
 cmp #2
 jcc @valid_count
 jne @reject
 lda dos64_files_count
 jne @reject
@valid_count:
 lda dos64_files_count
 sta dos64_uci_command+2
 lda dos64_files_count+1
 sta dos64_uci_command+3
 lda #4
 sta dos64_uci_command_len
 lda dos64_files_op
 cmp #FILES_WRITE
 bne @need_open
 clc
 lda dos64_files_count
 adc #4
 sta dos64_uci_command_len
 lda dos64_files_count+1
 adc #0
 sta dos64_uci_command_len+1
 jmp @need_open
@seek:
 ldx #3
@offset: lda dos64_files_offset,x
 sta dos64_uci_command+2,x
 dex
 bpl @offset
 lda #6
 sta dos64_uci_command_len
@need_open:
 lda dos64_files_handle
 jeq @reject
@launch:
 lda dos64_files_target
 sta dos64_uci_command
 lda dos64_files_op
 sta dos64_uci_command+1
 lda #$80
 sta dos64_uci_data_capacity
 lda #3
 sta dos64_uci_data_capacity+1
 lda #0
 sta dos64_uci_status_capacity
 lda #1
 sta dos64_uci_status_capacity+1
 lda #0
 sta dos64_files_error
 sta dos64_files_transport_error
 sta dos64_files_actual
 sta dos64_files_actual+1
 sta dos64_files_short
 sta dos64_files_count_known
 sta files_seen
 jsr files_clock
 jsr dos64_uci_start
 bcs @start_error
 lda dos64_files_target
 sta files_owned_target
 lda dos64_files_op
 cmp #FILES_WRITE
 bne @accepted
 lda #1
 sta dos64_files_uncertain
@accepted:
 lda #FILES_BUSY
 sta dos64_files_state
 LEAVE 0
@start_error:
 lda dos64_uci_error
 sta dos64_files_transport_error
 lda #FILES_ERR_TRANSPORT
 sta dos64_files_error
 lda #FILES_FAILED
 sta dos64_files_state
 LEAVE 1
@reject:
 LEAVE 1

dos64_files_poll:
 ENTER
 lda dos64_files_state
 cmp #FILES_BUSY
 jne @reject
 jsr files_clock
 jsr dos64_uci_poll
 lda dos64_uci_state
 cmp #UCI_BLOCK
 beq @block
 cmp #UCI_DONE
 jeq @done
 cmp #UCI_FAILED
 jne @return
 lda dos64_uci_error
 sta dos64_files_transport_error
 lda dos64_files_error
 bne @fail
 lda #FILES_ERR_TRANSPORT
 sta dos64_files_error
 lda #2
 sta dos64_files_handle
@fail:
 lda #FILES_FAILED
 sta dos64_files_state
 jmp @return
@block:
 lda files_seen
 jne @protocol
 inc files_seen
 lda dos64_uci_last_status
 and #$10
 jne @protocol
 lda dos64_uci_flags
 jne @protocol
 lda dos64_files_op
.if DOS64_FILES_INFO
 cmp #FILES_INFO
 jeq @info
.endif
 cmp #FILES_READ
.if DOS64_FILES_INFO
 jeq @read
.else
 beq @read
.endif
 cmp #FILES_IDENTIFY
 beq @identify
 lda dos64_uci_data_len
 ora dos64_uci_data_len+1
 jne @protocol
@status:
 lda dos64_uci_status_len+1
 jne @status_error
 lda dos64_uci_status_len
 cmp #5
 jne @status_error
 ldx #4
@compare:
 lda dos64_uci_status,x
 cmp files_ok,x
 jne @status_error
 dex
 bpl @compare
 jmp @accept
.if DOS64_FILES_INFO
@info:
 lda dos64_uci_data_len+1
 jne @protocol
 lda dos64_uci_data_len
 cmp #13
 jcc @protocol
 cmp #76
 jcs @protocol
 lda dos64_uci_data+11
 and #$18                       ; volume/directory is not an export file
 jne @protocol
 ldx #12
@name:
 lda dos64_uci_data,x
 jeq @protocol                  ; firmware omits terminating filename NUL
 inx
 cpx dos64_uci_data_len
 bne @name
 lda dos64_uci_data_len
 sta dos64_files_actual
 lda #1
 sta dos64_files_count_known
 jmp @status
.endif
@identify:
 lda dos64_uci_data_len+1
 jne @protocol
 lda dos64_uci_data_len
 cmp #20
 jne @protocol
 ldx #19
@identity:
 lda dos64_uci_data,x
 cmp files_identity,x
 jne @protocol
 dex
 bpl @identity
 jmp @status
@read:
 lda dos64_uci_status_len
 ora dos64_uci_status_len+1
 jne @status_error
 lda dos64_uci_data_len+1
 cmp dos64_files_count+1
 bcc @short
 bne @protocol
 lda dos64_uci_data_len
 cmp dos64_files_count
 bcc @short
 bne @protocol
 jeq @count_ok
@short:
 lda #1
 sta dos64_files_short
@count_ok:
 lda dos64_uci_data_len
 sta dos64_files_actual
 lda dos64_uci_data_len+1
 sta dos64_files_actual+1
 lda #1
 sta dos64_files_count_known
@accept:
 jsr dos64_uci_accept
 jmp @return
@status_error:
 ; A null firmware file is a known closed handle, even though CLOSE failed.
 lda dos64_files_op
 cmp #FILES_CLOSE
 bne @bad_status
 lda dos64_uci_status_len+1
 bne @bad_status
 lda dos64_uci_status_len
 cmp #19
 bne @bad_status
 ldx #18
@no_file:
 lda dos64_uci_status,x
 cmp files_no_file,x
 bne @bad_status
 dex
 bpl @no_file
 lda #FILES_ERR_STATUS
 sta dos64_files_error
 jmp @accept
@bad_status:
 lda #FILES_ERR_STATUS
 bne @error
@protocol:
 lda #FILES_ERR_PROTOCOL
@error:
 sta dos64_files_error
 lda dos64_files_op
 cmp #FILES_WRITE
 beq @uncertain
 cmp #FILES_OPEN
 beq @unknown
 cmp #FILES_CLOSE
 bne @abort
@unknown:
 lda #2
 sta dos64_files_handle
 jmp @abort
@uncertain:
 lda #1
 sta dos64_files_uncertain
@abort:
 jsr dos64_uci_abort
 jmp @return
@done:
 lda files_seen
 beq @protocol
 lda dos64_files_op
 cmp #FILES_OPEN
 beq @opened
 cmp #FILES_CLOSE
 beq @closed
 cmp #FILES_WRITE
 bne @success
 lda #1
 sta dos64_files_uncertain
 bne @success
@opened:
 lda #1
 sta dos64_files_handle
 lda dos64_files_target
 sta files_owned_target
 jmp @success
@closed:
 lda #0
 sta dos64_files_handle
@success:
 lda dos64_files_error
 jne @fail
 lda #FILES_DONE
 sta dos64_files_state
@return:
 LEAVE 0
@reject:
 LEAVE 1
files_no_file: .byte "84,NO FILE TO CLOSE"
files_ok: .byte "00,OK"
files_identity: .byte "ULTIMATE-II DOS V1.2"
dos64_files_code_end:
