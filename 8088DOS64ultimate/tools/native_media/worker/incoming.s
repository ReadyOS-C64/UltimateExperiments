.setcpu "6502"
.macpack longbranch
.include "imports.inc"
.export iw_begin,iw_poll,iw_take,iw_state,iw_error,iw_closed
.export iw_path,iw_enable,iw_cancel,iw_limit,iw_private_start,iw_private_end
.export _iw_begin:=iw_begin,_iw_poll:=iw_poll,_iw_take:=iw_take
.export _iw_state:=iw_state,_iw_error:=iw_error,_iw_closed:=iw_closed
.export _iw_path:=iw_path,_iw_enable:=iw_enable,_iw_cancel:=iw_cancel,_iw_limit:=iw_limit
.segment "LOADADDR"
.word $a000
.segment "BSS"
iw_path:.res 128
iw_enable:.res 1
iw_cancel:.res 1
iw_limit:.res 2
iw_private_start:
receipt:
r_drive:.res 1
r_flags:.res 1
r_base:.res 3
r_token:.res 4
r_mount:.res 4
r_content:.res 4
r_crc:.res 4
r_path:.res 128
snapshot:.res 25
original_online:.res 1
target:.res 1
limit:.res 2
now:.res 2
started:.res 2
raw_last:.res 4
raw_seen:.res 1
sample_count:.res 1
ports:.res 4
offset:.res 3
state:.res 1
error:.res 1
closed:.res 1
ready:.res 1
entered:.res 1
phase:.res 1
waiting:.res 1
raw:.res 1
seen:.res 1
context:.res 1
fatal:.res 1
aborted:.res 1
cleanup_close:.res 1
drain:.res 1
steps:.res 2
work:.res 1
pathlen:.res 1
retA:.res 1
retX:.res 1
iw_private_end:
.assert r_path-receipt=21,error,"receipt field layout"
.assert snapshot-receipt=149,error,"receipt size"
.segment "CODE"
; Preserve caller flags and current native20..43 scratch; no phase ZP/staticC
; software stack, no high96 writes. Native FILES/UCI use their existing state.
.macro API body
 php
 sei
 cld
 ldx #0
: lda $20,x
 pha
 inx
 cpx #36
 bne :-
 jsr body
 sta retA
 stx retX
 ldx #35
: pla
 sta $20,x
 dex
 bpl :-
 lda retA
 ldx retX
 plp
 rts
.endmacro
iw_begin: API begin
iw_poll: API poll
iw_take: API take
iw_state: lda state
 ldx #0
 rts
iw_error: lda error
 ldx #0
 rts
iw_closed: lda closed
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
 lda #$e1
 sta dos64_native_diag
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
@bad: sec
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
 dex
 bpl :-
 lda dos64_elapsed_now
 sta now
 lda dos64_elapsed_now+1
 sta now+1
 lda #1
 sta raw_seen
 clc
 rts
stop:
 ldx #3
: lda $dc00,x
 sta ports,x
 dex
 bpl :-
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
 beq @yes
 lda iw_cancel
 bne @yes
 clc
 rts
@yes: sec
 rts
copy_now:
 lda now
 sta dos64_files_now
 sta dos64_uci_now
 lda now+1
 sta dos64_files_now+1
 sta dos64_uci_now+1
 rts
ownership:
 jsr broker_presentation_owner
 jcs @bad
 lda dos64_cold_open
 ora dos64_cache_limit
 ora sav_borrowed
 ora sav_context_pending
 ora dos64_overlay_busy
 ora hdb_active
 ora hd_uncertain
 jne @bad
 ldx #hd_state_end-hd_state_start-1
: lda hd_state_start,x
 cmp broker_saved_hd,x
 bne @bad
 dex
 bpl :-
 ldx #hdb_state_end-hdb_state_start-1
@hdb:
 cpx #hdb_online-hdb_state_start
 beq @online
 lda hdb_state_start,x
 cmp broker_saved_hdb,x
 bne @bad
 jmp @next
@online:
 lda context
 beq :+
 lda hdb_online
 bne @bad
 beq @next
: lda hdb_online
 cmp broker_saved_hdb,x
 bne @bad
@next:
 dex
 bpl @hdb
 lda context
 bne @borrowed
 ldx #24
: lda dos64_files_state_start,x
 cmp broker_saved_files,x
 bne @bad
 dex
 bpl :-
 clc
 rts
