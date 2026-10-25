.setcpu "6502"
.macpack longbranch
.include "history/api.inc"
.include "object/api.inc"
.include "document/api.inc"
.import se_overlay_call, se_overlay_frame, se_h_state_start, se_h_state_end
.segment "CODE"
; Once per initialized object/provider epoch; same-epoch calls preserve history.
.ifdef EDITOR_COLD_DISPATCH
.segment "COLD"
.endif
se_history_cold:
    jsr object_service_valid
    bcs @return
    lda se_h_service_epoch
    cmp se_object_epoch
    bne @clear
    lda se_h_service_epoch+1
    cmp se_object_epoch+1
    beq @ok
@clear:
    lda #0
    ldx #0
@byte:
    sta se_h_state_start,x
    inx
    cpx #<(se_h_state_end-se_h_state_start)
    bcc @byte
    lda se_object_epoch
    sta se_h_service_epoch
    lda se_object_epoch+1
    sta se_h_service_epoch+1
@ok:
    lda #0
    clc
@return:
    rts

; A command from api.inc. Step dispatches by persistent phase; no same-slot
; nesting. Feed/cancel stay resident and cannot replace a running command.
.ifdef EDITOR_COLD_DISPATCH
.segment "CODE"
.endif
se_history_call:
    cmp #1
    bcc @state
    cmp #11
    bcs @state
    sta se_overlay_frame
    cmp #H_CANCEL
    beq @cancel
    cmp #H_FEED
    beq @feed
    cmp #H_STEP
    beq @step
    ldx se_h_phase
    bne @busy
    cmp #H_UNDO
    beq @play
    cmp #H_REDO
    beq @play
@edit:
    lda #H_EDIT_ID
    ldx #1
    bne @invoke
@play:
    lda #H_PLAY_ID
    ldx #1
@invoke:
    jsr se_overlay_call
    bcc @done
    cmp #$45
    beq @done ; retryable missing insertion data
    pha
    lda se_h_phase
    beq @inactive
    pla
    jmp se_h_abort ; loader/context failures must release owned state too
@inactive:
    pla
    sec
@done:
    rts
@step:
    lda se_h_phase
    beq @state
    cmp #H_COPY
    bcs @play
    bcc @edit
@feed:
    lda se_h_phase
    cmp #H_FEEDING
    bne @busy
    jmp se_doc_splice_feed
@cancel:
    jmp se_h_cancel
@busy:
    lda #$61
    sec
    rts
@state:
    lda #$60
    sec
    rts
