# 8088DOS64ultimate

Planning and implementation of a C64 Ultimate program that boots the supplied **real MS-DOS 3.3**, emulates the 8086/8088 instruction set, and provides 640 KiB of conventional PC memory through the REU. Target hardware is the user's 64 MHz C64U with **4 MiB or larger REU**.

**Status: last physically accepted A+C build45896d10/a8274e7c boots genuine DOS3.3 from A and uses the complete20MiB C drive on the physical C64U at PALManual64 MHz.** Real DOS listings, GW-BASIC file output/SYSTEM, original Turbo Pascal7.01 compilation/run, COPY/run and CHKDSK pass. Native backing-file CLOSE/reopen/readback and strict whole-image verification pass; original4MiB REU/settings/media/reset restored. [Physical A+C evidence](agentworking/evidence/c64u-ac-development-20261016.json). OriginalTURBO editor compatibility remains separate private work.

The earlier target (`d883c678`/`88669999`) passed genuine DOS COPY and complete whole-floppy SAVE on the physical Ultimate at Manual64/PAL. Each sector is written as two256-byte transfers, then all368640bytes are reopened and compared; independent retrieval before/after recovery matches the retained REU image. Complete4MiB recovery, settings/media/reset and all3446 frozen inputs/copies passed. The development host uses acknowledged load-only followed by observed BASIC READY and SYS2061. Native Save/Discard controls remain pending. [Physical SAVE acceptance](agentworking/evidence/c64u-complete-split-save-20261015.json).

The user's older-build interactive keyboard use is confirmed, and its separate post-reboot recovery passed. [Recovery evidence](agentworking/evidence/c64u-interactive-reboot-recovery-20261015.json). Physical performance of two warmed historical interpreter kernels at64MHz measured about2.65% and3.96% of a separately pinned modeled4MHz8088 reference; these are workload-specific historical results, not current whole-DOS performance. The50% target remains unmet. [Performance evidence](agentworking/evidence/c64u-fixedwork-performance-20261015.json). The requested [actual GW-BASIC video](docs/videos/gwbasic-hangman-c64u-20261015.mp4) now passes independent archive, chapter, game and recovery checks.

The interpreter foundation includes a cached 2/20 MiB HD backend, verified copied code beneath KERNAL ROM and faster coherent scrolling, on top of timer IRQ0 and native CGA modes 4/5/6. The previous combined-clock checkpoint passed **421 Zig/Peddle tests, 597 quick CPU cases and 286 tooling checks**, plus genuine native DOS/MODE and focused HD gates. The historical runtime22f82091/unit8a84329c preserves every interrupt boundary and reduces modeled native-DOS CPU cost about8.8%. The older full5,701-case and longHD proofs remain specific to98fc/6eba. [Current evidence](agentworking/evidence/boundary-performance-20261015.json). HD and floppy startup remain disabled until explicitly configured.

Genuine internal DOS file workflows also pass through native startup and ticks: MD/CD, COPY/TYPE, REN, IF EXIST, DEL/RD and expected missing-file handling. Independent FAT12 checks inspect every sector and preserve all original files. [Workflow evidence](agentworking/evidence/dos-native-workflows-20261015.json).

The supplied MODE utility now passes CO40 and CO80 on the physical C64U, with returned DOS prompts and all 8,000 bitmap bytes and 1,000 color cells checked at each mode. Recovery restored every byte of the first 4 MiB on its second attempt; the first protocol failure is retained. [Physical MODE evidence](agentworking/evidence/c64u-native-mode-20261015.json). A one-byte BIOS fix follows original XT ignored-function behavior. [Unit evidence](agentworking/evidence/dos-mode-xt-20261015.json).

The earlier five-overlay physical attempt remains failed after exceeding its observation budget; recovery passed. The six-overlay floppy-only run passed with explicit2s/360s observer settings. Human matrix input, physical 40/80-column readability, native graphics on the display, persistent floppy/HD/IEC images and XT performance remain unfinished. Graphics reduction and palette compromises are explicit; guest VRAM is preserved. CPU profiles exclude DMA stalls and cannot establish a physical XT speed ratio. Historical failures and earlier accepted targets remain in the working records.

