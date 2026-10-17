.setcpu "6502"
.macpack longbranch
.include "runtime.inc"
.include "media_transaction.inc"
.include "binding_receipt.inc"
.ifndef DOS64_MEDIA_INSERT
DOS64_MEDIA_INSERT=0
.endif
.assert DOS64_MEDIA_INSERT=0 || DOS64_MEDIA_INSERT=1,error,"INSERT boolean"
.if DOS64_MEDIA_INSERT
.include "insert_contract.inc"
.include "insert_native.inc"
.include "insert_broker.inc"
.endif
.export tw_begin,tw_poll,tw_state,tw_error,tw_closed,tw_cancel
.ifndef DOS64_MEDIA_SEQUENCE
DOS64_MEDIA_SEQUENCE=0
.endif
.if DOS64_MEDIA_SEQUENCE
.include "sequence_broker.inc"
.export tw_take_sequence,tw_drive
.export _tw_begin := tw_begin, _tw_poll := tw_poll
.export _tw_state := tw_state, _tw_error := tw_error, _tw_closed := tw_closed
.export _tw_drive := tw_drive
.export _tw_take_sequence := tw_take_sequence
.export _tw_home := tw_home, _tw_sequence := tw_sequence
.export _tw_mode := tw_mode, _tw_limit := tw_limit, _tw_cancel := tw_cancel
.endif
.export tw_committing
.export tw_home,tw_sequence,tw_mode,tw_limit,tw_private_start,tw_private_end
.segment "LOADADDR"
.word $a000
.segment "ZEROPAGE"
wp:.res 2
rp:.res 2
.segment "BSS"
tw_home:.res 128
tw_sequence:.res 2
tw_mode:.res 1
tw_limit:.res 2
tw_cancel:.res 1
.if DOS64_MEDIA_SEQUENCE
tw_drive:.res 1
.endif
tw_private_start:
home:.res 128
sequence:.res 2
mode:.res 1
limit:.res 2
state:.res 1
error:.res 1
closed:.res 1
context:.res 1
original_online:.res 1
snapshot:.res 25
phase:.res 1
script:.res 1
name:.res 1
rename_to:.res 1
raw:.res 1
seen:.res 1
aborted:.res 1
cleanup_close:.res 1
drain:.res 1
samples:.res 1
steps:.res 2
started:.res 2
now:.res 2
source:.res 3
size:.res 2
offset:.res 2
count:.res 2
store_read:.res 1
path_offset:.res 2
basename:.res 10
work:.res 1
append_byte:.res 1
verify_kind:.res 1
verified_script:.res 1
crc:.res 4
plan_claim:.res 1
waiting:.res 1
fatal:.res 1
committing:.res 1
cancel_late:.res 1
call_zp:.res 4
.if DOS64_MEDIA_SEQUENCE
alloc_drive:.res 1
alloc_first:.res 2
alloc_ready:.res 1
alloc_exists:.res 1
alloc_collision:.res 1
alloc_last:.res 4
alloc_seen:.res 1
.endif
.if DOS64_MEDIA_INSERT
insert_job:.res 1
insert_blocks:.res 2
.endif
tw_private_end:
.segment "CODE"
; Standalone native/UI call boundary. Indirect pointers are temporary only
; within one returned API call; preserve all four high-ZP caller bytes.
.macro worker_api target
 php
 sei
 cld
 ldx #3
: lda $80,x
 sta call_zp,x
 dex
 bpl :-
 jsr target
 pha
 ldx #3
: lda call_zp,x
 sta $80,x
 dex
 bpl :-
 pla
 ldx #0
 plp
 rts
.endmacro
tw_begin: worker_api begin_job
tw_poll: worker_api poll_job
; Public getters refresh no mutable result object; private state survives calls.
tw_state: lda state
 ldx #0
 rts
tw_error: lda error
 ldx #0
 rts
tw_committing: lda committing
 ldx #0
 rts
tw_closed: lda closed
 ldx #0
 rts
latch:
 ldx error
 bne :+
 sta error
: rts
fatal_latch:
 pha
 lda #1
 sta fatal
 pla
 jmp latch
quiet:
 lda dos64_uci_recovery_failed
 bne @bad
 lda dos64_uci_state
 beq @ok
 cmp #9
 beq @ok
 cmp #10
 bne @bad
@ok: clc
 rts
@bad: sec
 rts
clock:
 jsr dos64_elapsed_poll
 bcs @bad
.if DOS64_MEDIA_SEQUENCE
 lda mode
 cmp #2
 bcc :+
 jsr alloc_clock32
 bcs @fatal
:
.endif
 lda #0
 sta samples
 ldx #1
: lda dos64_elapsed_now,x
 sta now,x
 dex
 bpl :-
 clc
 rts
@bad:
 lda dos64_host_clock_status
 cmp #4
 bne @fatal
 inc samples
 bne @pending
@fatal:
 lda #2
 jsr fatal_latch
 inc now
 bne @pending
 inc now+1
@pending: sec
 rts
copy_now:
 ldx #1
: lda now,x
 sta dos64_files_now,x
 sta dos64_uci_now,x
 dex
 bpl :-
 rts
; Canonical ASCII home <=117, zero padding, strict FatFs aliases. Captured now.
path_capture:
 ldx #127
: lda tw_home,x
 sta home,x
 dex
 bpl :-
 lda home
 cmp #$2f
 ; char literal above is replaced by build script with $2f for ca65.
 bne @bad
 ldx #1
 lda #1
 sta work
@char:
 lda home,x
 beq @end
 cpx #118
 bcs @bad
 cmp #$20
 bcc @bad
 cmp #$7f
 bcs @bad
 cmp #$5c
 beq @bad
 cmp #':'
 beq @bad
 cmp #'"'
 beq @bad
 cmp #'*'
 beq @bad
 cmp #'<'
 beq @bad
 cmp #'>'
 beq @bad
 cmp #'?'
 beq @bad
 cmp #'|'
 beq @bad
 cmp #$2f
 bne @next
 cpx work
 beq @bad
 lda home-1,x
 cmp #'.'
 beq @bad
 cmp #' '
 beq @bad
 txa
 clc
 adc #1
 sta work
@next: inx
 bne @char
@bad: sec
 rts
@end:
 cpx #1
 beq @pad
 cpx work
 beq @bad
 lda home-1,x
 cmp #'.'
 beq @bad
 cmp #' '
 beq @bad
