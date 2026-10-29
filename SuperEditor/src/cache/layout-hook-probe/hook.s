; PRIVATE coarse page protocol. INIT is exact C21 common initialization.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/layout-hook-probe/api.inc"
.include "cache/api.inc"
.include "cache/query/proof-api.inc"
.include "render/geos/editor.inc"
.include "render/geos/source-line.inc"
.include "render/geos/semantic.inc"
.include "render/geos/fold-query.inc"
.include "render/geos/checkpoint/codec.inc"
.include "render/geos/edit-cache.inc"
.import se_lm_capture,se_lm_restore,se_lm_step
.import se_bc_flags,se_v_top,se_l_mode
.import se_l_valid,se_r_valid,se_st_request,se_st_cp_valid
.export se_lmh_init,se_lmh_begin,se_lmh_step
P=GP_CONTROL
LINE=P+3
TOP=P+4
ANCHOR=P+5
FAST_PAINT=P+20
.segment "CODE"
se_lmh_init:
    lda GEC_VALID
    sta GSC_ALLOW_EDIT
    lda #0
    sta GS_ACTIVE
    sta GFQ_ACTIVE
    sta GS_CONTEXT_VALID
    sta GSEM_FRAME+GSEM_ACTIVE
    sta GSC_CAPTURED
    lda se_bc_flags
    and #($FF-BCQ_PAGE_PROOF)
    sta se_bc_flags
    lda #0
    sta GSEM_FRAME+GSEM_CP_VALID
    sta $8B40 ;fresh caller-owned painter state may contain native power-on RAM
    sta $8B41
    sta LINE
    sta FAST_PAINT
    sta GEX_PHASE
    sta se_l_valid
    sta se_r_valid
    sta se_st_request
    sta se_st_cp_valid
    ldx #GP_MAX_GLYPHS-1
@clear_roles:
    sta GP_ROLES,x
    dex
    cpx #$FF
    bne @clear_roles
    lda #16
    sta TOP
    ldx #2
@anchor:
    lda se_v_top,x
    sta ANCHOR,x
    dex
    bpl @anchor
    lda #0
    clc
    rts
; Clear permission before bounded work: cancel/missing continuation remains
; unarmed even if no R34 code is available for cleanup. Every complete hit
; or capture must freshly rearm it. No extra nonce/BSS is invented.
se_lmh_begin:
    lda #0
    ldx #63
@clear:
    sta LM_STATE,x
    dex
    bpl @clear
    lda se_bc_flags
    and #LM_SESSION_PERMISSION
    sta LM_PAGE_STATE
    lda se_bc_flags
    and #($FF-LM_SESSION_PERMISSION)
    sta se_bc_flags
    lda se_l_mode
    bne refusal
    jsr se_gp_cache_guard
    bcs refusal
    ldx #2
@target:
    lda se_v_top,x
    sta LM_TARGET,x
    dex
    bpl @target
    lda LM_PAGE_STATE
    beq capture_begin
    lda #1
    sta LM_PAGE_STATE
    jsr se_lm_restore
    bcs refusal
    rts
se_lmh_step:
    lda LM_PAGE_STATE
    cmp #3
    beq capture_begin
    jsr se_lm_step
    bcs refusal
    cmp #1
    beq return
    ldx LM_PAGE_STATE
    cpx #1
    bne captured
    cmp #0
    beq restored
    ; Defer miss->capture to the next bounded call, not another CRC unit now.
    lda #3
    sta LM_PAGE_STATE
    lda #1
    clc
return:
    clc
    rts
capture_begin:
    lda #2
    sta LM_PAGE_STATE
    jsr se_lm_capture
    bcs refusal
    rts
captured:
    cmp #0
    bne refusal
    jsr arm
refusal:
    lda #2
    clc
    rts
restored:
    jsr arm
    lda #0
    clc
    rts
arm:
    lda se_bc_flags
    ora #LM_SESSION_PERMISSION
    sta se_bc_flags
    rts
