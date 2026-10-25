.setcpu "6502"
.include "editor-api.inc"
.include "render/geos/page-paint.inc"
.export entry
.segment "GEOS_PAGE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    beq @begin
    cmp #1
    beq @step
    cmp #2
    beq @cancel
    lda #$90
    sec
    rts
@begin: jmp se_gp_paint_begin
@step: jmp se_gp_paint_step
@cancel: jmp se_gp_paint_cancel
