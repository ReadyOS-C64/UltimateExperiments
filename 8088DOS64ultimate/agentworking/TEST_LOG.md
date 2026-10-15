# Verification log

## 2026-10-14 — planning pass

Scope: repository/reference inspection and planning artifact verification only.

- Read-only BPB/FAT12/root/cluster-chain inspection of all three supplied images; geometry and system-file hashes recorded in `research/reference-images.json`.
- Ran `/opt/homebrew/bin/dosbox-x -version`: DOSBox-X 2026.01.02 SDL2. No DOSBox guest was launched.
- Ran `../../zeropage-tooling/bin/zig version` from the project-relative context: 0.16.0; inspected `zp64c tools` and local test sources. Did not rebuild or run the sibling compiler suite.
- Located NASM, VICE x64sc, c1541 and cc65 tools. Toolchain existence does not prove this project's build.
- Read current Ultimate documentation/source and Soft-80 implementation, plus instruction/BIOS/test-corpus references. No physical C64U was accessed.
- Ran `python3 agentworking/research/validate_planning.py` from this project root: PASS. Checked 19 Markdown files, 28 local links, contiguous 65,536-byte host and 16,777,216-byte REU maps, repeatable inventory, unchanged hashes for all three originals, tracked-record/ignored-scratch policy, and recorded D81 roundtrip. Full results: `research/planning-validation.json`. These are planning checks, not emulator tests.
- c1541 D81 container experiment passed: 819,200-byte D81, 1452-block SEQ containing disk 1, 1708 free blocks, extracted file exactly 368,640 original bytes. Exact argument arrays/output are in `research/d81-container-proof.json`. First attempt hit a host UTF-8 decoding error on a PETSCII directory byte after creating the file; retry captured raw bytes and extracted successfully. c1541 also printed an unavailable OpenCBM library notice, but image operations returned zero and byte comparison passed; no physical CBM device was used.

Reproduce inventory from this project root:

```sh
python3 agentworking/research/inspect_reference_images.py > agentworking/research/reference-images.json
```

The inventory command reads original images and writes only the report named in the redirection. It is not a full FAT checker or boot test.

Failed lookups during research: the guessed `uci/dos.html` documentation path and `libsrc/c64/soft80.s` source path were incorrect; resolved to `uci/ultimate_dos_target.html` and the split Soft-80 files. An IBM XT PDF URL could not be fetched; accessible BIOS listing/reference sources were used. These were research lookup failures, not product test failures.

**Not run:** project unit/integration/end-user tests (not implemented), DOSBox reference boot, VICE runtime, real C64U, emulator benchmarks. No product functionality has been marked passed.

## Future entry format

Record date, slice/commit, exact working directory and command, tool/firmware and fixture hashes, lane/configuration, pass/fail/skipped totals, first failure, output/evidence path, limitations, and any deviation from the plan. Preserve a failing regression before fixing it; link its passing rerun.

## 2026-10-14 — M0 foundation

Working directory: this project root. Commands: `make test`; `python3 build_support/reference_boot.py --timeout 15`.

- First `make test`: assembly/maps built; runaway test exposed a zero CPU clock counter and required interrupting exec session 29588. Peddle core expects external clock advancement. Fixed the bridge without editing upstream source, then added exact-cycle regression coverage.
- Final assembly test pass: **10/10 Zig/Peddle tests**, run time 313 ms (compile 1 s on warm host cache), plus **4/4 Python linker-contract tests**. Linked runtime CODE 73 bytes, BSS 36, PRG 87; raw fixture payload matches linked PRG bytes. Final negative linker test was made independent of exact code length.
- Reference boot passed: `agentworking/runs/reference-20261014-220319/result.json`; compact retained evidence `agentworking/evidence/dosbox-reference-20261014.json`. Real guest output: MS-DOS Version 3.30; DIR lists supplied utilities. Original hash unchanged. DOSBox-X logged its 8086 CPU mode as experimental, so it remains a functional reference, not CPU conformance/timing proof.
- `build/manifest.json` captures actual tool binaries/versions and source/output hashes; vendored Peddle archive/files checked against its pinned upstream commit.
- Not run: VICE or physical C64U; no guest interpreter, REU/UCI, target boot or XT performance claim.

