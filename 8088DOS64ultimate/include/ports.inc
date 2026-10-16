.ifndef DOS64_PORTS_INC
DOS64_PORTS_INC = 1
IO_BYTE = 0
IO_WORD = 1
PIC_COMMAND_PORT = $0020
PIC_DATA_PORT = $0021
; dos64_io_{read,write}: descriptor port/value are little-endian words;
; width is IO_BYTE/IO_WORD. C=0 handled, C=1 unsupported port/width/command.
; Preserve host P except returned C, preserve descriptors on write and port/
; width on read; byte read changes value low only. A/X/Y may be clobbered.
; Requires ordinary C64 RAM/I/O mapping. No guest registers/FLAGS are touched.
;
; PIC20/21 and byte GLOBAL REARM writes02F2..02F7 (absent boards) are
; supported. The latter ignore data and never mutate PIC state.
; XT8255 port61 byte read/write exposes its mode0 output latch, initially48h
; as at original XT BIOS boot. This is not ATport61 timer/status semantics.
; Speaker waveform, parity faults, keyboard wire/reset effects are not modeled.
; Fixed BIOS PITcounter0 binary mode3/divisor65536/RWlohi additionally accepts
; only zero byte writes40h, tracking the nextLSB/MSB phase. Same-divisor writes
; retain the current phase, rational remainder, edge accounting and PIC state.
; Nonzero data, reads, words, controls43h and other PIT channels are rejected.
; Absent game adapter201h has explicit byte inputFFh. This is an absent-device
; profile; no joystick/button support or broader unknown-port fallback exists.
; Writes/words and neighboring/high-alias game addresses remain rejected.
; CGA 3D0..3D7 are four MC6845 index/data mirrors: selector low5bits,
; significant register masks, R14/15 RW, R16/17 RO, remaining reads rejected.
; Byte 3D8 is write-only: video enable and blink/background intensity within
; BIOS-selected geometry; geometry/colorburst changes and word cycles refuse.
; Explicit no-MDA profile: byte3B4/3B5 readsFF and ignores writes. Neighbors,
; high aliases, undefined reads and other unimplemented devices fail closed.
; CGA hardware gates require the installed HDBIOS extension; ordinary PIC/PPI
; services remain resident and usable before bootstrap. Direct port writes do
; not alter BIOS BDA software shadows. 3DA byte input is a functional canonical
; CGA beam derived from the existing virtual PIT publication, independent of
; read count and C64 VIC raster. Requires normalized ready/error-free PIT and
; original R0..9 timing. SAMPLE4 keeps last published beam; other errors refuse.
; Pure arithmetic leases FILE, rejects original C900-CFFF caller provenance,
; and returns resident before release. No CIA/FILE/UCI/PIT/IRQ state mutation.
; Nonstandard raster status, lightpen input and direct cursor overlay remain
; unsupported. Explicit debugger pause/resume follows existing PIT time policy.
; PIC word cycles preflight both 16-bit consecutive
; ports; therefore only a word at0020 succeeds. Failed cycles have no device
; effect and leave value untouched. No mirrored ports are claimed.
;
; PIC state is functional software-visible state, with no IRQ scheduling,
; input-edge capture, INTA, AEOI delivery, cascade delivery or poll support.
; ICW1/3/4 retain programmed configuration; base is ICW2&F8 for 8088 mode.
; phase:0=OCW1,2=ICW2,3=ICW3,4=ICW4. priority is lowest-priority IRQ0..7.
; read_isr/special_mask/rotate_auto are booleans. IRR/ISR are explicit latches
; reserved for a future event dispatcher. Reads never acknowledge requests.
.endif
