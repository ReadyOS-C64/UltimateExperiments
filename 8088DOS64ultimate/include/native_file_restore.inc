.ifndef DOS64_NATIVE_FILE_RESTORE_INC
DOS64_NATIVE_FILE_RESTORE_INC=1
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
; Standalone whole-file development restoration engine. Direct resident FILECODE,
; fixed UCI target1/baseDF1C, exclusive CIA2/UCI/REU and RAM+I/O mapping.
; Caller supplies path in uci_command+3, pathLen including NUL, expected IEEE
; reflected CRC32, and monotonic16 elapsed units of4096 PAL-phi2 ticks.
; Start explicitly resolves unknown firmware handle with CLOSE before OPEN.
; Poll gaps must remain below32768 units; elapsed is accumulated into32 bits.
; Four512-byte READ/CRC groups precede each2048-byte REU DMA; only000000..3FFFFF.
; Exact4MiB, one-byte EOF, CRC match, accepted CLOSE and known handle0 precede
; complete=1. Read-only source; no file WRITE. CRC is corruption detection.
; Operation stops by590 nominal PAL seconds; cleanup bounded by600 inclusive.
; Host must independently enforce600 wall-clock seconds, capture failure RAM,
; retain immutable verified backup and reload the original service for full
; 4MiB byte comparison. Unknown ownership/cleanup failure must remain explicit.
; Firmware3.14 accepted CLOSE does not establish an underlying fclose result.
.endif
