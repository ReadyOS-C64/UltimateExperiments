.ifndef SE_GEOS_CARET_UI
SE_GEOS_CARET_UI=1
.include "render/geos/caret-cache.inc"
.include "render/narrow/api8.inc"
.global se_gcc_cell,se_gcc_status,se_gcc_row
; No storage declaration: exclusive synchronous R27 UI scratch at warm tail.
GCC_UI_COLUMN=GCC_STATE+82
GCC_UI_END=GCC_STATE+88
GCC_UI_OWNER=$B2
.assert GCC_UI_END<=$D000,error,"caret UI scratch exceeds warm extent"
; CELL: owner0/1 only; overlay_frame+1/+2 -> immutable BC_SIZE11 frame.
; Requires exact FONTAC00/BITMAP6000/ATTRIBUTES4000 descriptors. Raster uses
; proven native lowercase ROM copy4800,128glyphs/inverse bit7, not overlay RAM.
; Existing BC caller disjoint-input/output contract applies. No frame writes.
; STATUS: owner4 only; shared tui_editor_status40 followed by row24 raster.
; STATUS paints onlyrow24; ROW opcode4 owner0/1 accepts row0/1/24 from
; overlay_frame+1 and converts40logicalmatrix/color cells in onecall. Foreign
; owner/invalidrow refuse before output. COLUMN,+1/+2 are the three used tailbytes.
; All operations loan/clobber existing text_ptr/screen_ptr, allocate noZP/BSS.
; Success A0/Cclear; foreign owner AB2/Cset, invalid BC A90/Cset before output.
.endif