@borrowed:
 lda dos64_files_target
 cmp target
 bne @bad
 lda dos64_files_owned_target
 cmp target
 bne @bad
 clc
 rts
@bad: sec
 rts
lease:
 lda dos64_floppy_stage_active
 cmp #$a5
 jne @bad
 lda stage_drive
 cmp r_drive
 jne @bad
 lda stage_flags
 cmp r_flags
 jne @bad
 lda dos64_floppy_stage_bank
 cmp r_base+2
 jne @bad
 ldx #3
: lda dos64_floppy_token,x
 cmp r_token,x
 bne @bad
 lda stage_mount,x
 cmp r_mount,x
 bne @bad
 lda stage_content,x
 cmp r_content,x
 bne @bad
 dex
 bpl :-
 lda r_drive
 asl
 asl
 tax
 ldy #0
: lda dos64_disk_mount_generation,x
 cmp r_mount,y
 bne @bad
 lda dos64_disk_content_generation,x
 cmp r_content,y
 bne @bad
 inx
 iny
 cpy #4
 bne :-
 lda dos64_disk_loaded
 beq :+
 lda dos64_disk_reu_base+2
 cmp r_base+2
 beq @bad
: lda dos64_disk_b_descriptor+9
 beq @ok
 lda dos64_disk_b_descriptor+2
 cmp r_base+2
 beq @bad
@ok: clc
 rts
@bad: sec
 rts
path:
 ldx #127
: lda iw_path,x
 sta r_path,x
 dex
 bpl :-
 lda r_path
 cmp #'/'
 bne @bad
 ldx #1
 lda #1
 sta work
@char:
 lda r_path,x
 beq @end
 cmp #32
 bcc @bad
 cmp #127
 bcs @bad
 cmp #92
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
 cmp #'/'
 bne @next
 cpx work
 beq @bad
 lda r_path-1,x
 cmp #'.'
 beq @bad
 cmp #' '
 beq @bad
 txa
 clc
 adc #1
 sta work
@next:
 inx
 bpl @char
@bad: sec
 rts
@end:
 cpx work
 beq @bad
 lda r_path-1,x
 cmp #'.'
 beq @bad
 cmp #' '
 beq @bad
 inx
 stx pathlen
@pad:
 cpx #128
 beq @ok
 lda r_path,x
 bne @bad
 inx
 bne @pad
@ok: clc
 rts
begin:
 lda #0
 sta ready
 lda state
 cmp #1
 jeq reject
 lda iw_enable
 cmp #$a5
 jne reject
 lda entered
 jne reject
 lda iw_limit
 ora iw_limit+1
 jeq reject
 lda iw_limit+1
 jmi reject
 lda #0
 sta context
 sta raw_seen
 jsr broker_native_owner
 jcs reject
 jsr ownership
 jcs reject
 jsr quiet
 jcs reject
 lda dos64_overlay_reu_mib
 cmp #4
 jcc reject
 lda dos64_floppy_request
 cmp #1
 jne reject
 lda dos64_floppy_request+1
 cmp #2
 jcs reject
 sta r_drive
 lda dos64_floppy_request+2
 sta r_flags
 and #$fc
 jne reject
 lda dos64_floppy_request+4
 cmp #4
 jcc reject
 cmp #17
 jcs reject
 lda dos64_floppy_request+5
 ora dos64_floppy_request+6
 jne reject
 sta r_base
 sta r_base+1
 lda dos64_floppy_request+7
 cmp #$10
 beq :+
 cmp #$18
 beq :+
 cmp #$38
 jne reject
: sta r_base+2
 ldx #3
: lda dos64_floppy_request+11,x
 sta r_token,x
 lda dos64_floppy_request+15,x
 sta r_mount,x
 lda dos64_floppy_request+19,x
 sta r_content,x
 dex
 bpl :-
 jsr lease
 jcs reject
 jsr path
 jcs reject
 jsr clock
 jcs reject
 jsr stop
 jcs reject
 lda iw_limit
 sta limit
 lda iw_limit+1
 sta limit+1
 lda now
 sta started
 lda now+1
 sta started+1
 ldx #24
: lda dos64_files_state_start,x
 sta snapshot,x
 dex
 bpl :-
 lda hdb_online
 sta original_online
 lda #1
 sta target
 lda original_online
 beq @capture
 lda hdc_target
 eor #3
 sta target
