.setcpu "6502"
.macpack longbranch
.include "editor_file/api.inc"
.include "fileio/api.inc"
.include "editor/api.inc"
.include "hot/api.inc"
.include "history/api.inc"
.include "document/api.inc"
.include "nav/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.import se_overlay_frame
.import se_fd_confirm,se_fd_list_count,se_fd_list_index,se_fd_list_names
.import se_fd_list_lengths,se_fd_page,se_fd_list_error,se_fd_resume
.import se_fd_open_name,se_fd_open_len,se_fd_open_device,se_fd_task,se_fd_skip
.import se_fd_index,se_fd_command
.import f_request
.export se_file_dialog,se_file_dialog_key,se_file_dialog_step,se_file_dialog_finish,se_file_dialog_cancel
.segment "CODE"
; Resident first flushes pending input and ends every other operation. Saved
; command byte is outside union until clearing finishes (stack, not overlay ptr).
se_file_dialog:
    lda se_f_owner
    ora se_doc_busy
    ora se_doc_read_locks
    ora se_hot_pending
    ora se_hot_phase
    jne busy
    jsr se_doc_validate
    bcs @invalid
    lda se_overlay_frame+1
    sec
    sbc #E_OPEN-1
    cmp #4
    jcs argument
    cmp #1
    jcc argument
    pha
    lda #1
    sta se_f_owner
    jsr invalidate
    lda #0
    ldx #0
@clear:
    sta $8D00,x
    sta $8E00,x
    sta $8F00,x
    sta $9000,x
    inx
    bne @clear
    ldx #127
@last:
    sta $9100,x
    dex
    bpl @last
    lda se_doc_epoch
    sta se_f_epoch
    lda se_doc_epoch+1
    sta se_f_epoch+1
    pla
    sta se_f_operation
    jsr current_name
    lda #3
    sta se_e_ui
    lda se_f_operation
    cmp #F_SAVE
    bne refresh
    lda se_f_name_len
    beq refresh
    jmp start
@invalid:
    rts
start:
    lda #0
    sta se_fd_confirm
    jsr se_file_begin
    bcs @return
    lda #1
    sta se_fd_command ; running operation, distinct from a directory job
@return:
    rts
current_name:
    ldx #15
@name:
    lda se_f_current_name,x
    sta se_f_name,x
    dex
    bpl @name
    lda se_f_current_len
    sta se_f_name_len
    lda se_f_current_device
    cmp #8
    beq :+
    cmp #9
    beq :+
    lda #8
:   sta se_f_device
    rts
refresh:
    lda #0
    sta se_fd_list_count
    sta se_fd_list_index
    sta se_fd_list_error
    sta se_f_error
    lda se_fd_page
    sta se_fd_skip
    lda se_fd_page+1
    sta se_fd_skip+1
    ldx #3
@times8:
    asl se_fd_skip
    rol se_fd_skip+1
    dex
    bne @times8
    lda se_f_device
    sta se_io_device
    lda #1
    sta se_fd_task
    lda #FT_DIRECTORY
    jmp f_request
se_file_dialog_step:
    lda se_fd_task
    jeq se_file_step
    lda se_f_request
    jne pending
    lda se_fd_index ; deferredcancel: consume outstanding action before CLOSE
    beq :+
    lda se_fd_task
    cmp #3
    jne close_directory
:   lda se_f_carry
    beq @success
    lda se_f_result
    cmp #FIO_LIMIT
    bne @error
    lda se_io_mode
    cmp #3
    beq next_entry ; provider's32-line slice is resumable only whilemode3
@error:
    lda se_f_result
    sta se_fd_list_error
    jmp close_directory
@success:
    lda se_fd_task
    cmp #3
    jeq modal
    cmp #1
    beq next_entry
    lda se_io_dir_len
    beq close_directory
    lda se_fd_skip
    ora se_fd_skip+1
    beq @record
    lda se_fd_skip
    bne :+
    dec se_fd_skip+1
:   dec se_fd_skip
    jmp next_entry
@record:
    ldx se_fd_list_count
    lda se_io_dir_len
    sta se_fd_list_lengths,x
    txa
    asl
    asl
    asl
    asl
    tax
    ldy #0
@copy:
    lda se_io_dir_name,y
    sta se_fd_list_names,x
    inx
    iny
    cpy #16
    bcc @copy
    inc se_fd_list_count
    lda se_fd_list_count
    cmp #8
    beq close_directory
next_entry:
    lda #2
    sta se_fd_task
    lda #FT_NEXT
    jmp f_request