@pad:
 inx
 bmi @tail
 lda home,x
 bne @bad
 jmp @pad
@tail:
 ; X reaches128; remaining tail is empty. All 128 source bytes captured.
 clc
 rts
; All new operations reset stale cancellation ONLY after accepted ownership.
begin_job:
.if DOS64_MEDIA_SEQUENCE
 lda #0
 sta alloc_ready
.endif
 lda state
 cmp #1
 jeq reject
 lda context
 jne reject
 ; No context/FILES mutation without a fresh coherent admission timestamp.
 jsr dos64_elapsed_poll
 jcs reject
 jsr quiet
 jcs reject
 lda dos64_native_diag
 cmp #8
 jne reject
 lda dos64_cache_limit
 jne reject
 lda dos64_cold_open
 jne reject
 lda dos64_cache_ready
 cmp #$a5
 jne reject
 ldx #31
: lda dos64_cache_pins,x
 jne reject
 dex
 bpl :-
 lda hdb_active
 ora hd_uncertain
 ora dos64_overlay_busy
 jne reject
 .if DOS64_MEDIA_INSERT
 lda #0
 sta insert_job
 lda tw_mode
 cmp #4
 bne :+
 lda #1
 sta insert_job
 jsr alloc_context
 jcs reject
 jmp @insert_mode
:
.endif
 lda tw_mode
.if DOS64_MEDIA_SEQUENCE
 cmp #4
.else
 cmp #2
.endif
 jcs reject
.if DOS64_MEDIA_SEQUENCE
 cmp #2
 bcc :+
 jsr alloc_context
 jcs reject
 lda tw_mode
 cmp #3
 bne :+
 ldx tw_drive
 cpx #2
 jcs reject
 lda dos64_disk_readonly,x
 and #1
 jne reject
 txa
 beq @alloc_a
 lda dos64_disk_b_descriptor+9
 jmp @alloc_loaded
@alloc_a:
 lda dos64_disk_loaded
@alloc_loaded:
 and #1
 jeq reject
:
.endif
.if DOS64_MEDIA_INSERT
@insert_mode:
.endif
 lda tw_sequence
 ora tw_sequence+1
 jeq reject
 lda tw_limit
 ora tw_limit+1
 jeq reject
 lda tw_limit+1
 jmi reject
 jsr path_capture
 jcs reject
 lda hdb_online
 cmp #2
 jcs reject
 sta original_online
 beq @closed_input
 lda dos64_files_handle
 cmp #1
 jne reject
 lda hdc_target
 cmp #1
 beq @target
 cmp #2
 jne reject
@target:
 cmp dos64_files_target
 jne reject
 cmp dos64_files_owned_target
 jne reject
 jmp @capture
@closed_input:
 lda dos64_files_handle
 jne reject
@capture:
 ldx #24
: lda dos64_files_state_start,x
 sta snapshot,x
 dex
 bpl :-
 lda tw_mode
.if DOS64_MEDIA_INSERT
 cmp #4
 beq @need_plan
.endif
.if DOS64_MEDIA_SEQUENCE
 cmp #1
 bne :+
.else
 beq :+
.endif
 .if DOS64_MEDIA_INSERT
@need_plan:
.endif
 lda ML_VALID
 cmp #$a5
 jne reject
 lda ML_PLAN
 cmp #$a5
 jne reject
 lda ML_STATE
 cmp #2
 jne reject
 jsr media_match
 jcs reject
: lda tw_mode
.if DOS64_MEDIA_INSERT
 cmp #4
 bne :+
 lda #1
:
.endif
 sta mode
 lda tw_sequence
 sta sequence
 lda tw_sequence+1
 sta sequence+1
 lda tw_limit
 sta limit
 lda tw_limit+1
 sta limit+1
 lda #0
 sta error
 sta closed
 sta tw_cancel
 sta aborted
 sta cleanup_close
 sta drain
 sta samples
 sta steps
 sta steps+1
 sta script
 sta raw
 sta plan_claim
 sta waiting
 sta fatal
 sta committing
 sta cancel_late
.if DOS64_MEDIA_SEQUENCE
 sta alloc_ready
 sta alloc_seen
 sta alloc_collision
 lda tw_drive
 sta alloc_drive
 lda sequence
 sta alloc_first
 lda sequence+1
 sta alloc_first+1
 lda #0
.endif
.if DOS64_MEDIA_BINDING
 .if DOS64_MEDIA_INSERT
 ldx insert_job
 beq :+
 sta MI_READY
 jmp :++
:
.endif
 sta MB_READY
.if DOS64_MEDIA_INSERT
:
.endif
.endif
 sta store_read
 sta hdb_online
 lda mode
.if DOS64_MEDIA_SEQUENCE
 cmp #1
 bne :+
.else
 beq :+
.endif
 lda #1
 sta plan_claim
 lda #0
 sta ML_PLAN
: lda #$ff
 sta verified_script
 lda #0
 ldx #24
: sta dos64_files_state_start,x
 dex
 bpl :-
 lda #1
 sta state
 sta context
 lda original_online
 beq @target1
 lda #3
 sec
 sbc hdc_target
 jmp @set_target
@target1: lda #1
@set_target:
 sta dos64_files_target
 sta dos64_files_owned_target
 lda #2
 sta dos64_files_handle
 lda dos64_elapsed_now
 sta now
 sta started
 lda dos64_elapsed_now+1
 sta now+1
 sta started+1
 .if DOS64_MEDIA_SEQUENCE
 lda mode
 cmp #2
 bcc :+
 jsr alloc_clock32
:
.endif
 lda #1
 sta phase
 lda #3
 jsr start_file
 bcs @accepted_failure
 lda #1
 ldx #0
 rts
@accepted_failure:
 lda #4
 jsr latch
 lda #1
 ldx #0
 rts
reject: lda #0
 ldx #0
 rts
start_file:
 sta dos64_files_op
 jsr copy_now
 jsr dos64_overlay_files_start
 bcs :+
 lda #1
 sta waiting
 clc
: rts
; FILES leaf errors are observed BEFORE same-poll cancel/clock error. Exact84
; is accepted only for safety/cleanup CLOSE and only after native parser close.
observe:
 lda waiting
 beq @return
 lda raw
 bne @return
 lda dos64_files_error
 beq @return
