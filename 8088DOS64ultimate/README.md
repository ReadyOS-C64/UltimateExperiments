# 8088DOS64ultimate

Planning and implementation of a C64 Ultimate program that boots the supplied **real MS-DOS 3.3**, emulates the 8086/8088 instruction set, and provides 640 KiB of conventional PC memory through the REU. Target hardware is the user's 64 MHz C64U with **4 MiB or larger REU**.

**Status: genuine DOS 3.3 boots on the physical C64U at Manual 64 MHz.** The frozen three-overlay runtime imports the unchanged floppy through native UCI, runs DOS and COMMAND.COM, and passes VER and DIR /P: all 35 filenames/sizes, 9,216 free bytes and the returned `A>` prompt. Complete first-4-MiB REU restoration, prior configuration/media and reset/resume pass. [Physical evidence](agentworking/evidence/c64u-native-dos-20261015.json). DOS owns INT 21h, FAT and application loading.

The current five-overlay target adds asynchronous IRQ0 through the guest IVT, the default guest timer/INT 1Ch handler, and native CGA modes 4/5/6. Root checks pass **410 Zig/Peddle tests, 597 quick hardware cases and 172 tooling checks**. The full 5,701-case proof is retained for timer integration; the latest BIOS-only fix leaves the interpreter unchanged. [Current evidence](agentworking/evidence/timer-graphics-integration-20261015.json). Native ENTRY/import/tick execution accepts VER/DIR /P after 598,702 guest instructions, with timer delivery enabled. Packaged startup remains disabled until explicitly configured with an owned image path and CRC.

Genuine internal DOS file workflows also pass through native startup and ticks: MD/CD, COPY/TYPE, REN, IF EXIST, DEL/RD and expected missing-file handling. Independent FAT12 checks inspect every sector and preserve all original files. [Workflow evidence](agentworking/evidence/dos-native-workflows-20261015.json).

The supplied MODE utility also passes CO40 and CO80 with exact BDA geometry and complete native bitmap/matrix checks. A one-byte BIOS fix follows original XT ignored-function behavior. [MODE evidence](agentworking/evidence/dos-mode-xt-20261015.json).

The five-overlay target has not yet run physically. Human matrix input, physical 40/80-column readability, native graphics on the display, persistent floppy/HD/IEC images and XT performance remain unfinished. Graphics reduction and palette compromises are explicit; guest VRAM is preserved. CPU profiles exclude DMA stalls and cannot establish a physical XT speed ratio. Historical failures and earlier accepted targets remain in the working records.

Compatibility targets the **original 8088 and IBM PC/XT**, with the shared 8086 instruction set. Existing 8086 implementations are references; they do not define our CPU profile or reduce the required functionality.

The target uses **6502/6510 assembly** via ca65/ld65. **Host Zig tests execute the assembled code in Peddle and assert its behavior**, following the existing ZeroPage project. This incorporates the user's two planning clarifications on 2026-10-14.

```sh
make test             # fast assembly, memory checks, tooling and Zig/Peddle tests
make test-image-import # opt-in whole 360 KiB cold import/CRC/error tests
make test-native-runtime # focused configured startup/scheduler/development controls
make test-native-dos  # opt-in native ENTRY/import/BIOS/VER/DIR /P end-to-end
make test-native-builtins # real MD/CD/COPY/TYPE/REN/IF/DEL/RD plus independent FAT checks
make test-native-mode # supplied MODE CO40/CO80 with bitmap and matrix oracles
make test-overlays    # focused overlays and cold lifetime checks
make test-timer-graphics # IRQ/PIT, startup/layout and native CGA checks
make test-timer-threshold # opt-in actual-assembly timer converter differential
make test-native-text # fonts, coherent text rows and native VIC setup
make test-dos-boot    # opt-in actual emulator COMMAND prompt, VER and exact DIR proof
make test-reference   # slower disposable real-DOS boot in installed DOSBox-X
make test-cpu-corpus  # broader pinned 8088 functional corpus after CPU changes
make probe            # standalone REU integrity PRG and symbol-based VICE plan
make test-vice        # slower VICE run plus independent captured-byte checks
make test-cache-vice  # slower coherent-cache probe with forced dirty eviction
make test-range-vice  # coherent disk-range integrity across guest/REU bank seams
make profile-cpu      # real linked interpreter cycle/counter baseline, not physical timing
make test-clock-probe # separate scripted CIA/VIC probe checks, not hardware calibration
make hardware-helpers # prepare physical backup/restore/cache probe images
make native-file-recovery # build optional whole-file REU restore helper
make test-native-file-recovery # fast checks for that opt-in development backend
```

