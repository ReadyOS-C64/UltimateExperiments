.ifndef DOS64_IMAGE_IMPORT_INC
DOS64_IMAGE_IMPORT_INC=1
IMPORT_IDLE=0
IMPORT_BUSY=1
IMPORT_DONE=2
IMPORT_FAILED=3
IMPORT_ERR_INPUT=1
IMPORT_ERR_FILES=2
IMPORT_ERR_SHORT=3
IMPORT_ERR_EXTRA=4
IMPORT_ERR_CRC=5
IMPORT_ERR_DMA=6
IMPORT_ERR_TIMEOUT=7
IMPORT_ERR_CLOSE=8
; Cold startup-only module at $7000-$7FFF. Never call after bitmap ownership.
; Caller initializes UCI/files/overlay, provides OPEN ASCII path in command+3,
; files_path_len and files_target, expected standard CRC32 (LE, IEEE reflected),
; import_now monotonic16 ticks, import_timeout 1..$7FFF ticks. Caller updates
; now on every poll, gaps < $8000 ticks; UCI timeout/recovery separately set.
; Path/target/expected CRC/timeout are immutable until terminal completion.
; Requires known closed single-file owner, exclusive REU/UCI/cache operation,
; RAM+I/O map is established/restored here. No IRQ/NMI may share these owners.
; Public calls preserve native P except C and $00/$01 driven bits; clobber A/X/Y.
; start returns C=1 on rejection without replacing an accepted request. poll
; C=1 rejects nonbusy calls. Terminal outcome is state/error, not poll carry.
; Each poll does one file poll/start, one512-byte DMA, or at most16 CRC bytes.
; Total timeout aborts transport once then allows its separate elapsed recovery
; timeout and one CLOSE attempt. Handle 2/cleanup_error means ownership unknown;
; never reinitialize files to pretend it is closed. Failure always loaded=0.
; Exactly720*512 bytes -> REU $100000-$159FFF, then1-byte EOF probe, CRC match,
; successful CLOSE and known handle0 required before loaded=1. Never WRITE.
; Close is firmware accepted closure; v3.14 does not report fclose result. This
; is read-only import, not persistence proof. CRC protects stale-error reads but
; is accidental corruption detection, not an authenticity/security primitive.
.endif
