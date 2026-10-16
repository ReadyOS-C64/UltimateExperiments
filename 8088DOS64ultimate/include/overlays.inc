.ifndef DOS64_OVERLAYS_INC
DOS64_OVERLAYS_INC = 1
OV_FILE = 1
OV_TEXT = 2
OV_INPUT = 3
OV_PIT = 4
OV_GFX = 5
OV_HD = 6
OV_HD_SOURCE = $9800
OV_PIT_SOURCE = $8800
OV_GFX_SOURCE = $9000
OV_INPUT_SOURCE = $8000
OV_READY = $A5
OV_WINDOW = $C900
OV_WINDOW_SIZE = $0700
OV_HEADER = $0010
OV_SLOT_SIZE = $0800
OV_SOURCE = $6000
OV_ASSETS = $340000
OV_ERR_BUSY = 1
OV_ERR_UNREADY = 2
OV_ERR_ID = 3
OV_ERR_HEADER = 4
OV_ERR_DMA = 5
OV_ERR_CAPACITY = 6
OV_ERR_ORIGIN = 7
OV_ERR_COLD = 8
; Resident synchronous, nonreentrant manager; same RAM+I/O map contract as cache.
; All APIs preserve native P except C, clobber A/X/Y. init is startup-only.
; bootstrap validates all five source headers before any immutable-slot copy.
; Only a successful bootstrap releases 6000–6FFF and8000–97FF to the bitmap owner. It is
; idempotent thereafter: the startup bytes are never consulted again.
; acquire uses dos64_overlay_requested and HOLDS busy until release. Only call
; acquire/release from resident code. All overlaid entry calls MUST occur while
; busy is held. Resident wrappers enforce this for files, INPUT and TEXT.
; TEXT is canonical718-byte renderer +245-byte VIC setup/restore, total963.
; TEXT row/setup/restore reject cold_open!=0 after busy/reentry checks; only
; dos64_cold_release grants bitmap/VIC ownership after real BIOS/import cleanup.
; Fonts4400–47FF and4800–4FFF are loaded non-executable data, never overlays.
; Wrappers reject reentry without changing requested/current/busy ownership.
; Failed replacement invalidates current, releases lock, and never calls code.
; REU assets are immutable after bootstrap: exact headers are checked on every
; replacement, but payload CRC is not recomputed; external mutation/corruption
; of payload or execution window is outside this contract. No persistent code
; pointers. State is resident; file poll and whole-row retries survive switches.
; Exclusive REU and C000–C00F scratch ownership during bootstrap/acquire; no
; interrupt may invoke REU/cache/range/overlay operations. Hardware capacity
; >=4 MiB is supplied by caller in reu_mib (4..16) AFTER init, based on
; separately verified hardware configuration, never inferred from REC bits.
.endif

; Native SAVE additionally installs immutable SAVER asset7 from startup B000-B7FF
; into REU343000-3437FF. Only paused SAVE may borrow cache frames24..31
; as B000-BFFF: code B010-B7FF, compare staging B800-B9FF. FILE remains
; exclusive C900-CFFF; permanent HDBIOS continuations restore all32frames.
