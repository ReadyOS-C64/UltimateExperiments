.ifndef DOS64_CLOCK_INC
DOS64_CLOCK_INC = 1
CLOCK_BDA_LOW = $6C
CLOCK_DAY = $1800B0
; service implements original XT INT1Ah. AH0 reads CX:DX, AL=overflow and
; clears overflow. AH1 sets CX:DX unchanged/unvalidated and clears overflow;
; AH is decremented for EVERY nonzero function, including unsupported RTC
; functions. All guest FLAGS and other registers are preserved. Return C=0;
; only coherent cache failure returns C=1 and host_error=1. No frame patch.
;
; advance consumes <=256 explicit virtual ticks per call. Input/output count
; is a word; done reports this call's consumed ticks. Call until count=0.
; Original equality rollover at001800B0h is retained even after invalid sets,
; including 32-bit wrap; overflow becomes1, never an accumulated day count.
; count=0 performs no memory access. A failed initial cache acquisition leaves
; BDA/count unchanged and done=0; retry is safe. All five BDA bytes share one
; cache page, so after acquisition no later transfer/eviction can partially
; commit them. Requires synchronous ordinary RAM/I/O mapping; non-reentrant.
; Native P except C preserved; A/X/Y and public address/value scratch clobbered.
; No PIT, host time, IRQ0, INT1Ch, floppy motor or guest instruction pacing.
.endif
