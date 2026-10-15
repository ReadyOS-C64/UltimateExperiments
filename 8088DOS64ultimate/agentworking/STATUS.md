# Current state

Updated: 2026-10-15, America/Los_Angeles.

**Phase: genuine DOS 3.3 COMMAND.COM, VER and DIR accepted in Peddle; full native emulator remains active work.** The opt-in long lane executes unchanged guest DOS, enqueues ten keys through actual assembly and accepts the initial `A>` prompt, `MS-DOS Version 3.30`, all 35 visible DIR filenames and exact sizes, `35 File(s)`, 9,216 free bytes and the returned prompt. It completes at **588,937 guest instructions / 592,171 CPU calls**, with source/in-REU floppy unchanged. No native INT 21h or guest application-loader substitute is involved.

Current accepted slice adds a third INPUT overlay, guarded disposable startup memory, initialized full/narrow fonts, native VIC text setup and a tested CIA elapsed adapter. Root checks pass **326 Zig/Peddle tests /597 quick hardware cases /129 tooling checks**, plus **8 dedicated import tests**, **1 genuine DOS long test** and **12 profile samples**. All 939 saved DOS observations, ten keys, registers, full 640 KiB guest RAM and 16 KiB CGA bytes exactly match the original COMMAND/VER/DIR milestone. CPU-step cycles are 1,164,555,140; this is not physical elapsed time. [Current evidence](evidence/native-text-input-20261015.json).

Native startup still initializes CPU/cache, commits all three overlay assets and idles. It does not yet import a file or run the guest. Display, input and elapsed modules are linked and functionally verified; the narrower font has separate VICE component proof, visually inspected by root. Physical display/input, native UCI boot, IRQ/PIT scheduling, CGA presentation, persistence, IEC and HD remain unfinished. Development-only first4MiB REU backup/recovery and fresh FTP fixture tools pass 4 native/21 host tests; they have not contacted hardware. The overall implementation goal remains active; verified commits are local only.

MAIN free runtime/unit is **1,151/175 bytes**, DEVICE **340**. TEXT957 and INPUT882 share C900 with FILE1088. All three startup slots must be committed before guest cache/BIOS work: INPUT initially occupies8000–87FF. BIOS initialization/import/bootstrap bodies at7000–7FFF have an irreversible resident cold-open guard; display wrappers reject calls until cold memory is released. No reset API reopens that lifetime. [Memory ledger](MEMORY_BUDGET.md).

## User decisions to preserve

- Build a real DOS 3.3 emulator for the 64 MHz C64U in this directory.
- Original **8088 / IBM PC XT** compatibility is the target; 8086 sources are references. Implement requirements regardless of what reusable cores provide.
- Target code should be **6502 assembly**, not ZeroPage-generated code. ZeroPage is the reference for the Peddle testing workflow.
- Retain **Zig tests that assert observable behavior of the actual assembled target**, like the existing compiler tests.
- 640 KiB guest RAM via REU paging, whole floppy images in REU, cached parts of hard disks around 2 MiB then 20 MiB.
- **4 MiB minimum REU**, larger optional; baseline budget fits guest RAM, two full floppy slots, HD cache, overlays, staging and traces.
- Keyboard, 40/80-column text and limited CGA; first application tests are applicable DOS tools on supplied images.
- Mock fast, exercise VICE/IEC/D81 as a second lane, and test on the physical C64U.
- All working records/scratch belong in this project's `agentworking`, not the enclosing repository folder.

## Completed planning work

- Inspected the supplied conversation, all three disk BPBs/root directories/configs, ZeroPage documentation/runner/shim, ReuSQL64 testing/storage integration, ReadyFS UCI rules/code, and .NET VICE harness usage.
- Researched primary instruction/BIOS references, hardware-generated tests, Ultimate firmware/docs, Soft-80 source, VICE, DOSBox-X, and timing-reference options.
- Wrote architecture, concrete RAM/REU allocation, memory ownership rules, storage persistence, display/input policy, test matrix, performance experiments, phased plan, requirements coverage and continuation records.
- Added a read-only disk-inventory research helper. It is not emulator code.
- Verified a disposable D81 can store disk 1 as a SEQ file and extract it byte-for-byte; this is container evidence, not emulator/IEC runtime acceptance.
- Planning validation passed: all 28 local links resolved, both address-space budgets are contiguous and complete, inventory repeats, originals retain their hashes, and ignore rules keep project context versionable while excluding scratch.

