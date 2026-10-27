.include "render/presentation.inc"
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "platform.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "block/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.include "style/api.inc"
.import tui_editor_chrome40
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #R_DRAW
    beq draw
    lda #$70
    sec
    rts
return:
    rts
draw:
    lda $D011
    and #$20
    beq :+
    php
    sei
    jsr se_display_init
    plp
:
    jsr se_view_init
    bcs return
    jsr se_selection_range
    lda se_l_mode
    bne @planned
    jsr wrapped_visibility
    bcs return
    lda se_l_need_wrap
    beq @planned
    lda #0
    clc
    rts ;resident queues C11 after leaving renderer slot
@planned:
    jsr style_context
    jsr cache_plan
    lda #0
    sta se_r_valid ;publish only after every body/chrome operation succeeds
    sta se_v_seen
    sta se_v_restart
    lda se_l_mode
    jne nowrap_draw
    lda se_r_path
    beq full_draw
    jsr restore_caret
    lda se_r_path
    cmp #1
    bne dirty_draw
    jsr paint_caret
    bcs full_draw
    jmp chrome
full_draw:
    lda #0
    sta se_r_path
    CMP24 se_hot_caret,se_v_top
    bcs :+
    COPY24 se_hot_caret,se_v_top
    jsr style_context
:
    jsr clear_screen
    COPY24 se_v_top,se_v_pos
    lda #0
    sta se_v_row
    jmp row
dirty_draw:
    ; cache_plan located the first damaged row before restore_caret.
    lda se_v_row
    asl
    clc
    adc se_v_row
    tax
    lda se_v_rows,x
    sta se_v_pos
    lda se_v_rows+1,x
    sta se_v_pos+1
    lda se_v_rows+2,x
    sta se_v_pos+2
row:
    inc se_r_rows
    lda se_v_row
    asl
    clc
    adc se_v_row
    tax
    ; Next anchor is separate at the final visible row.
    jsr read_next
    jsr se_ef_visible
    bne @fold_anchor
    ADD24 se_r_next,se_r_delta,se_r_next
@fold_anchor:
    ldy #0
@map:
    lda se_v_pos,y
    sta se_v_rows,x
    inx
    iny
    cpy #3
    bcc @map
    lda #0
    sta se_v_col
cell:
    CMP24 se_v_pos,se_v_length
    bcs end_of_source
    jsr se_view_peek
    jcs return
    cmp #13
    beq newline
    jsr se_petscii_screen
    sta se_v_cell
    jsr put_source
    jsr se_view_advance
    inc se_v_col
    lda se_v_col
    cmp #40
    bcc cell
    jmp next_row
newline:
    jsr put_end
    jsr se_view_advance
    jmp pad_begin
end_of_source:
    jsr put_end
pad_begin:
    inc se_v_col
    lda se_v_col
    cmp #40
    bcs next_row
pad:
    lda #TUI_FG
    sta tui_color
    ldx se_v_col
    lda se_v_row
    clc
    adc #2
    tay
    lda #32
    jsr body_put
    inc se_v_col
    lda se_v_col
    cmp #40
    bcc pad
next_row:
    jsr se_ef_visible
    beq :+
    COPY24 se_r_next,se_v_pos ;the next canonical anchor can skip hidden bytes
:
    inc se_v_row
    lda se_v_row
    cmp #EDITOR_BODY_ROWS
    jcs rows_complete
    lda se_r_path
    cmp #2
    jne row
    CMP24 se_v_pos,se_r_last
    jcc row
    lda se_r_mode
    bne @stable
    CMP24 se_v_pos,se_r_next
    jne row
@stable:
    ; The remaining rows contain identical bytes and styling; shift their
    ; source anchors without rewriting pixels. Include the final end anchor.
    lda se_v_row
    asl
    clc
    adc se_v_row
    tax
@shift:
    clc
    lda se_v_rows,x
    adc se_r_delta
    sta se_v_rows,x
    lda se_v_rows+1,x
    adc se_r_delta+1
    sta se_v_rows+1,x
    lda se_v_rows+2,x
    adc se_r_delta+2
    sta se_v_rows+2,x
    inx
    inx
    inx
    cpx #EDITOR_ROW_START_BYTES
    bcc @shift
    ADD24 se_v_bottom,se_r_delta,se_v_bottom
    jmp rows_drawn
rows_complete:
    COPY24 se_v_pos,se_v_bottom
rows_drawn:
    lda se_v_seen
    jne chrome
    lda se_r_path
    cmp #2
    bne @reveal
    jsr paint_caret
    jcc chrome
@reveal:
    lda se_v_restart
    jne chrome
    COPY24 se_hot_caret,se_v_top
    jsr style_context
    inc se_v_restart
    jmp full_draw
 ; The shared query reads only the published C11 map, never fold/source REU.
put_end:
    lda #32
    sta se_v_cell
    lda #TUI_FG
    sta tui_color
    lda se_v_row
    jsr se_ef_summary
    beq @plain
    lda #$AB
    sta se_v_cell
    bcc @plain
    ; Selection/caret are a single inversion union over the inverse marker.
    sta se_r_glyph
    lda #$2B
    sta se_v_cell
    lda #TUI_HIGHLIGHT
    sta tui_color
    jmp source_caret
@plain:
    jmp source_base
put_plain:
    lda #TUI_FG
    sta tui_color
    jmp source_base
put_source:
    lda #TUI_FG
    sta tui_color
    jsr style_cell
source_base:
    lda se_v_cell
    sta se_r_glyph
    lda se_sel_mark
    beq source_caret
    CMP24 se_v_pos,se_sel_start
    bcc source_caret
    CMP24 se_v_pos,se_sel_end
    bcs source_caret
    lda #TUI_HIGHLIGHT
    sta tui_color
    lda se_v_cell
    eor #$80
    sta se_v_cell
source_caret:
    CMP24 se_v_pos,se_hot_caret
    bne @put
    lda se_v_seen
    bne @put
    lda #1
    sta se_v_seen
    lda se_v_row
    sta se_v_caret_row
    sta se_r_caret_row
    lda se_v_col
    sta se_v_caret_col
    sta se_r_caret_col
    lda se_v_cell
    sta se_r_under_glyph
    lda tui_color
    sta se_r_under_color
    lda #TUI_HIGHLIGHT
    ldx se_sel_mark
    beq :+
    lda #TUI_TITLE
:
    sta tui_color
    lda se_r_glyph
    eor #$80
    sta se_v_cell
@put:
    ldx se_v_col
    lda se_v_row
    clc
    adc #2
    tay
    lda se_v_cell
    jmp body_put

clear_screen:
    ldx #0
    lda #32
@space:
    .repeat 4,P
    sta VIC_SCREEN+P*$100,x
    .endrepeat
    inx
    bne @space
    lda #TUI_FG
@ink:
    .repeat 4,P
    sta $D800+P*$100,x
    .endrepeat
    inx
    bne @ink
    rts
chrome:
    jsr tui_editor_chrome40
    jmp cache_save
.include "overlays/render-cache.s"
.include "overlays/render-visibility.s"
.include "overlays/render-nowrap.s"
.include "overlays/render-style.s"