@capture:
 lda #0
 sta error
 sta closed
 sta fatal
 sta aborted
 sta cleanup_close
 sta drain
 sta steps
 sta steps+1
 sta waiting
 sta raw
 sta iw_cancel
 sta hdb_online
 ldx #24
: sta dos64_files_state_start,x
 dex
 bpl :-
 lda target
 sta dos64_files_target
 sta dos64_files_owned_target
 lda #2
 sta dos64_files_handle
 lda #1
 sta context
 sta entered
 sta state
 sta phase
 lda #3
 jsr start_file
 bcc @accepted
 lda #4
 jsr fatal_latch
 jsr blocked
@accepted:
 lda #1
 ldx #0
 rts
reject:
 lda #0
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
observe:
 lda waiting
 beq @done
 lda raw
 beq @file
 lda dos64_uci_error
 beq @done
 lda #4
 jmp latch
@file:
 lda dos64_files_error
 beq @done
 cmp #3
 bne @error
 lda dos64_files_op
 cmp #3
 bne @error
 ; FILES posts close status before ACK/finalization. Exact84 only becomes
 ; known CLOSED at terminal; do not abort its native close handshake early.
 lda dos64_uci_state
 cmp #6
 beq @done
 cmp #7
 beq @done
 cmp #9
 beq @done
@error:
 lda #4
 jmp latch
@done: rts
poll:
 lda state
 cmp #1
 jne done
 inc steps
 bne :+
 inc steps+1
 bne :+
 lda #8
 jsr fatal_latch
:
 jsr observe
 jsr clock
 bcc :+
 lda #2
 jsr fatal_latch
:
 jsr ownership
 bcs @lost
 jsr lease
 bcc @progress
@lost:
 lda #7
 jsr fatal_latch
@progress:
 lda waiting
 beq @serviced
 jsr copy_now
 lda raw
 beq @file
 jsr dos64_uci_poll
 jmp @observed
@file:
 jsr dos64_overlay_files_poll
@observed:
 jsr observe
@serviced:
 lda error
 jne cleanup
 jsr stop
 bcc :+
 lda #3
 jsr latch
 jmp cleanup
:
 sec
 lda now
 sbc started
 sta work
 lda now+1
 sbc started+1
 cmp limit+1
 bcc @dispatch
 bne @deadline
 lda work
 cmp limit
 bcc @dispatch
@deadline:
 lda #2
 jsr fatal_latch
 jmp cleanup
@dispatch:
 lda raw
 jne raw_poll
 lda waiting
 beq @idle
 lda dos64_files_state
 cmp #1
 jeq done
 cmp #2
 beq @terminal
 lda dos64_files_op
 cmp #3
 jne file_failure
 lda dos64_files_handle
 jne file_failure
@terminal:
 lda #0
 sta waiting
@idle:
 lda phase
 cmp #1
 jeq first_closed
 cmp #2
 jeq open_done
 cmp #3
 jeq info_done
 cmp #5
 jeq hash_page
 cmp #6
 jeq eof_done
 cmp #7
 jeq second_open
 cmp #8
 jeq open_done
 cmp #9
 jeq info_done
 cmp #10
 jeq compare_page
 cmp #11
 jeq eof_done
 cmp #12
 jeq finish
 lda #4
 jsr latch
 jmp cleanup
done:
 lda #0
 ldx #0
 rts
first_closed:
 lda dos64_files_handle
 jne file_failure
 lda #2
 sta phase
 jmp open_file
second_open:
 lda dos64_files_handle
 jne file_failure
 lda #8
 sta phase
open_file:
 lda #1
 sta dos64_files_mode
 ldx #0
: lda r_path,x
 sta dos64_uci_command+3,x
 inx
 cpx pathlen
 bne :-
 lda pathlen
 sta dos64_files_path_len
 lda #2
 jsr start_file
 jcs file_failure
 rts
open_done:
 inc phase
 lda #7
 jsr start_file
 jcs file_failure
 rts
info_done:
 lda dos64_files_count_known
 cmp #1
 jne file_failure
 lda dos64_uci_data
 ora dos64_uci_data+3
 jne size_failure
 lda dos64_uci_data+1
 cmp #$a0
 jne size_failure
 lda dos64_uci_data+2
 cmp #5
 jne size_failure
 lda #0
 sta offset
 sta offset+1
 sta offset+2
 lda phase
 cmp #3
 jne read_next
 lda #$ff
 ldx #3
: sta r_crc,x
 dex
 bpl :-
 jmp start_load