## Verified implementation slice: M0 foundation

- ca65/ld65 PRG and raw test payload, labels/maps, memory-contract checks and dependency/tool/artifact manifest.
- Vendored original Peddle core at its pinned upstream commit with license and per-file hashes.
- Zig tests exercise the linked reset routine and actual PRG startup; 10 tests cover state/ABI, error detection, runaway budget, stack imbalance, forbidden writes, unimplemented-device rejection, raw payload identity and exact CPU clocks.
- Four negative/positive linker-contract tests guard resident/entry placement.
- DOSBox-X boots a cloned supplied disk 1 with original CONFIG.SYS and an injected evidence AUTOEXEC. Guest VER reports **MS-DOS Version 3.30**; DIR and completion marker were read back from the guest floppy; original SHA-256 matches.
- Found and fixed clock integration: Peddle's embedding application must increment `clock` after each microcycle. The first runaway test exposed the missing clock advancement; exact LDA/RTS timing now guards it.

## Limits at the historical M0 checkpoint

At that checkpoint the target had an initial instruction subset but no full interpreter, BIOS, UCI/file backend or target DOS boot. Physical C64U timing and XT performance remain unmeasured. The reference DOSBox process was stopped after its guest output files closed; this is not a clean-storage-shutdown test. Original CONFIG diagnostics were not captured as screen text.

## Verified implementation slice: REU primitive

- Assembly immediate transfer primitive validates host/count/bank ranges, preserves Y/P and 6510 mapping, and reports completion/error. Descriptor accesses under KERNAL RAM occur with correct banking.
- Functional C64 banking subset and REU register model support used semantics, 4/8/16 MiB capacities and explicit unsupported-feature faults. DMA timing and complete CIA/VIC behavior are not modeled.
- `make test` passes **26 Zig/Peddle tests and 9 tooling tests** (four linker contracts, five acceptance-verifier checks). Shared probe verifies 4 KiB store/clear/reload against all expected bytes.
- Standalone probe passed VICE run `vice_auto_20261014_222223`. Independent verification matches captured executable to the current PRG and checks every returned byte. Compact record: [reu-vice-20261014.json](evidence/reu-vice-20261014.json). Harness used 16 MiB REU/warp, not a physical 4 MiB or 64 MHz validation.
- Runtime CODE 255, BSS 46, ZP 4; standalone probe CODE 416, BSS 46, ZP 6. See [memory ledger](MEMORY_BUDGET.md) and [contract](../docs/REU_IMPLEMENTATION.md).
- NES86 is a real 6502-assembly 8086 core with ca65/ld65, GPLv3, mapper-specific memory and ELKS/serial BIOS. It is a reference, not adopted code or a conformance oracle. Pinned findings: [existing emulators](../docs/EXISTING_EMULATORS.md).

## Verified implementation slice: addressing and coherent byte cache

