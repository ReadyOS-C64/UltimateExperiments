; View-only layout.0 grid soft wrap,1 logical lines with horizontal pan.
LAYOUT_ID=11
L_BEGIN=4
L_STEP=5
.global se_layout_prepare,se_layout_service
.global se_l_mode,se_l_pan,se_l_manual,se_l_valid
.global se_l_original,se_l_append,se_l_generation,se_l_revision,se_l_top
.global se_l_scan,se_l_rows,se_l_col,se_l_seen,se_l_index
.global se_l_preferred,se_l_column,se_l_remaining,se_l_saved_preferred
.global se_l_active,se_l_end
.global se_l_caret
.global se_l_need_wrap

; Requested grid width.0 is the legacy40-column view; only40,60,80 are valid.
; Set only at an idle view boundary, invalidate derived render/layout maps.
; Active C8/C11 continuations capture normalized width and refuse changes74.
; Invalid dimensions fail7B before source-view writes or read acquisition.
.global se_v_columns,se_n_view_columns
