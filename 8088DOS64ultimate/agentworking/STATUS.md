# Current state

Updated: 2026-10-15, America/Los_Angeles.

**Phase: six-overlay floppy-only native DOS, MODE CO40/CO80 and complete recovery accepted physically; physical HD and external display acceptance remain pending.** Implementation remains active, with local commits only.

Current runtime98fcd115/unit6eba1ee7,42497-byte PRGs load0801–ADFF. Root417default/597quick/218tooling plus nativeDOS1/MODE1/HDfixtures1/backend14/BIOS12/cold6 pass. Three optional long cases skip in the root quick lane; reviewed eight-case long HD and5701CPU proofs are retained by exact bothPRG/203execution-test-source identity. All398frozen dependencies independently checked. Independent normalproduction review13 and shadowhost28 pass. Required Make range.inc dependency fixed without nativebytechange. Actual rootDOS64KiB capture passes sixresidentproofs/all3584shadowbytes/A5guard. [Evidence](evidence/hd-production-20261015.json).

Sixassets commit12288bytes toREU340000–342FFF; separate A000–ADFF copies to hostF000–FDFF beforecache/BIOS.23cacheframes initially overlap sources. MAINfree115runtime/114unit,DEVICE22,cold1093/118;HDBIOS2144+1440zero tail. BSS223,DEVICESTATE659,ZP18/30. [Memory](MEMORY_BUDGET.md),[HDcontract](../docs/HD_IMPLEMENTATION.md). HDdisabled remains default; realDOSowns FAT/INT21/loading. PhysicalHDwrite failure must preserve newuncertainsector350000 andhandoff352000 before restoring oldREU.

Frozen three-overlay647eca has physicalC64U Manual64MHz/PAL/firmware3.14 DOS/VER/DIR /P/all35entries/9216free/returnedA> andfirst4MiB/config/media/reset acceptance. Currentfive3c physicalattemptfailed180s beforeVERcomplete; native-file4MiBrestorepassed231.923s. Those scopes remain unchanged. [EarlierDOS](evidence/c64u-native-dos-20261015.json),[failedapp/recovery](evidence/c64u-native-file-recovery-20261015.json).

Fresh Terminal physicalsix run085647 PASSES with D64Hdisabled,37coherentscreens/14keys/35entries/9216free/returnedA>,684371guest at118.151s;app+evidence138.700s. Allfivephysicalresidentsegments,3584shadowbytes/1440tail/A5guard andfull8000bitmap/1000matrix match. PITenabled/ready1/errors0,total1351. Fresh4MiBbackup beforeapp andallbyteaftercompare,firstattemptnativefile222.093s<600,priorconfig/media/resetpass;whole436.493s/exit0. Ownedfloppy/twoPRGs postFTP exact. [Currentphysical](evidence/c64u-native-six-20261015.json). OptionalMODEhostproduction nowpromoted/root238tooling;both targetPRGsunchanged. [MODEhost](evidence/mode-host-production-20261015.json). RESTunderlyingRAM0000/0001 does notprove liveCPUbanking. Humanmatrixkeyboard/external40/80readability/CGA/physicalHDpersistence/IEC runtime/nearXTspeed remainopen. PrivateIECfix/coldprofile, HDfailureevidencehook andowned-clockperformance are separately under review; no privateproof expands shared acceptance. Historicalrecords below retain their original scope andfailures.

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


## Configured native runtime accepted in Peddle; first physical attempt rejected

The accepted runtime647eca6fb65db56153067c6a6be0209cb7f63955a904e618400b6734e2dc1023 and unit ecc86eeeb8366ded34a04df29d149cf617275db67bd4a6874e8a2b2d89330997 replace idle-only native startup when explicitly configured. Default D64N remains disabled. Full original360KiB import/CRC/EOF/CLOSE, BIOS/cold release, input/text and bounded guest execution now run through the native entry. Peddle native end-to-end passes606910 instructions/40315 ticks/149 observations/14 keys, genuine VER and exact35-entry DIR /P/9216free/returned A>. Root global326/597quick/143tooling, focused14, legacy DOS34 exact comparisons and12 profiles pass. Raw `agentworking/runs/native-runtime-20261015-root`; [evidence](evidence/native-runtime-20261015.json), [runtime contract](../docs/NATIVE_RUNTIME_IMPLEMENTATION.md).

First failures are retained: blink128 was a real target error, fixed to strict0/1 and exhaustively checked; AH01-polling DOS required periodic coherent observations; old pagination text on another row required cursor-local prompt checks; one legitimate scroll exceeded the former3M test budget. Native source and host runner fixes are reflected in the pinned binaries. MAIN runtime/unit free988/12, DEVICE12; cold2471/tail1625. Additional modules require deliberate placement, not assumed spare RAM.