- Segment/offset helper wraps at 20 bits and preserves input/register/flag contract. A 512-byte cache uses 32 frames in 8000–BFFF, a 2,048-entry direct map and bounded clock replacement, with forced 1/2-frame tests.
- Dirty write-back/load publication order, aliases, pins, PC holes/ROM/CGA and input rejection are tested against actual assembly; synthetic partial-transfer failures preserve authority and retry behavior.
- Latest `make test`: **41 Zig/Peddle + 10 tooling tests**, including all 2,048 physical pages, seeded oracle comparisons and shared cache probe. Warm test execution about four seconds.
- Cache probe passed VICE run `vice_auto_20261014_225535`; all 1,536 bytes and captured executable independently verified. [Evidence](evidence/cache-vice-20261014.json) and [API/limits](../docs/MEMORY_IMPLEMENTATION.md).
- Runtime CODE 1,109, BSS 62, map 2,048, frame metadata 192, ZP 16. Measured public warm byte read is 221 CPU cycles in ALL_RAM mode; this is a correctness baseline requiring fetch/hot-path optimization, not an XT-speed result.
- Physical read-only inventory succeeded at 10.0.0.79: C64 Ultimate firmware 3.14, FPGA 121, core 1.47, enabled 16 MB REU. Configured CPU speed 64 is controlled by C64U registers, so effective speed is not established. [Inventory](evidence/c64u-inventory-20261014.json). No physical probe program run; no machine/media settings changed.

The full-system memory allocation, final page size and performance thresholds remain proposals except user requirements. Disk 1's C:-specific config and disk 3's boot/OEM field still need observed diagnostics; do not silently repair originals.

## Continue from

[NEXT_SLICE](NEXT_SLICE.md), then [PLAN](../docs/PLAN.md), [TESTING](../docs/TESTING.md), [DECISIONS](DECISIONS.md). Implementation is authorized; preserve user clarifications and proceed in verified slices.

Existing unrelated ReadyFS edits and the large dirty sibling ZeroPage checkout were left unchanged. Root `agentworking` was not written. Project `.gitignore` overrides the parent's working-record ignore so these planning records can be versioned; scratch/runs remain ignored.

## Verified physical cache slice

- Native cache probe passed at manual 1/16/64 MHz settings on firmware 3.14. All 1,536 bytes and uploaded executable identity verified. Exact prior REU page envelope 07FC00–0803FF was backed up, restored and byte-compared; machine/turbo/media configuration matched before/after. [Evidence](evidence/c64u-cache-20261014.json), [procedure and limits](../docs/HARDWARE_TESTING.md).
- Latest fast checks: 42 Zig/Peddle + 15 tooling tests. Native backup/restore is tested across the bank seam; workflow tests cover cleanup on failure and firmware-padded speed options.
- First hardware run failed with HTTP 400 because `1` did not match the advertised ` 1` option. Recovery succeeded; corrected mapping and subsequent full matrix passed. No calibrated timing or DOS boot claim.

## Verified initial CPU execution slice

- Assembly step/init, immediate register MOV, AX exchanges/NOP, accumulator byte/word memory transfers, relative/far jumps, guest control flags and halt. Prefix streams yield in 64-prefix slices without an invented length exception. Unsupported instructions and host memory failures latch explicit diagnostics.
- `make test`: 55 Zig/Peddle + 15 tooling, including 41 hardware cases, approximately six seconds warm. `make test-cpu-corpus`: all 481 pinned SingleStepTests cases pass with register and complete 1 MiB RAM comparison, approximately 26 seconds. [CPU contract/limits](../docs/CPU_IMPLEMENTATION.md).
- Runtime CODE 2,019, RODATA 8, BSS 84, ZP 16, map 2,048, frame metadata 192; PRG 2,041 bytes. Probe binaries are isolated from the execution module and retain their physically tested identity.
- Word transfers use wrapping 16-bit offset then 20-bit translation per byte, following pinned original-8088 MartyPC implementation. Hardware projection covers FFFE, but contains no audited FFFF word case; that particular hardware corner remains open.
- No arithmetic/ModR/M/stack/string/I/O/interrupt execution, synthetic BIOS, target DOS boot or speed claim yet.


## Verified arithmetic, operand and stack slice — 2026-10-15

