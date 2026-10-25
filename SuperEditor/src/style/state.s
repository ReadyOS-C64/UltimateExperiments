.setcpu "6502"
.include "style/api.inc"
.segment "STYLE_DESCRIPTOR"
se_st_descriptor:.res STYLE_KEY_BYTES
se_st_generation:.res 2
se_st_valid:.res 1
se_st_request:.res 1 ;0idle,1needed,$80last failure for this exact key
.segment "STYLE_CHECKPOINT"
.export se_st_cp_state,se_st_cp_key
se_st_cp_state:.res 79
se_st_cp_anchor:.res 3
se_st_cp_key:.res STYLE_KEY_BYTES
se_st_cp_valid:.res 1
; Root records earliest mutation since checkpoint before R1 clears damage.
; If range unknown root clears cp_valid instead. No optimistic prefix reuse.
se_st_cp_damage:.res 3
se_st_cp_dirty:.res 1
.segment "STYLE_STATE"
se_st_state:
se_st_key:.res STYLE_KEY_BYTES
se_st_rows:.res 69 ;22 canonical row starts plus exclusive bottom anchor
se_st_busy:.res 1
se_st_error:.res 1
.export st_phase,st_resume,st_budget,st_reads,st_index,st_used,st_buffer
.export st_pos,st_next,st_end,st_from,st_to,st_paint,st_style,st_row,st_col,st_cell
.export st_offset,st_finish,st_kind,st_base,st_owned,st_inline
st_phase:.res 1
st_resume:.res 1
st_budget:.res 1
st_reads:.res 1
st_index:.res 1
st_used:.res 1
st_buffer:.res 128
st_pos:.res 3
st_next:.res 3
st_end:.res 3
st_from:.res 3
st_to:.res 3
st_paint:.res 2
st_style:.res 1
st_row:.res 1
st_col:.res 1
st_cell:.res 3
st_offset:.res 2
st_finish:.res 1
st_kind:.res 1
st_base:.res 1
st_owned:.res 1
st_inline:.res 1
.ifdef SE_STYLE_GRID
; Grid plan aliases the inactive character-font window in bitmap modes.
.export st_columns,st_plan_page,st_cells
st_columns:.res 1
st_plan_page:.res 1
st_cells:.res 2
.endif
se_st_state_size=*-se_st_state
