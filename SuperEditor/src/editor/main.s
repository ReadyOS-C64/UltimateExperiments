.setcpu "6502"
.include "render/geos/edit-certificate.inc"
.macpack longbranch
.include "platform.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "history/api.inc"
.import __BSS_RUN__,__BSS_SIZE__
.import se_display_init,se_input_init,se_input_get,se_reu_probe,se_editor_startup
.import se_overlay_call,se_overlay_frame
.export se_entry,se_idle,se_diagnostics,se_status,se_mode,se_reu_banks
.export se_last_key,se_key_sequence,se_probe_bank,se_probe_byte,se_probe_saved,se_probe_original,se_ink_reverse
.export se_editor_latch_event
.include "render/api.inc"
.include "layout/api.inc"
.include "style/api.inc"
.import se_style_idle
.import se_geos_render
.export se_editor_render_ui,se_editor_render_failed
.export se_clear_state,se_editor_render,se_editor_error,se_editor_render_call
.exportzp text_ptr,screen_ptr
se_probe_original=$0F00 ;cold-only saved probe bytes, excluded from warm state
.segment "LOADADDR"
    .word $0801
.segment "BOOT"
    .word boot_end
    .word 10
    .byte $9E,$34,$30,$39,$36,0
boot_end: .word 0
.segment "ZEROPAGE"
text_ptr: .res 2
screen_ptr: .res 2
.segment "BSS"
se_diagnostics: .res 4
se_schema: .res 1
se_status: .res 1
se_mode: .res 1
se_reu_banks: .res 2
se_last_key: .res 1
se_key_sequence: .res 2
se_probe_bank: .res 1
se_probe_byte: .res 1
se_probe_saved: .res 1
se_ink_reverse: .res 1
.segment "ENTRY"
se_entry:
    sei
    cld
    lda $00
    ora #7
    sta $00
    lda $01
    and #$F8
    ora #6
    sta $01
    jsr se_clear_state
    lda #$53
    sta se_diagnostics
    lda #$45
    sta se_diagnostics+1
    sta se_diagnostics+2
    lda #$44
    sta se_diagnostics+3
    lda #1
    sta se_schema
    lda #$80
    sta $0291
    lda #1
    sta $CC
    jsr se_display_init
    jsr se_reu_probe
    jsr se_input_init
    cli
    jsr se_editor_startup
    bcc se_editor_ready
    sta se_e_error
    lda #3
    sta se_status
    jmp se_idle
se_editor_ready:
    lda #1
    sta se_status
    sta se_e_redraw
se_idle:
    jsr se_editor_service
    lda se_e_job
    bne se_idle
    lda se_status
    cmp #1
    bne se_idle
    jsr se_input_get
    beq @draw
    jsr se_editor_latch_event
    jsr se_editor_input
    jmp se_idle
@draw:
    lda se_e_redraw
    beq @background
    jsr se_editor_render
    jmp se_idle
@background:
    lda se_e_ui
    bne se_idle
    lda se_st_request
    cmp #1
    bne se_idle
    jsr se_style_idle
    ; Style idle returns A=$80 on either handled or transport failure.
    bpl se_idle
    inc se_e_redraw ;a later planner failure must publish the plain fallback once
    jmp se_idle
.segment "CODE"
se_editor_latch_event:
    sta se_e_key
    sta se_last_key
    stx se_e_mods
    sty se_e_matrix
    inc se_key_sequence
    bne :+
    inc se_key_sequence+1
:
    rts
.segment "COLD"
se_clear_state:
    lda #<__BSS_RUN__
    sta text_ptr
    lda #>__BSS_RUN__
    sta text_ptr+1
    ldx #>__BSS_SIZE__
    ldy #0
    lda #0
@page:
    sta (text_ptr),y
    iny
    bne @page
    inc text_ptr+1
    dex
    bne @page
    ldx #<__BSS_SIZE__
    beq @view
@byte:
    sta (text_ptr),y
    iny
    dex
    bne @byte
@view:
    .import se_editor_state_start,se_editor_state_end
    .assert se_r_valid >= __BSS_RUN__ .and se_r_valid < __BSS_RUN__ + __BSS_SIZE__, lderror, "render valid flag outside cleared BSS"
    .assert se_r_revision >= __BSS_RUN__ .and se_r_revision + 4 <= __BSS_RUN__ + __BSS_SIZE__, lderror, "render revision outside cleared BSS"
    .assert se_r_damage_valid >= __BSS_RUN__ .and se_r_damage_valid < __BSS_RUN__ + __BSS_SIZE__, lderror, "render damage flag outside cleared BSS"