- 6502 ALU supports byte/word ADD/OR/ADC/SBB/AND/SUB/XOR/CMP/INC/DEC with eager guest flags, plus TEST. All 16-bit ModR/M forms, register/high-byte operands, general/segment MOV, LEA, LES/LDS, immediate groups and C6/C7 original extension aliases now execute.
- Stack words, register/segment PUSH/POP, PUSHF/POPF/SAHF/LAHF, direct near/far CALL and RET with cleanup preserve original SP ordering and reserved flags. Interrupt shadows are recorded; interrupt/trap delivery remains absent.
- **75/75 Zig/Peddle + 15/15 tooling pass**. Quick includes **338 hardware cases**, full **1,622**, all guest registers/defined flags and all 1 MiB RAM checked. Independent ALU 3,200 and address 720 case sets supplement hardware vectors. Measured commands: quick5.21 seconds, full 11.57 seconds, including build checks; host runner optimization accelerates feedback, not target execution.
- Real unchanged disk-1 sector completes16 instructions, then unsupported LODSB AC at 0000:7C51. IVT is zero in that fixture; no BIOS/DOS boot claim. Next: strings and conditional flow, then interrupt/BIOS/boot transport.
- Runtime CODE 4,394, RODATA 305, BSS 116, ZP 16; PRG 4,713. Hardware probe bytes still match prior VICE captures; no new physical run warranted by CPU-only changes. [Evidence](evidence/cpu-arithmetic-operands-stack-20261015.json), [contract/limits](../docs/CPU_IMPLEMENTATION.md), [ledger](MEMORY_BUDGET.md).
- Three user-authorized subagents owned stack, operand/corpus tests and runner improvements; parent integrated arithmetic/CPU, reviewed, verified and retained all context under this project. No pushes.


## Verified strings, control and software interrupt slice — 2026-10-15

- Implemented all 10 byte/word string forms with DF/segment rules and bounded 16-iteration REP continuation. Host yields preserve decoded state and count one completed instruction; asynchronous interrupt restart remains future work.
- Added all 32 Jcc encodings (including 60–6F original aliases), LOOPNE/LOOPE/LOOP/JCXZ, D0–D3 rotates/shifts with unmasked CL and original SETMO/SETMOC, INT3/INT/INTO/IRET normal guest routing.
- **95/95 Zig/Peddle + 15/15 tooling pass**; quick 502/full 2,278 hardware cases. Independent assertions include 1,024 branch flag combinations, 64 LOOP cases, 1,748 shift/rotate cases, 8 string tests and 4 interrupt tests. Full command 15.82 seconds. Hardware corpus's longest instruction uses 8 bounded host calls.
- Unchanged disk sector reaches real INT 13h disk reset; explicit guest IRET fixture returns to 7C70; first missing CPU instruction is CBW 98 at 7C75. No native BIOS/disk service, genuine target DOS boot or throughput claim. Next priority: CBW/CWD and multiply/divide, then BIOS ROM/IVT/BDA and coherent disk range support.
- Runtime CODE 6,094, RODATA 305, BSS 137, ZP 16; PRG 6,413. Standalone hardware probe images remain unchanged. [Evidence](evidence/cpu-strings-control-20261015.json), [API and remaining limitations](../docs/CPU_IMPLEMENTATION.md).


## Historical work in progress after c7450ff

Math/sign-extension/indirect execution now passes 114 Zig/Peddle + 15 tooling and 2,555 full hardware cases (581 quick); not yet committed. Real unchanged sector computes root LBA 5/data LBA 12 and requests CHS 0/0/6 into 0000:0500 before fixture stops at 7D73. New coherent range copying with reserved C000–C0FF staging is being integrated; disk sector primitive, BIOS bootstrap/ROM gates and host image tools are parallel work. These new storage/BIOS paths are not yet accepted or physically verified. Preserve standalone probe identity and immutable inputs.

## CPU, BIOS and storage baseline — 2026-10-15

