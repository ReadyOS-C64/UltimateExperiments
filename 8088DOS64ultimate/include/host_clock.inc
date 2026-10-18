.ifndef DOS64_HOST_CLOCK_INC
DOS64_HOST_CLOCK_INC = 1
; Explicit destructive runtime takeover token. Caller guarantees ownership of
; CIA2 timers A/B, serial control, timer IRQ masks and the CIA2 NMI policy.
; Caller must disable timer A/B interrupt masks before claim/init; these routines
; NEVER read/write ICR, TOD, ports, DDRs or NMI vectors. Prior timer state is not
; saved/restored: write-only latches and interrupt masks cannot be reconstructed.
HC_OWNED = $a5
HC_OK = 0
HC_ERR_OWNER = 1
HC_ERR_UNREADY = 2
HC_ERR_CONTROL = 3
HC_ERR_SAMPLE = 4
HC_READ_ATTEMPTS = 8
; init: requires dos64_host_clock_claim=HC_OWNED; starts FFFF-latched chained
; CIA2 A(phi2)/B(A underflow), sets ready. read: bounded coherent counter read.
; Both preserve A/X/Y/native P except returned C; C=0 success, C=1 error.
; DDR and $01 output-configured bits/effective banking are restored; hidden
; output-latch bits configured as inputs cannot be read/saved by a 6510.
; status gives reason. Successful read atomically publishes ticks[4] LE,
; bitwise complement of the running B:A downcounter, modulo 2^32. Failure
; preserves all four previously published bytes. Not reentrant / NMI-safe.
; Sampling rejects A high=FF (first 256 ticks after startup/reload), including
; cascade pipeline uncertainty; caller retries on a subsequent scheduling pass.
; Units are CIA phi2 ticks, NOT microseconds or turbo 6510 cycles. Epoch/start
; pipeline offset is intentionally unspecified; use subtraction between reads.
; Do not use intervals >=2^31 ticks, or fail to sample for a complete wrap.
; Runtime must identify/calibrate video clock domain, prove timer progress and
; turbo independence on the actual core before trusting real-time deadlines.
.endif
