.ifndef SE_GRID_CACHE_API
SE_GRID_CACHE_API=1
; Disposable exact-input cache. Foreground/nonreentrant, no ZP loans.
; BEGIN A=60/80, X=body-popup-visible (0/1). ROW/COMMIT A=physical2..23.
; ROW returns A0 clean/A1 dirty; COMMIT only after successful leaf paint.
; BEGIN/ROW/COMMIT/FINISH return Cclear for cache faults (render-all fallback).
; Invalid dimensions return A=$7B/Cset before any write. FINISH only after a
; complete frame. INVALIDATE on EVERY mode/font/palette/external-output change.
; BEGIN includes unfinished UI from an aborted frame when forcing all rows.
; A dirty ROW invalidates itself BEFORE paint, including failed leaf paint.
; Input must remain byte-identical between ROW, successful leaf and COMMIT.
; Source packet is all240 contiguous G_CHARS/G_ROLES/G_FLAGS bytes, even60mode.
; Clobbers A/X/Y/P, CPU stack and resident REU request/counters; no other RAM
; except nine owned state bytes and comparison buffer $8A44..$8B33.
; $FE is reserved exclusively for this derived grid cache (not object types).
GRID_CACHE_OWNER=$FE
GRID_CACHE_TEMP=$8A44
GRID_CACHE_ROWS=22
GRID_CACHE_PACKET=240
.assert GRID_CACHE_TEMP+GRID_CACHE_PACKET <= $8C00,error,"cache temp crosses VIEW"
.ifndef GRID_CACHE_IMPLEMENTATION
.import se_grid_cache_begin,se_grid_cache_row,se_grid_cache_commit
.import se_grid_cache_finish,se_grid_cache_invalidate
.ifndef EDITOR_OVERLAY
.import se_gc_handle,se_gc_epoch,se_gc_width,se_gc_valid,se_gc_previous_ui,se_gc_current_ui
.endif
.endif
.endif