- Actual assembly adds CBW/CWD, general XCHG, accumulator TEST, FE INC/DEC, FF indirect CALL/JMP/PUSH including /7 alias, POP r/m16 and F6/F7 TEST/NOT/NEG/MUL/IMUL/DIV/IDIV. Math and indirect checkpoint: 114 Zig + 15 tooling quick; 2,555 full hardware cases. Original signed minimum quotient and REP IDIV/divide-return-IP policies retain pinned evidence and explicit source gaps.
- Coherent guest/REU ranges use a linker-enforced 256-byte staging buffer at C000–C0FF, <=256-byte chunks and explicit REU bank splits. Every guest byte uses the memory bus. Dirty import neighbors/export authority, PC ROM/hole/CGA policy, wrap, input rejection and partial failures/retry are checked. Additional resident code budget is now C100–CFFF, 3,840 bytes.
- Disk A defaults unloaded at REU 100000, 720×512 bytes, 40×2×9 geometry. Actual assembly reset/read/write/verify checks all 720 CHS positions, physical DMA boundaries, exact slot end and errors. Writes are volatile REU mutations; Ultimate/IEC persistence and floppy B/HD remain unfinished.
- Synthetic BIOS populates owned ROM/IVT/BDA through coherent writes. Only exact owned physical OUT opcode entries invoke native bootstrap/disk service; ordinary INT/IRET and mutable hooks remain intact. INT 11h/12h are ordinary guest ROM handlers reading dirty mutable BDA; INT 15h returns original XT AH=86h/CF=1. Wider BIOS/video/input/clock services are absent.
- Genuine boot integration seeds only the whole immutable floppy image into its owned REU slot. Reset→original sector→IO.SYS requires 392 completed guest instructions and 12,019,126 native step cycles excluding setup. All 51 raw sectors, including the bootloader's overread beyond the 44 rounded IO.SYS sectors, match the independent oracle. Source image and in-REU floppy remain unchanged. No host kernel/application loader or native INT 21h replacement exists. Current continuation stops at PIC OUT 20h, and the complete DOS prompt remains ahead.
- Native coherent range probe passed VICE run `logs/vice_auto_20261015_011028`: all 1,536 output bytes include dirty edits and match independently; captured executable matches. Previous four hardware PRG identities remain unchanged. New physical range probe passed Manual 64 MHz with independent exact restoration of 5,120 guest/source/destination bytes and prior machine/turbo/drive JSON equality. [Physical evidence](evidence/c64u-range-20261015.json).
- Final quick integration `build/storage-bootstrap-test.log`: 150 Zig/Peddle + 45 tooling pass, 12.45 seconds. Final full corpus `build/storage-bootstrap-corpus.log`: 150 Zig/Peddle, all 2,555 hardware cases, 23.70 seconds. Runtime map: CODE 9,702, RODATA 673, BSS 211, ZP 16; PRG 10,389 bytes. See [memory ledger](MEMORY_BUDGET.md) for actual boundaries and 45 BSS bytes remaining before E100. Unit helper changes do not change runtime bytes.
- `build/cpu-profile.json` contains 12 validated real-assembly cold/warm samples. Warm register/branch cost is 1,762.55 native cycles/instruction; 20 KiB REP is 1,081.19 cycles/copied byte, before DMA stalls and physical effects. This pre-optimization baseline does not establish XT speed. Unlinked fetch/PC-port/video work is future work, excluded from accepted functionality/performance.

Next acceptance is the full real DOS prompt followed by applicable command/application tests, 640 KiB RAM, 40/80 text and limited CGA, keyboard, native Ultimate/IEC media and 2 MiB→20 MiB file-backed HD persistence. Kernel entry does not reduce that scope. See [NEXT_SLICE](NEXT_SLICE.md) and the [BIOS](../docs/BIOS_IMPLEMENTATION.md), [disk](../docs/DISK_IMPLEMENTATION.md), [range](../docs/RANGE_IMPLEMENTATION.md) contracts.

## Verified fetch optimization

Following baseline commit `49ac73f`, the CPU fetch helper now reuses an unpinned cache span only after validating CS/IP, cache readiness/limit/mode, frame validity/tag and generation. Writes, operand eviction, redirects, initialization, page ends and IP wrap force fresh coherent lookup. The former helper remains independently executable for differential tests. Full guest state and all 1 MiB of RAM match after the 261-instruction fast/slow comparison.