.if DOS64_MEDIA_SEQUENCE
 lda mode
 cmp #2
 bcc :+
 lda phase
 cmp #20
 bne @not_probe
 jsr alloc_missing
 bcc @return
 jmp @bad
@not_probe:
 cmp #21
 bne :+
 lda dos64_files_handle
 beq @return
:
.endif
 lda phase
.if DOS64_MEDIA_SEQUENCE
 cmp #21
 beq @close
.endif
 cmp #1
 beq @close
 cmp #31
 bne @bad
@close:
 lda dos64_files_error
 cmp #3
 bne @bad
 lda dos64_uci_state
 cmp #6
 beq @return
 cmp #7
 beq @return
 cmp #9
 beq @return
@bad:
 lda dos64_files_error
 cmp #2
 bne :+
 lda #12
 jsr fatal_latch
 rts
: lda #4
 jsr latch
@return: rts
poll_job:
 lda state
 cmp #1
 jne done
 inc steps
 bne :+
 inc steps+1
 bne :+
 lda #8
 jsr fatal_latch
 jmp blocked
: jsr observe
 jsr observe_cancel
 jsr clock
 bcc @clock_ok
 lda error
 jeq done
@clock_ok:
 jsr observe_cancel
 lda error
 jne cleanup
 lda now
 sec
 sbc started
 sta work
 lda now+1
 sbc started+1
 cmp limit+1
 bcc @active
 bne @deadline
 lda work
 cmp limit
 bcc @active
@deadline:
 lda #2
 jsr fatal_latch
 jmp cleanup
@active:
.if DOS64_MEDIA_SEQUENCE
 lda mode
 cmp #2
 bcc :+
 lda phase
 cmp #20
 bcc :+
 jmp alloc_poll
:
.endif
 lda raw
 jne rename_poll
 lda phase
 cmp #10
 jeq verify_job
 jsr copy_now
 jsr dos64_overlay_files_poll
 jcs file_failure
 lda dos64_files_state
 cmp #1
 jeq done
 lda dos64_files_state
 cmp #2
 beq @terminal
 ; Parser exact84 close reports FAILED but has actually closed the target.
 lda phase
 cmp #1
 bne file_failure
 lda dos64_files_handle
 jne file_failure
 jsr quiet
 jcs file_failure
 lda dos64_files_error
 cmp #3
 jne file_failure
@terminal:
 lda #0
 sta waiting
 jmp dispatch
file_failure:
 lda committing
 beq :+
 lda #1
 sta fatal
: lda #4
 jsr latch
 jmp cleanup
done: rts
dispatch:
 lda phase
 cmp #1
 jeq next_script
 cmp #2
 jeq write_prepare
 cmp #3
 jeq write_advance
 cmp #4
 jeq read_open
 cmp #5
 jeq read_info
 cmp #6
 jeq read_prepare
 cmp #7
 jeq read_compare
 cmp #8
 jeq eof_check
 cmp #9
 jeq job_done
 lda #4
 jsr latch
 jmp cleanup
next_script:
 lda error
 jne cleanup
 lda mode
.if DOS64_MEDIA_SEQUENCE
 cmp #2
 bcc :+
 lda #0
 sta name
 sta store_read
 lda #$20
 sta source
 lda #$f0
 sta source+1
 lda #$3f
 sta source+2
 lda #$40
 sta size
 lda #2
 sta size+1
 jmp read_open
: lda mode
.endif
 bne @publish
 lda #0
 sta name
 lda #1
 sta store_read
 lda #0
 sta source
 sta source+1
 lda #$3e
 sta source+2
 lda #$40
 sta size
 lda #2
 sta size+1
 jmp read_open
@publish:
 lda script
 beq @guard
 cmp #3
 beq @guard
 cmp #8
 bne @script
@guard:
 cmp verified_script
 beq @script
 jmp verify_begin
@script:
 ldx script
 cpx #8
 jeq finish
 lda kinds,x
 cmp #1
 beq @write
 cmp #2
 jeq rename_begin
 lda #0
 sta name
 sta store_read
 lda #0
 sta source
 lda kinds,x
 cmp #4
 bne :+
 lda #0
 beq :++
: lda #3
: sta source+1
 lda #$3e
 sta source+2
 lda #$40
 sta size
 lda #2
 sta size+1
 jmp read_open
@write:
 lda names,x
 sta name
 lda #0
 sta source
 lda #$3e
 sta source+2
 lda name
 cmp #1
 bne @journal
 lda #3
 sta source+1
 lda #$40
 sta size
 lda #2
 sta size+1
 jmp @open
@journal:
 lda #6
 sta source+1
 lda #4
 sta size
 lda #5
 sta size+1
@open:
 lda #0
 sta offset
 sta offset+1
 lda #6
 sta dos64_files_mode
 lda #3
 jsr path_command
 lda #2
 sta phase
 lda #2
 jsr start_file
 jcs file_failure
 rts
set_count:
 lda size
 sec
 sbc offset
 sta count
 lda size+1
 sbc offset+1
 beq @small
 lda #0
 sta count
 lda #1
@small:
 sta count+1
 lda count
 sta dos64_files_count
 lda count+1
 sta dos64_files_count+1
 rts
reu:
 ; expected reference is phase-owned, same REU engine; never uses FILES handle.
 lda #<$b800
 sta dos64_reu_request
 lda #>$b800
 sta dos64_reu_request+1
 lda source
 clc
 adc offset
 sta dos64_reu_request+2
 lda source+1
 adc offset+1
 sta dos64_reu_request+3
 lda source+2
 adc #0
 sta dos64_reu_request+4
 lda count
 sta dos64_reu_request+5
 lda count+1
 sta dos64_reu_request+6
 jmp dos64_reu_transfer
write_prepare:
 jsr set_count
 lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 ldy #0
: lda $b800,y
 sta dos64_uci_command+4,y
 iny
 cpy count
 bne :-
 lda #3
 sta phase
 lda #5
 jsr start_file
 jcs file_failure
 rts
write_advance:
 jsr advance
 bcc write_prepare
 lda #4
 sta phase
 lda #3
 jsr start_file
 jcs file_failure
 rts
advance:
 lda offset
 clc
 adc count
 sta offset
 lda offset+1
 adc count+1
 sta offset+1
 cmp size+1
 bne @more
 lda offset
 cmp size
 beq @end
