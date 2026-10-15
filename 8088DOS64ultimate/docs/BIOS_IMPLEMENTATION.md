# Synthetic BIOS implementation

Updated 2026-10-15. `src/bios.s` is independently authored 6510 assembly. It supplies boot/disk/query, logical video and absent serial/printer services; the entire IBM PC/XT BIOS contract and a complete DOS boot are still unfinished. The [architecture](ARCHITECTURE.md) remains the full target.

## Initialization and owned ROM

`dos64_bios_init` clears IVT/BDA 00000–004FF, fills the entire F0000–FFFFF ROM with FF and patches project-owned code/data through the coherent memory API. Conventional RAM outside that area and disk configuration are preserved; logical mode-3 initialization also owns the 16 KiB CGA aperture. It temporarily selects ALL_RAM so it can populate ROM and restores the caller's memory mode on success and failure. The ready byte becomes A5 only after all initialization succeeds. Host P is preserved except returned carry; A/X/Y and public address scratch are clobbered. Cache failure is terminal and never publishes ready.

The initializer supplies 640 KiB at BDA 0413, equipment word 0021 at 0410, an empty keyboard ring, and CGA mode-3/80-column defaults. The initializer invokes the actual logical video mode-3 service, preserving guest AX, clearing all 16 KiB CGA VRAM to space/07h and setting BDA palette 30h. These guest-state operations do not implement a C64 renderer or keyboard. The disk parameter table at F0300 has the configured sectors/track; its field meanings follow the pinned IBM XT listing noted in `src/bios.s`, with independently encoded bytes. The reset location FFFF:0000 contains a far jump to the synthetic bootstrap. The ROM reports the synthetic build date 10/15/26 and XT model byte FE; it is not a bundled IBM ROM.

| Guest vector/entry | Current behavior |
|---|---|
| INT 10h, F000:0150 | Owned OUT F3h gate for logical CGA/text services, followed by ordinary IRET |
| INT 14h, F000:0160 | Owned OUT F4h gate for accurate absent serial-device behavior, followed by IRET |
| INT 17h, F000:0170 | Owned OUT F5h gate for accurate absent printer-device behavior, followed by IRET |
| INT 11h, F000:0120 | Ordinary guest code returns the mutable BDA equipment word, preserving DS and saved FLAGS |
| INT 12h, F000:0130 | Ordinary guest code returns the mutable BDA conventional-memory word, preserving DS and saved FLAGS |
| INT 13h, F000:0100 | Owned `OUT F1h,AL` gate invokes the coherent disk primitive, followed by ordinary guest IRET |
| INT 15h, F000:0140 | Original XT unsupported-system-service result: AH=86h, saved CF=1; no AT configuration pointer |
| INT 19h/bootstrap, F000:0110 | Owned `OUT F2h,AL` loads sector 1 into 0000:7C00, then transfers guest execution there; failure reaches ROM HLT |
| INT 1Eh | Pointer to disk parameter table F000:0300 |

INT 16h/1Ah, timer/keyboard IRQ handlers and wider disk functions remain unfinished. Present serial/printer devices are explicitly unsupported. Logical video is implemented; host rendering remains ahead.

## Entry recognition and guest hooks

The CPU's E6 dispatch calls `dos64_bios_port` for the private bootstrap/disk/video/absent-device protocol. The gate requires ready=A5, translates CS:(IP−2), and whitelists the exact physical opcode addresses F0100/F0110/F0150/F0160/F0170 with their matching ports. Segment aliases of those addresses work; arbitrary guest E6 instructions using the private ports cannot invoke native service. General IN/OUT now dispatches to the functional PIC described in [PC ports](PORTS_IMPLEMENTATION.md); other device ports remain unsupported.

Software INT always follows the writable IVT and normal guest stack. Disk callbacks do not intercept interrupt numbers. A replaced vector can handle or chain to the owned ROM, including `PUSHF; CALL FAR`. The disk wrapper changes only saved CF at SS:(SP+4); the ROM's actual IRET restores the frame and other caller flags. INT 11h/12h execute ordinary guest instructions and read dirty mutable BDA bytes through the CPU bus. INT 15h modifies saved CF through its guest frame, preserves BP and other caller registers except AH, and returns through IRET.

Guest disk errors return through the ordinary BIOS frame. Coherent guest-cache failure sets native host-error state and remains a terminal CPU memory diagnostic. Private gate rejection is an unsupported-I/O diagnostic. None is replaced with a fabricated original-8088 invalid-opcode exception.

## Genuine DOS bootstrap evidence

The Zig/Peddle integration seeds only the complete immutable raw floppy into its owned REU media slot. It initializes the actual assembly cache/disk/BIOS/CPU, starts at FFFF:0000, and lets BIOS and original sector code perform every guest-memory load. No host kernel loader or native INT 21h replacement supplies DOS state.