Quick/full gates pass **161 Zig/Peddle + 45 tooling**, with all **2,555** selected hardware cases. Twelve profile samples pass; warm register/memory loops use about 21% fewer CPU cycles, multiply/divide 18% and stack calls 10%; large REP copies change by about +0.08%. No hardware/XT timing claim. Runtime CODE 9,999, RODATA 673, BSS 222, ZP 18, PRG 10,686. [Evidence](evidence/fetch-optimization-20261015.json). At that checkpoint genuine IO.SYS still stopped at OUT 20h after 2,335 instructions; PIC/video/adjust/UCI modules were unlinked work.
## Verified PIC and guest I/O integration

All eight original 8088 IN/OUT forms now use a bounded descriptor and functional PIC at 20h/21h. Original XT defaults are installed by BIOS initialization. Private synthetic-ROM callbacks retain their address whitelist. Quick/full lanes pass 172 Zig tests, with 47 tooling checks and all 2,555 selected hardware cases; the full command takes 25.19 seconds. The device's six independent tests include 2,048 EOI cases. [Contract](../docs/PORTS_IMPLEMENTATION.md), [evidence](evidence/pic-io-20261015.json). Genuine boot advances to INT 14h after 2,347 instructions. No serial hardware, asynchronous IRQs, prompt or runtime file loader is claimed. Video, adjust and Ultimate transport remain separate work pending integration.


## Verified logical video, adjust, absent-device BIOS and resident layout

- Actual assembly logical INT 10h handles modes 0–6, text pages/cursor/cell operations, bounded scrolling, text teletype, CGA pixel read/write/XOR and mutable BDA queries. BIOS cold initialization establishes mode 3 and all 16 KiB CGA VRAM coherently, preserving guest AX. CP437 bytes/attributes remain exact. No C64 font/renderer/presentation or physical readability claim.
- INT 14h/17h implement original XT absent-device behavior: a zero mutable BDA base returns before AH dispatch with registers/FLAGS unchanged, using original wrapping DX indexes. Present serial/printer bases are explicitly unsupported. Private ROM gates for video/serial/printer retain exact physical address+port whitelisting and ordinary guest IRET.
- DAA/DAS/AAA/AAS/AAM/AAD/SALC/XLAT now execute original 8088 behavior. AAM base zero preserves AX, produces hardware-observed SZP and enters ordinary INT 0 after its immediate; no REP hardware-adjust coverage is invented. All 3,146 added hardware rows compare complete 1 MiB RAM; all 47 AAM-zero frames are exact without new masks.
- Quick **205/205 Zig + 57/57 tooling**, 29.12 seconds. Final full **205/205 Zig**, all **5,701 hardware cases**, 59.26 seconds; maximum eight slices. Final profile **1/1**, 12 samples, 3.28 seconds. Fixture SHA-256 `aba315edeb9bf6517e9c0eb0f5a887d97589c1604b74ff7f83e1dd2a64bf2f8e`. First quick attempt found two fixture issues (obsolete D6 unsupported sentinel and writes beneath a live cache); coherent fixture fixes passed, with no target failure.
- Current runtime CODE **11,443**, RODATA **808**, DEVICECODE **1,696** at 5000–569F, BSS **222**, DEVICESTATE **61**, ZP **18**. Linked usage **16,758** differs from PRG **20,129**, which includes **6,168** padding/startup-zero bytes. Unit CODE **12,359**, RODATA **832**, TESTCODE **36**, ZP **30**, ends 3BB7; linked **17,746**, same PRG size with **5,192** padding/startup zeros. [Ledger](MEMORY_BUDGET.md) preserves exact per-window headroom and conditional future UCI buffer budget.
- Genuine IO.SYS handoff remains 392 instructions, now 11,860,775 step cycles excluding setup. Continuation reaches missing INT 1Ah after 2,542 instructions and 26,023,384 step cycles; setup is separately 26,360,254 cycles. Prompt remains false. Clock/native-clock, keyboard and UCI modules remain unlinked future work.
- Final profile reports 62,013,116 CPU cycles, 18,258,732 native instructions, 10,314 guest instructions, 12,902 calls, 223 DMA operations and 114,176 bytes. Warm register loop is 1,410.56 host cycles/instruction; 20 KiB REP is 1,082.04 cycles/byte. Physical timing and XT ratios remain unmeasured. All four original hardware PRGs are byte-identical; no slow physical rerun was needed for these isolated CPU/BIOS changes.

