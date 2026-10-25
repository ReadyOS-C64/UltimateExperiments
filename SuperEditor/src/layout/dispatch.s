.include "render/presentation.inc"
.setcpu "6502"
.macpack longbranch
.include "layout/api.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "nav/api.inc"
.include "render/api.inc"
.include "aux/api.inc"
.import se_editor_error
.import se_mode
.import se_overlay_call,se_overlay_frame
.import se_ef_prepare,se_ef_valid,se_ef_generation,se_ef_projection_generation
.segment "CODE"
; Called at the resident redraw safe point.0 ready,1 queued; carry error.
; R1 checks actual wrapped visibility before requesting a reveal. The old bottom
; source offset can be EOF with many free rows and is not a visibility test.
se_layout_prepare:
    lda se_mode
    cmp #3
    jeq ready ;GEOS has its own pixel-width line planner and page job
    jsr se_ef_prepare ;phase-independent source-key guard, without a C reload
    jcs failed
    tax ;se_ef_prepare returns only0ready/1queued
    bne @queued
    ; Keep the common source40/wrapped-ready predicate resident: no C load.
    jsr se_ef_visible
    bne @folded
    lda se_l_mode
    bne @no_wrap
    lda se_l_need_wrap
    beq ready
    bne @start
@folded:
    lda #2 ;pure fold/layout decision, no phase/private scratch access
    sta se_overlay_frame
    lda #33
    ldx #1
    jsr se_overlay_call
    bcs failed
    lsr ;private C33 returns only0ready/1start/2context
    bcs @start
    beq ready
@no_wrap:
    lda #A_LAYOUT_CONTEXT
    sta se_overlay_frame
    lda #AUX_ID
    ldx #1
    jsr se_overlay_call
    bcs failed
    tax
    beq ready
@start:
    lda #L_BEGIN
    jsr se_navigation_call
    bcs failed
    lda #0
    sta se_l_need_wrap
    lda #7
    sta se_e_job
    lda #1
@queued:
    clc
    rts
ready:
    lda #0
    clc
    rts
se_layout_service:
    lda #L_STEP
    jsr se_navigation_call
    bcs failed
    cmp #0
    bne @done
    sta se_e_job
    lda #1
    sta se_e_redraw
@done:
    rts
failed:
    jmp se_editor_error