Terminal-owned physical run `agentworking/runs/c64u-native-dos-20261015-054149` failed before recovery service loading: POST runners:run_prg404 Cannot open file; cleanup POST configs500 Could not buffer attachment. No verified REU backup, native DMA or application occurred; original result remains failed. Full RAM was captured before cleanup/reset, reset/resume passed; an independent read-only follow-up proved machine/turbo/mounted-media JSON equality. Underlying temporary-file failure remains unproven. [Failure](evidence/c64u-native-first-failure-20261015.json). A private firmware-supported bodyless PUT/file-path adapter is in progress; no Temp deletion or firmware reboot.

Overall goal remains active. Private PIT/IRQ, five-overlay/unit-cold placement, CGA,2/20MiB DOS-created fixtures and HD-backend proofs are proposals pending root integration; none extend accepted runtime scope. No physical DOS/display/input, persistence/IEC/HD or XT-speed acceptance yet. Commit locally; no pushes.


## Physical development transport probes

Terminal RAM-only checks pass and leave settings/media equal. Serial256 same-value128byte PUTs average37.33ms, implying1223seconds for4MiB payload alone. Four/eight workers both take9.49seconds per256requests (~1215second extrapolation), proving no useful throughput improvement. Full RAM captures include volatileD000–DFFF IO; all compared RAM outsideIO and original128byte staging/restoration are exact. No REU commands or PRG launches occurred in these PUT probes.

A fresh owned FTP47105byte extended recovery PRG subsequently loaded/runs through the bodyless file route: original590 executable bytes and all16384 staging bytes exact, mailboxREADY/sequence0/noGO. FTP+readback1.679s and runner→READY/capture2.317s imply~1023seconds for256 reloads; that bulk proposal is also rejected before touching REU. Settings/media equality and reset/resume pass. Native DOS has still not run physically. [Probe evidence](evidence/c64u-rest-transport-probes-20261015.json). Next is a single-file native read-only UCI4MiB restoration program, retaining verified backup, CRC/EOF/knownCLOSE and independent fullREU readback under600second deadlines.


## Bounded delta recovery prepared; UCI code identity corrected

Root host/tooling168/168 pass7.25wall;17 new attachment-free transport and7 delta-recovery tests include complete4MiB/unchanged upper12MiB, unexpected regions, partial upload, partial DMA plus alias change, fresh exhaustive rescan, incomplete scan/deadline rejection and exact full readback. `DeltaService` scans ALL4MiB against the complete verified immutable backup within600seconds, uploads only changed16KiB chunks, then the unchanged recovery workflow independently compares ALL4MiB. Every retry rescans; no expected-footprint assumption skips bytes. Actual Terminal-owned staging verified both current corrected native/service PRGs in a new owned directory. No full native physical run has occurred yet. [Preparation](evidence/delta-recovery-preparation-20261015.json).

Hardware identity now handles exactly four legitimately self-modified UCI operand bytes: upload/read AD and drain/store8D operands must point inside their own896-byte buffers after successful DOS. All other resident code remains byte-exact, including fixed DF1C register operands. Stable exported aliases add no target bytes; the first naive cheap-local alias compile failure is retained, and corrected scoped labels rebuild runtime647eca/unit ecc86 identically. Root reran native DOS1/1,27.29wall,606910instructions; actual64KiB native capture passes this strict resident comparison. Physical launch must use refreshed labels and final host hashes, not the earlier review package. One-file native UCI restore and combined IRQ/CGA/HD candidates remain private, independently tracked work.


## Physical native DOS3.3 accepted at Manual64MHz

Terminal-owned `agentworking/runs/c64u-native-delta-20261015-064456` PASSED on firmware3.14/FPGA121/core1.47 PAL16MiBREU. The frozen THREE-overlay runtime647eca/configured3103258f imports the real whole floppy through nativeUCI, executes DOS's own boot/COMMAND.COM, accepts14 BIOS-enqueued keys and verifies VER3.30, all35 exact DIR /P names/sizes,9216free,1pagination and returnedA>.108 coherent observations; final622478 guest instructions at109.456seconds; application plus memory evidence124.474seconds. No host kernel/EXE loader or INT21 replacement. Resident code matches after strict four-byte UCI operand validation; physical16KiB CGA equals nativePeddle exactly. Source and postrun FTP disk/PRGs read back unchanged.

All4MiB backup/readback bytes independently compare equal, SHAac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3. Exhaustive256-chunk scan finds37 changed16KiB chunks/606208bytes; scan+write282.119seconds stays below600bound, first attempt succeeds, then ALL4MiB independently reread. Prior configuration/turbo/mounted media restored and reset/resume pass. Complete workflow545.455seconds. [Physical evidence](evidence/c64u-native-dos-20261015.json).