The entire prompt/application/640 KiB/40–80 text+CGA/keyboard/Ultimate+IEC/2 MiB→20 MiB HD objective remains binding. Next: [NEXT_SLICE](NEXT_SLICE.md). The newly included `video.inc` dependency in `bios.s` still needs an explicit Makefile prerequisite in the following slice; this checkpoint's verified binary/source hashes are retained.


## Clock/keyboard/UCI and genuine DOS built-ins checkpoint

- Guest INT 1Ah implements original mutable BDA time and bounded explicit tick advancement. INT 16h uses the original 15-key ring, exact AH=01 saved flags and bounded empty-read yield at its owned ROM gate. Generic UCI transport and native CIA2 clock are linked and independently modeled; neither provides native image loading or scheduling by itself.
- Default quick **258/258 Zig/Peddle**, **597 selected hardware rows**, 33.75 wall seconds (29 test seconds). Current commit scope has **72 tooling checks**, selected separately after three clock-failure diagnostic checks were added; the working tree also contains five tests for an **unlinked** future overlay package, reported separately rather than counted as accepted runtime work. No new full 5,701-case rerun was made; that pinned corpus remains the prior accepted original-ISA evidence.
- Explicit long lane **1/1 pass**, 18.83 wall seconds (16 test seconds), with genuine COMMAND.COM, VER and exact 35-file DIR/9,216-free-byte/returned-prompt proof. Final **588,937 instructions**, **592,171 calls**, **1,269,694,142 CPU-step cycles**, **9,698,220 support cycles** and **26,364,820 setup cycles**. Ten assembly-enqueued keys and 939 changed-screen observations are retained by raw identity/reference; source/media unchanged.
- Runtime CODE **12,138**, RODATA **864**, DEVICECODE **3,684**, BSS **222**, DEVICESTATE **147**, ZP **18**, linked **21,631**, PRG **22,117** with **5,417** padding/startup-zero bytes. Unit CODE **13,054**, RODATA **888**, TESTCODE **36**, DEVICECODE **3,684**, ZP **30**, linked **22,619**, same PRG with **4,441** padding/startup zeros. UCI buffer C100–C8FF is now linked. MAIN runtime/unit headroom is **1,321/345** bytes, DEVICECODE **412**, and C900–CFFF **1,792** remains a future code budget.
- Profile **1/1**, 12 samples: **61,959,008 CPU cycles**, **18,258,732 native instructions**, **10,314 guest instructions**, **12,902 calls**, **223 DMA operations / 114,176 bytes**, exact registers/full 1 MiB RAM. Identity `87eab9545143199ee360ca7831af65876e61792424090f891a72300d89927770`. Warm register **1,409.40 cycles/instruction**, 20 KiB REP **1,081.04 cycles/byte**; physical exclusions remain.
- Historical [first physical clock run](evidence/c64u-clock-first-failure-20261015.json) `agentworking/runs/c64u-clock-20261015-030029` failed first Manual **1 MHz** with mailbox **01e1000003000000** (error **3**); 16/64 MHz calibration was not reached. Prior machine/turbo/media configuration was restored and reset/resume completed. The first error-3 subreason remains unknown. Failure capture now saves full RAM/mailbox/40-byte DCK1 before cleanup reset; the subsequent corrected matrix below passed. This first attempt itself provides no clock-domain calibration. Physical DOS execution and XT speed remain unmeasured.
- Native startup remains init+idle. File-command loader, C64 font/VIC rendering/key scan, IRQ scheduling, persistent Ultimate/IEC storage and 2 MiB→20 MiB HD remain required. Private file/render/overlay components remain unlinked. The earlier missing `video.inc` Makefile dependency is now present; build identity captures this correction.


