.setcpu "6502"
.include "diagnostics/api.inc"
.include "layout/api.inc"
.import se_overlay_call,se_overlay_frame,se_diag_abort
.export se_diag_call
.segment "CODE"
; Synchronous entry from a resident safe point. C11 owns no executable pointers
; between slices; failed admission must still release only our own read lease.
se_diag_call:
    sta se_overlay_frame
    lda #LAYOUT_ID
    ldx #1
    jsr se_overlay_call
    bcc :+
    cmp #D_STATE
    beq :+ ;competing BEGIN must preserve the already-active job
    jmp se_diag_abort
:
    rts