## 2026-10-14 — REU primitive and shared integrity probe

Working directory: this project root. Commands: `make test`; `make test-vice`; `python3 build_support/vice_probe.py --verify-existing logs/vice_auto_20261014_222223 --evidence agentworking/evidence/reu-vice-20261014.json`.

- Final fast pass: **26/26 Zig/Peddle**, 912 ms warm execution; **9/9 Python tooling** (four linker, five capture-verifier). Includes 4/8/16 MiB final-bank actual-assembly transfers. Tools remain Zig 0.16.0, ca65/ld65 V2.18 and Peddle `c23e34a7e6516b284750b8c7caaa8c41948a407a`; exact binary/source/output hashes in `build/manifest.json`.
- Runtime CODE 255, BSS 46, ZP 4, BASIC 12, header 2. Probe CODE 416, BSS 46, ZP 6; PRG SHA-256 `a1e277d2ed8bfad12796efa4a54eec3b4e57e355086b228c030dd9ccb2d3291e`.
- First VICE attempt failed required plan-schema retry_policy validation; fixed generator. Run `logs/vice_auto_20261014_222223` then succeeded, five steps; completion assertion needed two attempts, error zero. Config: established .NET x64sc harness, headless/warp, 16,384 KiB REU, virtual drives disabled. No physical C64U access.
- Rechecked existing capture without another slow run: all 4,096 restored bytes match pattern; captured executable equals current PRG. Restored SHA-256 `544a424fc1268f07738317486fd59978ebb6b3107c2ef80caacc2afe60b64f1e`. Tracked record `agentworking/evidence/reu-vice-20261014.json`; full manifest/state/dumps retained in ignored logs.
- Capture-verifier negative tests reject corruption with a passing mailbox, failed mailbox, partial run and stale executable. These test acceptance reliability, not extra target functionality.
- Mock checked against pinned VICE source, but one VICE integrity vector does not validate all modeled edges. IRQ/compare/swap/deferred DMA and unknown CIA/VIC fail explicitly. No physical/DMA timing, UCI/storage/cache/interpreter/target DOS boot or XT-speed result claimed.
- NES86 source inspection pinned to `d72debaa0a5daed533d994e087fa2963e1793820`. Downloads only in ignored scratch; no runtime code copied. License/adaptation boundaries in `docs/EXISTING_EMULATORS.md`.

## 2026-10-14 — 20-bit addresses and coherent byte cache

Working directory: this project root. Commands: `make test`; `make cache-probe probe`; `make test-cache-vice`; `python3 build_support/vice_probe.py --kind cache --verify-existing logs/vice_auto_20261014_225535 --evidence agentworking/evidence/cache-vice-20261014.json`.