@more: clc
 rts
@end: sec
 rts
read_open:
 lda #0
 sta offset
 sta offset+1
 lda #1
 sta dos64_files_mode
 lda #3
 jsr path_command
 lda #5
 sta phase
 lda #2
 jsr start_file
 jcs file_failure
 rts
read_info:
 lda #6
 sta phase
 lda #7
 jsr start_file
 jcs file_failure
 rts
read_prepare:
 lda dos64_files_count_known
 cmp #1
 jne file_failure
 lda dos64_uci_data
 cmp size
 jne compare_failure
 lda dos64_uci_data+1
 cmp size+1
 jne compare_failure
 lda dos64_uci_data+2
 ora dos64_uci_data+3
 jne compare_failure
read_next:
 jsr set_count
 lda #7
 sta phase
 lda #4
 jsr start_file
 jcs file_failure
 rts
read_compare:
 lda dos64_files_count_known
 cmp #1
 jne compare_failure
 lda dos64_files_actual
 cmp count
 jne compare_failure
 lda dos64_files_actual+1
 cmp count+1
 jne compare_failure
 .if DOS64_MEDIA_SEQUENCE
 lda mode
 cmp #2
 jcs alloc_read_compare
.endif
 lda store_read
 beq @compare
 ldy #0
: lda dos64_uci_data,y
 sta $b800,y
 iny
 cpy count
 bne :-
 lda #0
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
@compare:
 lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 ldy #0
: lda dos64_uci_data,y
 cmp $b800,y
 bne compare_failure
 iny
 cpy count
 bne :-
read_advance:
 jsr advance
 bcc read_next
 lda #1
 sta dos64_files_count
 lda #0
 sta dos64_files_count+1
 lda #8
 sta phase
 lda #4
 jsr start_file
 jcs file_failure
 rts
eof_check:
 lda dos64_files_actual
 ora dos64_files_actual+1
 jne compare_failure
 lda dos64_files_count_known
 cmp #1
 jne compare_failure
 lda dos64_files_short
 cmp #1
 jne compare_failure
 lda #9
 sta phase
 lda #3
 jsr start_file
 jcs file_failure
 rts
compare_failure: lda #5
 bne failure
dma_failure: lda #6
 jsr fatal_latch
 jmp cleanup
failure: jsr latch
 jmp cleanup
job_done:
 lda dos64_files_handle
 jne file_failure
 jsr quiet
 jcs file_failure
 lda mode
.if DOS64_MEDIA_SEQUENCE
 cmp #2
 bcc :+
 lda #1
 sta name
 jmp alloc_open
: lda mode
.endif
 jeq finish
 inc script
 jmp next_script
; direct native DOS rename0A: both alternate handles knownclosed, no engine init.
rename_begin:
 lda script
 cmp #3
 bne :+
 lda #1
 sta committing
: lda dos64_files_handle
 jne file_failure
 jsr quiet
 jcs file_failure
 lda names,x
 sta name
 lda destinations,x
 sta rename_to
 lda #2
 jsr path_command
 lda rename_to
 sta name
 jsr append_name
 lda dos64_files_target
 sta dos64_uci_command
 lda #$0a
 sta dos64_uci_command+1
 lda path_offset
 sta dos64_uci_command_len
 lda path_offset+1
 sta dos64_uci_command_len+1
 lda #0
 sta dos64_uci_data_capacity
 sta dos64_uci_data_capacity+1
 lda #255
 sta dos64_uci_status_capacity
 lda #0
 sta dos64_uci_status_capacity+1
 sta seen
 lda #1
 sta raw
 jsr copy_now
 jsr dos64_uci_start
 jcs file_failure
 rts
rename_poll:
 jsr copy_now
 jsr dos64_uci_poll
 jcs file_failure
 lda dos64_uci_state
 cmp #5
 beq @block
 cmp #9
 beq @complete
 cmp #10
 jeq file_failure
 rts
@block:
 lda seen
 jne file_failure
 inc seen
 lda dos64_uci_last_status
 and #$10
 jne file_failure
 lda dos64_uci_flags
 ora dos64_uci_data_len
 ora dos64_uci_data_len+1
 ora dos64_uci_status_len+1
 jne file_failure
 lda dos64_uci_status_len
 cmp #5
 jne file_failure
 ldx #4
: lda dos64_uci_status,x
 cmp ok,x
 jne file_failure
 dex
 bpl :-
 jsr dos64_uci_accept
 jcs file_failure
 rts
@complete:
 lda seen
 cmp #1
 jne file_failure
 lda #0
 sta raw
 inc script
 jmp next_script
cleanup:
 inc drain
 jeq blocked
 jsr copy_now
 lda raw
 beq @file
 jsr dos64_uci_poll
 jmp @quiet
@file:
 lda dos64_files_state
 cmp #1
 bne @quiet
 jsr dos64_overlay_files_poll
@quiet:
 jsr quiet
 bcc @closed
 lda dos64_uci_recovery_failed
 jne blocked
 ; Safety CLOSE and our one cleanup CLOSE must drain, never self-abort.
 lda phase
 cmp #1
 jeq done
 cmp #31
 jeq done
.if DOS64_MEDIA_SEQUENCE
 cmp #21
 jeq done
.endif
 lda aborted
 jne done
 inc aborted
 jsr dos64_uci_abort
 rts
@closed:
 lda dos64_files_handle
 beq finish
 lda phase
 cmp #1
 jeq blocked
 .if DOS64_MEDIA_SEQUENCE
 lda phase
 cmp #21
 jeq blocked
.endif
 lda cleanup_close
 jne blocked
 inc cleanup_close
 lda #0
 sta raw
 lda #31
 sta phase
 lda #3
 jsr start_file
 jcs blocked
 rts
finish:
 lda mode
.if DOS64_MEDIA_SEQUENCE
 cmp #1
 bne :+
.else
 beq :+
.endif
 jsr media_match
 bcc :+
 lda #10
 jsr fatal_latch
: lda dos64_files_handle
 jne blocked
 jsr quiet
 jcs blocked
 ldx #24
: lda snapshot,x
 sta dos64_files_state_start,x
 dex
 bpl :-
 lda original_online
 sta hdb_online
 lda #0
 sta context
 lda #1
 sta closed
 lda fatal
 beq :+
 lda #$e1
 sta dos64_native_diag
