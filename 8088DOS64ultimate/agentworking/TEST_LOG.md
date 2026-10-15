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
