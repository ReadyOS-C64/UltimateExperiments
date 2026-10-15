# Research record and source register

Inspected 2026-10-14 (America/Los_Angeles). Distinguish **local observation**, **source-backed fact**, **proposed design**, and **unmeasured hypothesis**. The user's pasted ChatGPT discussion is useful background, not a specification or evidence of hardware performance.

## Local observations

| Item | Observed evidence | Planning consequence |
|---|---|---|
| Project contents | Three `.img` files in `reference/`; no emulator implementation | No existing project architecture to preserve |
| Disk size/BPB | All 368,640 bytes, FAT12, 512-byte sectors, 2 sectors/cluster, 720 sectors, 9 sectors/track, 2 heads; 55AA boot trailer | First storage profile is 360 KiB, 40-cylinder floppy; fits inside D81 SEQ file |
| Disk 1 | IO.SYS, MSDOS.SYS, COMMAND.COM, DOS tools and CONFIG.SYS; subsequent cloned DOSBox boot reports MS-DOS 3.30 | Primary boot fixture; retain original CONFIG behavior |
| Disk 2 | Utility files, no IO.SYS/MSDOS.SYS/COMMAND.COM | Data/utility disk, not independently bootable from these files |
| Disk 3 | DOS system binaries hash-identical to disk 1, GWBASIC.EXE, HDFORM/HDPARK; different boot sector/OEM bytes | Later BASIC/CGA fixture; do not infer version/validity from OEM string |
| Configuration | Disk 1 contains `c:` and `device=c:\dos\ansi.sys`; disk 3 includes `config.sys` and `control-c` lines | Observe original diagnostics; use separately hashed minimal/driver test copies |
| ZeroPage | `../../zig64` README/testing/ABI/memory docs, runner, C++ shim, fixtures | Copy testing architecture, not compiler/runtime as target |
| Zig test idiom | Fixture discovery, linker label hooks, C imports, `std.testing.expectEqual`, KERNAL return/memory assertions | Host Zig behavior tests around assembled target routines |
| ReuSQL64 | ca65/cc65 builds, configurable REU shim, Zig runner, .NET VICE plans, independent c1541 extraction | Good model for assembly artifact tests and disk persistence evidence |
| ReadyFS | Asynchronous UCI code and failure tests; prior protocol/ASCII/banking lessons | Port protocol semantics with tests; do not copy its whole application |
| Local tools | Zig 0.16.0, DOSBox-X 2026.01.02 SDL2; NASM, x64sc, c1541, cc65 toolchain paths found | No need to install DOSBox now; pin tool versions/binaries in M0 |
| Sibling compiler state | HEAD `82f16cf8afea90a43a8f8560692b869d55d34dd7`; 1668 status entries during inspection | Working tree differs substantially from HEAD; use content hashes if copying references |
| Repository state | Pre-existing ReadyFS modifications; project initially untracked; parent ignores working-record directories | Stay inside project; local ignore override makes planning records trackable |
| D81 container proof | c1541 stored disk 1 as 1452-block SEQ and extracted identical bytes; 1708 blocks remained | Proposed development container is feasible; target IEC runtime remains untested |

Exact image and per-file hashes are in [reference-images.json](../agentworking/research/reference-images.json), produced by the retained read-only [inventory script](../agentworking/research/inspect_reference_images.py). That script is research tooling, not emulator implementation. Its limitations are recorded in the JSON. During that read-only inventory, originals were not mounted writable, modified, or executed. Later reference/target boot observations are recorded separately below.

[Local tool/source evidence](../agentworking/research/local-evidence.json) records exact observed versions and hashes of the inspected local integration sources. ca65/ld65 report V2.18 even though the package directory names cc65 2.19; pin reported tool identity rather than infer it from a folder. The user-supplied [prior conversation](../agentworking/research/prior-conversation.txt) is retained verbatim as non-authoritative background.

## Sources actually consulted

