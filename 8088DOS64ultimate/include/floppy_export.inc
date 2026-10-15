.ifndef DOS64_FLOPPY_EXPORT_INC
DOS64_FLOPPY_EXPORT_INC=1
; Standalone prototype, exclusive paused guest/UCI/REU ownership.
; init is startup-only. Caller supplies immutable owned=$a5, paused=$a5,
; bank=$10 or $18, path_len2..128 (absolute raw bytes/NUL) and path[128].
; now is monotonic 16-bit elapsed time, maximum gap $7fff ticks. limit is
; 32-bit total tick budget, default144323 (~600 PAL seconds at4096PHI2/tick).
; Calls preserve native P except C and $00/$01; A/X/Y clobbered. start C=1
; rejects without wire/DMA/state mutation. state1 busy,2 verified,3 failed.
; verified implies all720 sectors +EOF after CLOSE/reopen and known final
; CLOSE. It does not imply power-fail durability. uncertain stays1 on failure;
; REU source is NEVER written, and no delete/rename/overwrite is implemented.
EXPORT_IDLE=0
EXPORT_BUSY=1
EXPORT_DONE=2
EXPORT_FAILED=3
EXPORT_ERR_FILES=1
EXPORT_ERR_DMA=2
EXPORT_ERR_SHORT=3
EXPORT_ERR_COMPARE=4
EXPORT_ERR_EXTRA=5
EXPORT_ERR_TIME=6
EXPORT_ERR_CANCEL=7
.endif
