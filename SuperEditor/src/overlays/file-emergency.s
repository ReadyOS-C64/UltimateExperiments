.setcpu "6502"
.macpack longbranch
.include "editor_file/api.inc"
.include "fileio/api.inc"
.include "document/api.inc"
.include "object/api.inc"
.include "history/api.inc"
.import se_fd_task,se_fd_command
.export se_file_emergency
.segment "CODE"
; AUX-private file-abort operation. Caller owns C slot and returned from failed C12
; admission. No C calls, DOS commands, filename guesses or disk writes here.
; Active frame returns9B/carry; owner/capabilities remain for explicit recovery.
; Owner0 is a no-op. A stale epoch only closes owned channels, never source state.
se_file_emergency:
    lda se_f_owner
    jeq done
    cmp #1
    jne recovery
    jsr $FFCC
    lda se_io_mode
    beq @raw
    cmp #4
    jcs recovery
    lda #FIO_DATA_LFN
    jsr $FFC3
    lda #0
    sta se_io_mode
@raw:
    lda se_f_preflight_phase
    beq @context
    cmp #4
    jcs recovery
    lda #7
    jsr $FFC3
    lda #0
    sta se_f_preflight_phase
@context:
    jsr se_doc_validate
    jcs recovery
    lda se_doc_epoch
    cmp se_f_epoch
    jne recovery
    lda se_doc_epoch+1
    cmp se_f_epoch+1
    jne recovery
    lda se_f_operation
    cmp #F_OPEN
    beq open
    cmp #F_SAVE
    beq lease
    cmp #F_SAVEAS
    jne recovery
lease:
    lda se_f_phase
    cmp #38 ;H_SAVED was requested only after final target verification
    bne @release
    lda se_f_request
    ora se_f_carry
    bne @release ;pending or refused savepoint keeps the previous association
    jsr se_h_context
    jcs recovery
    ldx #3
@saved:
    lda se_h_saved,x
    cmp se_f_history,x
    jne recovery
    dex
    bpl @saved
    jsr bind_name
@release:
    lda se_f_lease
    jeq finish
    cmp #1
    jne recovery
    jsr se_doc_read_release
    jcs recovery
    lda #0
    sta se_f_lease
    jeq finish
open:
    lda se_f_committed
    jeq candidates
    cmp #2
    jeq candidates ;any queue now contains only retired old objects
    cmp #1
    jne recovery
    lda se_f_phase
    cmp #6
    jne recovery
    lda se_f_request
    cmp #FA_HISTORY_INIT
    jeq restore ; not consumed, so H_INIT did not run
    cmp #0
    jne recovery
    lda se_f_carry
    cmp #1
    jeq restore ; definite failed H_INIT, old history still installed
    cmp #0
    jne recovery
    ; Acknowledged H_INIT has installed the new history context. Preserve it.
    jsr se_h_context
    jcs recovery
    lda #2
    sta se_f_committed
    jsr bind_name
    ; Convert the queue before any fallible operation after publication.
    ldx #9
@retire:
    lda se_f_old,x
    sta se_f_candidate,x
    dex
    bpl @retire
    lda #2
    sta se_f_allocated
    DOC_TOKEN se_doc_append
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    sta se_object_offset+2
    jsr se_object_resize
    jcs recovery
    jmp candidates
restore:
    lda se_f_backup+278
    cmp se_f_epoch
    jne recovery
    lda se_f_backup+279
    cmp se_f_epoch+1
    jne recovery
    ldx #0
@roots:
    lda se_f_backup,x
    sta se_doc_roots,x
    inx
    bne @roots
    ldx #21
@canonical:
    lda se_f_backup+256,x
    sta se_doc_ready,x
    dex
    bpl @canonical
    lda #0
    sta se_f_committed
    jsr se_doc_invalidate
candidates:
    lda se_f_allocated
    jeq finish
    cmp #3
    jcs recovery
    sec
    sbc #1
    sta se_f_compare
    asl
    asl
    clc
    adc se_f_compare
    tax
    ldy #0
@token:
    lda se_f_candidate,x
    sta se_object_id,y
    inx
    iny
    cpy #5
    bcc @token
    jsr se_object_release
    jcs recovery ; failed token remains queued, never erase its ownership
    dec se_f_allocated
    jmp candidates
finish:
    lda #0
    sta se_f_phase
    sta se_f_request
    sta se_fd_task
    sta se_fd_command
recovery:
    lda #F_RECOVERY
    sta se_f_error
    sec
    rts
done:
    lda #0
    clc
    rts
bind_name:
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
    rts

.include "editor/api.inc"
.include "nav/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.export se_file_recovery_key
; AUX op4: recovery remains usable even when C12 cannot be admitted. K explicitly
; leaves retained temp/backup on disk; STOP requires no remaining DOS capabilities.
; No DOS or C calls. A0stay/redraw, A2closed; carry/9B means source not safe to close.
se_file_recovery_key:
    lda se_e_key
    cmp #$8B ;F6 remains available even for an old-epoch frame
    beq @help
    cmp #3
    beq @close
    and #$7F
    cmp #$4B
    beq @close
    cmp #$6B
    bne @stay
@close:
    lda se_f_owner
    cmp #1
    jne recovery
    jsr se_doc_validate
    jcs recovery
    lda se_doc_epoch
    cmp se_f_epoch
    jne recovery
    lda se_doc_epoch+1
    cmp se_f_epoch+1
    jne recovery
    lda se_f_phase
    ora se_f_request
    ora se_f_preflight_phase
    ora se_io_mode
    ora se_f_allocated
    ora se_f_lease
    jne recovery
    lda se_e_key
    cmp #3
    bne @keep
    lda se_io_owned_temp
    ora se_io_owned_backup
    jne recovery
@keep:
    lda #0
    sta se_io_owned_temp
    sta se_io_owned_backup
    sta se_f_error
    sta se_f_owner
    sta se_e_ui
    sta se_i_ready
    sta se_i_count
    sta se_n_cache_count
    sta se_l_valid
    sta se_r_valid
    lda #2
    clc
    rts
@help:
    lda se_f_ui_help
    eor #1
    sta se_f_ui_help
@stay:
    lda #0
    clc
    rts
