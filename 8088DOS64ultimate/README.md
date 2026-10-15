# 8088DOS64ultimate

Planning package for a C64 Ultimate program that boots the supplied **real MS-DOS 3.3**, emulates the 8086/8088 instruction set, and provides 640 KiB of conventional PC memory through the REU. Target hardware is the user's 64 MHz C64U with a 16 MiB REU.

**Status: implementation underway; assembly/Zig/Peddle foundation verified.** `make test` assembles the target and runs 10 Zig/Peddle behavior tests plus 4 linker-contract tests. The supplied DOS disk boots in DOSBox-X and reports MS-DOS 3.30. Target-emulator DOS boot and physical C64U performance remain future milestones.

The target uses **6502/6510 assembly** via ca65/ld65. **Host Zig tests execute the assembled code in Peddle and assert its behavior**, following the existing ZeroPage project. This incorporates the user's two planning clarifications on 2026-10-14.

```sh
make test             # fast assembly, memory checks, tooling and Zig/Peddle tests
make test-reference   # slower disposable real-DOS boot in installed DOSBox-X
```

Tool overrides: `DOS64_ZIG`, `DOS64_CA65`, `DOS64_LD65`, `DOS64_PYTHON`, `DOS64_DOSBOX`. Zig defaults to the sibling pinned 0.16.0 tooling, then PATH. Build outputs and identity manifest are in `build/`; reference-run evidence is retained in project-local `agentworking/runs/`.

## Review first

1. [Plan and milestones](docs/PLAN.md) — proposed scope, sequence, gates, and risks.
2. [Architecture](docs/ARCHITECTURE.md) — actual DOS boot, native BIOS, PC devices, assembly boundaries.
3. [Memory and paging](docs/MEMORY.md) — complete host/guest/REU budgets and cache coherence.
4. [Tests and acceptance](docs/TESTING.md) — Zig/Peddle, PC references, VICE, real C64U, DOS utilities.
5. [Performance experiments](docs/PERFORMANCE.md) — what must be measured before promising XT speed.

Details: [storage](docs/STORAGE.md), [display and keyboard](docs/DISPLAY_INPUT.md), [research and sources](docs/RESEARCH.md), [requirements coverage](docs/REQUIREMENTS.md).

## Main decisions proposed

- Boot disk 1 through a small synthetic PC BIOS; execute `IO.SYS`, `MSDOS.SYS`, `COMMAND.COM`, and DOS applications as guest instructions. DOS owns FAT, files, handles, the PSP, and EXE loading. No native replacement for INT 21h.
- Keep each floppy's complete raw image in a dedicated REU slot. Start with the actual 360 KiB fixtures, then use file-backed cached extents for an approximately 2 MiB hard disk and a 20 MiB hard disk.
- Use one guest physical page cache, initially 16 KiB of host RAM; compare 256/512/1024/2048-byte pages before fixing the production page size.
- Implement 40×25 and 80×25 text, plus CGA modes 4/5/6. Preserve guest VRAM exactly; document the unavoidable C64 rendering compromises.
- Prove the actual assembly through Zig assertions in Peddle, then VICE with REU and D81/IEC, then physical C64U at 1/16/64 MHz. Warp-mode VICE is a development accelerator, not a 64 MHz timing model.
- Measure near-4.77 MHz XT performance early. It remains an objective, not an established capability.

## Continuation

All project working records live here, under lowercase [agentworking](agentworking/STATUS.md), never in the enclosing repository's `agentworking` folder. Start with [STATUS](agentworking/STATUS.md), [NEXT_SLICE](agentworking/NEXT_SLICE.md), and [DECISIONS](agentworking/DECISIONS.md). [AGENTS.md](AGENTS.md) specifies the implementation workflow.

The three user-provided images remain unchanged in `reference/`. Their read-only [inventory](agentworking/research/reference-images.json) records geometry, hashes, file contents' hashes, and configuration text. The [DOSBox-X baseline](agentworking/evidence/dosbox-reference-20261014.json) records the actual guest's VER/DIR output and immutable source hash.