Compatibility targets the **original 8088 and IBM PC/XT**, with the shared 8086 instruction set. Existing 8086 implementations are references; they do not define our CPU profile or reduce the required functionality.

The target uses **6502/6510 assembly** via ca65/ld65. **Host Zig tests execute the assembled code in Peddle and assert its behavior**, following the existing ZeroPage project. This incorporates the user's two planning clarifications on 2026-10-14.

`make setup-installer` now builds native C/6502 SETUP and its two overlays. The complete fresh-install model flow creates and verifies C/B/A, a folder-aware START and configuration; file-conflict cleanup also passes. `make setup-installer-tests` runs the optional full installer model lane using locally supplied DOS images. Physical acceptance, full error screens, reconfiguration and emulator-preference integration remain pending. See [installer build and workflow](docs/NATIVE_SETUP_INSTALLER.md), [configuration contract](docs/NATIVE_SETUP_CONFIG.md) and [REU allocation policy](docs/REU_ALLOCATION_POLICY.md). Extra REU may be used where it improves speed, while retaining the 4 MiB minimum.

`make setup-release-tests` verifies the native release descriptor and host generator. The main now accepts verified preloaded A/B images through the [handoff contract](docs/NATIVE_START_HANDOFF.md); `make test-loader-handoff` and `make test-loader-dos` exercise this path, including genuine DOS. Public runtime `8711c155` and unit `56b1d7d8` preserve the startup-clock repair and pass 503 base behavior tests plus focused startup/boot checks. The preceding clock-fix build also booted the native-generated START/A/B/C/config through genuine DOS VER and paged A/C listings in the model. `make start` now builds the native START template, and `make start-tests` runs 46 actual 6510/Peddle groups, including startup file-handle recovery, cancellation and genuine DOS boot. The template stays disabled until its persistent home is configured. Physical START qualification and the complete SETUP installer remain in progress. Native 32/128 KiB transfers passed on the Ultimate; the 2 MiB qualification remains failed. Live hardware ownership and recovery state are recorded in `agentworking/ACTIVE_HARDWARE_SESSION.json`.

