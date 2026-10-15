# 8088DOS64ultimate

Planning and implementation of a C64 Ultimate program that boots the supplied **real MS-DOS 3.3**, emulates the 8086/8088 instruction set, and provides 640 KiB of conventional PC memory through the REU. Target hardware is the user's 64 MHz C64U with **4 MiB or larger REU**.

**Status: the current six-overlay target boots genuine DOS 3.3 on the physical C64U at Manual64 MHz.** Runtime98fc/configured1ff1 passes native UCI import, DOS/COMMAND.COM, VER and DIR /P: all35 filenames/sizes,9,216 free bytes and returned`A>`. Complete first4MiB restoration, settings/media/reset and strict copied-code identity pass. HD was disabled for this hardware run. [Physical evidence](agentworking/evidence/c64u-native-six-20261015.json). DOS owns INT21h,FAT and application loading.

The current six-overlay target adds a cached 2/20 MiB HD backend, verified copied code beneath KERNAL ROM and faster coherent scrolling, on top of timer IRQ0 and native CGA modes 4/5/6. Root checks pass **417 Zig/Peddle tests, 597 quick CPU cases and 238 tooling checks**, plus genuine native DOS/MODE and focused HD gates. The reviewed full 5,701-case CPU and long HD proofs apply by exact source/binary identity. [Current evidence](agentworking/evidence/hd-production-20261015.json). HD and floppy startup remain disabled until explicitly configured.

Genuine internal DOS file workflows also pass through native startup and ticks: MD/CD, COPY/TYPE, REN, IF EXIST, DEL/RD and expected missing-file handling. Independent FAT12 checks inspect every sector and preserve all original files. [Workflow evidence](agentworking/evidence/dos-native-workflows-20261015.json).

The supplied MODE utility now passes CO40 and CO80 on the physical C64U, with returned DOS prompts and all 8,000 bitmap bytes and 1,000 color cells checked at each mode. Recovery restored every byte of the first 4 MiB on its second attempt; the first protocol failure is retained. [Physical MODE evidence](agentworking/evidence/c64u-native-mode-20261015.json). A one-byte BIOS fix follows original XT ignored-function behavior. [Unit evidence](agentworking/evidence/dos-mode-xt-20261015.json).

The earlier five-overlay physical attempt remains failed after exceeding its observation budget; recovery passed. The six-overlay floppy-only run passed with explicit2s/360s observer settings. Human matrix input, physical 40/80-column readability, native graphics on the display, persistent floppy/HD/IEC images and XT performance remain unfinished. Graphics reduction and palette compromises are explicit; guest VRAM is preserved. CPU profiles exclude DMA stalls and cannot establish a physical XT speed ratio. Historical failures and earlier accepted targets remain in the working records.

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

Details: [storage](docs/STORAGE.md), [display and keyboard](docs/DISPLAY_INPUT.md), [research and sources](docs/RESEARCH.md), [existing emulator references](docs/EXISTING_EMULATORS.md), [REU implementation](docs/REU_IMPLEMENTATION.md), [memory implementation](docs/MEMORY_IMPLEMENTATION.md), [CPU implementation](docs/CPU_IMPLEMENTATION.md), [BIOS implementation](docs/BIOS_IMPLEMENTATION.md), [disk implementation](docs/DISK_IMPLEMENTATION.md), [HD implementation](docs/HD_IMPLEMENTATION.md), [DOS disk tools](docs/DISK_TOOLS.md), [coherent ranges](docs/RANGE_IMPLEMENTATION.md), [PC ports](docs/PORTS_IMPLEMENTATION.md), [guest clock](docs/CLOCK_IMPLEMENTATION.md), [keyboard BIOS](docs/KEYBOARD_IMPLEMENTATION.md), [UCI transport](docs/UCI_IMPLEMENTATION.md), [native clock](docs/NATIVE_CLOCK_IMPLEMENTATION.md), [native startup/runtime](docs/NATIVE_RUNTIME_IMPLEMENTATION.md), [physical tests](docs/HARDWARE_TESTING.md), [MODE hardware workflow](docs/MODE_HARDWARE_WORKFLOW.md), [optional whole-file recovery](docs/NATIVE_FILE_RECOVERY.md), [requirements coverage](docs/REQUIREMENTS.md).

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