@clear_view:
    sta se_editor_state_start,x
    inx
    bne @clear_view
    sta se_st_cp_valid
    ; Cold-only owned C64 metadata. A missing REU/asset can fail before each
    ; service initializer, so ready/phase fields must not retain power-on RAM.
    sta text_ptr
    lda #$9A
    sta text_ptr+1
    lda #0
    ldy #0
    ldx #6
@metadata:
    sta (text_ptr),y
    iny
    bne @metadata
    inc text_ptr+1
    dex
    bne @metadata
    rts
.segment "CODE"
se_editor_render:
    lda se_mode
    cmp #3
    bne :+
    jmp se_geos_render ;bounded page job, never the source-grid layout path
:
    lda #1
    sta se_overlay_frame
    lda #33
    ldx #1
    jsr se_overlay_call
    bcs @ordinary
    tax
    bne @ordinary
    sta se_e_redraw
    jmp se_er_publish_only
@ordinary:
    jsr se_layout_prepare
    bcs se_editor_render_failed
    cmp #0
    beq se_er_paint
    clc ;queued work is success, no pixels published yet
    rts
se_er_paint:
    lda #1
    sta se_e_draw_busy
    lda #0
    sta se_e_redraw
    lda #R_DRAW
    jsr se_editor_render_call
    bcs se_editor_render_failed
    cmp #ST_PENDING
    beq se_er_style_pending
    lda se_l_need_wrap
    beq se_editor_render_ui
    lda #0
    sta se_e_draw_busy
    jsr se_layout_prepare
    bcs se_editor_render_failed
    rts ;C11 queued without publishing pixels or draw sequence
se_er_style_pending:
    lsr se_e_draw_busy ;strict 1 -> 0; carry is cleared below
    clc
    rts ;idle checks input again before running the first bounded style slice
se_editor_render_ui:
    lda se_e_ui
    cmp #3
    bne se_er_menu_ui
    lda #5 ;stateless AUX file popup, entered only from resident
    sta se_overlay_frame
    lda #13
    bne se_er_ui_call
se_er_menu_ui:
    cmp #1
    bne se_er_drawn
    lda #U_DRAW
    sta se_overlay_frame
    lda #7
se_er_ui_call:
    ldx #1
    jsr se_overlay_call
    bcc se_er_drawn
    jsr se_editor_error
se_editor_render_failed:
    lda #0
    sta se_r_valid
    sta se_e_redraw ;persistent render failures cannot spin retrying forever
    sta se_e_draw_busy
    sec
    rts
se_er_drawn:
    lda se_mode
    beq se_er_published
    lda #2 ;C16 finalizes the logical chrome and current popup as bitmap tiles
    sta se_overlay_frame
    lda #16
    ldx #1
    jsr se_overlay_call
    bcs se_editor_render_failed
.export se_er_published
se_er_published:
    jsr se_er_publish_only
    ldx se_mode
    beq @done
    cpx #3
    bcc @narrow
    bne @done ;invalid mode>=4 retains the original no-overlay behavior
    lda GEC_SEQUENCE
    clc
    adc #1
    cmp se_e_draw_sequence
    bne @done ;cheap necessary test only; fullauthority remains inside AUX
    lda #6
    sta se_overlay_frame
    lda #13
    bne @invoke
@narrow:
    sta se_overlay_frame
    lda #33
@invoke:
    ldx #1
    jsr se_overlay_call
@done:
    lda #0
    clc
    rts
se_er_publish_only:
    inc se_e_draw_sequence
    bne :+
    inc se_e_draw_sequence+1
:
    lda #0
    sta se_e_draw_busy
    clc
    rts
se_editor_render_call:
    sta se_overlay_frame
    lda se_mode
    beq @text
    lda #16 ;C16 produces narrow source rows using its independent R leaf
    ldx #1
    bne @invoke
@text:
    lda #EDITOR_RENDER_ID
    ldx #0
@invoke:
    jsr se_overlay_call
    bcc done
se_editor_error:
    pha
    sta se_e_error
    lda #0
    sta se_e_job
    lda #1
    sta se_e_redraw
    pla
    sec
    rts
done:
    rts