Tool overrides: `DOS64_ZIG`, `DOS64_CA65`, `DOS64_LD65`, `DOS64_PYTHON`, `DOS64_DOSBOX`. Zig defaults to the sibling pinned 0.16.0 tooling, then PATH. Build outputs and identity manifest are in `build/`; reference-run evidence is retained in project-local `agentworking/runs/`.

## Review first

1. [Plan and milestones](docs/PLAN.md) — proposed scope, sequence, gates, and risks.
2. [Architecture](docs/ARCHITECTURE.md) — actual DOS boot, native BIOS, PC devices, assembly boundaries.
3. [Memory and paging](docs/MEMORY.md) — complete host/guest/REU budgets and cache coherence.
4. [Tests and acceptance](docs/TESTING.md) — Zig/Peddle, PC references, VICE, real C64U, DOS utilities.
5. [Performance experiments](docs/PERFORMANCE.md) — what must be measured before promising XT speed.

Details: [storage](docs/STORAGE.md), [display and keyboard](docs/DISPLAY_INPUT.md), [research and sources](docs/RESEARCH.md), [existing emulator references](docs/EXISTING_EMULATORS.md), [REU implementation](docs/REU_IMPLEMENTATION.md), [memory implementation](docs/MEMORY_IMPLEMENTATION.md), [CPU implementation](docs/CPU_IMPLEMENTATION.md), [BIOS implementation](docs/BIOS_IMPLEMENTATION.md), [disk implementation](docs/DISK_IMPLEMENTATION.md), [DOS disk tools](docs/DISK_TOOLS.md), [coherent ranges](docs/RANGE_IMPLEMENTATION.md), [PC ports](docs/PORTS_IMPLEMENTATION.md), [guest clock](docs/CLOCK_IMPLEMENTATION.md), [keyboard BIOS](docs/KEYBOARD_IMPLEMENTATION.md), [UCI transport](docs/UCI_IMPLEMENTATION.md), [native clock](docs/NATIVE_CLOCK_IMPLEMENTATION.md), [native startup/runtime](docs/NATIVE_RUNTIME_IMPLEMENTATION.md), [physical tests](docs/HARDWARE_TESTING.md), [optional whole-file recovery](docs/NATIVE_FILE_RECOVERY.md), [requirements coverage](docs/REQUIREMENTS.md).

## Main decisions and remaining scope

- Boot disk 1 through a small synthetic PC BIOS; execute `IO.SYS`, `MSDOS.SYS`, `COMMAND.COM`, and DOS applications as guest instructions. DOS owns FAT, files, handles, the PSP, and EXE loading. No native replacement for INT 21h.
- Keep each floppy's complete raw image in a dedicated REU slot. Start with the actual 360 KiB fixtures, then use file-backed cached extents for an approximately 2 MiB hard disk and a 20 MiB hard disk.
- Use one guest physical page cache, initially 16 KiB of host RAM; compare 256/512/1024/2048-byte pages before fixing the production page size.
- Implement 40×25 and 80×25 text, plus CGA modes 4/5/6. Preserve guest VRAM exactly; document the unavoidable C64 rendering compromises.
- Prove the actual assembly through Zig assertions in Peddle, then VICE with REU and D81/IEC, then physical C64U at 1/16/64 MHz. Warp-mode VICE is a development accelerator, not a 64 MHz timing model.
- Measure near-4.77 MHz XT performance early. It remains an objective, not an established capability.

## Continuation

All project working records live here, under lowercase [agentworking](agentworking/STATUS.md), never in the enclosing repository's `agentworking` folder. Start with [STATUS](agentworking/STATUS.md), [NEXT_SLICE](agentworking/NEXT_SLICE.md), and [DECISIONS](agentworking/DECISIONS.md). [AGENTS.md](AGENTS.md) specifies the implementation workflow.

The three user-provided images remain unchanged in `reference/`. Their read-only [inventory](agentworking/research/reference-images.json) records geometry, hashes, file contents' hashes, and configuration text. The [DOSBox-X baseline](agentworking/evidence/dosbox-reference-20261014.json) records the actual guest's VER/DIR output and immutable source hash.
