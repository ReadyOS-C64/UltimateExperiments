.ifndef DOS64_FLOPPY_EXPORT_INC
DOS64_FLOPPY_EXPORT_INC=1
; Standalone prototype, exclusive paused guest/UCI/REU ownership.
; init is startup-only. Caller supplies immutable owned=$a5, paused=$a5,
; bank=$10 or $18, path_len2..128 (absolute raw bytes/NUL) and path[128].
; now is monotonic 16-bit elapsed time, maximum gap $7fff ticks. limit is
; 32-bit total tick budget, default144323 (~600 PAL seconds at4096PHI2/tick).
; Calls preserve native P except C and $00/$01; A/X/Y clobbered. start C=1
; rejects without wire/DMA/state mutation. state1 busy,2 verified,3 failed.
; verified requires fresh successful FILE_INFO after CLOSE/reopen with a
; declared LE32size exactly368640, then720matching sectors, zero-data EOF and
; known final CLOSE. It proves the observed metadata/content/closure contract,
; not filesystem flush, protection from external mutation or power-fail
; durability. The caller must also bind media generation before clean UI. uncertain stays1 on failure;
; Each logical512-byte sector is written as two256-byte requests. The public
; write_half and first failure_half (0/1) locate a failed write within the sector
; when failure_phase is2 (DMA) or3 (WRITE); other phases have no write-half meaning.
; sectors counts only completed logical sectors, never successful first halves.
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
EXPORT_ERR_LENGTH=8
.endif