read_next:
 lda #10
 sta phase
 lda #0
 sta dos64_files_count
 lda #1
 sta dos64_files_count+1
 lda #4
 jsr start_file
 jcs file_failure
 rts
start_load:
 lda target
 sta dos64_uci_command
 lda #$21
 sta dos64_uci_command+1
 lda #0
 sta dos64_uci_command+2
 sta dos64_uci_command+3
 sta dos64_uci_command+5
 sta dos64_uci_command+6
 sta dos64_uci_command+9
 sta seen
 lda r_base+2
 sta dos64_uci_command+4
 lda #$a0
 sta dos64_uci_command+7
 lda #5
 sta dos64_uci_command+8
 lda #10
 sta dos64_uci_command_len
 lda #0
 sta dos64_uci_command_len+1
 sta dos64_uci_data_capacity+1
 sta dos64_uci_status_capacity+1
 lda #64
 sta dos64_uci_data_capacity
 lda #80
 sta dos64_uci_status_capacity
 lda #1
 sta raw
 sta waiting
 lda #4
 sta phase
 jsr copy_now
 jsr dos64_uci_start
 jcs file_failure
 rts
raw_poll:
 lda dos64_uci_state
 cmp #5
 beq @reply
 cmp #9
 jeq @complete
 cmp #10
 jeq file_failure
 rts
@reply:
 lda seen
 jne file_failure
 inc seen
 lda dos64_uci_flags
 ora dos64_uci_data_len+1
 ora dos64_uci_status_len+1
 jne file_failure
 lda dos64_uci_last_status
 and #$10
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
 lda dos64_uci_data_len
 cmp #35
 jne file_failure
 ldx #28
: lda dos64_uci_data,x
 cmp load_prefix,x
 jne file_failure
 dex
 bpl :-
 lda r_base+2
 lsr
 lsr
 lsr
 lsr
 tax
 lda digits,x
 cmp dos64_uci_data+29
 jne file_failure
 lda r_base+2
 and #15
 tax
 lda digits,x
 cmp dos64_uci_data+30
 jne file_failure
 ldx #3
: lda dos64_uci_data+31,x
 cmp #'0'
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
 sta waiting
 lda #5
 sta phase
 rts
; Two different initialized FETCH buffers prevent suppressed/partial DMA from
; self-verifying. Both buffers remain outside this phase's complete code/BSS.
fetch:
 ldx #0
: lda #$a5
 sta $b800,x
 lda #$5a
 sta $b900,x
 inx
 bne :-
 lda #0
 sta dos64_reu_request
 lda #$b8
 sta dos64_reu_request+1
 lda offset
 sta dos64_reu_request+2
 lda offset+1
 sta dos64_reu_request+3
 clc
 lda offset+2
 adc r_base+2
 sta dos64_reu_request+4
 lda #0
 sta dos64_reu_request+5
 lda #1
 sta dos64_reu_request+6
 sta dos64_reu_request+7
 jsr dos64_reu_transfer
 bcs @bad
 lda #$b9
 sta dos64_reu_request+1
 jsr dos64_reu_transfer
 bcs @bad
 ldx #0
: lda $b800,x
 cmp $b900,x
 bne @bad
 inx
 bne :-
 clc
 rts
@bad: sec
 rts
hash_page:
 jsr fetch
 jcs dma_failure
 lda offset+1
 ora offset+2
 bne @crc_page
 ldx #11
@geometry:
 ldy iw_bpb_offsets,x
 lda $b800,y
 cmp iw_bpb_values,x
 jne geometry_failure
 dex
 bpl @geometry
@crc_page:
 ldy #0
@byte:
 lda $b800,y
 eor r_crc
 sta r_crc
 ldx #8
@bit:
 lsr r_crc+3
 ror r_crc+2
 ror r_crc+1
 ror r_crc
 bcc @skip
 lda r_crc
 eor #$20
 sta r_crc
 lda r_crc+1
 eor #$83
 sta r_crc+1
 lda r_crc+2
 eor #$b8
 sta r_crc+2
 lda r_crc+3
 eor #$ed
 sta r_crc+3
@skip:
 dex
 bne @bit
 iny
 bne @byte
 jsr advance
 bcc @return
 ldx #3
: lda r_crc,x
 eor #$ff
 sta r_crc,x
 dex
 bpl :-
 lda #6
 sta phase
 jmp eof_read
