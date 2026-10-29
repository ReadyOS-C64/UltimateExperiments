.setcpu "6502"
.include "editor/api.inc"
.include "nav/api.inc"
.segment "VIEWSTATE"
.export se_editor_state_start,se_editor_state_end
se_editor_state_start:
se_e_key: .res 1
se_e_mods: .res 1
se_e_matrix: .res 1
se_e_command: .res 1
se_e_job: .res 1 ;0idle,1load,2flush,3history,4navigation
se_e_after_load: .res 1
se_e_error: .res 1
se_e_redraw: .res 1
se_e_draw_busy: .res 1
se_e_draw_sequence: .res 2
se_e_ui: .res 1 ;0document,1menu,2typed command
se_e_menu: .res 1 ;0bar or1..6 heading
se_e_item: .res 1
se_e_text: .res 32
se_e_text_length: .res 1
se_e_target: .res 3
se_v_top: .res 3
se_v_pos: .res 3
se_v_length: .res 3
se_v_hot_end: .res 3
se_v_span: .res 3
se_v_old_span: .res 3
se_v_phys: .res 3
se_v_cache_base: .res 3
se_v_cache_end: .res 3
se_v_cache_count: .res 2
se_v_temp: .res 3
se_v_row: .res 1
se_v_col: .res 1
se_v_caret_row: .res 1
se_v_caret_col: .res 1
se_v_seen: .res 1
se_v_rows: .res EDITOR_ROW_START_BYTES ;22 body starts; end anchor is separate
se_v_cell: .res 1
se_v_restart: .res 1
se_v_nav_busy: .res 1
se_v_menu_row: .res 1
se_v_menu_count: .res 1
se_v_menu_index: .res 1
se_v_menu_ptr: .res 2
.export tui_box_x,tui_box_y,tui_box_w,tui_box_h,box_rx,box_ry
tui_box_x: .res 1
tui_box_y: .res 1
tui_box_w: .res 1
tui_box_h: .res 1
box_rx: .res 1
box_ry: .res 1
.include "nav/header.inc"
se_editor_state_end:
.assert se_editor_state_end-se_editor_state_start <256,error,"editor frame clear bound"
