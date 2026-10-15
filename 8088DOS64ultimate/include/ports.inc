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
; Only PIC20/21 are supported. Word cycles preflight both 16-bit consecutive
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
