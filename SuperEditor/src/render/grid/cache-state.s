.setcpu "6502"
.export se_gc_handle,se_gc_epoch,se_gc_width,se_gc_valid,se_gc_previous_ui,se_gc_current_ui
.segment "BSS"
; Cold-clear with resident BSS. Retained ownership belongs only to this module;
; nobody may free/rebind its live handle. No stale-epoch frees are attempted.
se_gc_handle: .res 1
se_gc_epoch: .res 2
se_gc_width: .res 1
se_gc_valid: .res 3
se_gc_previous_ui: .res 1
se_gc_current_ui: .res 1