- First behavior run: 38/39 Zig passed; expected P value in the test was 28 after applying mask 0C, while the target correctly returned 08. Fixed that expected masked value. No target flag fix was required. A separate address-size import warning was corrected with `.importzp` before clean final builds.
- Final pass: **41/41 Zig/Peddle**, approximately four seconds warm, **10/10 Python tooling**. Includes 4,103 segment/offset pairs (seed 808864), all 2,048 physical pages at both edges, 1,200 oracle operations with two frames (seed 65108088), pin cases, ROM/holes/CGA, host write guards and synthetic prefix-DMA failures. Distinct pin/replacement patterns guard against all-zero false positives.
- Runtime CODE 1,109, BSS 62, ZP 16, PAGEMAP 2,048, CACHEMETA 192; PRG 1,123 bytes. Cache probe CODE 1,284, ZP 21, PRG 1,298. Full source/tool identity is in `build/manifest.json`; retained compact slice record includes maps and actual test output.
- Measured Peddle profile: ALL_RAM warm byte read **221 CPU cycles** without DMA; shared cache probe **1,103,632 CPU cycles**, stack high-water **14 bytes**, **12 DMA operations / 6,144 bytes**. DMA stalls/physical elapsed time are unmodeled. This is not an XT-performance result.
- Native cache probe passed VICE run `logs/vice_auto_20261014_225535`, five steps, 16 MiB REU/warp/headless. Completion took three observations while boot/probe initialized. All 1,536 exported bytes and captured executable independently match; surrounding partial guest pages also checked in Peddle. [Compact evidence](evidence/cache-vice-20261014.json). Rechecked original REU capture against rebuilt unchanged standalone PRG without another slow run.
- Read-only physical discovery launched in Terminal (window id 1294) through `build_support/c64u_preflight.py --host 10.0.0.79 --output agentworking/runs/c64u-preflight-20261014-225535`. All five GET requests succeeded without API errors. Device firmware 3.14, FPGA 121, core 1.47; enabled REU 16 MB, PAL, configured speed 64 under C64U-register control. Raw outputs retained there; [compact inventory](evidence/c64u-inventory-20261014.json). No machine/media mutation, physical PRG, UCI transfer or timing test occurred.
- Still absent: multi-byte 8088 operand policy, instruction interpreter, BIOS/range coherence, disk backends, target DOS boot, physical integrity/timing, final page-size decision and optimized fetch path.

## 2026-10-14 — physical cache matrix

Commands from this project: `make hardware-helpers`; `make test`; Terminal-owned `/usr/bin/python3 build_support/c64u_probe.py --host 10.0.0.79 --output <owned-run>`. Fast tests: 42 Zig/Peddle + 15 tooling passed.

First helper compilation rejected C-style `!` in a ca65 conditional; used nested `.ifndef` blocks. First physical run `c64u-cache-20261014-231434` backed up/restored REU successfully but failed speed configuration with HTTP 400 before running the cache probe. Discovered firmware advertises ` 1` with a leading space; selected exact advertised values and added a regression.

Run `c64u-cache-20261014-231652` passed manual 1/16/64 MHz settings, firmware 3.14 / FPGA 121 / core 1.47 / PAL / 16 MB REU. Each captured 1,536-byte result has SHA-256 `90c3cb67dae979134af6135359c23bcd3bd7c5a2dff06e41a794bcbf493b3230`. Uploaded executable bytes independently match. Backup and restored 2 KiB envelope SHA-256 both `32bfa7834e0c6f117ad40eb75cad39e0c945bec449e6de26687504396c43fdb5`; prior configuration/media matched. [Compact evidence](evidence/c64u-cache-20261014.json); raw RAM/REU captures and owned restoration PRG retained in ignored project-local runs. No persistent hardware file writes. Prior program execution is not resumed after reset. Timing/UCI/IEC/full IRQ/DOS boot remain untested.

## 2026-10-14 — initial original-8088 execution

Commands: `make test`; `make test-cpu-corpus`; explicit source import `python3 build_support/fetch_8088_subset.py`. Initial broader run passed all 53 Zig tests including 481 hardware cases but took 27 seconds; separated the default 41-case representative lane from the full corpus. Final default passes 53 Zig + 15 tooling in about six seconds; final full corpus passes all 481 cases in 26 seconds. No target behavior failure was observed in this slice.

Corpus pin `aea84484abc79d09639d855b7b0ab32bc9e4dbeb`; selected 20 opcode files, first 24 rows plus audited A3 edge row 9570. MIT license and compressed-source/fixture hashes in third_party/sst8088/UPSTREAM.json. All guest registers and all 1 MiB RAM compare after executing actual linked assembly and flushing its cache. Cycles/queue/interrupt behavior are not checked.