: lda #2
 ldx error
 beq :+
 lda #3
 : sta state
.if DOS64_MEDIA_BINDING
 cmp #2
 bne @return
 lda mode
.if DOS64_MEDIA_SEQUENCE
 cmp #1
 bne @return
.else
 beq @return
.endif
 jsr binding_mint
@return:
.endif
 rts
blocked:
 lda #1
 sta fatal
 lda #$e1
 sta dos64_native_diag
 lda #3
 sta state
 rts
verify_begin:
 jsr media_match
 jcs identity_failure
 lda ML_VALID
 cmp #$a5
 jne identity_failure
 lda ML_STATE
 cmp #2
 jne identity_failure
 lda plan_claim
 cmp #1
 jne identity_failure
 lda #0
 sta verify_kind
 sta offset
 sta offset+1
.if DOS64_MEDIA_INSERT
 lda insert_job
 beq @no_image
 lda script
 bne @no_image
 lda #3
 sta verify_kind
 lda #$a0
 sta insert_blocks
 lda #5
 sta insert_blocks+1
 lda MI_FQ+5
 sta source
 lda MI_FQ+6
 sta source+1
 lda MI_FQ+7
 sta source+2
@no_image:
.endif
 lda #$ff
 ldx #3
: sta crc,x
 dex
 bpl :-
 lda #10
 sta phase
 rts
verify_job:
.if DOS64_MEDIA_INSERT
 lda verify_kind
 cmp #3
 jeq insert_image_poll
 cmp #4
 jcs insert_cfg_poll
.endif
 lda verify_kind
.if DOS64_MEDIA_INSERT
 jne verify_match
.else
 bne verify_match
.endif
 lda #0
 sta source
 lda #6
 sta source+1
 lda #$3e
 sta source+2
 lda offset+1
 cmp #5
 beq verify_footer
 lda #0
 sta count
 lda #1
 sta count+1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
.if DOS64_MEDIA_INSERT
 lda insert_job
 beq :+
 lda offset+1
 bne :+
 jsr insert_journal_check
 jcs identity_failure
:
.endif
 ldy #0
: lda $b800,y
 jsr crc_byte
 iny
 bne :-
 inc offset+1
 rts
verify_footer:
 lda #4
 sta count
 lda #0
 sta count+1
 lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 ldx #3
: lda crc,x
 eor #$ff
 cmp ML_JCRC,x
 jne identity_failure
 lda $b800,x
 cmp ML_JCRC,x
 jne identity_failure
 dex
 bpl :-
 lda #1
 sta verify_kind
 lda #0
 sta offset
 sta offset+1
 rts
verify_match:
 lda #0
 sta source
 lda #$3e
 sta source+2
 lda #0
 sta count
 lda #1
 sta count+1
 lda offset+1
 cmp #2
 bne :+
 lda #64
 sta count
 lda #0
 sta count+1
: lda verify_kind
 cmp #1
 bne @old_ref
 lda #$c0
 sta source
 lda #8
 bne @ref
@old_ref:
 lda #$80
 sta source
 lda #6
@ref:
 sta source+1
 lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 ldy #0
: lda $b800,y
 sta $b900,y
 iny
 cpy count
 bne :-
 lda #0
 sta source
 lda verify_kind
 cmp #1
 bne :+
 lda #3
 bne :++
: lda #0
: sta source+1
 lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 ldy #0
: lda $b800,y
 cmp $b900,y
 jne identity_failure
 iny
 cpy count
 bne :-
 lda offset
 clc
 adc count
 sta offset
 lda offset+1
 adc count+1
 sta offset+1
 cmp #2
 bne @return
 lda offset
 cmp #64
 bne @return
 lda #0
 sta offset
 sta offset+1
 inc verify_kind
 lda verify_kind
 cmp #3
 bne @return
.if DOS64_MEDIA_INSERT
 lda insert_job
 beq :+
 lda #4
 sta verify_kind
 rts
:
.endif
 lda script
 sta verified_script
 jmp next_script
@return: rts
 .if DOS64_MEDIA_INSERT
insert_journal_check:
 ldx #7
: lda $b800,x
 cmp insert_journal_magic,x
 jne @bad
 dex
 bpl :-
 lda $b808
 cmp ML_DRIVE
 jne @bad
 lda MI_FQ+2
 and #1
 cmp $b809
 jne @bad
 ldx #1
: lda $b80a,x
 cmp sequence,x
 jne @bad
 dex
 bpl :-
 ldx #41
: lda $b80c,x
 cmp ML_SNAPSHOT,x
 jne @bad
 dex
 bpl :-
 ldx #3
: lda $b836,x
 cmp ML_CRC,x
 jne @bad
 dex
 bpl :-
 ldx #69
: lda $b83a,x
 jne @bad
 dex
 bpl :-
 clc
 rts
@bad: sec
 rts
; Insert-only prepublication reconstruction proof. OLD must equal accepted
; startup CFG, NEW may change only selectedpath/RO/presence/CRC/bodyfooter.
insert_cfg_poll:
 lda #0
 sta count
 lda #1
 sta count+1
 lda offset+1
 cmp #2
 bne :+
 lda #64
 sta count
 lda #0
 sta count+1
: lda #0
 sta source
 sta source+1
 lda #$3e
 sta source+2
 lda verify_kind
 cmp #4
 bne :+
 lda #$20
 sta source
 lda #$f0
 sta source+1
 lda #$3f
 sta source+2
: lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 ldy #0
: lda $b800,y
 sta $b900,y
 iny
 cpy count
 bne :-
 lda #0
 sta source
 sta source+1
 lda #$3e
 sta source+2
 lda verify_kind
 cmp #5
 bne :+
 lda #3
 sta source+1
: lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 lda #1
 ldx ML_DRIVE
 beq :+
 asl
: sta work
 ldy #0
@bytes:
 lda verify_kind
 cmp #4
 bne @new
 lda $b800,y
 cmp $b900,y
 jne identity_failure
 jmp @next
@new:
 jsr insert_cfg_byte
 jcs identity_failure
@next:
 iny
 cpy count
 bne @bytes
 lda offset
 clc
 adc count
 sta offset
 lda offset+1
 adc count+1
 sta offset+1
 cmp #2
 bne @return
 lda offset
 cmp #64
 bne @return
 lda #0
 sta offset
 sta offset+1
 lda verify_kind
 cmp #4
 bne @complete
 lda #5
 sta verify_kind
 jsr binding_crc_reset
