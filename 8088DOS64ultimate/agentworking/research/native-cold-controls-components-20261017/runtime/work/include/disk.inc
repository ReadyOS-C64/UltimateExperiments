.ifndef DOS64_DISK_INC
DOS64_DISK_INC = 1
DISK_OK = $00
DISK_ERR_COMMAND = $01
DISK_ERR_SECTOR = $04
DISK_ERR_DMA = $09
DISK_ERR_CONTROLLER = $20
DISK_ERR_NOT_READY = $80

; Native dual-floppy control request. Not an emulated DOS/INT21 interface.
; All calls require exclusive paused-native (diag.stage=5) or cold-open ownership,
; overlay-ready, RAM+I/O mapping; preserve native P except C, clobber A/X/Y.
; PREPARE returns a free complete360KiB arena (100000,180000,380000), token and
; old mount/content snapshots. Caller loads only this free arena, then publishes
; COMPLETE=A5 after exact full image/CRC/close validation. COMMIT checks geometry
; and snapshots before atomically changing the descriptor; it never copies over
; mounted media. Rotating the three arenas makes repeated swaps safe. CANCEL
; releases only the matching token. Old media remains authoritative on failure.
; DIRTY discard requires FLAGS bit1. FLAGS bit0 is incoming readonly, captured
; at PREPARE. CLEAN requires an independent successful save/reopen proof from
; the caller plus exact mount/content snapshots and a new binding cookie.
FQ_OP=0
FQ_DRIVE=1
FQ_FLAGS=2
FQ_COMPLETE=3
FQ_CAPACITY=4
FQ_BASE=5
FQ_LENGTH=8
FQ_TOKEN=11
FQ_MOUNT=15
FQ_CONTENT=19
FQ_BIND=23
FQ_SIZE=27
FOP_PREPARE=1
FOP_COMMIT=2
FOP_CANCEL=3
FOP_EJECT=4
FOP_CLEAN=5
FOP_PROTECT=6 ; optional MEDIA_BINDING session-only policy, exact snapshots
FERR_INPUT=1
FERR_BUSY=2
FERR_DIRTY=3
FERR_CONTEXT=4
FERR_IO=5
FERR_GEOMETRY=6
FERR_GUARD=7
FERR_GENERATION=8
FLOPPY_BYTES=$05A000
FLOPPY_SPARE=$380000
FLOPPY_STAGE_END=$3DA000
INSTALLER_STAGE=$3E0000
INSTALLER_STAGE_END=$3F0000
INSTALLER_ANCHOR=$3FF000
INSTALLER_ANCHOR_END=$400000
.assert FLOPPY_STAGE_END <= INSTALLER_STAGE, error, "floppy swap overlaps installer stage"
.assert INSTALLER_STAGE_END <= INSTALLER_ANCHOR, error, "installer stage overlaps anchor"
.assert INSTALLER_ANCHOR_END = $400000, error, "installer anchor exceeds minimum REU"
.endif