Runtime CODE 2,019, RODATA 8, BSS 84, ZP 16; PRG 2,041. Independent guest tests include offset/physical/fetch wrap, self-modification followed by jump, prefix yielding, control flags, halt/loop budgets, STI shadow and latched unsupported/error conditions. Word offset-FFFF policy follows MartyPC source pin 05c0d088e84ad6bbfac9b3f0d051e7eadefd9f44; audited A1/A3 hardware files lacked that exact case, so no direct hardware-FFFF claim is made.

No slow VICE/physical rerun was necessary: those standalone builds exclude the new execution module and retain uploaded byte identity. Arithmetic, general ModR/M, stack/strings/I/O/interrupts, BIOS and target DOS boot remain absent.

Final integration addition loads the unchanged supplied disk-1 boot sector: target executes its jump to 7C36 and CLI, then latches unsupported XOR opcode 33 at 7C37 without changing AX. First attempt failed in Zig fixture loading because an exact-size reader limit produced StreamTooLong; allowed bounded headroom and separately asserted the exact disk size. This was a fixture failure before CPU execution.

Host RAM comparison now uses a bounded native memcmp with first-divergence fallback, retaining all 1 MiB checks. A separate test flips first/middle/last bytes and checks rejected bounds. Final quick lane: 55 Zig/Peddle + 15 tooling passed. Full corpus remains 481 functional cases; actual current output/profile retained in the slice evidence.


## 2026-10-15 — arithmetic, ModR/M, stack and runner

Commands: `make build`; `/usr/bin/time -p make test`; `/usr/bin/time -p make test-cpu-corpus`; explicit pinned import `python3 build_support/fetch_8088_subset.py`. Toolchain remains Zig 0.16.0, ca65/ld65 V2.18 package 2.19, pinned Peddle unchanged. Full input/tool/artifact hashes retained in compact evidence manifest.

First integrated compile found a symbol-parser local shadow during concurrent runner work; fixed before execution. First behavior gate passed69/71: stack test incorrectly expected raw $01 latch35 rather than preserved DDR/output bits (actualF5); corrected the assertion. C7 hardware idx0 uses /6 and exposed the documented-only guard; implemented original extension aliases and retained/expanded all failing evidence. Final C6/C7 selection covers every extension in quick/full. No remaining known failure in the accepted slice.

Final quick **75/75 Zig/Peddle + 15/15 tooling**,338 hardware cases, wall5.21/user4.31/sys0.87 seconds. Full **75/75 Zig/Peddle**,1,622 hardware cases, wall11.57/user10.72/sys1.63 seconds. Test-only reports2s quick/9s full. Logs `build/alu-operands-stack-test.log` and `build/alu-operands-stack-corpus.log`; profiles `build/cpu-corpus-{fast,full}.json`. Both compare all registers under defined masks and complete1 MiB RAM. Corpus pin unchanged,162 opcode/extensionfiles; fixture 722,208 bytes SHA-256 58ad1e901f81a4a1bf26de2352649f7b4da5bd66c7d185dbd2d81b6ecc453239. Independent tests include 3,200 ALU oracle inputs, 720 address combinations, highbyte/register widths, eviction-surviving descriptors, flags/stack/wrap/failure paths.

Host batching/cached symbols preserve exact known clocks and old-loop failure precedence/RAM/write bitmap/diagnostics in3 regressions. Standalone identical ALU workload medians measured by runneragent0.626 s old → 0.491 s batched → 0.0226 s host C++O2, excluding build time. Final global build uses host C++O2 and Debug Zig assertions. Do not equate these host improvements with target8088 throughput.

Runtime CODE 4,394 RODATA 305 BSS 116 ZP 16 PRG 4,713; unit CODE 4,817 RODATA 305 TESTCODE 36 ZP 23 PRG 5,172. Maps verify before cache/resident boundaries. The unchanged supplied disk sector completes16 instructions and stops at unsupported AC LODSB at 0000:7C51, with zero IVT explicitly documented; not BIOS/DOS boot. Reference disk hashes retained unchanged in manifest.

