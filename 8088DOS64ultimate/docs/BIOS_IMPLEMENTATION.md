# Synthetic BIOS implementation

Updated 2026-10-15. `src/bios.s` is independently authored 6510 assembly. It supplies the current boot/disk/query baseline; the entire IBM PC/XT BIOS contract and a complete DOS boot are still unfinished. The [architecture](ARCHITECTURE.md) remains the full target.

## Initialization and owned ROM

`dos64_bios_init` clears IVT/BDA 00000–004FF, fills the entire F0000–FFFFF ROM with FF and patches project-owned code/data through the coherent memory API. Conventional RAM outside that area and disk configuration are preserved. It temporarily selects ALL_RAM so it can populate ROM and restores the caller's memory mode on success and failure. The ready byte becomes A5 only after all initialization succeeds. Host P is preserved except returned carry; A/X/Y and public address scratch are clobbered. Cache failure is terminal and never publishes ready.

The initializer supplies 640 KiB at BDA 0413, equipment word 0021 at 0410, an empty keyboard ring, and CGA mode-3/80-column defaults. These BDA defaults do not implement a renderer or keyboard. The disk parameter table at F0300 has the configured sectors/track; its field meanings follow the pinned IBM XT listing noted in `src/bios.s`, with independently encoded bytes. The reset location FFFF:0000 contains a far jump to the synthetic bootstrap. The ROM reports the synthetic build date 10/15/26 and XT model byte FE; it is not a bundled IBM ROM.

| Guest vector/entry | Current behavior |
|---|---|
| INT 11h, F000:0120 | Ordinary guest code returns the mutable BDA equipment word, preserving DS and saved FLAGS |
| INT 12h, F000:0130 | Ordinary guest code returns the mutable BDA conventional-memory word, preserving DS and saved FLAGS |
| INT 13h, F000:0100 | Owned `OUT F1h,AL` gate invokes the coherent disk primitive, followed by ordinary guest IRET |
| INT 15h, F000:0140 | Original XT unsupported-system-service result: AH=86h, saved CF=1; no AT configuration pointer |
| INT 19h/bootstrap, F000:0110 | Owned `OUT F2h,AL` loads sector 1 into 0000:7C00, then transfers guest execution there; failure reaches ROM HLT |
| INT 1Eh | Pointer to disk parameter table F000:0300 |

Other BIOS vectors remain absent. INT 10h/16h/1Ah, timer/keyboard IRQ handlers, absent serial/printer responses and wider disk functions must be implemented before their requirements can be accepted.

## Entry recognition and guest hooks

The CPU's E6 dispatch calls `dos64_bios_port` only for the private bootstrap/disk protocol. The gate requires ready=A5, translates CS:(IP−2), and whitelists the exact physical opcode address F0100/F0110 with its matching port. Segment aliases of those addresses work; arbitrary guest E6 instructions using F1/F2 cannot invoke native service. General PC port I/O remains unsupported in this baseline.

Software INT always follows the writable IVT and normal guest stack. Disk callbacks do not intercept interrupt numbers. A replaced vector can handle or chain to the owned ROM, including `PUSHF; CALL FAR`. The disk wrapper changes only saved CF at SS:(SP+4); the ROM's actual IRET restores the frame and other caller flags. INT 11h/12h execute ordinary guest instructions and read dirty mutable BDA bytes through the CPU bus. INT 15h modifies saved CF through its guest frame, preserves BP and other caller registers except AH, and returns through IRET.

Guest disk errors return through the ordinary BIOS frame. Coherent guest-cache failure sets native host-error state and remains a terminal CPU memory diagnostic. Private gate rejection is an unsupported-I/O diagnostic. None is replaced with a fabricated original-8088 invalid-opcode exception.

## Genuine DOS bootstrap evidence

The Zig/Peddle integration seeds only the complete immutable raw floppy into its owned REU media slot. It initializes the actual assembly cache/disk/BIOS/CPU, starts at FFFF:0000, and lets BIOS and original sector code perform every guest-memory load. No host kernel loader or native INT 21h replacement supplies DOS state.

The target reaches IO.SYS at 0070:0000 after 392 completed instructions and 12,019,126 native CPU step cycles. An independent FAT12 oracle checks all 22,398 IO.SYS bytes and the complete 51-sector raw extent that this bootloader actually reads; the file itself rounds to 44 sectors. Extra sectors/padding are compared too. The original source image and in-REU floppy remain byte-identical. The test continues after handoff and records the next unsupported behavior with the last 32 state snapshots, code bytes, hashes, reads and bounded execution counts in `build/dos-boot-first.json`, retained as [kernel handoff evidence](../agentworking/evidence/dos-kernel-handoff-20261015.json).

The current continuation stops at PIC `OUT 20h` (`E6 20`) at 0070:2BFB after 2,335 completed instructions. COMMAND.COM has not reached a prompt. Native startup initializes then idles; Ultimate/IEC media import and the runtime dispatch loop remain required work.

## Verification and limits

Actual-assembly tests assert exact ROM/IVT/BDA bytes, conventional-RAM/media preservation, mode restoration and partial initialization failure; private gate aliases/rejection; INT disk success/errors and saved flags; guest far-call chaining; normal reset and failed bootstrap; terminal cache errors; dirty mutable BDA queries; and XT INT 15h return registers/frame/branch behavior. The real DOS test adds complete source/kernel/raw-extent identity and continuation diagnostics.

These are functional Peddle tests with a synchronous REU model. They do not establish hardware event timing, physical BIOS execution, UCI/IEC persistence, display/keyboard behavior, a complete PC BIOS, a DOS prompt or XT throughput.
