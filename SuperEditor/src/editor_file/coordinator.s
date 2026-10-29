.setcpu "6502"
.macpack longbranch
.include "editor_file/api.inc"
.include "fileio/api.inc"
.include "fileio/save.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "object/api.inc"
.include "history/api.inc"
.export se_file_begin,se_file_step,se_file_cancel
.export f_request,f_done,f_fail,f_names,f_target,f_temp_name,f_backup_name
.import f_open_step,f_save_begin,f_save_step,f_release_candidates,f_restore
.segment "CODE"
; Caller flushes pending edits, ends transactions, invalidates index/render, acquires
; owner=1 and initializes union requests before entry. Failure does not clear owner:
; resident releases it only after request=0, phase=0 and channels/capabilities safe.
se_file_begin:
    lda se_f_owner
    cmp #1
    jne bad
    lda se_f_phase
    ora se_f_request
    ora se_io_mode
    ora se_io_owned_temp
    ora se_io_owned_backup
    jne busy
    lda se_f_operation
    cmp #F_OPEN
    jcc bad
    cmp #F_SAVEAS+1
    jcs bad
    lda se_doc_busy
    ora se_doc_read_locks
    jne busy
    jsr se_h_validate
    jcs return
    lda se_doc_epoch
    sta se_f_epoch
    lda se_doc_epoch+1
    sta se_f_epoch+1
    lda #0
    sta se_sv_phase
    sta se_f_error
    sta se_f_raw_error
    sta se_f_dos_error
    sta se_f_cancel
    sta se_f_committed
    sta se_f_allocated
    sta se_f_lease
    sta se_f_request
    sta se_f_position
    sta se_f_position+1
    sta se_f_position+2
    sta se_io_done
    sta se_io_done+1
    sta se_f_verify_target
    sta se_f_preflight_phase
    lda #1
    sta se_f_phase
    lda #FT_INIT
    jmp f_request
bad:
    lda #FIO_ARGUMENT
    sec
return:
    rts
busy:
    lda #FIO_BUSY
    sec
    rts
se_file_cancel:
    lda #1
    sta se_f_cancel
    jmp se_file_step
se_file_step:
    lda se_f_phase
    jeq f_done
    lda se_f_request
    jne pending ; outstanding action must be consumed once, by resident
    lda se_f_phase
    cmp #$F0
    jeq cleanup
    ; An acknowledged H_INIT is the publication boundary. Cancellation after
    ; this point must never restore canonical roots against new history context.
    lda se_f_operation
    cmp #F_OPEN
    beq @open_boundary
    lda se_f_phase
    cmp #38 ; acknowledged H_SAVED is a completed save, even if STOP follows
    bne @cancel_check
    lda se_f_carry
    bne @cancel_check
    jsr f_names
    jmp f_save_step
@open_boundary:
    lda se_f_phase
    cmp #6
    bne @cancel_check
    lda se_f_carry
    bne @cancel_check
    jsr f_names
    jmp f_open_step
@cancel_check:
    lda se_f_cancel
    beq :+
    lda se_f_committed
    bne :+
    lda #0
    jmp f_fail
:   lda se_f_carry
    beq :+
    lda se_f_result
    jmp f_fail
:   jsr f_names
    lda se_f_phase
    cmp #1
    bne @active
    lda se_f_operation
    cmp #F_OPEN
    bne @save
    lda #2
    sta se_f_phase
    lda #FT_PREFLIGHT_BEGIN
    jmp f_request
@save:
    jmp f_save_begin
@active:
    lda se_f_operation
    cmp #F_OPEN
    jeq f_open_step
    jmp f_save_step
pending:
    lda #1
    clc
    rts
f_request:
    sta se_f_request
    lda #1
    clc
    rts
f_names:
    lda se_f_device
    sta se_io_device
f_target:
    ldx #15
@copy:
    lda se_f_name,x
    sta se_io_name,x
    dex
    bpl @copy
    lda se_f_name_len
    sta se_io_name_len
    rts
f_temp_name:
    ldx #15
@copy:
    lda se_f_temp,x
    sta se_io_name,x
    dex
    bpl @copy
    lda #16
    sta se_io_name_len
    rts
f_backup_name:
    ldx #15
@copy:
    lda se_f_backup_name,x
    sta se_io_other,x
    dex
    bpl @copy
    lda #16
    sta se_io_other_len
    rts
f_fail:
    sta se_f_error
    lda se_io_raw_status
    sta se_f_raw_error
    lda se_io_dos_code
    sta se_f_dos_error
    ; Recovery after a rename is handled by save policy, never blind deletion.
    lda se_f_operation
    cmp #F_OPEN
    beq @open
    lda se_f_error
    jmp f_save_failure
@open:
    lda se_f_committed
    cmp #1
    bne :+
    jsr f_restore
:   lda #$F0
    sta se_f_phase
    lda se_f_preflight_phase
    beq :+
    lda #FT_PREFLIGHT_CANCEL
    jmp f_request
:   lda #FT_ABORT
    jmp f_request
cleanup:
    lda se_f_preflight_phase
    beq :+
    lda #FT_PREFLIGHT_CANCEL
    jmp f_request
:   jsr f_release_candidates
    lda se_f_lease
    beq :+
    jsr se_doc_read_release
    lda #0
    sta se_f_lease
:   lda #0
    sta se_f_phase
    lda se_f_error
    jeq f_done
    sec
    rts
f_done:
    lda #0
    clc
    rts
.import f_save_failure