@return: rts
@complete:
 lda script
 sta verified_script
 jmp next_script
insert_cfg_byte:
 lda offset+1
 beq @page0
 cmp #1
 beq @page1
 ; final64 bytes contain flags, cookies, and stored bodyCRC.
 cpy #60
 bcc @flags
 tya
 sec
 sbc #60
 tax
 lda crc,x
 eor #$ff
 jmp @expected
@flags:
 cpy #12
 beq @readonly
 cpy #13
 beq @presence
 lda ML_DRIVE
 asl
 asl
 clc
 adc #16
 sta append_byte
 tya
 sec
 sbc append_byte
 cmp #4
 bcs @old
 tax
 lda ML_CRC,x
 jmp @feed
@readonly:
 lda MI_FQ+2
 and #1
 beq :+
 lda $b900,y
 ora work
 jmp @feed
: lda $b900,y
 ora work
 eor work
 jmp @feed
@presence:
 lda $b900,y
 ora work
 jmp @feed
@page0:
 lda ML_DRIVE
 bne @old
 cpy #136
 bcc @old
 tya
 sec
 sbc #136
 jmp @path
@page1:
 lda ML_DRIVE
 bne @bpath
 cpy #8
 bcs @old
 tya
 clc
 adc #120
 jmp @path
@bpath:
 cpy #8
 bcc @old
 cpy #136
 bcs @old
 tya
 sec
 sbc #8
@path:
 tax
 lda ML_PATH,x
 jmp @feed
@old:
 lda $b900,y
@feed:
 cmp $b800,y
 bne @bad
 lda $b800,y
 jsr crc_byte
 clc
 rts
@expected:
 cmp $b800,y
 bne @bad
 clc
 rts
@bad: sec
 rts
.segment "RODATA"
insert_journal_magic:.byte "D64J",1,4,5,0
.segment "CODE"
.endif
 .if DOS64_MEDIA_INSERT
insert_image_poll:
 lda #0
 sta count
 lda #1
 sta count+1
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 ldy #0
: lda $b800,y
 jsr crc_byte
 iny
 bne :-
 inc source+1
 bne :+
 inc source+2
: lda insert_blocks
 bne :+
 dec insert_blocks+1
: dec insert_blocks
 lda insert_blocks
 ora insert_blocks+1
 bne @return
 ldx #3
: lda crc,x
 eor #$ff
 cmp ML_CRC,x
 jne identity_failure
 dex
 bpl :-
 jsr media_match
 jcs identity_failure
 lda #0
 sta verify_kind
 jsr binding_crc_reset
@return: rts
.endif
identity_failure:
 lda #11
 jsr fatal_latch
 jmp cleanup
crc_byte:
 eor crc
 sta crc
 ldx #8
@bit:
 lsr crc+3
 ror crc+2
 ror crc+1
 ror crc
 bcc @next
 lda crc
 eor #$20
 sta crc
 lda crc+1
 eor #$83
 sta crc+1
 lda crc+2
 eor #$b8
 sta crc+2
 lda crc+3
 eor #$ed
 sta crc+3
@next:
 dex
 bne @bit
 rts
observe_cancel:
 lda tw_cancel
 beq @return
 lda committing
 beq @cancel
 lda #1
 sta cancel_late
 rts
@cancel: lda #7
 jsr latch
@return: rts
media_match:
 ldx #9
: lda dos64_disk_reu_base,x
 cmp ML_SNAPSHOT,x
 bne @bad
 dex
 bpl :-
 ldx #31
: lda dos64_disk_b_descriptor,x
 cmp ML_SNAPSHOT+10,x
 bne @bad
 dex
 bpl :-
.if DOS64_MEDIA_INSERT
 lda insert_job
 beq :+
 jmp insert_stage_check
:
.endif
 clc
 rts
@bad: sec
 rts
.if DOS64_MEDIA_INSERT
.include "insert_stage.inc"
.endif
; Append canonical home/name to command, with16bit cursor allowing2x128.
path_command:
 sta path_offset
 lda #0
 sta path_offset+1
 lda #<dos64_uci_command
 clc
 adc path_offset
 sta wp
 lda #>dos64_uci_command
 adc #0
 sta wp+1
append_name:
 ldx #0
@home: lda home,x
 beq @slash
 jsr append
 inx
 bne @home
@slash:
 cpx #1
 beq @base
 lda #$2f
 jsr append
@base:
 lda name
 cmp #4
 bcs @archive
 asl
 tax
 lda nameptrs,x
 sta rp
 lda nameptrs+1,x
 sta rp+1
 ldy #0
@copy: lda (rp),y
 jsr append
 cmp #0
 beq @end
 iny
 bne @copy
@archive:
.if DOS64_MEDIA_SEQUENCE
 lda name
 cmp #6
 bne :+
 lda alloc_drive
 clc
 adc #'A'
 bne @prefix
:
.endif
 lda #'S'
.if DOS64_MEDIA_SEQUENCE
@prefix:
.endif
 jsr append
 lda sequence+1
 jsr hex
 lda sequence
 jsr hex
 lda #'.'
 jsr append
 lda name
 sec
 sbc #4
 asl
 tax
 .if DOS64_MEDIA_SEQUENCE
 cpx #4
 bne :+
 lda #<imageext
 sta rp
 lda #>imageext
 sta rp+1
 jmp @extension
:
.endif
 lda extptrs,x
 sta rp
 lda extptrs+1,x
 sta rp+1
.if DOS64_MEDIA_SEQUENCE
@extension:
.endif
 ldy #0
 jmp @copy
@end:
 lda path_offset
 sec
 sbc #3
 sta dos64_files_path_len
 rts
append:
 sta append_byte
 tya
 pha
 ldy #0
 lda append_byte
 sta (wp),y
 inc wp
 bne :+
 inc wp+1
: inc path_offset
 bne :+
 inc path_offset+1
: pla
 tay
 lda append_byte
 rts
hex:
 pha
 lsr
 lsr
 lsr
 lsr
 jsr nibble
 pla
 and #15
nibble:
 tax
 lda digits,x
 jmp append
