; Warm C16 mode transition. Numeric resident bindings only: no additive state,
; cold-code calls, phase-union reads, source publication or IRQ ownership.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/grid/api.inc"
.include "render/narrow/grid.inc"
.include "render/grid/cache.inc"
E_SOURCE=67
E_PREVIEW=102
E_SETTINGS=103
.include "render/geos/preview.inc"
.include "render/geos/caret-cache.inc"
.export grid_mode
.segment "CODE"
grid_mode:
    lda se_f_owner
    ora se_v_nav_busy
    ora se_n_owned
    jne busy
    lda se_mode
    cmp #4
    jcs unavailable
    lda se_e_command
    cmp #104
    bcc @ordinary
    ldx se_r_presentation
    jeq unavailable
    cmp #105
    jeq preview_next
    jmp preview_previous
@ordinary:
    cmp #E_SETTINGS
    jeq session_settings
    cmp #E_SOURCE
    jeq presentation
    cmp #E_PREVIEW
    jeq preview
    cmp #100 ;E_MODENEXT; native CTRL modifier4 reverses F8 direction
    beq cycle
    cmp #101 ;E_MODEPREV
    beq previous
    sec
    sbc #96 ;direct E_MODE40/60/80/GEOS
    cmp #4
    jcs unavailable
    bcc target
cycle:
    lda se_e_mods
    and #4
    bne previous
    lda se_mode
    clc
    adc #1
    cmp #4
    bcc target
    lda #0
    beq target
previous:
    lda se_mode
    bne :+
    lda #4
:
    sec
    sbc #1
target:
    sta g_width ;temporary requested mode0/1/2/3, not an NR frame
    tax
    beq publish
    cpx #3
    bne @narrow
    ; R21 ADMIT checks owner4 before reading any operation/frame. This brief
    ; claim invokes only its no-frame/no-write admission entry, then releases.
    lda #4
    sta se_f_owner
    lda #1 ;R21 ADMIT
    sta se_overlay_frame
    lda #21
    ldx #0
    jsr se_overlay_call
    php
    pha
    lda #0
    sta se_f_owner
    pla
    plp
    jcs done
    jmp publish
@narrow:
    lda backends,x
    sta g_backend
    lda #GRID_ADMIT
    sta se_overlay_frame
    lda g_backend
    ldx #0
    jsr se_overlay_call
    jcs done ;old mode, layout, VIC and source remain untouched
publish:
    lda g_width
    bne bitmap
    lda se_mode
    beq settings
    php
    sei ;resident warm charset copier temporarily exposes character ROM
    jsr se_display_init
    plp
    jmp settings
bitmap:
    lda g_width
    cmp #3
    bne :+
    php
    sei
    jsr se_display_init ;GEOS/native code needs its explicit restored4800 font
    plp
:
    php
    sei
    lda #$08
    sta $D018
    sta $D016
    lda #$3B
    sta $D011
    lda #0
    sta $D015
    plp
settings:
    lda #0
    sta GCC_VALID
    sta se_r_presentation
    lda se_e_ui
    cmp #4
    bne :+
    lda #0
    sta se_e_ui
:
    jsr se_grid_cache_invalidate
    ldx g_width
    stx se_mode
    lda widths,x
    sta se_v_columns
    lda #0
    sta se_r_valid
    sta se_l_valid
    sta se_st_valid
    sta se_st_request
    sta se_st_cp_valid
    sta se_n_preferred_valid
    sta se_l_manual
    sta se_l_pan
    sta se_l_pan+1
    sta se_l_pan+2
    sta se_v_top
    sta se_v_top+1
    sta se_v_top+2
    lda #1
    sta se_l_need_wrap
    sta se_e_redraw
    lda #0
    clc
done:
    rts
preview_next:
    lda PP_HISTORY_COUNT
    cmp #32
    bcs @full
    asl
    clc
    adc PP_HISTORY_COUNT
    tax
    ldy #0
@push:
    lda se_v_top,y
    sta PP_HISTORY,x
    inx
    iny
    cpy #3
    bcc @push
    inc PP_HISTORY_COUNT
@full:
    ldx #2
@top:
    lda PP_BOTTOM,x
    sta se_v_top,x
    dex
    bpl @top
    jmp preview_changed
preview_previous:
    lda PP_HISTORY_COUNT
    beq @zero
    dec PP_HISTORY_COUNT
    lda PP_HISTORY_COUNT
    asl
    clc
    adc PP_HISTORY_COUNT
    tax
    ldy #0
@pop:
    lda PP_HISTORY,x
    sta se_v_top,y
    inx
    iny
    cpy #3
    bcc @pop
    jmp preview_changed
@zero:
    lda #0
    sta se_v_top
    sta se_v_top+1
    sta se_v_top+2
preview_changed:
    lda #0
    clc
    rts
session_settings:
    lda #1
    sta se_e_ui
    lda #8
    sta se_e_menu
    lda #0
    sta se_e_item
    clc
    rts
presentation:
    lda se_mode
    cmp #3
    bne unavailable
    lda se_r_presentation
    eor #1
    jmp set_presentation
preview:
    lda se_mode
    cmp #3
    jne unavailable
    lda #1
set_presentation:
    sta se_r_presentation
    ldx #0
    stx PP_HISTORY_COUNT
    asl
    asl
    sta se_e_ui ;4 preview owns document keys,0 source editing
    lda #0
    sta se_r_valid
    lda #1
    sta se_l_need_wrap
    sta se_e_redraw
    lda #0
    clc
    rts
busy:
    lda #$7A
    sec
    rts
unavailable:
    lda #$77
    sec
    rts
.segment "RODATA"
widths: .byte 0,60,80,0
backends: .byte 0,GRID60_ID,GRID80_ID
