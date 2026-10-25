.ifndef SE_NARROW_GRID_API
SE_NARROW_GRID_API=1
; R16/R17 leaf operations. se_overlay_frame+1/+2 contain caller frame pointer.
GRID_ROW=0
GRID_CELL8=1
GRID_ADMIT=2 ;pure checked-overlay admission; no frame/output dereference
GRID_FONT=$A800
GRID_NATIVE_FONT=$AC00
GRID80_ID=16
GRID60_ID=17
.endif