Rechecked both existing VICE captures using `python3 build_support/vice_probe.py --verify-existing logs/vice_auto_20261014_222223` and `python3 build_support/vice_probe.py --kind cache --verify-existing logs/vice_auto_20261014_225535`; every returned byte and captured executable match current standalone images. No new slow hardware run: CPU-only modules are excluded from those builds. Physical timing, strings/conditional flow, interrupts/BIOS/storage/display and real DOSboot remain unverified/unimplemented.


## 2026-10-15 — strings, conditional flow, shifts and software interrupts

Commands from this project: `make build`; `/usr/bin/time -p make test`; `/usr/bin/time -p make test-cpu-corpus`; explicit pinned source import `python3 build_support/fetch_8088_subset.py`. Toolchain unchanged (Zig 0.16.0, ca65/ld65 V2.18 package 2.19; optimized host Peddle with Debug Zig assertions).

First integrated behavior gate passed 95/95 Zig/Peddle  + 15/15 tooling without a target failure. Added hostP preservation assertions and a 257-element backwards STOS/LODS case to cross CX low-byte borrow and pointer wrap; final quick also passes95/95  + 15/15, wall 6.93/user 5.97/sys 1.35 seconds. Final full gate passes95/95 including 2,278 hardware cases, wall 15.82/user 14.68/sys 1.64 seconds. Test executable reports 4s quick/13s full. Earlier full gate before the additional 257-element assertion passed 16.38s; final evidence supersedes that measurement. Logs: `build/strings-control-test.log`, `build/strings-control-corpus.log`. Quick 502 cases, full 2,278, maximum 8 calls per hardware instruction; independent257-element tests use 17 calls. Driver bounds 256 calls/10M aggregate CPU cycles and 100k per call. Every hardware projection compares registers/defined flags and all 1 MiB RAM after coherent flush.

Pinned corpus now 244 opcode/extensionfiles, including 82 new files; all prior 1,622 projected rows preserved exactly before additions. Fixture 1,053,661 bytes SHA-256 80b5ee9a45a38c6be33bbda351aad3067c63e2111d844e0f2a036dc552eb2138. New independent tests cover 1,024 Jcc flag truth combinations, 64 LOOP cases, 1,748 rotate/shift cases, 8 string behavior tests and 4 software interrupt tests. No randomized new seed; cases are exhaustive deterministic flag combinations and explicit edge tables. Existing ALU seed 8088a1 retained.

Primary source review corrected a modern-CPU assumption before implementation: original /6 shifts are SETMO/SETMOC; counts use all 8 CL bits. Software INT reads IVT before stacking per pinned original MartyPC; independent stack-alias test enforces that functional policy, not hardware bus timing. REP yields at 16 iterations are host scheduling; original guest interrupt restart/traps remain deferred. No source copied.

Unchanged disk 1 sector reaches its INT 13h disk-reset request at 0000:7C6E. Explicit normal guest IRET fixture returns to 7C70, JC/MOV AL complete, and unsupported CBW 98 latches at 7C75. This is CPU/interrupt integration, not BIOS disk service or DOS boot.

Runtime CODE 6,094 RODATA 305 BSS 137 ZP 16 PRG 6,413; unit CODE 6,517 RODATA 305 TESTCODE 36 ZP 23 PRG 6,872; maps verify ranges. Compared all four standalone hardware PRG SHA256 values to previous verified slice manifest: unchanged. Compared all three immutable DOS image hashes: unchanged. No slow VICE/physical rerun; no DMA/pager/hardware code changed. Compact source/tool/map/output evidence saved as [cpu-strings-control-20261015.json](evidence/cpu-strings-control-20261015.json). Hardware IRQ/traps, BIOS/UCI/IEC/display/target DOS boot and physical throughput remain unfinished.


