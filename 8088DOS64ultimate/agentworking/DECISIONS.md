# Decision register

Statuses: **user requirement** is binding scope; **proposed** awaits plan review and implementation evidence; **deferred** is not v1 work. Supersede rows with dated entries rather than deleting the history.

| ID | Status | Decision | Reason / validation |
|---|---|---|---|
| D01 | User requirement | Work only under 8088DOS64ultimate; project-local agentworking | Long-horizon context without cluttering enclosing project |
| D02 | User requirement | Boot real DOS 3.3 from supplied images | DOS execution is the objective; earlier chat's native INT 21h recommendation does not govern |
| D03 | User requirement, clarified 2026-10-14 | 6502/6510 assembly target | User explicitly rejected using ZeroPage to build the emulator |
| D04 | User requirement, clarified 2026-10-14 | Zig host tests/assertions + Peddle execution of actual assembly | Preserve ZeroPage's test approach and observable behavior assertions |
| D05 | Proposed | ca65/ld65 target tools, Zig 0.16.0 host, C++ Peddle adapter | Existing installed toolchain and nearby linker/test patterns; no C target runtime planned |
| D06 | Proposed | Synthetic BIOS with native callbacks at ROM entries; normal guest INT routing | Avoid full peripheral controller emulation while retaining DOS/TSR hooks and real kernel |
| D07 | Proposed | Functional original-8088 profile for shared 8086 ISA; no cycle-accurate prefetch initially | DOS compatibility and limited host resources; explicit conformance exclusions |
| D08 | Proposed | Eager flags/simple interpreter first; optimize measured hot paths | Independent tests before lazy flags/predecode complexity |
| D09 | User requirement; implementation proposed | 640 KiB guest RAM, whole floppy images in REU | A single coherent physical cache; 16 KiB host frames and 512-byte initial candidate, page size selected by M1/M2 |
| D10 | Superseded by D22 | Initial 16 MiB minimum proposal | User clarified 4 MiB or larger on 2026-10-14 |
| D11 | User requirement | HD backed by file and cached extents; ~2 MiB first, then 20 MiB | 32-bit file offsets separate from 24-bit REU addresses; force eviction even on small fixture |
| D12 | Proposed | Floppy session writes plus explicit verified save/export; HD write-through first | Clear persistence semantics and limited recovery complexity; do not promise power-fail atomicity |
| D13 | User requirement / proposed boundary | Keyboard, 40/80 text, manageable CGA modes 4/5/6; no extra peripherals | Exact guest state, approximate C64 rendering; minimal timer/ports still required |
| D14 | Proposed | 80-column 4×8 packed bitmap with monochrome and deterministic approximate color | VIC cell color limitation; validate actual readability and contrast |
| D15 | User requirement | Peddle mocks + real C64U; VICE IEC/D81/traps/warp development lane | Physical timing/firmware validation cannot be replaced by host mocks; no UCI proof from VICE |
| D16 | User requirement | Applicable supplied DOS utilities before third-party software | Coverage matrix explicitly distinguishes required/conditional/excluded operations |
| D17 | Proposed | “Near XT” measured as disclosed per-workload ratios; initial aim ≥0.75× representative set | A reviewable threshold, not a proven result or universal speed promise |
| D18 | Deferred | Dynamic translation, full FDC/HD controller, 8087, EGA/VGA, DOS 4, network/sound | Revisit only for demonstrated requirements after v1 gates |
| D19 | Proposed | Track planning records with a local ignore override; keep scratch/runs generated | Parent repository ignores agentworking everywhere; continuation records should survive a clean clone |
| D20 | User requirement, 2026-10-14 | Implement progressively; commit verified slices locally; never push | Active thread goal authorizes implementation and local Git commits |
| D21 | Implemented, 2026-10-14 | Advance Peddle clock explicitly per microcycle, with bounded stepping | Upstream core delegates clock advancement to embedding application; 8-cycle LDA/RTS assertion verifies bridge |
| D22 | User requirement, 2026-10-14 | 4 MiB minimum REU; allow larger capacities | Budget guest RAM, complete floppy images, HD cache, overlays/staging within baseline; extra memory is optional |
| D23 | Implemented, 2026-10-14 | Restrict DMA primitive to one REU 64 KiB bank | Avoid expanded-REC 512 KiB counter wrap; range operations must split and reload bank explicitly |
| D24 | User clarification, 2026-10-14 | Original 8088 / IBM PC XT is the CPU/machine target | Shared 8086 ISA makes other cores useful references; no shift to 8086 timing or 80186 extensions |
| D25 | User direction, 2026-10-14 | Requirements govern implementation regardless of reference availability | NES86 provides useful 6502 techniques; research neither constrains scope nor makes progress depend on reusable source |

## Clarification history

2026-10-14: Initial investigation considered C/assembly because user permitted Zig or C. Before implementation, the user explicitly chose assembly and emphasized Zig behavior tests. All current plans use assembly as target and Zig as host tooling. No target implementation was created or discarded.