close_directory:
    lda #3
    sta se_fd_task
    lda #FT_ABORT
    jmp f_request
modal:
    lda #0
    sta se_fd_task
    clc
    rts
pending:
    lda #1
    clc
    rts
se_file_dialog_key:
    lda se_fd_task
    ora se_f_phase
    ora se_f_request
    jne busy
    ; Preserve all ownership in recovery. Never turn STOP into implicit scratch.
    lda se_io_owned_temp
    ora se_io_owned_backup
    jne recovery
    lda se_e_key
    cmp #$8B
    jeq se_file_ui_key
    cmp #3
    jeq cancel
    lda se_fd_confirm
    beq ordinary
    lda se_e_key
    and #$7F
    cmp #$43
    jeq cancel
    cmp #$63
    jeq cancel
    cmp #$44
    jeq start
    cmp #$64
    jeq start
    cmp #$53
    beq save_first
    cmp #$73
    beq save_first
    jmp ready
save_first:
    ldx #15
@save_open:
    lda se_f_name,x
    sta se_fd_open_name,x
    dex
    bpl @save_open
    lda se_f_name_len
    sta se_fd_open_len
    lda se_f_device
    sta se_fd_open_device
    lda #1
    sta se_fd_resume
    lda #F_SAVE
    sta se_f_operation
    jsr current_name
    lda se_f_name_len
    jne start
    lda #F_SAVEAS
    sta se_f_operation
    lda #0
    sta se_fd_confirm
    sta se_fd_page
    sta se_fd_page+1
    jmp refresh
ordinary:
    lda se_e_key
    cmp #$87 ;F5 nextpage
    beq page
    cmp #$11
    beq down
    cmp #$91
    beq up
    cmp #$86 ;F3 device
    beq device
    jsr se_file_ui_key
    jcs dialog_return
    cmp #1
    bne ready
    lda se_f_operation
    cmp #F_OPEN
    bne accepted
    lda se_h_dirty
    beq accepted
    lda #1
    sta se_fd_confirm
ready:
    lda #0
    clc
dialog_return:
    rts
accepted:
    jmp start
device:
    jsr se_file_ui_key
    lda #0
    sta se_fd_page
    sta se_fd_page+1
    jmp refresh
page:
    inc se_fd_page
    bne :+
    inc se_fd_page+1
:   jmp refresh
down:
    lda se_fd_list_count
    beq ready
    lda se_fd_list_index
    clc
    adc #1
    cmp se_fd_list_count
    bcs ready
    sta se_fd_list_index
    jmp choose
up:
    lda se_fd_list_index
    beq choose
    dec se_fd_list_index
choose:
    ldx se_fd_list_index
    lda se_fd_list_lengths,x
    sta se_f_name_len
    txa
    asl
    asl
    asl
    asl
    tax
    ldy #0
@copy:
    lda se_fd_list_names,x
    sta se_f_name,y
    inx
    iny
    cpy #16
    bcc @copy
    jmp ready
se_file_dialog_finish:
    lda se_f_phase
    ora se_f_request
    ora se_fd_task
    jne pending
    lda se_io_mode
    ora se_f_preflight_phase
    ora se_io_owned_temp
    ora se_io_owned_backup
    jne recovery
    lda se_fd_index
    jne cancel
    lda se_fd_command
    jeq ready ; directory completion leaves filename modal open
    lda #0
    sta se_fd_command
    lda se_f_error
    jne ready ; error remains modal for correction/retry/cancel
    lda se_fd_resume
    beq release
    lda #0
    sta se_fd_resume
    ldx #15
@restore_open:
    lda se_fd_open_name,x
    sta se_f_name,x
    dex
    bpl @restore_open
    lda se_fd_open_len
    sta se_f_name_len
    lda se_fd_open_device
    sta se_f_device
    lda #F_OPEN
    sta se_f_operation
    jmp start
se_file_dialog_cancel:
    lda #1
    sta se_fd_index
    lda se_fd_task
    jne pending
    jmp se_file_cancel
cancel:
    lda #0
    sta se_fd_resume
    jsr release
    lda #2
    clc
    rts
release:
    jsr invalidate
    lda #0
    sta se_e_ui
    sta se_f_owner
    clc
    rts
invalidate:
    lda #0
    sta se_i_ready
    sta se_i_count
    sta se_n_cache_count
    sta se_l_valid
    sta se_r_valid
    rts
busy:
    lda #FIO_BUSY
    sec
    rts
argument:
    lda #FIO_ARGUMENT
    sec
    rts
recovery:
    lda #F_RECOVERY
    sec
    rts