Captured native80column bitmap8000bytes and matrix1000bytes exactly match an independent CP437/narrow-font/attribute oracle. [RAM reconstruction](runs/c64u-native-delta-20261015-064456/native-framebuffer-reconstruction.png) uses an illustrative palette, not a physical HDMI screenshot/readability approval. Physical matrix input/40column mode/CGA, persistence/IEC/HD and XT-speed acceptance remain open. The new five-overlay timer/CGA source is a separate root-verified Peddle candidate; this hardware run does NOT establish its physical acceptance. Overall goal remains active.


## Genuine DOS internal file workflows accepted

Root `make test-native-builtins` passes2/2 plus9independent FAT12 oracle checks,51.28wallseconds. Actual nativeENTRY/import/ticks run11commands:MD/CD,COPYCONFIG.SYS,TYPE,REN,IFEXISTTYPE/ECHO,DEL,expectedmissing-fileTYPE,CDroot,RD.754292guestinstructions/3562751733CPUcycles/49859ticks/185observations/173BIOSkeywords. All720sectors captured at eachcheckpoint; bothFATs, original38live entries(35visiblefiles+2hidden+label), everyoriginalfilechain/content and exactcopiedbytes verified. Freebytes9216→8192→7168→8192→9216; final logicalallocation/rootoriginal, deletion slack preserved. Sourceimagebyteexact; mutations are disposableREU only. TargetPRGs unchangedd0aa/5b174. [Evidence](evidence/dos-native-workflows-20261015.json). RealMODEAH1Bh failure remains recorded; a separate source-backed one-byteXTBIOSfix is privately under verification. No persistence/matrix/physicalacceptance follows.


## Genuine MODE CO40/CO80 accepted; original XT ignored-function fix

Current runtime3c2627a4/unit6280024d differs from timer/CGA checkpoint by exactly one byte at host5014, no layout growth. Original11/08/82 IBMXT listing and separately archived ROM bytes show out-of-range INT10AH10..FF restores registers/IRET unchanged. Target now follows that behavior; noEGA/VGA services are implemented. Genuine suppliedMODECO40thenCO80 passes nativeENTRY/import/DOSloader/ticks, both returnedprompts,mode1/40thenmode3/80 BDA and all8000bitmap+1000matrixbytes each.377062guest/1932569645CPU/24931ticks/93observations/22BIOSkeys. Source/inREUfloppyexact. Root410default/597quick/172tooling andMODE1pass; private storage regression counters/files exact. [Evidence](evidence/dos-mode-xt-20261015.json). Modeclearlegitimatelycosts6213001cycles, so MODE-only bound8M; retained5Mfailurewasfixturebudget,notCPUfault. No newphysical/originalXTsilicon/readability/XTspeedclaim.


## Source-complete opt-in whole-file REU recovery prepared

Native-file recovery is promoted as an explicit development backend; default delta stays unchanged. Clean source builds reproduce disabled4624byte388069 helper and original592byte40fe service. Root27/27host tests pass; seven native tests compile, with prior7/7actualPeddle proof reused only by exact target/core identity. Compiler/source/output provenance is retained. Rootnormalbuild passes and runtime3c2627a4/unit6280024d remainbyteexact after zero-byte FILEownedtarget alias export. Localnormalapplicationvalidation accepts currentnew5artifacts/staging/PALevidence withoutnetwork or stalebackup. [Evidence](evidence/native-file-recovery-promotion-20261015.json),[contract](../docs/NATIVE_FILE_RECOVERY.md).

ActualTerminalFTPstaging `/usb1/DOS64_TEST/native-prgs-five-20261015-074537` byte-verifies currentconfigured00e70875/36865bytes and40fe/592. No new5C64execution yet. Next rootphysicalrun uses freshfull4MiB snapshot before application; nativeCRC/EOF/knownCLOSE plus independentfull4MiBaftercompare/config/media/reset are mandatory.600secondabsolutephase coversFTP/native/reload/compare; no physicalnativefilethroughput claim until that run. Historical064456backup is localvalidationonly, never a testrestoration source.


## Clean-checkout DOS disk helpers accepted

Seven additive source/asset/test/doc files provide read-only FAT12/FAT16/MBR/CHS inspection and genuineDOSBox-X2/20MiB fixture creation from immutable supplied images. Root189toolingpass(17new),allseven sourcehashes and both accepted wholeimage/manifests independently rechecked. Independent review17tests+3adversarial cases/all8390656CROSS16words passes. Final2MiBSHA590c110b;20MiBSHA0637b75c,actualDOSCROSS16file16781312bytes spansraw01000000. Systemfiles/sourceimages unchanged. [Evidence](evidence/dos-disk-tools-20261015.json),[usage](../docs/DISK_TOOLS.md). Reference creation ran realFDISK/FORMAT/SYS/CHKDSK/HDboot; exact2MiB derived fromadvertisedgeometry3MiBtemporaryonlyafterextra1MiBzero. No20MiBbinarytracked,no nativeHD/physicalpersistence/performanceacceptance implied.


