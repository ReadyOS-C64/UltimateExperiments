.setcpu "6502"
.macpack longbranch
.include "imports.inc"
.export fn_begin,fn_poll,fn_take_restart,fn_state,fn_error,fn_known_closed
.export fn_enable,fn_discard,fn_limit,fn_cancel,fn_private_start,fn_private_end
.export _fn_begin:=fn_begin,_fn_poll:=fn_poll,_fn_take_restart:=fn_take_restart
.export _fn_state:=fn_state,_fn_error:=fn_error,_fn_known_closed:=fn_known_closed
.export _fn_enable:=fn_enable,_fn_discard:=fn_discard,_fn_limit:=fn_limit,_fn_cancel:=fn_cancel
.segment "LOADADDR"
.word $a000
.segment "BSS"
fn_enable:.res 1
fn_discard:.res 1
fn_limit:.res 2
fn_cancel:.res 1
fn_private_start:
entered:.res 1
state:.res 1
error:.res 1
known:.res 1
ready:.res 1
attempts:.res 1
phase:.res 1
owner_target:.res 1
policy:.res 1
limit:.res 2
started:.res 2
now:.res 2
raw_last:.res 4
raw_seen:.res 1
sample_count:.res 1
ports:.res 4
drain:.res 1
steps:.res 2
work:.res 1
media:.res 42
fn_private_end:
.segment "CODE"
.macro API body
 php
 sei
 cld
 jsr body
 ldx #0
 plp
 rts
.endmacro
fn_begin: API begin
fn_poll: API poll
fn_take_restart: API take
fn_state: lda state
 ldx #0
 rts
fn_error: lda error
 ldx #0
 rts
fn_known_closed: lda known
 ldx #0
 rts
latch:
 ldx error
 bne :+
 sta error
: rts
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
; Existing coherent mainclock only: no init/provider takeover. Same raw32
; half-range fence as admitted native controller; STOP only after freshsample.
service:
 lda #0
 sta sample_count
@sample:
 jsr dos64_elapsed_poll
 bcc @fresh
 lda dos64_host_clock_status
 cmp #4
 bne @bad
 inc sample_count
 bne @sample
@bad: lda #2
 rts
@fresh:
 lda raw_seen
 beq @capture
 sec
 lda dos64_host_clock_ticks
 sbc raw_last
 lda dos64_host_clock_ticks+1
 sbc raw_last+1
 lda dos64_host_clock_ticks+2
 sbc raw_last+2
 lda dos64_host_clock_ticks+3
 sbc raw_last+3
 cmp #8
 bcs @bad
@capture:
 ldx #3
: lda dos64_host_clock_ticks,x
 sta raw_last,x
 lda $dc00,x
 sta ports,x
 dex
 bpl :-
 lda dos64_elapsed_now
 sta now
 lda dos64_elapsed_now+1
 sta now+1
 lda #1
 sta raw_seen
 lda #$ff
 sta $dc02
 lda #0
 sta $dc03
 lda #$7f
 sta $dc00
 nop
 nop
 lda $dc01
 and #$80
 pha
 ldx #3
: lda ports,x
 sta $dc00,x
 dex
 bpl :-
 pla
 beq @stop
 lda #0
 rts
@stop: lda #7
 rts
; Presentation-owned E1 is intentional terminal Finish fence, never RUN.
common:
 lda hdc_target
 cmp owner_target
 jne @bad
 cmp broker_saved_target
 jne @bad
 jsr broker_presentation_owner
 jcs @bad
 lda $00
 and #7
 cmp #7
 jne @bad
 lda $01
 and #7
 cmp #5
 jne @bad
 lda dos64_cold_open
 ora sav_context_pending
 ora sav_borrowed
 ora hdb_active
 ora hd_uncertain
 ora dos64_overlay_busy
 ora hd_request
 ora hd_error
 jne @bad
 lda hd_state
 cmp #1
 jeq @bad
 cmp #3
 jeq @bad
 ldx #31
: lda dos64_cache_flags,x
 ora dos64_cache_pins,x
 jne @bad
 dex
 bpl :-
 ldx #hd_state_end-hd_state_start-1
: lda hd_state_start,x
 cmp broker_saved_hd,x
 jne @bad
 dex
 bpl :-
 ldx #hdb_state_end-hdb_state_start-1
@hd:
 cpx #1 ; online is intentionally retired only after a known CLOSE.
 beq @skip
 lda hdb_state_start,x
 cmp broker_saved_hdb,x
 jne @bad
@skip: dex
 bpl @hd
 clc
 rts
@bad: sec
 rts
media_same:
 ldx #9
: lda dos64_disk_reu_base,x
 cmp media,x
 bne @bad
 dex
 bpl :-
 ldx #31
: lda dos64_disk_b_descriptor,x
 cmp media+10,x
 bne @bad
 dex
 bpl :-
 clc
 rts
@bad: sec
 rts
open_context:
 jsr common
 bcs @bad
 jsr quiet
 bcs @bad
 lda hdb_online
 cmp #1
 bne @bad
 lda broker_saved_online
 cmp #1
 bne @bad
 lda hdc_target
 cmp owner_target
 bne @bad
 cmp broker_saved_target
 bne @bad
 lda dos64_files_handle
 cmp #1
 bne @bad
 ldx #24
: lda dos64_files_state_start,x
 cmp broker_saved_files,x
 bne @bad
 dex
 bpl :-
 clc
 rts
@bad: sec
 rts
begin:
 lda entered
 jne reject
 lda fn_enable
 cmp #$a5
 jne reject
 jsr broker_native_owner
 jcs reject
 lda fn_limit
 ora fn_limit+1
 jeq reject
 lda fn_limit+1
 jmi reject
 lda fn_discard
 and #$fc
 jne reject
 lda hdc_target
 cmp #1
 beq :+
 cmp #2
 jne reject