## 2026-10-15 — math/indirect CPU baseline

Working directory: this project root. Commands recorded in `build/math-indirect-test.log` and `build/math-indirect-corpus.log`: `/usr/bin/time -p make test`; `/usr/bin/time -p make test-cpu-corpus`. Explicit hardware-source import remains `python3 build_support/fetch_8088_subset.py`. Toolchain unchanged: Zig 0.16.0, ca65/ld65 reported V2.18 (package directory 2.19), Peddle `c23e34a7e6516b284750b8c7caaa8c41948a407a`, optimized C++ host bridge and Debug Zig assertions.

- Quick checkpoint **114/114 Zig/Peddle + 15/15 tooling**, wall **8.00** / user 6.99 / sys 1.43 seconds; full **114/114 Zig/Peddle**, wall **17.73** / user 16.60 / sys 1.83. Hardware projection now quick **581** / full **2,555**, maximum eight scheduling slices; every case retains full 1 MiB RAM comparison and defined flag masks. Original corpus pin `aea84484abc79d09639d855b7b0ab32bc9e4dbeb`; fixture SHA-256 `ac0aec1995ab621589439c6db0ade54cc8d45c7c5b25f216a2f6466993fe5fe1`.
- Actual assembly covers F6/F7 TEST alias/NOT/NEG/MUL/IMUL/DIV/IDIV and CBW/CWD/XCHG/TEST accumulator/FE INC DEC/FF indirect control/PUSH aliases/POP r/m. Independent edge/seed arithmetic and register/stack/overlap tests supplement original hardware rows. Seeds and selection/source gaps are retained in target tests and `third_party/sst8088/UPSTREAM.json`; REP MUL/IMUL/unsigned DIV are not hardware-corpus claims.
- Original signed minimum-quotient, post-instruction divide saved IP, REP IDIV and FF PUSH SP aliases are explicit. Unaudited FE control/stack and far register-pointer forms fail diagnostically. No broader asynchronous-event or cycle-accurate original-PC claim follows from functional rows.

## 2026-10-15 — coherent ranges, floppy BIOS and genuine IO.SYS handoff

Working directory: this project root. Commands: `/usr/bin/time -p make test` (recorded `build/storage-bootstrap-test.log`); `make test-range-vice` (run `logs/vice_auto_20261015_011028`); `make profile-cpu` (artifact `build/cpu-profile.json`). Final snapshot-helper/physical integration is pending a subsequent entry; these are completed recorded checkpoints.