## Physical native-file recovery accepted; new-five-overlay DOS attempt remains failed

Terminal `c64u-native-five-file-20261015-080121` exits1 because current3c/00e708 DOSapp hits180secondobserverbound beforeVER/DIRcomplete. It reachesinitialA>,143coherentviews/6BIOSkeys,lastobserved215630guest;failurecapture217502. FullresidentBASIC/CODE/RODATAexact,DEVICEexactafterfourvalidatedUCIoperands. FailureRAMshowsPAUSED/error0/command0/ackA5: the finalREAD had completed, so genericACKtimeoutdoesnotprove12secondnativehang. PITflags1/1/errors0/0/752periods showpartialnewtargetprogress,notfullfunctionalacceptance.

SEPARATE native-file restoration PASSES firstattempt: fresh4194304bytebackupbeforeapp,actualFTP/native388069CRC/8192sectors/knownCLOSE,original40feserviceall256chunkreadback/rootallbytesequality, SHAac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3. Complete restorestageincludingouterreload231.922859seconds<600;wholeworkflow488.766818seconds. Priorconfiguration/turbo/mountedmedia/resetresumeallpass. Independent86checkaudit supportsrecoveryonly. [Physical record](evidence/c64u-native-file-recovery-20261015.json). Upper12MiBnotindependentlycompared; priorCPUexecutionnotrestored.

Observeranalysisfinds113.390secondsconfirmedpausedlowerboundover143SNAPSHOT→RUN windows,versus56.018secondsintheolderacceptedrun; workloads/binaries/transportdiffer,soPIT/MMIOcostisnotisolated. Root197tooling+27recoveryhostchecks/localexplicit2s360svalidationpassforOPTIONALboundedobservercontrols,old0.25s/180sdefaultsretained. [Observer evidence](evidence/native-observer-controls-20261015.json). Nextphysicaltargetmaybethe reviewed6overlayHD/scrollcohort afternormalrootpromotion+strictF000sourceidentity; no stalebackupreuse ornewtargetacceptanceyet.


## Physical MODE acceptance, 2026-10-15

Terminal run `c64u-native-mode-file-20261015-092257` passes genuine MODE CO40/CO80 on runtime98fc/configuredab50, with HD disabled. Both returned prompts; 22 BIOS keys and 25 observations; 112.328 seconds including application evidence. Each checkpoint independently checks all source fonts, 8,000 bitmap bytes, 1,000 matrix bytes, coherent BDA/CGA and resident/shadow code. Guest counts are 340,818 and 434,422. Fresh original floppy and configured PRGs were staged and read back byte-for-byte.

The first recovery attempt failed at OPEN/cleanup with protocol error4, unknown handle and zero sectors before any restore DMA. Its failure RAM is retained; stale status bytes with declared length zero do not explain the firmware cause. Attempt two passed fresh staging/startup/CRC/EOF/known CLOSE and independent comparison of all4,194,304 bytes. Prior machine/media settings and reset/resume passed. Observed restoration across both attempts took272.930 seconds, whole workflow461.177 seconds; the configured600-second bound applies separately to each allowed attempt. Independent preflight741 and raw audit1,443 checks pass. All349 reviewed inputs have immutable historical copies. [Evidence](evidence/c64u-native-mode-20261015.json).

This accepts BIOS-ring input and captured framebuffer bytes. Physical matrix input, external VIC/HDMI readability, graphics modes, physical HD/IEC/floppy-save persistence, upper12MiB and near-XT speed remain open. Shared target remains98fc/6eba. Private combined clock/PIC candidate passes421default/597quick/238tooling and54 focused/native gates, under independent review; it has no physical acceptance yet.


## HD failure-evidence foundation

Four reviewed host files are promoted. Root273tooling and27native-file host checks pass; independent clean-layout273 checks pass with networking forbidden and zero live children. Optional pre-restoration collection retains RAM, newly authoritative sector350000, handoff352000 and complete/partial owned remote image. Failed/interrupted collection and malformed reports cannot skip full REU/configuration/reset recovery. Default hook=None flow and target PRGs are unchanged. Original rejected/repair cohorts remain retained. [Evidence](evidence/hd-failure-evidence-foundation-20261015.json),[caller contract](../docs/HD_FAILURE_EVIDENCE.md).

Future HD runner must retain the application's original pre-helper RAM; the later collector can see DRS1. Full physical guest-write tracing, owned HD stager/runner and persistence acceptance remain unfinished.
