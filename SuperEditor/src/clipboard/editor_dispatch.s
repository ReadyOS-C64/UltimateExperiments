.setcpu "6502"
.include "clipboard/api.inc"
.include "block/api.inc"
.import se_overlay_call,se_overlay_frame
.segment "CODE"
; Root-only public compatibility entries. C10 calls its private implementations.
; A refused/failed BEGIN never cancels an existing copy operation.
se_clip_copy_begin:
    lda #B_COPY_BEGIN
    bne invoke
se_clip_copy_step:
    lda #B_COPY_STEP
    jsr invoke
    bcc done
    pha
    jsr se_clip_copy_cancel ;resident cleanup survives an unavailable C10
    pla
    sec
done:
    rts
invoke:
    sta se_overlay_frame
    lda #BLOCK_ID
    ldx #1
    jmp se_overlay_call