.segment "RODATA"
kinds:.byte 1,1,4,2,2,3,2,2
names:.byte 1,2,0,0,1,0,3,2
destinations:.byte 0,0,0,3,0,0,4,5
ok:.byte "00,OK"
digits:.byte "0123456789ABCDEF"
nameptrs:.word cfg,new,journal,old
extptrs:.word oldext,journalext
cfg:.asciiz "DOS64.CFG"
new:.asciiz "DOS64.NEW"
journal:.asciiz "DOS64.JRN"
old:.asciiz "DOS64.OLD"
oldext:.asciiz "OLD"
journalext:.asciiz "JRN"

.import __BSS_RUN__,__BSS_SIZE__
.assert __BSS_RUN__+__BSS_SIZE__ <= $7e80,lderror,"WIRE state must not overwrite PLAN saved96 or jobcapsule"

.if DOS64_MEDIA_BINDING
; Only actual private successful mode1 finish reaches this immutable writer.
; No callback/public observation can mint a retained terminal receipt.
binding_mint:
.if DOS64_MEDIA_INSERT
 lda insert_job
 jne binding_mint_insert
.endif
 lda #0
 sta MB_READY
 lda #1
 sta MB_VERSION
 lda original_online
 sta MB_ONLINE
 lda sequence
 sta MB_SEQUENCE
 lda sequence+1
 sta MB_SEQUENCE+1
 ldx #24
: lda snapshot,x
 sta MB_FILES,x
 dex
 bpl :-
 jsr binding_crc_reset
 ldy #0
: lda ML_STATE,y
 jsr crc_byte
 iny
 cpy #ML_BYTES
 bne :-
 ldx #3
: lda crc,x
 eor #$ff
 sta MB_LEDGER_CRC,x
 dex
 bpl :-
 jsr binding_crc_reset
 ldy #0
: lda home,y
 jsr crc_byte
 iny
 bpl :-
 ldx #3
: lda crc,x
 eor #$ff
 sta MB_HOME_CRC,x
 dex
 bpl :-
 ldx #23
: lda dos64_disk_clean_mount,x
 sta MB_TAIL,x
 dex
 bpl :-
 jsr binding_crc_reset
 lda #0
 sta source
 sta offset
 sta offset+1
 lda #$f0
 sta source+1
 lda #$3f
 sta source+2
 lda #32
 sta count
 lda #0
 sta count+1
 lda #1
 sta dos64_reu_request+7
 jsr reu
 bcs binding_mint_fail
 ldy #0
: lda $b800,y
 jsr crc_byte
 iny
 cpy #28
 bne :-
 lda #$f5
 sta source+1
 lda #1
 sta dos64_reu_request+7
 jsr reu
 bcs binding_mint_fail
 ldy #0
: lda $b800,y
 jsr crc_byte
 iny
 cpy #28
 bne :-
 ldx #3
: lda crc,x
 eor #$ff
 sta MB_ANCHORS_CRC,x
 dex
 bpl :-
@clock:
 jsr clock
 bcc :+
 lda fatal
 beq @clock
 jmp binding_mint_fail
: jsr binding_crc_reset
 ldy #1
: lda MB_READY,y
 jsr crc_byte
 iny
 cpy #66
 bne :-
 ldx #3
: lda crc,x
 eor #$ff
 sta MB_CHECKSUM,x
 dex
 bpl :-
 lda #$a5
 sta MB_READY
 rts
binding_mint_fail:
 lda #4
 jsr fatal_latch
 lda #3
 sta state
 lda #$e1
 sta dos64_native_diag
 rts
binding_crc_reset:
 lda #$ff
 ldx #3
: sta crc,x
 dex
 bpl :-
 rts
.if DOS64_MEDIA_INSERT
binding_mint_insert:
 lda #0
 sta MI_READY
 lda #2
 sta MI_VERSION
 lda original_online
 sta MI_ONLINE
 lda sequence
 sta MI_SEQUENCE
 lda sequence+1
 sta MI_SEQUENCE+1
 jsr binding_crc_reset
 ldy #0
: lda ML_STATE,y
 jsr crc_byte
 iny
 cpy #MI_LEDGER_BYTES
 bne :-
 ldx #3
: lda crc,x
 eor #$ff
 sta MI_LEDGER_CRC,x
 dex
 bpl :-
 jsr binding_crc_reset
 ldy #0
: lda home,y
 jsr crc_byte
 iny
 bpl :-
 ldx #3
: lda crc,x
 eor #$ff
 sta MI_HOME_CRC,x
 dex
 bpl :-
 ldx #23
: lda dos64_disk_clean_mount,x
 sta MI_TAIL,x
 dex
 bpl :-
 jsr binding_crc_reset
 lda #0
 sta source
 sta offset
 sta offset+1
 lda #$f0
 sta source+1
 lda #$3f
 sta source+2
 lda #32
 sta count
 lda #0
 sta count+1
 lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs binding_mint_fail
 ldy #0
: lda $b800,y
 jsr crc_byte
 iny
 cpy #28
 bne :-
 lda #$f5
 sta source+1
 lda #1
 sta dos64_reu_request+7
 jsr reu
 jcs binding_mint_fail
 ldy #0
: lda $b800,y
 jsr crc_byte
 iny
 cpy #28
 bne :-
 ldx #3
: lda crc,x
 eor #$ff
 sta MI_ANCHORS_CRC,x
 dex
 bpl :-
@clock:
 jsr clock
 bcc :+
 lda fatal
 beq @clock
 jmp binding_mint_fail
: jsr binding_crc_reset
 ldy #1
: lda MI_READY,y
 jsr crc_byte
 iny
 cpy #41
 bne :-
 ldx #3
: lda crc,x
 eor #$ff
 sta MI_CHECKSUM,x
 dex
 bpl :-
 lda #$a5
 sta MI_READY
 rts
.endif

.endif

.if DOS64_MEDIA_SEQUENCE
.segment "CODE"
; Allocation-only API. Public hint/result bytes never mint authority. Preserve
; caller P/high ZP; AX is the private selected nonzero sequence, or zero.
tw_take_sequence:
 php
 sei
 cld
 jsr alloc_take
 plp
 rts
alloc_take:
 lda alloc_ready
 cmp #$a5
 bne @bad
 lda state
 cmp #2
 bne @bad
 lda mode
 cmp #2
 bcc @bad
 lda error
 ora context
 bne @bad
 lda closed
 cmp #1
 bne @bad
 jsr alloc_context
 bcs @authority_lost
 jsr clock
 bcs @withdraw
 lda #0
 sta alloc_ready
 lda sequence
 ldx sequence+1
 rts
