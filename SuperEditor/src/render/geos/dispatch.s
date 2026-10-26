; Resident sequential C21/C20/C22 job pump. No overlay pointer survives a swap.
.setcpu "6502"
.macpack longbranch
.include "editor/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.include "render/geos/editor.inc"
.include "render/geos/edit-certificate.inc"
.include "render/grid/api.inc"
.include "cache/api.inc"
.import se_mode,se_f_owner,se_fs_state,se_fs_end
.import se_ef_prepare
.import se_gc_valid
.import se_overlay_call,se_overlay_frame,se_editor_error
.import se_editor_render_ui,se_editor_render_failed,se_er_published
.import se_editor_reload,se_editor_reveal,se_editor_redraw
.export se_geos_render,se_geos_service,se_geos_cancel,se_geos_navigate
STATE=GP_CONTROL
REQUEST=GP_CONTROL+1
OP=GP_CONTROL+2
SOURCE_ACTIVE=$912C
SOURCE_CONTEXT=$912D
SOURCE_SAVED=$9040
.segment "CODE"
se_geos_render:
    ; The R27 root path leaves C6 active and reuses the native chrome leaf.
    ; Full layout/preview/selection/mode changes retain the coordinator path.
    lda #3
    sta se_overlay_frame
    lda #27
    ldx GEC_VALID
    beq :+
    ; Nine-pixel prose uses R30; aligned native8 code uses R31.
    ; Each worker independently refuses malformed or ineligible packets.
    lda GCC_HEIGHT
    and #1
    eor #31
:
    ldx #0
    jsr se_overlay_call
    jcs failed
    cmp #2
    beq @full
    lda #0
    sta se_e_redraw
    jmp se_er_published
@full:
    jsr se_ef_prepare
    bcs :+
    beq @ready
:   rts
@ready:
    lda #1
    sta se_e_draw_busy
    lda #0
    sta se_e_redraw
    sta se_overlay_frame
    lda #GP_PAGE_ID
    ldx se_f_owner
    dex
    bne :+
    ; FILE owns the complete phase. C16 chrome is stateless and never enters
    ; C21 or interprets GP_CONTROL9134 as a GEOS continuation.
    lda #GRID_CHROME
    sta se_overlay_frame
    lda #GRID_EDITOR_ID
:
    ldx #1
    jsr se_overlay_call
    jcs failed
    tax ;explicit A->Z test; X is dead before either path
    beq painted
    lda #11
set_job:
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
    bne set_job
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
    jmp failed
:
    cmp #GP_LAYOUT_ID
    beq resume
    .assert GP_SEMLEX_ID=GP_SEMANTIC_ID+1 .and GP_INLINE_ID=GP_SEMANTIC_ID+2,error,"semantic worker range"
    cmp #GP_SEMANTIC_ID
    bcc :+
    cmp #GP_INLINE_ID+1
    bcc resume
:
    ; C34 builds a baseline and restarts C21; C35 resumes its query caller.
    ; Both remain loaded across bounded slices, just like semantic workers.
    cmp #34
    bcc ordinary_worker
    cmp #36
    bcs ordinary_worker
    cpx #1
    bne cache_complete
    stx OP ;new jobs enter with BEGIN0, then retain their STEP1 operation
    beq done ;CPX equality survives STX
cache_complete:
    ;A2 MISS/A3 STREAM also return to the coordinator for fallback.
    and #1
    bne :+
    sta se_f_owner ;C34 completion restarts C21 through its fresh claim
:
    jmp set_page
ordinary_worker:
    cmp #GP_NAV_ID
    bne :+
    txa
    beq navigation_done
    cmp #2
    bne done
    lda #0
    sta se_e_job
    clc
    jmp se_editor_redraw
navigation_done:
    sta se_e_job
    jmp se_editor_reload
:
    cmp #GP_PAINT_ID
    beq paint_result
    cpx #2 ;C21 A2: complete page did not contain the caret; flush/reveal
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
    txa ;C22 A1pending/A0complete is saved in X
    bne set_operation
    lda #3
    bne set_page
resume:
    ; A pending worker already owns its continuation. Keep it loaded for the
    ; next bounded idle slice; swapping to the coordinator after every packet
    ; only makes it ask for this same worker again. Completion alone resumes
    ; the coordinator. Input/STOP still runs between every public service call.
    cpx #0
    bne done ;workers publish their own continuation, including a child request
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
    lda se_bc_flags
    and #BC_ACTIVE
    beq legacy_cancel
    lda se_bc_flags
    and #($FF-BC_ACTIVE)
    ora #BC_REBUILD_TRIED
    sta se_bc_flags
    ldx #85
cache_restore:
    lda BC_FRAME+BCF_READER,x
    sta se_fs_state,x
    dex
    bpl cache_restore
    bmi source_end ;X=$FF; shared resident lease release, no overlay dependency
legacy_cancel:
    lda SOURCE_CONTEXT
    beq clear
    ldx #85
restore:
    lda SOURCE_SAVED,x
    sta se_fs_state,x
    dex
    bpl restore
source_end:
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
