.setcpu "6502"
.include "layout/api.inc"
.segment "BSS"
se_l_mode: .res 1
se_l_pan: .res 3
se_l_manual: .res 1
se_l_valid: .res 1
se_l_original: .res 5
se_l_append: .res 5
se_l_generation: .res 2
se_l_revision: .res 4
se_l_top: .res 3
se_l_scan: .res 3
se_l_rows: .res 1
se_l_col: .res 1
se_l_seen: .res 1
se_l_index: .res 1
se_l_preferred: .res 3
se_l_column: .res 3
se_l_remaining: .res 3
se_l_saved_preferred: .res 3
se_l_active: .res 1
se_l_end: .res 3
se_l_caret: .res 3
; R1 requests a bounded C11 reveal before any pixels/draw sequence publish.
; Suffix preserves every existing resident and layout field address.
se_l_need_wrap: .res 1

; No new resident BSS: width request belongs to the snapshot's view state,
; captured active-job dimension uses one of NAVSTATE's five spare bytes.
.segment "VIEWSTATE"
se_v_columns: .res 1
.assert se_v_columns >= $8C00 .and se_v_columns < $8D00,lderror,"view width outside VIEWSTATE"
.segment "NAVSTATE"
se_n_view_columns: .res 1
.assert se_n_view_columns >= $9180 .and se_n_view_columns < $9200,lderror,"captured width outside NAVSTATE"