The current slice reaches IO.SYS at 0070:0000 after 392 completed instructions and 11,860,775 native CPU step cycles. An independent FAT12 oracle checks all 22,398 IO.SYS bytes and the complete 51-sector raw extent that this bootloader actually reads; the file itself rounds to 44 sectors. Extra sectors/padding are compared too. The original source image and in-REU floppy remain byte-identical. The test continues after handoff and records the next unsupported behavior with the last 32 state snapshots, code bytes, hashes, reads and bounded execution counts in `build/dos-boot-first.json`, retained as [kernel handoff evidence](../agentworking/evidence/dos-kernel-handoff-20261015.json).

The original storage continuation stopped at PIC `OUT 20h` (`E6 20`) at 0070:2BFB after 2,335 completed instructions. PIC integration passed that instruction and reached absent serial BIOS INT 14h after 2,347 instructions. Logical video/absent-device integration now reaches missing clock BIOS INT 1Ah after 2,542 instructions; continuation step cycles are 26,023,384, separate from 26,360,254 setup cycles. COMMAND.COM has not reached a prompt. Native startup initializes then idles; Ultimate/IEC media import and the runtime dispatch loop remain required work.

## Verification and limits

Actual-assembly tests assert exact ROM/IVT/BDA bytes, conventional-RAM/media preservation, mode restoration and partial initialization failure; private gate aliases/rejection; INT disk success/errors and saved flags; guest far-call chaining; normal reset and failed bootstrap; terminal cache errors; dirty mutable BDA queries; and XT INT 15h return registers/frame/branch behavior. The real DOS test adds complete source/kernel/raw-extent identity and continuation diagnostics.

These are functional Peddle tests with a synchronous REU model. They do not establish hardware event timing, physical BIOS execution, UCI/IEC persistence, display/keyboard behavior, a complete PC BIOS, a DOS prompt or XT throughput.

## Logical video and absent-device implementation

The verified combined slice adds whitelisted ordinary INT/IRET ROM entries at F000:0150 for INT 10h (`OUT F3h,AL; IRET`), F000:0160 for INT 14h (`OUT F4h,AL; IRET`) and F000:0170 for INT 17h (`OUT F5h,AL; IRET`). Each still requires initialized BIOS state, the matching private port and exact physical opcode address, including legitimate segment aliases. Arbitrary guest OUT cannot invoke a callback. Successful native services preserve guest FLAGS; ordinary guest IRET restores the original frame. Fatal coherent-memory errors propagate through the separate service/BIOS host-error latches.

`src/video.s` supplies logical CGA video state and memory operations through the coherent guest bus. AH=00 supports modes 0–6 and clears all 16 KiB VRAM deterministically. AH=01/02/03 handles cursor shape/position, AH=05 the active page, AH=06/07 bounded text scrolling, AH=08/09/0A text cells, AH=0C/0D CGA pixel read/write including XOR, AH=0E text teletype and AH=0F raw mutable BDA queries. Text preserves exact CP437 bytes/attributes. Repeated writes preserve the cursor and wrap a 16-bit B800 offset; bytes outside CGA backing still obey PC bus policy. Scroll operations use the active text page, preserve overlap order and clear a bounded window for zero or excessive line counts. Malformed geometry/windows and unsupported services are rejected explicitly.

This is guest-visible logical video support. There is no C64 font, renderer, screen presentation, CGA port/retrace implementation, graphics glyph teletype or physical readability acceptance. Mode 7, EGA preserve-clear behavior, light pen AH=04 and palette AH=0B remain unsupported. Native service scratch resides in DEVICESTATE and code in DEVICECODE at 5000–5FFF. Deep cache-error exits restore the saved native SP to unwind private helper calls; partial guest writes remain terminal diagnostics rather than rollback.

`src/aux_bios.s` implements accurate absent-device responses for original XT serial/printer calls. It reads the mutable BDA device-base word before AH dispatch: a zero base returns all guest state unchanged, including AX, rather than inventing a timeout. Serial uses 0040:(DX*2); printer reads 0040:(0078+DX) before 0040:(0008+DX*2). Original 16-bit index arithmetic wraps without a modern range guard, including DX=8000h aliasing device zero. A nonzero base or unsupported vector is explicitly unsupported; this does not emulate serial/printer hardware. Dirty BDA bytes are authoritative. Failed coherent reads set a fatal host-error latch.

Private component checks passed 10 video, 10 adjust and 8 auxiliary-BIOS test blocks. Global linked acceptance passes 205 Zig/Peddle tests, 57 tooling checks, all 5,701 selected hardware cases and 12 profile samples. [Current evidence](../agentworking/evidence/video-adjust-bios-20261015.json) retains exact source/map/trace identities. The global integration tests also exercise normal INT/IRET query and absent-device frames, aliases, wrong gates and terminal cache errors.
