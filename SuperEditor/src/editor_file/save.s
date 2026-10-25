.setcpu "6502"
.macpack longbranch
.include "editor_file/api.inc"
.include "fileio/api.inc"
.include "fileio/save.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "history/api.inc"
.import f_request,f_done,f_fail,f_target,f_temp_name,f_backup_name
.export f_save_begin,f_save_step,f_save_failure
.segment "CODE"
f_save_begin:
    jsr se_doc_read_acquire
    jcs f_fail
    lda #1
    sta se_f_lease
    lda #0
    sta se_f_nonce
    sta se_sv_phase
    sta se_f_target_exists
    COPY24 se_doc_length,se_f_length
    ldx #3
@node:
    lda se_h_current,x
    sta se_f_history,x
    dex
    bpl @node
    lda se_doc_generation
    sta se_f_generation
    lda se_doc_generation+1
    sta se_f_generation+1
    ; Private16-byte native names. Collision refuses safely; never scratch byprefix.
    ldx #15
@names:
    lda temp_name,x
    sta se_f_temp,x
    lda backup_name,x
    sta se_f_backup_name,x
    dex
    bpl @names
    lda #20
    sta se_f_phase
    lda #FT_PREFLIGHT_BEGIN
    jmp f_request
f_save_step:
    lda se_f_phase
    cmp #20
    jeq existing
    cmp #30
    jeq dispatch
    cmp #31
    jeq acknowledged
    cmp #32
    jeq write_ack
    cmp #33
    jeq preflight
    cmp #34
    jeq opened
    cmp #35
    jeq read_ack
    cmp #36
    jeq compare
    cmp #37
    jeq verified_close
    cmp #38
    jeq saved
    cmp #39
    jeq recovery_done
    cmp #40
    jeq preflight_failed
    cmp #41
    jeq candidate_exists
    lda #FIO_STATE
    jmp f_fail
existing:
    lda se_f_result
    bne @next
    lda #1
    sta se_f_target_exists
    jmp start_policy
@next:
    lda #FT_PREFLIGHT_STEP
    jmp f_request
start_policy:
    lda se_f_target_exists
    jsr se_sv_begin
    jcs f_fail
next_action:
    lda #30
    sta se_f_phase
dispatch:
    lda se_sv_phase
    cmp #SV_CREATE
    jeq create
    cmp #SV_WRITE
    jeq write
    cmp #SV_CLOSE
    jeq close_write
    cmp #SV_OPEN_VERIFY
    jeq verify_begin
    cmp #SV_COMPARE
    jeq next_read
    cmp #SV_CLOSE_VERIFY
    jeq close_verify
    cmp #SV_BACKUP
    jeq backup
    cmp #SV_PROMOTE
    jeq promote
    cmp #SV_CHECK_TARGET
    jeq verify_target
    cmp #SV_DELETE_BACKUP
    jeq delete_backup
    cmp #SV_DONE
    jeq done
    cmp #SV_ABORT_CLOSE
    jeq abort_close
    cmp #SV_DELETE_TEMP
    jeq delete_temp
    cmp #SV_ROLLBACK
    jeq rollback
    cmp #SV_RECOVERY
    jeq recovery
    lda #FIO_STATE
    jmp f_fail
create:
    jsr f_temp_name
    lda #41
    sta se_f_phase
    lda #FT_EXISTS_BEGIN
    jmp f_request
candidate_exists:
    jsr f_temp_name
    lda se_f_result
    beq @occupied
    lda #FT_PREFLIGHT_STEP
    jmp f_request
@occupied:
    ; Even an unclosed SEQ is foreign: DOS W-open could replace it silently.
    lda #63
    sta se_io_dos_code
    lda #FIO_DOS
    jmp f_fail
create_absent:
    jsr f_temp_name
    lda #FT_CREATE
    jmp generic
write:
    CMP24 se_f_position,se_f_length
    jeq policy_ok
    jsr source_packet
    jcs f_fail
    lda se_doc_read_done
    sta se_io_count
    lda #32
    sta se_f_phase
    lda #FT_WRITE
    jmp f_request
write_ack:
    jmp next_action
close_write:
    lda se_f_length
    ora se_f_length+1
    ora se_f_length+2
    beq @empty
    lda #FT_CLOSE
    jne generic