Clock diagnostic correction before commit: the standalone probe now passes **6 Peddle tests and 15 tooling checks**, including three new failure-capture cases. Its endpoint window is **16 PAL raster lines**, yielding an independent **±1,008 phi2-tick** bound over the 100-frame delta. The runner captures full RAM, mailbox and the 40-byte DCK1 record before cleanup reset on failure. `src/host_clock.s` is unchanged. Current feature tooling is **72**, checked separately; working discovery is **77** with five unlinked future overlay-package tests. The original 258-test quick run's 74-tooling working count remains historical. First physical error 3 is retained with unknown subreason; the subsequent physical success is recorded below.


## Accepted physical PAL CIA/raster clock matrix

The corrected probe passed Manual **1/16/64 MHz** in `agentworking/runs/c64u-clock-20261015-031712`, on firmware **3.14**, FPGA **121**, core **1.47**. Over **100** observed frames, raw CIA deltas are **1,965,627 / 1,965,599 / 1,965,600** ticks, errors **+27 / −1 / 0** from **1,965,600 ±1,008**. All runs report zero sampling retries; cross-speed spread is **28** ticks. Machine/turbo/media configuration restoration and reset/resume passed. [Physical evidence](evidence/c64u-clock-20261015.json).

This accepts the observed PAL CIA-versus-raster clock domain and turbo independence, not external wall-clock accuracy, interpreter/REU throughput or an XT ratio. `src/host_clock.s` is unchanged, and conversion into native scheduler/UCI deadlines is not yet wired. The first rejected error-3 run remains preserved; the corrected 1 MHz post-read raster endpoints were 8/8, suggesting the former eight-line window as a possible cause, but the missing old RAM capture prevents proof.

The final selected feature tooling command passes **72/72 in 0.331 seconds**; working discovery has 77 including five unlinked overlay-package tests. The original 258-Zig/74-working-tooling quick result and its then-69 in-scope subset remain historical. Probe-specific checks are six Peddle tests/15 tooling checks. No guest/DOS/global runtime-source result changed in this diagnostic/physical follow-up.

## Verified FILE/TEXT overlay and dispatch slice

The full gate accepts 298 tests/all 5,701 hardware cases in 66.84 host wall seconds, with 89 tooling checks in 0.50 seconds. Long DOS passes 1/1 in 14.88 seconds; all 939 observations and complete guest RAM/CGA/register/input results equal 1fb3fe7. Profile 12 samples totals 59,844,100 CPU cycles, 10,314 guest instructions/12,902 calls, 223 DMA/114,176 bytes; all full 1 MiB state checks pass. Host durations are not physical performance.

FILE 1,088 bytes and TEXT 906 bytes share only C900–CFFF. Resident manager 363 DEVICE + 134 MAIN bytes and cold-entry 32 bytes hold ownership across calls. State 197 bytes; MAIN ends 3BE3 runtime/3FB3 unit, leaving 1,052/76 bytes. DEVICE ends 5FCE, leaving 49 bytes. Final PRG 26,625 bytes loads 0801–6FFF, including 4,096 startup assets released only after native bootstrap. Headers and linked payloads are checked independently by build tooling; runtime payloads are trusted immutable, not CRC-verified. Native startup still idles after initialization. [Contracts](../docs/OVERLAYS_IMPLEMENTATION.md), [evidence](evidence/overlays-dispatch-20261015.json).

## Verified linked cold importer

Native code/state 7000–73A2 totals 931 bytes; zero tail 3,165 bytes makes PRG 30,721 bytes through 7FFF, no resident growth. Dedicated 8/8/20 test seconds includes exact DOS disk1 CRC 30770A37 and 723 read-only commands, seeded 4 MiB oracle/guards, failures and optional source-model isolation. Root default 298/99 passes in 36.38 wall seconds with 597 selected hardware cases. Native entry still idles. [Contract](../docs/IMAGE_IMPORT_IMPLEMENTATION.md), [evidence](evidence/image-import-linked-20261015.json).