The [independent A/B core](docs/FLOPPY_CORE.md) now passes combined model tests and genuine DOS boot/VER/DIR. It provides distinct disks, readonly/dirty tracking and safe rotating swap buffers. Startup configuration, the user disk menu, save integration and physical A/B testing remain pending.

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
make test-floppy-export # native create-new/save/reopen prototype, Peddle only
make test-iec-standalone # real assembly import from mocked KERNAL APIs
make vice-iec-standalone # owned VICE full PC image import from D81/SEQ
```

Tool overrides: `DOS64_ZIG`, `DOS64_CA65`, `DOS64_LD65`, `DOS64_PYTHON`, `DOS64_DOSBOX`. Zig defaults to the sibling pinned 0.16.0 tooling, then PATH. Build outputs and identity manifest are in `build/`; reference-run evidence is retained in project-local `agentworking/runs/`.

## Review first

1. [Plan and milestones](docs/PLAN.md) — proposed scope, sequence, gates, and risks.
2. [Architecture](docs/ARCHITECTURE.md) — actual DOS boot, native BIOS, PC devices, assembly boundaries.
3. [Memory and paging](docs/MEMORY.md) — complete host/guest/REU budgets and cache coherence.
4. [Tests and acceptance](docs/TESTING.md) — Zig/Peddle, PC references, VICE, real C64U, DOS utilities.
5. [Performance experiments](docs/PERFORMANCE.md) — what must be measured before promising XT speed.

Details: [storage](docs/STORAGE.md), [display and keyboard](docs/DISPLAY_INPUT.md), [research and sources](docs/RESEARCH.md), [existing emulator references](docs/EXISTING_EMULATORS.md), [REU implementation](docs/REU_IMPLEMENTATION.md), [memory implementation](docs/MEMORY_IMPLEMENTATION.md), [CPU implementation](docs/CPU_IMPLEMENTATION.md), [BIOS implementation](docs/BIOS_IMPLEMENTATION.md), [disk implementation](docs/DISK_IMPLEMENTATION.md), [HD implementation](docs/HD_IMPLEMENTATION.md), [HD failure evidence](docs/HD_FAILURE_EVIDENCE.md), [standalone IEC development](docs/IEC_STANDALONE_IMPLEMENTATION.md), [floppy export prototype](docs/FLOPPY_EXPORT_PROTOTYPE.md), [DOS disk tools](docs/DISK_TOOLS.md), [coherent ranges](docs/RANGE_IMPLEMENTATION.md), [PC ports](docs/PORTS_IMPLEMENTATION.md), [guest clock](docs/CLOCK_IMPLEMENTATION.md), [keyboard BIOS](docs/KEYBOARD_IMPLEMENTATION.md), [UCI transport](docs/UCI_IMPLEMENTATION.md), [native clock](docs/NATIVE_CLOCK_IMPLEMENTATION.md), [native startup/runtime](docs/NATIVE_RUNTIME_IMPLEMENTATION.md), [physical tests](docs/HARDWARE_TESTING.md), [MODE hardware workflow](docs/MODE_HARDWARE_WORKFLOW.md), [optional whole-file recovery](docs/NATIVE_FILE_RECOVERY.md), [requirements coverage](docs/REQUIREMENTS.md).

## Main decisions and remaining scope

- Boot disk 1 through a small synthetic PC BIOS; execute `IO.SYS`, `MSDOS.SYS`, `COMMAND.COM`, and DOS applications as guest instructions. DOS owns FAT, files, handles, the PSP, and EXE loading. No native replacement for INT 21h.
- Keep each floppy's complete raw image in a dedicated REU slot. Start with the actual 360 KiB fixtures, then use file-backed cached extents for an approximately 2 MiB hard disk and a 20 MiB hard disk.
- Use one guest physical page cache, initially 16 KiB of host RAM; compare 256/512/1024/2048-byte pages before fixing the production page size.
- Implement 40×25 and 80×25 text, plus CGA modes 4/5/6. Preserve guest VRAM exactly; document the unavoidable C64 rendering compromises.
- Prove the actual assembly through Zig assertions in Peddle, then VICE with REU and D81/IEC, then physical C64U at 1/16/64 MHz. Warp-mode VICE is a development accelerator, not a 64 MHz timing model.
- Measure near-4.77 MHz XT performance early. It remains an objective, not an established capability.

The current assembly `da95caf7` / `bc6ab7fd` includes canonicalCGA cursor presentation, registers/control/status and independently reviewed memory optimization;472 Peddle tests and308 tooling tests pass. See [cursor contract](docs/CGA_CURSOR.md). Modeled CPU reductions5.90% across12profiles/1.98% genuineDOS are separate from physical timing. Public A+C host/helper passes43host/6Peddle/6layout checks; see [workflow](docs/HARDWARE_AC_WORKFLOW.md). OriginalTurboPascal7.01 editor load/compile/run/exit passes Peddle; physical editor testing remains pending. A complete20MiB C image with allDOSfloppies, GW-BASIC/Hangman and Turbo Pascal7.01 is staged on the Ultimate. Physical Cdrive acceptance passes; the originalTURBO editor is not yet physically accepted. [Installation and evidence](docs/TURBO_PASCAL.md).

## Continuation

All project working records live here, under lowercase [agentworking](agentworking/STATUS.md), never in the enclosing repository's `agentworking` folder. Start with [STATUS](agentworking/STATUS.md), [NEXT_SLICE](agentworking/NEXT_SLICE.md), and [DECISIONS](agentworking/DECISIONS.md). [AGENTS.md](AGENTS.md) specifies the implementation workflow.

The three user-provided images remain unchanged in `reference/`. Their read-only [inventory](agentworking/research/reference-images.json) records geometry, hashes, file contents' hashes, and configuration text. The [DOSBox-X baseline](agentworking/evidence/dosbox-reference-20261014.json) records the actual guest's VER/DIR output and immutable source hash.

The opt-in genuine DOS CGA probe now passes modes4/5/6 through DOS loading and an independent full-pixel oracle. This is model evidence; physical graphics capture remains separate. [Evidence](agentworking/evidence/genuine-cga-workflow-20261015.json).

[Live progress lab](https://dos64-ultimate-lab.klumsy.chatgpt.site) — interactive diagrams, verified screenshots and highlighted BASIC source. [Publication/update process](docs/PROGRESS_SITE.md). The actual game video and its download button are published.
