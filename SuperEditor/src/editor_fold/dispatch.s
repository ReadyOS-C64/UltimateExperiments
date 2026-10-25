; Resident safe points between command overlays. Never called from a C leaf.
.setcpu "6502"
.macpack longbranch
.include "editor/api.inc"
.import se_overlay_frame,se_overlay_call,se_ef_active,se_ef_operation
.import se_ec_result,se_ec_carry,se_ef_emergency
.import se_ef_valid,se_ef_key_match
.import se_l_valid,se_l_need_wrap,se_r_valid,se_st_valid,se_st_request,se_st_cp_valid
.import se_ef_motion,se_ef_checked_motion
.import se_ef_modal,se_f_owner,se_ej_status
.export se_ef_dispatch,se_ef_prepare,se_ef_motion_ack,se_ef_projection_invalidate
.segment "CODE"
; A0 begin(frame+1 action),1 step,2 cancel. C19 owns the
; state machine. A requested parser leaf runs only after C19 has returned.
; A0 complete/A1 pending/Cclear, or primary error/Cset after resident cleanup.
se_ef_dispatch:
    sta se_overlay_frame
    lda #19
    ldx #1
    jsr se_overlay_call
    bcs failed
    cmp #0
    beq done
    lda se_ef_active
    cmp #17
    bcc pending
    cmp #19
    bcs pending
    lda se_ef_operation
    sta se_overlay_frame
    lda se_ef_active
    ldx #1
    jsr se_overlay_call
    sta se_ec_result
    lda #0
    rol ;capture the leaf's actual carry before the next controller slice
    sta se_ec_carry
    lda #19
    sta se_ef_active
pending:
    lda #1
done:
    clc
    rts
failed:
    jmp se_ef_emergency
; A content change discards only derived folding and layout. The next C11
; projection displays the unchanged canonical bytes as ordinary source rows.
; This guard is safe while a modal dialog owns the shared phase workspace.
se_ef_prepare:
    jsr se_ef_modal
    bcs failed
    lda se_f_owner
    bne ready
    lda se_ej_status
    cmp #2
    beq rebuild
    lda se_ef_valid
    bne @key
    lda se_ej_status
    cmp #1
    beq rebuild ;known flush may invalidate the key while FILE owns the phase
    bne ready
@key:
    jsr se_ef_key_match
    bcc motion
    pha
    lda se_ej_status
    cmp #1
    bne :+
    pla
    cmp #$B7
    beq rebuild
    jmp failed
:
    pla
    cmp #$B7 ;EF_CHANGED; an expected edit is not a user-facing error
    bne failed
se_ef_projection_invalidate:
    lda #0
    sta se_l_valid
    sta se_r_valid
    sta se_st_valid
    sta se_st_request
    sta se_st_cp_valid
    lda #1
    sta se_l_need_wrap
    bne ready
rebuild:
    lda #6 ;internal ordered edit retention, followed by caret reveal
    bne schedule
motion:
    ldx #3
@compare:
    lda se_ef_motion,x
    cmp se_ef_checked_motion,x
    bne @reveal
    dex
    bpl @compare
    bmi ready
@reveal:
    lda #5 ;canonical navigation into hidden text opens its collapsed ancestors
schedule:
    sta se_overlay_frame+1
    lda #0
    jsr se_ef_dispatch
    bcs failed
    cmp #0
    beq @complete
    lda #10
    sta se_e_job
    lda #1
    clc
    rts
@complete:
    jsr se_ef_motion_ack
ready:
    lda #0
    clc
    rts
se_ef_motion_ack:
    ldx #3
@copy:
    lda se_ef_motion,x
    sta se_ef_checked_motion,x
    dex
    bpl @copy
    rts
