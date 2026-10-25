.setcpu "6502"
.macpack longbranch
.include "hot/api.inc"
.include "history/api.inc"
.include "document/api.inc"
.include "object/api.inc"
.import se_overlay_call,se_overlay_frame,se_hot_state_start,se_hot_state_end
.segment "CODE"
.ifdef EDITOR_COLD_DISPATCH
.segment "COLD"
.endif
se_hot_cold:
    jsr object_service_valid
.ifdef EDITOR_COLD_DISPATCH
    jcs return
.else
    bcs return
.endif
    lda se_hot_epoch
    cmp se_object_epoch
    bne @clear
    lda se_hot_epoch+1
    cmp se_object_epoch+1
.ifdef EDITOR_COLD_DISPATCH
    jeq okay
.else
    beq okay
.endif
@clear:
    lda #0
    ldx #0
@byte:
    sta se_hot_state_start,x
    inx
    cpx #<(se_hot_state_end-se_hot_state_start)
    bcc @byte
    lda se_object_epoch
    sta se_hot_epoch
    lda se_object_epoch+1
    sta se_hot_epoch+1
.ifdef EDITOR_COLD_DISPATCH
    jmp okay
.segment "CODE"
.endif
okay:
    lda #0
    clc
return:
    rts
; Command inA. INSERT consumes se_hot_byte; other requests in protected frame.
se_hot_call:
    ; Refusing a competing command must not cancel the active load/flush.
    tax
    lda se_hot_phase
    beq @route
    txa
    cmp #W_STEP
    beq @route
    cmp #W_CANCEL
    beq @route
    lda #$71
    sec
    rts
@route:
    txa
    cmp #W_CANCEL
    jeq cancel
    cmp #W_STEP
    beq step
    cmp #W_FLUSH
    beq flush
    jmp invoke
step:
    lda se_hot_phase
    cmp #2
    bne window_step
    lda se_h_phase
    cmp #H_FEEDING
    bne @advance
    lda se_hot_feed_left
    ora se_hot_feed_left+1
    beq @advance
    lda #W_PACKET
.ifdef EDITOR_FAST_HOT_FEED
    sta se_overlay_frame
    lda #H_EDIT_ID
    ldx #1
    jsr se_overlay_call
.else
    jsr invoke
.endif
    bcs return
    lda #H_FEED
    bne history
@advance:
    lda #H_STEP
history:
    jsr se_history_call
    bcs failed
    lda se_h_phase
    bne pending
    lda #W_COMMIT
    jmp invoke
window_step:
    lda #W_STEP
    jmp invoke
flush:
    lda #W_PREPARE
    jsr invoke
    bcs return
    lda se_hot_phase
    beq okay
    lda #H_BEGIN
    jsr se_history_call
    bcs failed
    lda se_h_phase
    beq flush_empty
pending:
    lda #1
    clc
    rts
flush_empty:
    lda #W_COMMIT
    jmp invoke
invoke:
    sta se_overlay_frame
    lda #HOT_ID
    ldx #1
    jsr se_overlay_call
    jcc return
failed:
    pha
    ; Test ownership/publication before cancel resets our phase.
    lda se_hot_phase
    cmp #2
    bne @cleanup
    lda se_h_applied
    beq @cleanup
    lda #0
    sta se_hot_ready
    sta se_hot_pending
    sta se_hot_phase
    jmp @error
@cleanup:
    jsr cancel
@error:
    pla
    sta se_hot_fault
    sec
    rts
cancel:
    lda se_hot_phase
    cmp #2
    beq @history
    cmp #1
    jne okay
    lda se_hot_original+3
    cmp se_doc_epoch
    bne @forget
    lda se_hot_original+4
    cmp se_doc_epoch+1
    bne @forget
    lda se_hot_owned
    beq @forget
    jsr se_doc_read_release
@forget:
    lda #0
    sta se_hot_owned
    sta se_hot_phase
    jmp okay
@history:
    lda #H_CANCEL
    jsr se_history_call
    jcs return
    lda #0
    sta se_hot_phase
    jmp okay
