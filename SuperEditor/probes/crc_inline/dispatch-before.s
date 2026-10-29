; Resident sequential C21/C20/C22 job pump. No overlay pointer survives a swap.
.setcpu "6502"
.macpack longbranch
.include "editor/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.include "render/geos/editor.inc"
.import se_mode,se_f_owner,se_fs_state,se_fs_end
.import se_gc_valid
.import se_overlay_call,se_overlay_frame,se_editor_error
.import se_editor_render_ui,se_editor_render_failed
.import se_editor_reload,se_editor_reveal
.export se_geos_render,se_geos_service,se_geos_cancel,se_geos_navigate
STATE=GP_CONTROL
REQUEST=GP_CONTROL+1
OP=GP_CONTROL+2
SOURCE_ACTIVE=$912C
SOURCE_CONTEXT=$912D
SOURCE_SAVED=$9040
.segment "CODE"
se_geos_render:
    lda #1
    sta se_e_draw_busy
    lda #0
    sta se_e_redraw
    sta se_overlay_frame
    lda se_f_owner
    cmp #1
    bne :+
    lda #5 ;FILE owns the phase: preserve body, draw chrome/popup only
    sta se_overlay_frame
:
    lda #GP_PAGE_ID
    ldx #1
    jsr se_overlay_call
    jcs failed
    cmp #0
    beq painted
    lda #11
    sta se_e_job
    clc
    rts
se_geos_navigate:
    lda #0
    sta se_overlay_frame
    lda #GP_NAV_ID
    ldx #1
    jsr se_overlay_call
    jcs failed
    lda #12
    sta se_e_job
    clc
    rts
se_geos_service:
    lda OP
    sta se_overlay_frame
    lda REQUEST
    pha
    ldx #1
    jsr se_overlay_call
    tax
    pla
    bcc :+
    txa
    bcs failed
:
    cmp #GP_LAYOUT_ID
    beq resume
    cmp #GP_SEMANTIC_ID
    beq resume
    cmp #GP_SEMLEX_ID
    beq resume
    cmp #GP_NAV_ID
    bne :+
    txa
    bne done
    sta se_e_job
    jmp se_editor_reload
:
    cmp #GP_PAINT_ID
    beq paint_result
    txa ;C21 controls its own next REQUEST/OP on pending
    cmp #2 ;complete page did not contain the caret: flush/reveal at root
    beq reveal
    txa
    bne done
painted:
    lda #0
    sta se_e_job
    jmp se_editor_render_ui ;shared menus/File popup + bitmap chrome finalizer
reveal:
    jmp se_editor_reveal
paint_result:
    lda #1 ;C22 pending STEP, completed -> C21 FINISH3
    cpx #0
    bne set_operation
    lda #3
    bne set_page
resume:
    ; A pending worker already owns its continuation. Keep it loaded for the
    ; next bounded idle slice; swapping to the coordinator after every packet
    ; only makes it ask for this same worker again. Completion alone resumes
    ; the coordinator. Input/STOP still runs between every public service call.
    cpx #0
    beq worker_complete
    lda #1
    sta OP
    jmp done
worker_complete:
    lda #1
    ldx #GP_PAGE_ID
    ldy se_e_job
    cpy #12
    bne :+
    ldx #GP_NAV_ID
:
    stx REQUEST
    sta OP
    jmp done
set_page:
    ldx #GP_PAGE_ID
    stx REQUEST
set_operation:
    sta OP
done:
    clc
    rts
failed:
    pha
    jsr se_geos_cancel
    pla
    jsr se_editor_error
    jmp se_editor_render_failed
; Always resident, including when any C/R image is missing. Only owner4 may
; interpret the phase union as GEOS state. An abandoned GL map need not survive.
se_geos_cancel:
    lda se_f_owner
    cmp #4
    bne done
    lda SOURCE_CONTEXT
    beq clear
    ldx #85
restore:
    lda SOURCE_SAVED,x
    sta se_fs_state,x
    dex
    bpl restore
    jsr se_fs_end
clear:
    lda #0
    sta SOURCE_ACTIVE
    sta SOURCE_CONTEXT
    sta STATE
    sta $8B40 ;C22 painting continuation cannot survive an aborted page
    sta $8B41
    sta se_f_owner
    sta se_l_valid
    sta se_r_valid
    sta se_gc_valid
    sta se_gc_valid+1
    sta se_gc_valid+2
    clc
    rts
