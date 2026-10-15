# 8088DOS64ultimate

Planning and implementation of a C64 Ultimate program that boots the supplied **real MS-DOS 3.3**, emulates the 8086/8088 instruction set, and provides 640 KiB of conventional PC memory through the REU. Target hardware is the user's 64 MHz C64U with **4 MiB or larger REU**.

**Status: genuine DOS 3.3 reaches COMMAND.COM and executes VER and DIR in Peddle.** The opt-in `make test-dos-boot` lane starts at guest reset, executes the unchanged boot sector and real DOS binaries, supplies ten keys through the assembled keyboard queue, verifies `MS-DOS Version 3.30`, checks all 35 visible DIR filenames/sizes plus `35 File(s)` and 9,216 free bytes against an independent FAT12 oracle, and requires the returned `A>` prompt. This completes after 588,937 guest instructions; the original image and in-REU floppy remain unchanged. DOS still owns INT 21h, FAT and application loading.

This is functional acceptance of the actual linked 6510 emulator in Peddle. Native startup commits FILE/TEXT/INPUT overlays to REU, then idles. A guarded cold importer, licensed fonts, native VIC text setup, CIA1 keyboard scanner and elapsed clock adapter are now linked and tested. Root checks pass **326 Zig/Peddle tests, 597 quick hardware cases, 129 tooling checks, eight dedicated import tests, genuine DOS equality and twelve profile samples**. All 939 saved DOS observations and complete guest/video bytes remain exact. The last full 5,701-case CPU proof remains retained; this slice changes no CPU instruction semantics. [Current evidence](agentworking/evidence/native-text-input-20261015.json).

Native file loading and guest execution are the next integration. Physical native DOS/display/input, asynchronous IRQ/PIT, CGA presentation, persistent Ultimate/IEC images and 2 MiB→20 MiB HD remain unfinished. Narrow-font 40/80 text has VICE component proof; it is not combined physical acceptance. REU recovery is prepared and tested without hardware execution. Terminal-owned FTP staging created one fresh disk1 copy and verified every byte; native UCI reading remains pending. Physical Manual1/16/64MHz already validates the raw PAL CIA clock domain; physical interpreter/XT throughput remains unmeasured.

REU/cache integrity passed Peddle, VICE and physical C64U at 1/16/64 MHz settings. The range probe passed VICE and physical Manual 64 MHz, including exact 5,120-byte recovery. Logical CGA/text, clock and keyboard BIOS behavior is verified through assembly tests; no full native display/input claim or XT-speed result exists. [DOS built-ins evidence](agentworking/evidence/dos-command-builtins-20261015.json), [clock/keyboard/UCI slice](agentworking/evidence/clock-keyboard-uci-20261015.json) and [prior video/adjust slice](agentworking/evidence/video-adjust-bios-20261015.json) retain scope and identities.

Compatibility targets the **original 8088 and IBM PC/XT**, with the shared 8086 instruction set. Existing 8086 implementations are references; they do not define our CPU profile or reduce the required functionality.

The target uses **6502/6510 assembly** via ca65/ld65. **Host Zig tests execute the assembled code in Peddle and assert its behavior**, following the existing ZeroPage project. This incorporates the user's two planning clarifications on 2026-10-14.

```sh
make test             # fast assembly, memory checks, tooling and Zig/Peddle tests
make test-image-import # opt-in whole 360 KiB cold import/CRC/error tests
make test-overlays    # focused FILE/TEXT/INPUT overlays and cold lifetime checks
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
```

Tool overrides: `DOS64_ZIG`, `DOS64_CA65`, `DOS64_LD65`, `DOS64_PYTHON`, `DOS64_DOSBOX`. Zig defaults to the sibling pinned 0.16.0 tooling, then PATH. Build outputs and identity manifest are in `build/`; reference-run evidence is retained in project-local `agentworking/runs/`.

## Review first

1. [Plan and milestones](docs/PLAN.md) — proposed scope, sequence, gates, and risks.
2. [Architecture](docs/ARCHITECTURE.md) — actual DOS boot, native BIOS, PC devices, assembly boundaries.
3. [Memory and paging](docs/MEMORY.md) — complete host/guest/REU budgets and cache coherence.
4. [Tests and acceptance](docs/TESTING.md) — Zig/Peddle, PC references, VICE, real C64U, DOS utilities.
5. [Performance experiments](docs/PERFORMANCE.md) — what must be measured before promising XT speed.

Details: [storage](docs/STORAGE.md), [display and keyboard](docs/DISPLAY_INPUT.md), [research and sources](docs/RESEARCH.md), [existing emulator references](docs/EXISTING_EMULATORS.md), [REU implementation](docs/REU_IMPLEMENTATION.md), [memory implementation](docs/MEMORY_IMPLEMENTATION.md), [CPU implementation](docs/CPU_IMPLEMENTATION.md), [BIOS implementation](docs/BIOS_IMPLEMENTATION.md), [disk implementation](docs/DISK_IMPLEMENTATION.md), [coherent ranges](docs/RANGE_IMPLEMENTATION.md), [PC ports](docs/PORTS_IMPLEMENTATION.md), [guest clock](docs/CLOCK_IMPLEMENTATION.md), [keyboard BIOS](docs/KEYBOARD_IMPLEMENTATION.md), [UCI transport](docs/UCI_IMPLEMENTATION.md), [native clock](docs/NATIVE_CLOCK_IMPLEMENTATION.md), [physical tests](docs/HARDWARE_TESTING.md), [requirements coverage](docs/REQUIREMENTS.md).

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
