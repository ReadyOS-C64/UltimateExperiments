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

Exact image and per-file hashes are in [reference-images.json](../agentworking/research/reference-images.json), produced by the retained read-only [inventory script](../agentworking/research/inspect_reference_images.py). That script is research tooling, not emulator implementation. Its limitations are recorded in the JSON. Originals were not mounted writable, modified, or executed.

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

Original-8088 word policy follows [MartyPC byte-bus implementation at 05c0d088](https://github.com/dbalsom/martypc/blob/05c0d088e84ad6bbfac9b3f0d051e7eadefd9f44/crates/lib/marty_core/src/cpu_808x/biu.rs): wrap the offset for the second byte, then translate. No source copied. The [pinned hardware projection](../third_party/sst8088/UPSTREAM.json) retains 1,622 functional cases as of 2026-10-15 and the MIT license. Audited A1/A3 originals have no word beginning at FFFF; A3 index 9570 covers FFFE. Independent corner tests supplement the source reference; they are not direct physical-8088 evidence. [CPU implementation](CPU_IMPLEMENTATION.md) lists actual opcode coverage and exclusions.
