.setcpu "6502"
.macpack longbranch
.include "block/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "history/api.inc"
.include "hot/api.inc"
.include "clipboard/api.inc"
.include "object/api.inc"
.import se_overlay_call,se_overlay_frame,se_index_changed
.segment "CODE"
se_block_begin:
    lda se_b_phase
    beq :+
    lda #$51
    sec
    rts ;refusing another begin must not cancel current operation
:
    lda #0
    sta se_b_changed
    sta se_b_error
    sta se_b_reveal
    sta se_b_history_owned
    sta se_b_clip_owned
    lda se_doc_epoch
    sta se_b_doc_epoch
    lda se_doc_epoch+1
    sta se_b_doc_epoch+1
    lda se_e_command
    sta se_b_command
    lda se_hot_byte
    sta se_b_byte
    lda #B_SETUP
    jsr invoke
    jcs failed
    clc
    rts
se_block_step:
    lda se_b_phase
    cmp #B_COPYING
    beq copy_step
    cmp #B_BEGIN_HISTORY
    beq history_begin
    cmp #B_HISTORY
    beq history_step
    lda #$51
    sec
    rts
copy_step:
    jsr se_clip_copy_step
    jcs failed
    lda se_clip_busy
    bne pending
    lda se_b_command
    cmp #E_COPY
    bne @cut
    lda #0
    sta se_b_phase
    clc
    rts
@cut:
    lda #B_AFTER_COPY
    jsr invoke
    jcs failed
    jmp pending
history_begin:
    lda #H_BEGIN
    jsr se_history_call
    jcs failed
    lda se_h_phase
    beq @empty
    lda #1
    sta se_b_history_owned
    lda #B_HISTORY
    sta se_b_phase
    jmp pending
@empty:
    jsr unlock_clip
    lda #0
    sta se_b_phase
    clc
    rts
history_step:
    lda se_h_phase
    beq committed
    cmp #H_FEEDING
    bne @advance
    lda se_b_left
    ora se_b_left+1
    ora se_b_left+2
    beq @advance
    lda #B_PACKET
    jsr invoke
    bcs failed
    lda #H_FEED
    bne @history
@advance:
    lda #H_STEP
@history:
    jsr se_history_call
    bcs failed
pending:
    lda #1
    clc
    rts
invoke:
    sta se_overlay_frame
    lda #BLOCK_ID
    ldx #1
    jmp se_overlay_call
committed:
    jsr publish
    jsr unlock_clip
    lda #0
    sta se_b_phase
    sta se_b_history_owned
    clc
    rts
; Publication already happened: invalidate stale hot data even on journal fault.
publish:
    jsr se_index_changed
    jsr se_selection_clear
    lda #0
    sta se_r_valid
    sta se_l_valid
    sta se_hot_ready
    sta se_hot_pending
    COPY24 se_h_caret,se_e_target
    lda #1
    sta se_b_changed
    sta se_b_reveal
    rts
failed:
    pha
    lda se_b_history_owned
    beq @precommit
    jsr context
    bne @precommit
    lda se_h_applied
    beq @precommit
    jsr publish
    jsr unlock_clip
    lda #0
    sta se_b_history_owned
    sta se_b_phase
    pla
    sta se_b_error
    sec
    rts
@precommit:
    jsr se_block_cancel
    pla
    sec
    rts
; Cancellation requires no asset reload. Applied work must finish its journal.
se_block_cancel:
    lda se_b_history_owned
    beq @copy
    jsr context
    beq :+
    lda #0
    jsr se_h_abort ;forget only old owned fields, never release new epoch lease
    jmp @copy
:
    lda se_h_applied
    beq @cancel_history
    lda #$61
    sec
    rts
@cancel_history:
    lda #H_CANCEL
    jsr se_history_call
    bcs @return
@copy:
    lda se_b_phase
    cmp #B_COPYING
    bne @clear
    jsr se_clip_copy_cancel
    bcs @return
@clear:
    jsr unlock_clip
    lda #0
    sta se_b_phase
    sta se_b_history_owned
    clc
@return:
    rts
unlock_clip:
    lda se_b_clip_owned
    beq @done
    lda se_b_epoch
    cmp se_clip_epoch
    bne @forget
    lda se_b_epoch+1
    cmp se_clip_epoch+1
    bne @forget
    ldx #4
@token:
    lda se_b_token,x
    cmp se_clip_token,x
    bne @forget
    dex
    bpl @token
    lda se_b_generation
    cmp se_clip_generation
    bne @forget
    lda se_b_generation+1
    cmp se_clip_generation+1
    bne @forget
    lda #0
    sta se_clip_busy
@forget:
    lda #0
    sta se_b_clip_owned
@done:
    rts

context:
    lda se_b_doc_epoch
    cmp se_doc_epoch
    bne @return
    lda se_b_doc_epoch+1
    cmp se_doc_epoch+1
@return:
    rts