: sta owner_target
 jsr open_context
 jcs reject
 lda fn_discard
 sta policy
 ; Require real dirty/exhausted floppy decisions, not a UI clean observation.
 ldx #1
@policy:
 lda dos64_disk_dirty,x
 ora dos64_disk_exhausted,x
 and #1
 beq @next
 lda policy
 and bits,x
 jeq reject
@next: dex
 bpl @policy
 lda #0
 sta raw_seen
 jsr service
 jne reject
 ldx #9
: lda dos64_disk_reu_base,x
 sta media,x
 dex
 bpl :-
 ldx #31
: lda dos64_disk_b_descriptor,x
 sta media+10,x
 dex
 bpl :-
 lda fn_limit
 sta limit
 lda fn_limit+1
 sta limit+1
 lda now
 sta started
 lda now+1
 sta started+1
 lda #0
 sta error
 sta known
 sta ready
 sta attempts
 sta phase
 sta drain
 sta steps
 sta steps+1
 sta fn_cancel
 lda #1
 sta state
 sta entered
 lda #$e1
 sta dos64_native_diag
 lda #1
 rts
reject: lda #0
 rts
copy_now:
 ldx #1
: lda now,x
 sta dos64_files_now,x
 sta dos64_uci_now,x
 dex
 bpl :-
 rts
; Exact84 may be observed before parser finishes; other leaf errors latch
; immediately, ahead of same-poll STOP or clock withdrawal.
observe:
 lda dos64_files_error
 beq @return
 cmp #3
 bne @file
 jsr status84
 bcc @return
@file: lda #4
 jsr latch
@return: rts
status84:
 lda dos64_uci_status_len
 cmp #19
 bne @bad
 lda dos64_uci_status_len+1
 bne @bad
 ldx #18
: lda dos64_uci_status,x
 cmp nofile,x
 bne @bad
 dex
 bpl :-
 clc
 rts
@bad: sec
 rts
closed_status:
 lda dos64_files_error
 beq @ok00
 cmp #3
 bne @bad
 jsr status84
 rts
@ok00:
 lda dos64_uci_status_len
 cmp #5
 bne @bad
 lda dos64_uci_status_len+1
 bne @bad
 ldx #4
: lda dos64_uci_status,x
 cmp ok00,x
 bne @bad
 dex
 bpl :-
 clc
 rts
@bad: sec
 rts
poll:
 lda state
 cmp #1
 jne done
 lda phase
 beq :+
 jsr observe
: inc steps
 bne :+
 inc steps+1
 jeq fail_unknown
: jsr service
 beq @service_ok
 jsr latch
@service_ok:
 lda fn_cancel
 beq :+
 lda #7
 jsr latch
: lda error
 beq @deadline
 inc drain
 jeq fail_unknown
@deadline:
 lda now
 sec
 sbc started
 sta work
 lda now+1
 sbc started+1
 cmp limit+1
 bcc @phase
 bne @late
 lda work
 cmp limit
 bcc @phase
@late: lda #2
 jsr latch
@phase:
 lda phase
 bne @poll_close
 lda error
 jne failure
 jsr open_context
 jcs context_failure
 jsr media_same
 jcs context_failure
 lda #3
 sta dos64_files_op
 jsr copy_now
 inc attempts
 inc phase
 jsr dos64_overlay_files_start
 jcs file_failure
 rts
@poll_close:
 jsr copy_now
 jsr dos64_overlay_files_poll
 jsr observe
 lda dos64_files_state
 cmp #1
 jeq done
 jsr quiet
 jcs fail_unknown
 lda dos64_files_handle
 jne file_failure
 jsr closed_status
 jcs file_failure
 ; Native parser + exact terminal status establish actual closed ownership.
 lda #0
 sta hdb_online
 lda #1
 sta known
 jsr common
 jcs context_failure
 jsr media_same
 jcs context_failure
 jsr service
 beq :+
 jsr latch
: lda error
 jne failure
 lda #2
 sta state
 lda #$a5
 sta ready
 rts
context_failure: lda #10
 bne finish_error
file_failure: lda #4
finish_error: jsr latch
failure:
 lda #0
 sta ready
 lda #3
 sta state
 rts
fail_unknown:
 lda #8
 jsr latch
 jmp failure
done: rts
take:
 lda ready
 cmp #$a5
 jne reject
 lda state
 cmp #2
 jne withdraw
 lda entered
 cmp #1
 jne withdraw
 lda error
 jne withdraw
 lda known
 cmp #1
 jne withdraw
 lda attempts
 cmp #1
 jne withdraw
 lda fn_cancel
 beq :+
 lda #7
 jsr latch
 jmp withdraw
: lda dos64_native_diag
 cmp #$e1
 jne withdraw
 jsr common
 jcs withdraw
 jsr media_same
 jcs withdraw
 lda hdb_online
 ora dos64_files_handle
 jne withdraw
 lda dos64_files_target
 cmp owner_target
 jne withdraw
 cmp dos64_files_owned_target
 jne withdraw
 jsr quiet
 jcs withdraw
 jsr closed_status
 jcs withdraw
 jsr service
 beq @grant
 jsr latch
 jmp withdraw
@grant:
 lda #0
 sta ready
 lda #1
 rts
withdraw:
 lda #10
 jsr latch
 jsr failure
 jmp reject
.segment "RODATA"
bits:.byte 1,2
ok00:.byte "00,OK"
nofile:.byte "84,NO FILE TO CLOSE"
.import __BSS_RUN__,__BSS_SIZE__
.assert __BSS_RUN__+__BSS_SIZE__ <= $7e80,lderror,"Finish state overlaps PLAN savedhigh96/job"
