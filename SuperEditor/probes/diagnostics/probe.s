.setcpu "6502"
.exportzp text_ptr
.segment "ZEROPAGE"
text_ptr: .res 2 ;existing shared resident pointer,not a diagnostic allocation
.segment "BSS"
.export se_reu_banks,se_h_dirty,se_h_phase,se_b_phase,se_clip_busy,se_r_revision
.export se_overlay_loads,se_overlay_hits,se_overlay_calls
; Minimal emitted-service consumer adapters,not an editor/overlay simulation.
se_reu_banks: .res 2
se_h_dirty: .res 1
se_h_phase: .res 1
se_b_phase: .res 1
se_clip_busy: .res 1
se_r_revision: .res 4
se_overlay_loads: .res 2
se_overlay_hits: .res 2
se_overlay_calls: .res 2