- First range gate failed its negative staging-layout tooling check (`build/range-test.log`): RANGEBUFFER was absent from the stale linked runtime map. An older privately built object added to the link list had not triggered relinking because Makefile changes were not prerequisites. Corrected link prerequisites and reserved C000–C0FF; later `build/disk-range-test.log` passed **130 Zig + 29 tooling** in **9.03** seconds. Preserve this failure as evidence that build success/old artifact identity alone is insufficient.
- Latest completed quick log passes **147/147 Zig/Peddle + 34/34 tooling**, wall **12.51** / user 11.68 / sys 1.46 seconds. It includes coherent range transfers with dirty neighbors/export authority and injected partial errors, all 720 CHS positions, physical DMA boundaries and disk error progress, exact BIOS ROM/IVT/BDA and callback guards, mutable dirty BDA queries/XT INT 15h, genuine reset/bootstrap and host FAT12 image-helper bounds/immutability tests.
- Genuine guest reset FFFF:0000→owned BIOS→unchanged disk sector→IO.SYS **0070:0000** takes **392 completed instructions** and **12,019,126 native step CPU cycles**, excluding setup. Only whole immutable floppy bytes seed REU media; no host kernel loader/INT 21h replacement participates. An independent oracle checks **22,398 IO.SYS bytes** and all **51 raw sectors** this bootloader reads, including padding/overread beyond the file's **44 rounded sectors**. The floppy/source remain exact. Original disk-1 SHA-256 `bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb`; oracle SHA-256 `6b99967e3861777a1e6a07fb6dc6c49d110fa534cf3bcbf25f006141fb15f3ca`.
- Continuation diagnostics in `build/dos-boot-first.json` retain exact linked identity, read extents, code bytes and last 32 state snapshots. Current stop is **unsupported `E6 20` PIC OUT 20h at 0070:2BFB**, **2,335 completed instructions**. Host disk/BIOS errors remain zero. COMMAND.COM acceptance is explicitly false. INT 11h/12h read mutable BDA, and INT 15h returns original XT unsupported AH=86h/CF=1 through its normal frame/IRET.
- Shared coherent range probe passed VICE `logs/vice_auto_20261015_011028`; all **1,536** returned bytes (including six dirty edits) and captured executable identity match independently. Guest transfer 07FD00–0802FF, source 34FF00–3504FF and destination 35FF00–3604FF cross distinct bank seams. VICE used 16 MiB REU/warp; no physical DMA/timing inference. Existing four physical-helper/probe identities remain unchanged.
- Inspected runtime map CODE **9,702** / RODATA **673** / BSS **211** / ZP **16**, range staging **256**, PRG **10,389**; unit CODE **10,526** / RODATA **673** / TESTCODE **36** / ZP **28**, PRG **11,249**. Runtime static control **2,451** bytes leaves **45** pre-E100 BSS bytes. The complete host map allocates C000–C0FF staging and C100–CFFF future resident code; new helpers are unit-only. See the memory ledger for addresses and distinction between PRG/file and linked-reservation totals.
- Real linked CPU profile validates **12** cold/warm samples with exact final registers/full 1 MiB RAM. Warm register/branch **1,762.33 host cycles/instruction**, warm 20 KiB REP **1,081.19 cycles/byte**. Interval includes step entry→RTS and excludes synthetic caller JSR, setup/final validation flush, DMA stalls, VIC, rendering/UCI/IEC and physical elapsed time. Source-pinned artifact records all counters/limits; these are pre-optimization costs, not physical XT ratios. Unlinked fetch/PC-port/video work is excluded.
- Still unfinished: native startup guest loop, Ultimate/IEC import and verified saves, floppy B, file-backed 2 MiB→20 MiB HD, complete CPU/PC ports/events/BIOS, keyboard, 40/80 text+CGA, prompt/application acceptance and calibrated hardware performance. Kernel handoff does not shrink the full goal.


## 2026-10-15 — final range helpers, quick integration and physical acceptance

Commands from this project: `/usr/bin/time -p make test`; Terminal-owned `/usr/bin/python3 build_support/c64u_range_probe.py --host 10.0.0.79 --output agentworking/runs/c64u-range-20261015-013537` with Manual 64 MHz. Final source/tool/artifact identities are retained in `build/manifest.json` and the compact evidence. No source image or persistent hardware file was written.