| ID | Primary source / implementation | What it supports; limitations |
|---|---|---|
| S01 | [Ultimate turbo settings](https://1541u-documentation.readthedocs.io/en/latest/config/turbo_mode.html) | U64 vs Elite-II speed tables, register availability modes, VIC/external-bus caveats. Exact user's hardware/firmware remains to be inventoried |
| S02 | [Ultimate DOS target](https://1541u-documentation.readthedocs.io/en/master/uci/ultimate_dos_target.html) | File targets, seek, bulk REU transfer commands and replies; not a latency measurement |
| S03 | [Ultimate dos.cc at 125da1f](https://github.com/GideonZ/1541ultimate/blob/125da1fec3e3b50d31f6409ec217d80693ed674d/software/filemanager/dos.cc) | Actual seek/read/write code and transferred counts. Address mask 24 bits; length mask 25 bits differs from prose docs. Does not establish installed firmware behavior |
| S04 | [UCI architecture](https://1541u-documentation.readthedocs.io/en/latest/uci/core_uci_architecture.html) | Asynchronous state/queue/abort handshake; combine with ReadyFS regression experience |
| S05 | [SingleStepTests 8088](https://github.com/SingleStepTests/8088) | Hardware-generated instruction tests, sparse expected states, flags metadata and exclusions. Not complete interrupt/system behavior coverage |
| S06 | [SingleStepTests 8086](https://github.com/SingleStepTests/8086) | Companion corpus for boundary/difference investigation; choose one declared original-CPU profile |
| S07 | [Microsoft Encyclopedia, Appendix M](https://msarchive.pcjs.org/mspl13/msdos/encyclopedia/appendix-m/) | Original 8086/8088 vs later CPUs: divide return IP, PUSH SP, shift counts and prefix limits |
| S08 | [Microsoft Encyclopedia, Appendix O](https://msarchive.pcjs.org/mspl13/msdos/encyclopedia/appendix-o/) | BIOS call contracts and text-page sizes; choose the PC/CGA subset rather than every later adapter function |
| S09 | [Microsoft Encyclopedia, Appendix A](https://msarchive.pcjs.org/mspl13/msdos/encyclopedia/appendix-a/) | DOS 3.3 changes and command/service context; actual supplied binaries remain acceptance fixtures |
| S10 | [cc65 Soft-80 drawing](https://github.com/cc65/cc65/blob/a6530f46914232c085c281c4bf84e87bd136596f/libsrc/c64/soft80_cputc.s) | Established 80-column drawing, two-character color conflict and restoration strategy |
| S11 | [cc65 Soft-80 color](https://github.com/cc65/cc65/blob/a6530f46914232c085c281c4bf84e87bd136596f/libsrc/c64/soft80_color.s), [layout](https://github.com/cc65/cc65/blob/a6530f46914232c085c281c4bf84e87bd136596f/libsrc/c64/soft80.inc) | Source-level display reference. Any reuse requires its license/attribution, and PC-specific glyph/attribute handling |
| S12 | [VICE quick setup](https://vice-emu.sourceforge.io/vice_5.html), [resource reference](https://vice-emu.sourceforge.io/vice_6.html), [machine features](https://vice-emu.sourceforge.io/vice_7.html) | Virtual traps, REU options and warp configuration; installed build help is the final command-line authority |
| S13 | [DOSBox-X DOS 2.x/3.x installation](https://dosbox-x.com/wiki/Guide:Installing-DOS-2.x-3.x), [image management](https://dosbox-x.com/wiki/Guide%3AManaging-image-files-in-DOSBox%E2%80%90X) | Real-image BOOT workflow and old DOS partition-format pitfalls. Its broad historical statements are not used as architectural evidence |
| S14 | [MartyPC](https://github.com/dbalsom/martypc) | Candidate original-PC timing/behavior reference; not installed/configured or benchmarked in this planning pass |
| S15 | [IBM XT BIOS listing archive](https://www.pcjs.org/software/pcx86/dev/rom/ibm/5160/) | Locates original IBM BIOS material and revisions; a synthetic BIOS will be project-owned rather than bundling an IBM ROM |
| S16 | [Peddle](https://github.com/dirkwhoffmann/Peddle) and local pinned source/license | Host MOS_6510 engine. Local integration/source inspected; emulator timing/device claims limited to the actual shim |

Additional authoritative references identified for detailed implementation: [Intel 8086 Family User's Manual, October 1979](https://bitsavers.org/components/intel/8086/9800722-03_The_8086_Family_Users_Manual_Oct79.pdf) and [Commodore 1764 user's guide](https://files.commodore.software/reference-material/manuals/commodore-64-manuals/hardware-manuals/1764-ram-expansion-module-users-guide.pdf). These were located, not fully audited page by page. Their detailed bus/REU edge semantics must be checked during M1/M2. An attempted IBM XT PDF fetch was unavailable; use the accessible listing archive/reference instead of claiming that PDF was read.

## Corrections to the pasted discussion

| Earlier suggestion | Planning conclusion |
|---|---|
| Prefer a native DOS API layer and add actual DOS later | Conflicts with this user's objective. Execute the real DOS kernel from the outset; native BIOS is the acceleration boundary |
| Map guest file handles to Ultimate DOS handles | Unnecessary here: DOS manages guest handles inside disk images; host handles are for images |
| Illustrative 26 KiB guest cache | Too optimistic to assume before layout. Budget 16 KiB with visible display/metadata/code allocations, then measure |
| Roughly 4 MB/s REU | Unverified scenario, not a specification; measure each direction/size at the actual firmware/turbo/display settings |
| 64 MHz might exceed XT generally | Workload-dependent hypothesis. Fast bulk storage does not prove CPU or memory-heavy performance |
| 80-column color is straightforward | Width is feasible; two arbitrary colored characters in one VIC hires cell cannot always be represented faithfully |
| Skip most PC I/O | Minimal PIC/PIT/keyboard/CGA port behavior is still needed for DOS/drivers and polling loops |
| “Zig” target | User clarified assembly; host Zig provides tests, generators and assertions. ZeroPage remains the example testing workflow |

## Open research to close during implementation

Follow-up source inspection is recorded in [existing emulator references](EXISTING_EMULATORS.md). NES86 is a verified 6502-assembly 8086 interpreter and the closest inspected host-CPU match. 8086tiny supplies an MIT-licensed C core and BIOS; XTulator supplies a readable GPL CPU reference. Our target remains original 8088/XT, and none of these sources has been incorporated into the target. [REU_IMPLEMENTATION.md](REU_IMPLEMENTATION.md) records the subsequently implemented primitive, mock and functional VICE evidence.

- Exact original-CPU multi-byte behavior at segment/physical boundaries; interrupt/prefix corner cases absent from public single-step vectors.
- Actual DOS version/OEM boot dependencies, observed INT/port trace, FDISK small/large geometry and FORMAT BIOS requirements.
- C64U firmware, REU transfer latency/stalls, turbo switching and I/O behavior; source/documentation discrepancies must be tested on that firmware.
- Final 80-column font quality, palette policy, graphics reduction and keyboard chords on the user's screen/keyboard.
- Corpus/download/toolchain pinning and source licenses for anything copied into the project. No downloaded DOS replacement is needed.

## Implementation follow-up: CPU boundaries and hardware corpus

Original-8088 word policy follows [MartyPC byte-bus implementation at 05c0d088](https://github.com/dbalsom/martypc/blob/05c0d088e84ad6bbfac9b3f0d051e7eadefd9f44/crates/lib/marty_core/src/cpu_808x/biu.rs): wrap the offset for the second byte, then translate. No source copied. The [pinned hardware projection](../third_party/sst8088/UPSTREAM.json) retains 2,555 functional cases as of the 2026-10-15 math/indirect checkpoint and the MIT license. Audited A1/A3 originals have no word beginning at FFFF; A3 index 9570 covers FFFE. Independent corner tests supplement the source reference; they are not direct physical-8088 evidence. [CPU implementation](CPU_IMPLEMENTATION.md) lists actual opcode coverage and exclusions.


Original shifts also consult [MartyPC common ALU at 05c0d088](https://github.com/dbalsom/martypc/blob/05c0d088e84ad6bbfac9b3f0d051e7eadefd9f44/crates/lib/marty_core/src/cpu_808x/common_alu.rs) and the pinned hardware vectors. Original D0/D1 /6 is SETMO; D2/D3 /6 is SETMOC, not the later SHL alias. CL counts use all eight bits. The [interrupt routine](https://github.com/dbalsom/martypc/blob/05c0d088e84ad6bbfac9b3f0d051e7eadefd9f44/crates/lib/marty_core/src/cpu_808x/interrupt.rs) reads IVT words before stacking FLAGS/CS/IP; the current functional policy follows that order. No reference code copied; hardware projections cover functional state, not asynchronous event timing.

[Intel iAPX86/88/186/188 manual (1985)](https://bitsavers.org/components/intel/8086/210912-001_iAPX_86_88_186_188_Users_Manual_1985.pdf), §1.7.8 printed1-122 /PDFpage138, distinguishes per-iteration guest interrupt restart from uninterrupted REP. Multiple-prefix restart quirks and precise segment-register interrupt inhibition still need direct original-hardware event evidence. Our host REP yields preserve all decoded prefixes and are explicitly not guest interrupts.

## Math, BIOS and real-kernel observations — 2026-10-15

The expanded [hardware selection](../third_party/sst8088/UPSTREAM.json) pins original F6/F7 divide-error, REP IDIV, signed-minimum-quotient and FF PUSH SP alias rows. F6/F7 MUL/IMUL/unsigned DIV input files have no REP prefixes at this pin; independent tests/source-derived policy must not be called direct hardware coverage. FE /2–7 input files are absent and 8F input contains only /0; unaudited forms remain explicit diagnostics. Original signed division rejects magnitude 80h/8000h even for a negative quotient, and divide errors retain original post-instruction saved IP. These distinctions were verified by the pinned original hardware projection rather than inferred from a modern x86 host.

The BIOS implementation's source comments pin the IBM 5160 XTBIOS/POST listings used for status/DMA interface facts, unsupported INT 15h AH=86h/CF=1, and disk-parameter table fields. Local archived listings and inspection notes are retained under ignored `agentworking/scratch/`; the synthetic code/table bytes are independently authored, and no IBM ROM is bundled. The configured 360 KiB profile uses nine sectors/track rather than treating a listing's compatibility default as the actual fixture geometry. The current [BIOS contract](BIOS_IMPLEMENTATION.md) distinguishes ordinary guest ROM handlers from whitelisted native disk/bootstrap gates.

The unchanged supplied bootloader actually reads 51 raw sectors starting at its IO.SYS extent; IO.SYS itself is 22,398 bytes and rounds to 44 sectors. An independent FAT12 fixture oracle records the full raw extent, padding and overread rather than assuming the file length describes every loaded byte. Actual target execution reaches 0070:0000 in 392 guest instructions, then continues to unsupported PIC OUT 20h at 0070:2BFB after 2,335 instructions. INT 11h/12h read mutable BDA and INT 15h returns XT unsupported status on this path. This is observed kernel entry, not evidence that COMMAND.COM, the original CONFIG.SYS or a DOS command prompt has completed.

Host disk-image tooling validates BPB/FAT/root/chain bounds and immutable source identity, and creates exclusive disposable clones/extractions for tests. It is a fixture/oracle aid, not a native DOS loader. Guest BIOS storage remains raw sectors through the actual assembly cache/range implementation. Native UCI/IEC import/persistence, hard-disk geometry/format behavior, display/input and event timing remain research/implementation gaps.

## Fetch/PIC and candidate BIOS/adjust follow-up

The accepted [fetch comparison](../agentworking/evidence/fetch-optimization-20261015.json) uses the previous actual assembly helper as a differential reference, including one-frame operand eviction, generation changes, redirects and self-modification. Its target-cycle gains are workload-specific; large REP behavior is nearly unchanged. [PIC integration](../agentworking/evidence/pic-io-20261015.json) adds all eight IN/OUT forms and software-visible 8259A programming, without asynchronous IRQ/INTA or imported IN/OUT hardware vectors. Genuine IO.SYS now passes OUT 20h and reaches INT 14h after 2,347 instructions at that accepted checkpoint.

Private adjust research pins the same SingleStepTests source revision and records 3,146 selected rows from eight additional files in `agentworking/scratch/adjust/hardware-sources.json`. Original BCD hardware distinguishes AF-sensitive DAA/DAS thresholds, DAS borrow and independent AAA/AAS byte corrections from later x86 assumptions. An initial AAM-zero expectation incorrectly preserved SZP; actual hardware rows showed the zero SZP result before INT 0, and the target/test were corrected. The source files contain no REP adjust cases; [microcode analysis](https://www.righto.com/2023/07/undocumented-8086-instructions.html) supplies that policy, with pinned MartyPC source as a cross-check. No implementation source was copied. Selected target execution, exhaustive offline oracle comparison and global corpus integration are distinct evidence lanes.

Private logical video tests consult Microsoft Appendix O, original XT listing facts and RBIL pixel/XOR/page behavior; exact citations and source identities are retained in `include/video.inc` and `agentworking/scratch/video/evidence.json`. The independently authored implementation preserves logical guest BDA/VRAM and exposes no host renderer/font/readability claim. Absent serial/printer calls follow the original XT listing's zero-base check before AH dispatch, preserving AX and unchecked wrapping DX index behavior; absence is not a timeout. Combined global quick/full/profile acceptance now passed; [retained evidence](../agentworking/evidence/video-adjust-bios-20261015.json) pins sources, exact maps, private research and the real DOS continuation.


The normal imported projection now contains **5,701 selected hardware cases**: all prior **2,555** retained unchanged plus the **3,146** adjust rows. Fixture SHA-256 `aba315edeb9bf6517e9c0eb0f5a887d97589c1604b74ff7f83e1dd2a64bf2f8e`; all 47 AAM-zero saved-FLAGS frames compare exact RAM with no new masks. The earlier 205-test quick gate executed its 581-row projection; the expanded fixture designates 597 quick rows, covered by the final full 5,701-case execution rather than a separate quick rerun. Original source-file populations and offline 10,000-row model audits remain distinct from selected target execution.

Logical mode-3 initialization and absent serial/printer services advance genuine IO.SYS to missing INT 1Ah after 2,542 instructions. Clock/native-clock, keyboard and UCI candidate modules are not linked. The new resident layout zero-pads MAIN and explicitly initializes 4000–4FFF display RAM before DEVICECODE at 5000; neither padding nor startup zeros are linked executable allocations. The full runtime binary is untested physically, while four isolated prior hardware probe PRGs remain byte-identical.


## Genuine SYSINIT shared-rearm and COMMAND built-ins

The [retained primary audit](../agentworking/research/dos-trace-audit-20261015.md) pins Microsoft SYSINIT1.ASM at repository revision `2d04cacc5322951f187bb17e017c12920ac8ebe2`, the original supplied binaries and the observed relocated SYSINIT span. The stop at 9DFD:0A53 with DX=02F2h was a legitimate DOS 3.30 GLOBAL REARM broadcast to shared IRQ levels 2–7. Microsoft v4 comments identify its inherited 3.30 purpose and arbitrary write value; they are not claimed to be the exact source build of this supplied binary. The actual six-port sequence and XT model check remain binary-authoritative. Only byte writes to 02F2h–02F7h are recognized for absent boards, without PIC side effects.

A [retained differential execution](../agentworking/evidence/dos-fetch-differential-20261015.json) compared the retained slow fetch with fast fetch through all 55,583 scheduling calls/53,861 guest instructions to that stop, every 14-word register state and complete coherent 640 KiB RAM plus 16 KiB CGA. It found identical results. This excludes a regression relative to the previous fetch path; it does not independently establish every CPU behavior. The original CONFIG.SYS `c:` line explains the observed unrecognized-command diagnostic; no source image repair was made.

After implementing that narrow port behavior and clock/keyboard BIOS, the opt-in long assembly/Peddle lane reaches real COMMAND.COM. Date/time Enter, VER and DIR use ten words through the actual assembly enqueue routine. The independent read-only FAT12 oracle requires all 35 visible names/exact sizes, the 35-file total and 9,216 free bytes; output observations also require MS-DOS Version 3.30 and the returned `A>` prompt. The original/in-REU floppy remains unchanged. [Built-ins evidence](../agentworking/evidence/dos-command-builtins-20261015.json) retains selected screens and exact raw schema-2 report identity; 939 changed-screen observations remain in the raw run.

This is a Peddle functional milestone. Default tests stop at IO.SYS handoff, while `make test-dos-boot` owns the long scripted command proof. Linked generic UCI transport does not yet open/import runtime images. Native file-command/render/overlay components remain private/unlinked; physical keyboard scanning, C64 presentation, asynchronous events and HD persistence remain ahead.


The first physical native-clock matrix failed at Manual 1 MHz and is explicitly rejected as timing validation. [Failure evidence](../agentworking/evidence/c64u-clock-first-failure-20261015.json) pins the probe/tool/firmware identity and configuration-restoration result. The first error-3 subreason remains unknown. Failure capture now retains RAM/mailbox/40-byte DCK1 before reset, and the probe uses a 16-line endpoint window with ±1,008-tick bounds; no successful physical rerun or 16/64 MHz calibration follows from these functional corrections alone.


The corrected [physical CIA/raster matrix](../agentworking/evidence/c64u-clock-20261015.json) passes Manual 1/16/64 MHz: 100-frame deltas 1,965,627/1,965,599/1,965,600 versus 1,965,600±1,008, zero retries, 28-tick spread and restored configuration/reset-resume. This establishes the observed PAL clock domain and turbo independence for the pinned firmware/core; it does not establish CPU/REU throughput or wire native time conversion. The corrected 1 MHz raster endpoints of 8/8 suggest the old narrow window as a possible first-failure cause, but the missing old record prevents confirmation.
