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