- Final quick gate **150/150 Zig/Peddle + 45/45 tooling**, wall **12.45** / user **11.35** / sys **1.47** seconds. `build/storage-bootstrap-test.log` now contains this final run, superseding its intermediate 147/34 output. Native range recovery tests preserve distinct nonzero full-envelope payloads/neighbor bytes and inject failure at each incomplete chunk; workflow tests cover failed probe, uncertain restore retries, corruption despite success mailbox and configuration cleanup.
- Physical range run **PASS**, firmware 3.14/FPGA 121/core 1.47, Manual 64 MHz. Result mailbox `01a5000000000000`, 1,536-byte readback SHA-256 `c3fb4990ccd22c9a06a78e6cffa3b198814e992e392ac914b9f83dc6e0fe3ada`. Native before/after backup payload SHA-256 both `c3f137b429eb9ce7a065e961f13803465cf51069e4cb7a2c31e43cd6fcb269b2`; independent review compared **all 5,120 bytes** exactly and machine/turbo/drives JSON equality. Restore needed one attempt. Tracked evidence [c64u-range-20261015.json](evidence/c64u-range-20261015.json); raw run `agentworking/runs/c64u-range-20261015-013537`.
- Probe PRG SHA-256 `e7b46c87bff1c84c37d0b32044310265ebfa34a966dbee4bf5a9349f1669b69d`; new range backup/restore hashes `3ac011f03e6418185bffde2c513774412056a78d96a1aa8f6c29831370e693ef` / `33f4135e9499a0cb35b7754972ec5ddee02ec55d3b548a243e6af3034c025ecc`. The original four REU/cache/backup/restore PRGs remain unchanged. Physical range acceptance is **64 MHz only**; earlier cache 1/16/64 evidence remains separate.
- Final runtime map unchanged: CODE **9,702**, RODATA **673**, BSS **211**, ZP **16**, PRG **10,389**. Unit helper code now CODE **10,618** at 080D–3186, RODATA **697** at 3187–343F, TESTCODE **36** at 3440–3463, ZP **28**, PRG **11,365**, linked total **14,100**. This unit growth does not consume extra runtime BSS/REU/ZP. New standalone range backup/restore maps have CODE **350**, RODATA **24**, BSS **46**, ZP **4**.
- No calibrated CPU/DMA elapsed timing, native UCI/IEC transfer, persistent image save, prompt or prior program-execution resumption is established. REST uploads only volatile PRGs for development; guest runtime networking is not introduced.


Final frozen-baseline reruns: `/usr/bin/time -p make test-cpu-corpus` passes **150/150 Zig/Peddle** with all **2,555 selected hardware cases**, exit 0, wall **23.70** / user **22.26** / sys **1.69** seconds; log `build/storage-bootstrap-corpus.log`. `make profile-cpu` passes **1/1**, wall **3.27** seconds, **12** validated samples, **10,314** guest instructions / **12,902** calls, **65,680,572** host CPU cycles / **19,297,856** native instructions, **223** DMA / **114,176** bytes. Final profile identity `95fd4e36c3744e01fd0ddd61f5bbd2bafdd993c489f2bb70029a00e919df1f02`; unit PRG SHA-256 `c035afe39e8c25239a7b17664b36c9688186e29b6adbef6ff01d3f3a2c01e6ab`. Final warm register/branch cost is **1,762.55 cycles/instruction**; 20 KiB REP remains **1,081.19 cycles/byte**. The final source-pinned table supersedes intermediate profile values above; physical exclusions remain unchanged. All state checks true. Tracked [baseline](evidence/storage-bootstrap-20261015.json), [kernel handoff](evidence/dos-kernel-handoff-20261015.json) and [profile](evidence/cpu-profile-baseline-20261015.json) accompany the physical range evidence.

## 2026-10-15 — integrated coherent fetch optimization

Commands: `/usr/bin/time -p make test`, `/usr/bin/time -p make test-cpu-corpus`, `/usr/bin/time -p make profile-cpu`, from this project. Logs `build/fetch-integration-test.log`, `build/fetch-integration-corpus.log`, `build/fetch-integration-profile.log`. Exit 0 for all; quick 161/161 Zig +45/45 tooling in 13.38 s; full 161/161 Zig and 2,555 selected hardware cases in 23.78 s; profile 1/1 with 12 samples in 3.07 s. Tool/dependency hashes are in [evidence](evidence/fetch-optimization-20261015.json). No original disk or hardware changes. Profile now 61,735,896 CPUcycles/18,149,832 native instructions, same 10,314 guest instructions/12,902 calls/223 DMA/114,176 bytes. Native clocks exclude physicalDMAstall and callerJSR. IO.SYS stop remains 2335 instructions at 0070:2BFB OUT20,25,546,417 step cycles. RuntimePRG10,686/unit 11,662, BSS222/ZP18 (unitZP30). All prior hardware probe PRGs excludefetch.