@empty:
    lda #FT_EMPTY_CLOSE
    jne generic
verify_target:
    lda #1
    sta se_f_verify_target
verify_begin:
    lda #0
    sta se_f_position
    sta se_f_position+1
    sta se_f_position+2
    lda se_f_verify_target
    bne :+
    jsr f_temp_name
:   lda #33
    sta se_f_phase
    lda #FT_PREFLIGHT_BEGIN
    jmp f_request
preflight:
    lda se_f_verify_target
    bne :+
    jsr f_temp_name
:   lda se_f_result
    beq @open
    lda #FT_PREFLIGHT_STEP
    jmp f_request
@open:
    CMP24 se_f_preflight_length,se_f_length
    jne mismatch
    lda #34
    sta se_f_phase
    lda #FT_OPEN
    jmp f_request
opened:
    lda se_f_verify_target
    jne next_read
    jmp policy_ok ; OPEN_VERIFY becomes COMPARE
next_read:
    lda #0
    sta se_io_count
    lda #35
    sta se_f_phase
    lda #FT_READ
    jmp f_request
read_ack:
    lda se_io_done
    sta se_f_packet
    sta se_f_left
    lda se_io_done+1
    sta se_f_packet+1
    sta se_f_left+1
    lda #0
    sta se_f_compare
    ldx #0
@copy:
    lda $8000,x
    sta $8100,x
    inx
    bne @copy
    lda #36
    sta se_f_phase
compare:
    lda se_f_left
    ora se_f_left+1
    beq compared
    ; Bound the request to bytes already received. Reader may complete<requested.
    COPY24 se_f_position,se_doc_offset
    lda se_f_left
    sta se_doc_count
    lda se_f_left+1
    sta se_doc_count+1
    lda #0
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    jsr se_doc_read_some
    jcs f_fail
    lda se_doc_read_done
    ora se_doc_read_done+1
    jeq mismatch
    ldx #0
@bytes:
    stx se_f_work
    ldy se_f_compare
    lda $8000,x
    cmp $8100,y
    jne mismatch
    inc se_f_compare
    ldx se_f_work
    inx
    cpx se_doc_read_done
    bne @bytes
    ; done=256 means low0; loop wraps naturally after256.
    jsr advance_source
    sec
    lda se_f_left
    sbc se_doc_read_done
    sta se_f_left
    lda se_f_left+1
    sbc se_doc_read_done+1
    sta se_f_left+1
    lda #1
    clc
    rts
compared:
    CMP24 se_f_position,se_f_length
    jcc @not_end
    jne mismatch
    lda se_io_eof
    jeq mismatch ; exact length with noEOI means a growing/different file
    lda se_f_verify_target
    bne close_target
    lda #SV_MATCH
    jmp policy_event
@not_end:
    lda se_io_eof
    jne mismatch
    jmp next_read
close_target:
    lda #37
    sta se_f_phase
    lda #FT_CLOSE
    jmp f_request
verified_close:
    jmp policy_ok
close_verify:
    lda #FT_CLOSE
    jne generic
backup:
    jsr f_backup_name
    lda #FT_BACKUP
    jne generic
promote:
    ; source=temp, destination=target; provider consumes exact tempcapability.
    ldx #15
@dest:
    lda se_f_name,x
    sta se_io_other,x
    dex
    bpl @dest
    lda se_f_name_len
    sta se_io_other_len
    jsr f_temp_name
    lda #FT_RENAME
    jne generic
rollback:
    ldx #15
@rollback:
    lda se_f_backup_name,x
    sta se_io_name,x
    lda se_f_name,x
    sta se_io_other,x
    dex
    bpl @rollback
    lda #16
    sta se_io_name_len
    lda se_f_name_len
    sta se_io_other_len
    lda #FT_RENAME
    jne generic
delete_backup:
    lda #FT_SCRATCH_BACKUP
    jne generic
delete_temp:
    lda #FT_SCRATCH_TEMP
    jne generic
abort_close:
    lda #FT_ABORT
generic:
    ldx #31
    stx se_f_phase
    jmp f_request
acknowledged:
policy_ok:
    lda #SV_OK
policy_event:
    jsr se_sv_step
    jcs f_fail
    jmp next_action
mismatch:
    lda #F_CHANGED
    jmp f_fail
