.ifndef DOS64_UCI_INC
DOS64_UCI_INC = 1
; Ultimate Command Interface, generic bounded streaming transport.
; Calls: init, start, poll, accept, abort. All preserve A/X/Y and native P except C.
; C=1 only for a rejected call; asynchronous results are in state/error.
; init installs defaults; caller then chooses base DF1C/DE1C/DFFC, fills command
; and command_len, and updates now before every other call. now is a caller
; supplied monotonic 16-bit tick, NOT CPU poll count. Durations must be 1..7FFF;
; callers must poll within <8000 ticks even while a BLOCK awaits acceptance.
; Command length is 1..895 conservatively: pinned FPGA saturates its command
; pointer at 895 (documented backing queue size is 896). Response blocks >895
; cannot terminate on that FPGA; 896 reads with DATA_AV still set fail protocol.
; Firmware status publication uses 8-bit length: max255 (256 wraps to zero).
; start validates/detects, synchronizes, uploads <=16 bytes per poll, then PUSH.
; BLOCK exposes one fully drained response; consumer copies it then accept.
; Both queues are always drained even after capacity truncation. No next block
; is accepted until the consumer releases this one. Target status bytes are
; opaque: transport DONE does not imply a successful Ultimate DOS operation.
; Timeout/error/cancel request ABORT once and recover with a separate deadline.
; Following an accepted start, FAILED + recovery_failed=0 means verified quiet
; idle; =1 means reset/recovery by caller required. INPUT/ID rejected starts
; perform no command but do not establish remote quiet-idle ownership.
; No-reply commands (target byte bit7) are rejected; this API requires a reply.
; No command may start while transport is active. Configuration/command must
; remain immutable until DONE/FAILED; only now and response-consumption calls
; may change while active. init is startup-only (never reset an active transfer).
; UCIBUFFER needs 2048 bytes of writable, unbanked native RAM outside I/O.
; Exclusive ownership/non-reentrant. No IRQ generation, DMA or TRIGGER mode.
UCI_IDLE = 0
UCI_SYNC = 1
UCI_UPLOAD = 2
UCI_WAIT = 3
UCI_DRAIN = 4
UCI_BLOCK = 5
UCI_ACK = 6
UCI_FINAL = 7
UCI_RECOVER = 8
UCI_DONE = 9
UCI_FAILED = 10
UCI_ERR_INPUT = 1
UCI_ERR_ID = 2
UCI_ERR_TIMEOUT = 3
UCI_ERR_PROTOCOL = 4
UCI_ERR_CANCEL = 5
UCI_ERR_STALE = 6
UCI_ERR_OVERFLOW = 7

.endif
