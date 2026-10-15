# Implementation plan for review

Planning date: 2026-10-14, America/Los_Angeles. This package incorporates the user's assembly and Zig-test clarifications. All milestones below are future work unless explicitly marked as planning evidence.

Implementation update 2026-10-14: M0 assembly/Zig/Peddle foundation and DOSBox-X reference boot are verified; detailed results and remaining limitations are in `agentworking/STATUS.md` and `agentworking/TEST_LOG.md`. Later milestones remain unimplemented.

## Outcome and boundaries

A standalone PRG boots the supplied MS-DOS 3.3 in an emulated PC with 640 KiB conventional RAM, two floppy drives, keyboard, 40/80-column text, and limited CGA graphics. Guest execution uses the C64U's 64 MHz 6510; the REU stores guest memory, whole floppy images, and cached hard-disk extents. Native Ultimate DOS loads/saves image bytes. A KERNAL IEC backend supports development in VICE using D81 containers.

The first end-user workload is the supplied DOS command set. Full PC hardware fidelity, EGA/VGA, 8087, protected mode, sound, serial/parallel output, mouse, networking, and arbitrary third-party software are outside v1. Some minimal timer, interrupt, and port behavior remains necessary even without those peripherals.

The CPU profile is functionally 8086/8088, with original 8088 behavior chosen for edge cases and PC compatibility. Exact prefetch/bus timing is deferred. If later software depends on those details, record the incompatibility rather than quietly claiming complete IBM PC emulation.

## Work sequence and gates

| Milestone | Bounded deliverable | Exit evidence / dependency |
|---|---|---|
| M0 — reproducible foundation | Pin ca65/ld65, Zig 0.16.0, Peddle; assembly PRG/raw-test targets; Zig assertions run linked routines; map checker; fixture manager | An intentional assertion failure fails CI; a minimal routine passes and returns within budget; input images retain hashes; DOSBox-X boots a disposable disk-1 copy and confirms actual version/config behavior |
| M1 — hardware feasibility | Small assembly probes for ALU, dispatch, address translation, cache hit/miss, REU DMA, bitmap rendering, and UCI image transfer | Peddle CPU counts plus real C64U 1/16/64 MHz elapsed times and configuration; first page-size trade study; no extrapolated hardware speed claim from VICE |
| M2 — memory and devices | One guest memory API, REU driver/model, 20-bit addressing, page cache, dirty write-back, bounded bulk copy, UCI state machine/file mock | Zig property tests + real assembly Peddle tests; same REU test vectors in VICE/hardware; cache/IO ownership invariants; all ranges verified |
| M3 — CPU foundation | Register state; instruction fetch; prefixes; ModR/M; MOV/ALU/flags/branches/stack; synthetic x86 test programs | Defined SingleStepTests subsets and independent arithmetic oracle; every addressing form; aliases, cross-page operations, branch targets, stack edges |
| M4 — CPU completion for boot | Remaining documented 8086 instructions; strings/REP; MUL/DIV; interrupt entry/IRET; TF/IF shadows; IN/OUT/HLT | All declared documented instruction groups covered; original-CPU edge cases; interruptible REP and code modification; no unrecorded skips |
| M5 — native BIOS and first DOS boot | Reset/IVT/BDA; disk INT 13h; video/keyboard/time/equipment/memory services; whole-image A:/B:; initial 40-column renderer | Original disk-1 boot result recorded, minimal-config copy reaches prompt, `VER`, `DIR`, `TYPE`, command execution and keyboard work; show INT 21h executes DOS code |
| M6 — persistent floppy and VICE development | Save/reload floppy image; Ultimate and IEC adapters; D81 packaging; error recovery | Identical guest sector results in Peddle/UCI and VICE/IEC; saved image independently extracted and compared; full restart proves persistence; real C64U load/edit/save/reboot |
| M7 — usable text and DOS suite | 80-column 4×8 renderer, colors policy, keyboard mapping, ANSI.SYS; internal commands and applicable included tools | DOS acceptance matrix passes at 40/80 where meaningful; readable EDLIN/DEBUG interaction; paging/input/cursor/scroll tests and screenshots; error/abort paths |
| M8 — small hard disk | Approximately 2 MiB raw disk, MBR/partition/CHS, file-offset adapter, bounded REU extent cache | Guest FDISK → FORMAT → SYS → boot C:; cache forced smaller than disk; independent FAT/files check; data survives clean close/reopen and eviction |
| M9 — 20 MiB hard disk | Same backend with larger offsets and image | Accesses below/above 16 MiB, final sector, cache churn, disk-full/errors, flush/restart and utilities pass; no 24-bit file-offset truncation |
| M10 — CGA | Guest modes 4/5/6, direct VRAM and BIOS pixel services, deterministic conversion | Synthetic test cards and GW-BASIC from supplied disk 3 used as a later included-program test; reference pixels checked before downsampling; C64U visual approval |
| M11 — optimization and release | Trace-driven hot paths, coherent fetch cache, safe REP acceleration, optional lazy flags | All functional lanes remain green; memory map fits; measured performance report for every workload; documented limitations and reproducible user guide |

