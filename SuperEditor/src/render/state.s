.setcpu "6502"
.include "render/api.inc"
.segment "BSS"
se_r_valid: .res 1
se_r_revision: .res 4
se_r_saved_revision: .res 4
se_r_damage_valid: .res 1
se_r_damage_from: .res 3
se_r_damage_to: .res 3
se_r_path: .res 1
se_r_rows: .res 1
se_r_cells: .res 2
se_r_original: .res 5
se_r_append: .res 5
se_r_generation: .res 2
se_r_length: .res 3
se_r_top: .res 3
se_r_mark: .res 1
se_r_anchor: .res 3
se_r_caret: .res 3
se_r_ui: .res 1
se_r_under_glyph: .res 1
se_r_under_color: .res 1
se_r_caret_row: .res 1
se_r_caret_col: .res 1
se_r_first: .res 3
se_r_last: .res 3
se_r_delta: .res 3
se_r_next: .res 3
se_r_pad: .res 1
se_r_mode: .res 1
se_r_glyph: .res 1
se_r_color: .res 1

; Separate end anchor keeps all existing VIEWSTATE field addresses stable.
.export se_v_bottom
se_v_bottom: .res 3

; Source/rendered is view state, not document metadata. Cold init clears the
; complete VIEW page; a presentation change preserves canonical source/carets.
.segment "VIEWSTATE"
.export se_r_presentation
se_r_presentation: .res 1