source_packet:
    COPY24 se_f_position,se_doc_offset
    SUB24 se_f_length,se_f_position,se_f_work
    lda se_f_work+2
    ora se_f_work+1
    bne @full
    lda se_f_work
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    beq @read
@full:
    lda #0
    sta se_doc_count
    lda #1
    sta se_doc_count+1
@read:
    lda #0
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    jsr se_doc_read_some
    bcs @return
    lda se_doc_read_done
    ora se_doc_read_done+1
    beq @changed
    jsr advance_source
    lda #0
    clc
@return:
    rts
@changed:
    lda #F_CHANGED
    sec
    rts
advance_source:
    clc
    lda se_f_position
    adc se_doc_read_done
    sta se_f_position
    lda se_f_position+1
    adc se_doc_read_done+1
    sta se_f_position+1
    lda se_f_position+2
    adc #0
    sta se_f_position+2
    rts
f_save_failure:
    ; Only a definite missing result may authorize a new target/temp action.
    ; STOP and unrelated errors must not reuse a stale DOS62 diagnostic.
    cmp #FIO_DOS
    bne @failure
    ldx se_f_cancel
    bne @failure
    ldx se_f_carry
    beq @failure
    ldx se_io_dos_code
    cpx #62
    bne @failure
    ldx se_f_phase
    cpx #20
    beq @original_missing
    cpx #41
    bne @failure
    lda #0
    sta se_f_error
    jmp create_absent
@original_missing:
    lda #0
    sta se_f_error
    jmp start_policy
@failure:
    ; Cancel after a successfully acknowledged mutating action must first
    ; advance that action's policy state (CREATE has already granted ownership).
    pha
    lda se_f_cancel
    beq @store_failure
    lda se_f_phase
    cmp #31
    bne @store_failure
    lda se_f_carry
    bne @store_failure
    lda #SV_OK
    jsr se_sv_step
@store_failure:
    pla
    sta se_f_error
    lda #0
    sta se_f_cancel
    lda se_f_preflight_phase
    beq @policy
    lda #40
    sta se_f_phase
    lda #FT_PREFLIGHT_CANCEL
    jmp f_request
@policy:
    lda se_sv_phase
    bne @has_policy
    lda se_f_error
    bne @no_policy
    lda #F_CANCELLED
    sta se_f_error
@no_policy:
    jmp finish
@has_policy:
    lda se_f_error
    beq @cancel
    cmp #FIO_IO
    beq @uncertain
    lda #SV_FAILED
    bne @event
@cancel:
    lda #F_CANCELLED
    sta se_f_error
    lda #SV_CANCEL
    beq @event
@uncertain:
    lda #SV_UNCERTAIN
@event:
    jsr se_sv_step
    jcs recovery
    jmp next_action
preflight_failed:
    lda se_f_error
    jmp f_save_failure
recovery:
    lda #F_RECOVERY
    sta se_f_error
    lda #39
    sta se_f_phase
    lda se_f_preflight_phase
    beq :+
    lda #FT_PREFLIGHT_CANCEL
    jmp f_request
:   lda #FT_ABORT
    jmp f_request
recovery_done:
    lda se_io_mode
    beq finish
    lda #FT_ABORT
    jmp f_request
done:
    lda se_f_error
    bne finish
    ; Snapshot identity must still match when savepoint is recorded.
    lda se_doc_generation
    cmp se_f_generation
    jne mismatch
    lda se_doc_generation+1
    cmp se_f_generation+1
    jne mismatch
    ldx #3
@node:
    lda se_h_current,x
    cmp se_f_history,x
    jne mismatch
    dex
    bpl @node
    lda #38
    sta se_f_phase
    lda #FA_HISTORY_SAVED
    jmp f_request
saved:
    ldx #15
@name:
    lda se_f_name,x
    sta se_f_current_name,x
    dex
    bpl @name
    lda se_f_name_len
    sta se_f_current_len
    lda se_f_device
    sta se_f_current_device
finish:
    lda se_f_lease
    beq :+
    jsr se_doc_read_release
    lda #0
    sta se_f_lease
:   lda #0
    sta se_f_phase
    lda se_f_error
    beq @ok
    sec
    rts
@ok:
    clc
    rts
.segment "RODATA"
temp_name: .byte "SE~T000000000000"
backup_name: .byte "SE~B000000000000"
