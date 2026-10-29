.ifndef SE_GRID_EDITOR_API
SE_GRID_EDITOR_API=1
; Foreground C16, lease-free. Source width60/80 only. All phase storage is in
; COW output suffix8880..8BFF, disjoint from diagnostics/VIEW/FILE/NAV/hot.
GRID_EDITOR_ID=16
GRID_SOURCE=1
GRID_FINALIZE=2
GRID_MODE=3
GRID_CHROME=4 ;stateless sharedlogical40chrome;owner0/1, no phase access
G_NR=$8880
G_CHARS=G_NR+68
G_ROLES=G_CHARS+80
G_FLAGS=G_ROLES+80
G_BC=G_FLAGS+80
g_width=G_BC+11
g_backend=g_width+1
g_row=g_backend+1
g_col=g_row+1
g_found=g_col+1
g_index=g_found+1
g_x=g_index+1
g_y=g_x+1
g_w=g_y+1
g_h=g_w+1
g_skip=g_h+1
g_start=$89D0
g_next=g_start+3
g_end=g_next+3
g_pos=g_end+3
g_column=g_pos+3
g_delta=g_column+3
g_ends=$8A00
g_style_ptr=g_ends+66
.assert g_style_ptr+2 <= $8C00,error,"grid workspace overlaps VIEW"
.endif