@return: rts
compare_page:
 lda dos64_files_count_known
 cmp #1
 jne file_failure
 lda dos64_files_actual
 jne size_failure
 lda dos64_files_actual+1
 cmp #1
 jne size_failure
 jsr fetch
 jcs dma_failure
 ldx #0
: lda dos64_uci_data,x
 cmp $b800,x
 jne size_failure
 inx
 bne :-
 jsr advance
 jcc read_next
 lda #11
 sta phase
eof_read:
 lda #1
 sta dos64_files_count
 lda #0
 sta dos64_files_count+1
 lda #4
 jsr start_file
 jcs file_failure
 rts
advance:
 inc offset+1
 bne :+
 inc offset+2
: lda offset+2
 cmp #5
 bcc @more
 lda offset+1
 cmp #$a0
 bcc @more
 sec
 rts
@more: clc
 rts
eof_done:
 lda dos64_files_count_known
 cmp #1
 jne file_failure
 lda dos64_files_actual
 ora dos64_files_actual+1
 jne size_failure
 lda dos64_files_short
 cmp #1
 jne file_failure
 inc phase
 lda #3
 jsr start_file
 jcs file_failure
 rts
geometry_failure:
 lda #9
 jsr latch
 jmp cleanup
size_failure:
 lda #5
 jsr latch
 jmp cleanup
dma_failure:
 lda #6
 jsr fatal_latch
 jmp cleanup
file_failure:
 lda #4
 jsr latch
 jmp cleanup
cleanup:
 lda waiting
 beq @quiet
 inc drain
 jeq blocked
 lda dos64_uci_state
 cmp #9
 beq @terminal
 cmp #10
 beq @terminal
 ; A safety CLOSE is already the one cleanup attempt. Let its actual
 ; handshake finish; an earlier latched cause must not abort that CLOSE.
 lda dos64_files_op
 cmp #3
 jeq done
 lda aborted
 jne done
 inc aborted
 jsr copy_now
 jsr dos64_uci_abort
 jmp done
@terminal:
 lda dos64_files_state
 cmp #1
 beq @check_raw
 jmp @clear
@check_raw:
 lda raw
 jeq done
@clear:
 lda #0
 sta waiting
 sta raw
@quiet:
 jsr quiet
 jcs blocked
 lda dos64_files_handle
 jeq finish
 lda dos64_files_op
 cmp #3
 jeq blocked
 lda cleanup_close
 jne blocked
 inc cleanup_close
 lda #31
 sta phase
 lda #3
 jsr start_file
 jcs blocked
 rts
finish:
 lda dos64_files_handle
 jne blocked
 jsr quiet
 jcs blocked
 jsr ownership
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
 jsr ownership
 jcs blocked
 lda fatal
 beq :+
 lda #$e1
 sta dos64_native_diag
: lda #3
 ldx error
 bne @state
 jsr lease
 bcs @lost
 lda #$a5
 sta ready
 lda #2
@state:
 sta state
 jmp done
@lost:
 lda #7
 jsr fatal_latch
blocked:
 lda #0
 sta ready
 lda #$e1
 sta dos64_native_diag
 lda #3
 sta state
 jmp done
take:
 lda ready
 cmp #$a5
 bne @bad
 lda state
 cmp #2
 bne @bad
 lda error
 ora context
 bne @bad
 lda closed
 cmp #1
 bne @bad
 jsr broker_native_owner
 bcs @lost
 jsr ownership
 bcs @lost
 jsr lease
 bcs @lost
 jsr clock
 bcs @clock
 jsr stop
 bcs @cancel
 lda #0
 sta ready
 lda #<receipt
 ldx #>receipt
 rts
@lost: lda #7
 bne @fatal
@clock: lda #2
 bne @fatal
@cancel:
 lda #3
 jsr latch
 lda #0
 sta ready
 lda #3
 sta state
 jmp @bad
@fatal:
 jsr fatal_latch
 jsr blocked
@bad: lda #0
 tax
 rts
.segment "RODATA"
ok:.byte "00,OK"
load_prefix:.byte "$ 5a000 BYTES LOADED TO REU $"
.assert *-load_prefix=29,error,"LOADprefix length"
digits:.byte "0123456789abcdef"
.include "geometry.inc"
.import __BSS_RUN__,__BSS_SIZE__
.assert __BSS_RUN__=$7d00,lderror,"incoming state placement"
.assert __BSS_RUN__+__BSS_SIZE__<=$7e80,lderror,"incoming state overlaps savedhigh96"