M1 can begin after the minimal M0 runner, before the entire reference-boot tooling is polished. M2's plain memory API should precede CPU work; aggressive paging optimization can follow CPU correctness. Do not make the full instruction suite wait for a beautiful UI. Ship bounded working boot slices, but do not mark CPU completion solely because DOS boots.

M10 follows the DOS text/utility acceptance priority. Graphics test-card research may happen earlier to validate the display budget. Do not pursue third-party applications before the applicable supplied DOS utilities are accounted for.

## Early stop-and-reconsider gates

- **RAM fit:** the working host layout budgets 22 KiB for hot/resident executable code and 16 KiB for guest frames. If linked code cannot fit, measure cold overlays or trade cache capacity explicitly. No invisible spill into screen, stack, or I/O space.
- **Performance:** use the M1/M3 measured cycles and miss rates to forecast realistic workloads. If representative CPU-bound tests are far below target, preserve the working emulator and report the gap; consider specialized handlers/predecode before a translator. Do not change the project into a DOS-call shim.
- **BIOS completeness:** trace actual disk-1 boot and tools. Additional ports/BIOS calls get explicit requirements and tests. Full FDC or XT hard-disk-controller emulation is not assumed necessary; a demonstrated direct-controller dependency can change that decision.
- **Disk integrity:** a successful screen message is insufficient. Verify saved bytes independently after a fresh process/session and keep originals immutable.
- **80-column usability:** color fidelity is constrained by VIC-II cells. Validate font legibility and the documented approximation on the actual display early enough to change the renderer.

## Deliverable layout for implementation

```text
src/                 6502 assembly: cpu, memory, bios, devices, video, storage
include/             assembly ABI, structures, constants
cfg/                 linker layouts and memory contracts
tests/host/          Zig runners, assertions, property tests, fixture parsing
tests/guest/         small NASM 8086 programs; source + deterministic fixtures
tests/vice/          VICE integration plans and image extraction checks
tests/ultimate/      physical C64U plans and ownership/configuration checks
tests/acceptance/    DOS scripts, expected semantics, disk transformations
third_party/         pinned Peddle core/license; test-corpus manifests
build_support/       artifact, fixture and map tooling
docs/                durable contracts and user documentation
agentworking/        state, decisions, lessons, research; ignored runs/scratch
```

Proposed command contract, not yet implemented: `make build`, `make test`, `make test-cpu-full`, `make test-vice`, `make test-ultimate`, `make benchmark`, `make verify-memory`. The standard fast test invokes Zig and Peddle, with deterministic seeds and no physical device. Hardware/reference tools are separate named lanes; unavailable lanes report **not run**, never pass.

## Review points

The defaults proposed for review are: native BIOS with real DOS, 16 MiB REU requirement, assembly via ca65/ld65, 16 KiB guest cache, measured page-size selection, explicit image-save behavior for floppies, read-through/write-through hard-disk caching initially, and approximate CGA rendering. No further preference is required to begin M0 after the user reviews this plan.