@authority_lost:
 lda #10
 jsr fatal_latch
@withdraw:
 lda fatal
 beq @bad
 lda #0
 sta alloc_ready
 jsr blocked
@bad: lda #0
 tax
 rts
; The published coherent 32bit sample must progress by less than 08000000.
; This detects full elapsed16 aliasing without acquiring/reinitializing timers.
alloc_clock32:
 lda alloc_seen
 beq @capture
 sec
 lda dos64_host_clock_ticks
 sbc alloc_last
 lda dos64_host_clock_ticks+1
 sbc alloc_last+1
 lda dos64_host_clock_ticks+2
 sbc alloc_last+2
 lda dos64_host_clock_ticks+3
 sbc alloc_last+3
 cmp #8
 bcs @bad
@capture:
 ldx #3
: lda dos64_host_clock_ticks,x
 sta alloc_last,x
 dex
 bpl :-
 lda #1
 sta alloc_seen
 clc
 rts
@bad: sec
 rts
; Exact private broker admission and original online-C context, not tw_* state.
alloc_context:
 jsr alloc_broker_native_owner
 bcs @bad
 jsr quiet
 bcs @bad
 ldx #24
: lda dos64_files_state_start,x
 cmp alloc_broker_saved_files,x
 bne @bad
 dex
 bpl :-
 ldx #hd_state_end-hd_state_start-1
: lda hd_state_start,x
 cmp alloc_broker_saved_hd,x
 bne @bad
 dex
 bpl :-
 ldx #hdb_state_end-hdb_state_start-1
: lda hdb_state_start,x
 cmp alloc_broker_saved_hdb,x
 bne @bad
 dex
 bpl :-
 clc
 rts
@bad: sec
 rts
; Two independent initialized FETCHes compared to actual READ04 bytes.
; Then stage the exact old CFG for the following caller-owned PLAN.
alloc_read_compare:
 jsr alloc_fetch_compare
 jcs compare_failure
 ; Captured home must equal current accepted CFG home, including zero padding.
 lda offset
 ora offset+1
 bne @store
 ldy #0
: lda home,y
 cmp $b808,y
 jne compare_failure
 iny
 cpy #128
 bne :-
@store:
 lda #0
 sta source
 sta source+1
 lda #$3e
 sta source+2
 lda #0
 sta dos64_reu_request+7
 jsr reu
 jcs dma_failure
 jsr alloc_fetch_compare
 jcs compare_failure
 lda #$20
 sta source
 lda #$f0
 sta source+1
 lda #$3f
 sta source+2
 jmp read_advance
alloc_fetch_compare:
 ldy #0
: lda #$a5
 sta $b800,y
 lda #$5a
 sta $b900,y
 iny
 cpy count
 bne :-
 lda #1
 sta dos64_reu_request+7
 jsr reu
 bcs @dma
 lda #$b9
 sta dos64_reu_request+1
 jsr dos64_reu_transfer
 bcs @dma
 ldy #0
: lda dos64_uci_data,y
 cmp $b800,y
 bne @bad
 cmp $b900,y
 bne @bad
 iny
 cpy count
 bne :-
 clc
 rts
@dma:
 lda #6
 jsr fatal_latch
@bad: sec
 rts
; Exact upstream v3.14 FR_NO_FILE status only, never PATH DOESN'T EXIST or85.
alloc_missing:
 lda dos64_files_error
 cmp #3
 bne @bad
 lda dos64_uci_status_len
 cmp #18
 bne @bad
 lda dos64_uci_status_len+1
 bne @bad
 ldx #17
: lda dos64_uci_status,x
 cmp alloc_missing_text,x
 bne @bad
 dex
 bpl :-
 lda dos64_uci_recovery_failed
 bne @bad
 lda dos64_files_transport_error
 beq :+
 cmp #5
 bne @bad
: lda dos64_uci_error
 beq @ok
 cmp #5
 bne @bad
@ok: clc
 rts
@bad: sec
 rts
alloc_open:
 lda #0
 sta alloc_exists
 lda #1
 sta dos64_files_mode
 lda #3
 jsr path_command
 lda #20
 sta phase
 lda #2
 jsr start_file
 jcs file_failure
 rts
alloc_poll:
 jsr copy_now
 jsr dos64_overlay_files_poll
 ; The leaf result is observed before cancellation on the next poll too.
 jsr observe
 lda error
 jne cleanup
 lda dos64_files_state
 cmp #1
 jeq done
 lda phase
 cmp #21
 beq @closed
 lda dos64_files_state
 cmp #2
 beq @exists
 jsr alloc_missing
 jcs file_failure
 jmp @close
@exists:
 lda #1
 sta alloc_exists
@close:
 lda #21
 sta phase
 lda #3
 jsr start_file
 jcs file_failure
 rts
@closed:
 lda dos64_files_handle
 jne file_failure
 jsr quiet
 jcs file_failure
 lda #0
 sta waiting
 lda name
 cmp #4
 bcs @archive
 lda alloc_exists
 bne @collision
 inc name
 jmp alloc_open
@collision:
 lda #13
 jsr latch
 jmp finish
@archive:
 lda alloc_exists
 ora alloc_collision
 sta alloc_collision
 lda name
 cmp #4
 bne @pair_done
 inc name
 jmp alloc_open
@pair_done:
 lda mode
 cmp #3
 bne @candidate_done
 lda name
 cmp #5
 bne @candidate_done
 inc name
 jmp alloc_open
@candidate_done:
 lda alloc_collision
 beq @selected
 lda #0
 sta alloc_collision
 inc sequence
 bne @next
 inc sequence+1
 bne @next
 inc sequence
@next:
 lda sequence
 cmp alloc_first
 bne @another
 lda sequence+1
 cmp alloc_first+1
 beq @exhausted
@another:
 lda #4
 sta name
 jmp alloc_open
@exhausted:
 lda #14
 jsr latch
 jmp finish
@selected:
 lda #$a5
 sta alloc_ready
 jmp finish
.segment "RODATA"
imageext:.asciiz "IMG"
alloc_missing_text:.byte "FILE DOESN'T EXIST"
.endif
