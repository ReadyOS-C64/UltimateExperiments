.ifndef SE_LIFECYCLE_RESUME
SE_LIFECYCLE_RESUME=1
.include "lifecycle/adapter.inc"
; Fresh COLDprelude runs at0A00, no saved stack/C/R continuation. It resets
; only derived/transient state and invokes C29 hardware5 then actual se_idle.
; Caller guarantees no external NMI/IRQ handler race during this controlled
; same-process proof. Existing known editor hooks remain installed. Full host
; IRQ/vector handoff/native held-key policy remains outside this primitive.
.endif
