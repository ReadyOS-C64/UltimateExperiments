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
| D26 | Implemented baseline, 2026-10-14 | 512-byte physical pages, 32 frames, direct 2,048-entry map and bounded clock eviction | Functional correctness verified, not a page-size/performance winner; limits 1..32 support forced-eviction tests |
| D27 | Implemented, 2026-10-14 | Publish cache ownership only after successful load; keep dirty victim on write-back failure | Partial-transfer fault tests guard data authority and retries |

| D28 | Implemented initial profile | Word transfers wrap the 16-bit offset before separately translating each byte | Pinned original-8088 MartyPC implementation and independent boundary tests; direct hardware FFFF case still absent |
| D29 | Implemented | Long prefix streams yield after bounded 64-prefix slices and continue the same guest instruction | Avoid hangs without introducing a modern 15-byte invalid-instruction limit |

## Clarification history

2026-10-14: Initial investigation considered C/assembly because user permitted Zig or C. Before implementation, the user explicitly chose assembly and emphasized Zig behavior tests. All current plans use assembly as target and Zig as host tooling. No target implementation was created or discarded.


| D30 | Implemented, 2026-10-15 | Store decoded operands as segment/offset descriptors across fetch/eviction | Immediate bytes can evict a frame; raw cache pointers would become stale |
| D31 | Implemented, 2026-10-15 | Accept original C6/C7 extension aliases shown by hardware cases | Modern documented /0-only decoding incorrectly rejected original-8088 behavior |
| D32 | Implemented, 2026-10-15 | Batch Peddle host stepping and optimize host C++ engine; retain Debug Zig assertions | Preserve clocks/budgets/errors with old-vs-new regression evidence; accelerate checks without changing target code |


| D33 | Implemented, 2026-10-15 | Yield REP after at most 16 iterations while retaining decoded state; count once at completion | Bound host work without refetching self-modified instructions; host yields are not original guest-interrupt restarts |
| D34 | Implemented functional policy, 2026-10-15 | Software INT captures IVT target before stacking; ordinary IRET restores guest frame | Pinned original MartyPC ordering, independent alias test and hardware functional vectors; asynchronous event timing remains open |
| D35 | Implemented, 2026-10-15 | Unmasked 8-bit shift count and original SETMO/SETMOC /6 | Original hardware vectors contradict later-CPU SHL alias assumption |
| D36 | Implemented, 2026-10-15 | Support 60–6F Jcc aliases with 70–7F conditions | Pinned original hardware files and exhaustive flag truth-table tests |


| D37 | Implemented, 2026-10-15 | Original F6/F7 math and indirect control retain hardware-derived alias/divide behavior | 2,555 pinned functional rows plus independent edge/seed oracles; minimum signed quotient faults, post-instruction divide IP and REP IDIV differ from modern assumptions; source gaps disclosed |
| D38 | Implemented, 2026-10-15 | Coherent guest/REU ranges use a fixed C000–C0FF bounce and <=256-byte bank-split chunks | Every guest byte uses cache authority; dirty neighbors/export reads, ROM/hole/CGA policy, progress and failures remain correct; additional resident code starts C100 |
| D39 | Implemented baseline, 2026-10-15 | INT 13h raw floppy A reset/read/write/verify, explicit unloaded media and validated CHS/physical DMA bounds | Whole-image REU ownership, all 720 sector tests and genuine unchanged bootloader reads; writes are volatile pending native file persistence |
| D40 | Implemented baseline, 2026-10-15 | Synthetic BIOS callbacks require exact owned physical ROM opcodes and matching private ports | Normal mutable guest IVT/stack/IRET and far-call hooks remain authoritative; arbitrary guest OUT cannot invoke native BIOS |
| D41 | Implemented, 2026-10-15 | INT 11h/12h ordinary guest ROM code reads mutable BDA; INT 15h returns XT unsupported AH=86h/CF=1 | Dirty BDA/default-query/flag/frame preservation tests; pinned original XT listing facts, independently authored code |
| D42 | Acceptance boundary, 2026-10-15 | Genuine IO.SYS entry is a verified checkpoint, not completion of the real DOS goal | Reset and original sector load all bytes through assembly BIOS; full COMMAND.COM prompt, runtime transport/devices/display/application/persistence milestones remain binding |
| D43 | Measured baseline, 2026-10-15 | Profile actual linked assembly with cold/warm state, exact whole-RAM oracle and explicit exclusions | 12 samples disclose dispatch/REP costs; DMA stalls/physical elapsed/XT ratio are unmeasured; unlinked optimizations excluded |
| D44 | Physically verified recovery, 2026-10-15 | New physical range probe must snapshot all touched guest/source/destination page envelopes before mutation | 5,120 bytes, six bank-split descriptors; retry full restore after partial failure and independently re-read every byte; Manual 64 MHz result, all 5,120 restored bytes and machine/turbo/drive JSON independently verified |

| D45 | Implemented, 2026-10-15 | Keep fetch spans unpinned and validate tag/generation/CS/IP/cache state before every dereference | Operand accesses can evict frames; prior actual assembly helper remains a differential oracle; source-pinned workload gains do not establish physical XT speed |
| D46 | Implemented, 2026-10-15 | PIC programming and all eight IN/OUT forms precede asynchronous IRQ delivery | State resides EA00–EEFF, CACHEMETA is bounded E900–E9FF and EF00–EFFF remains reserved; unknown word I/O preflights both ports without partial side effects |
| D47 | Implemented, 2026-10-15 | Logical video/absent serial/printer callbacks use exact initialized owned ROM addresses and ordinary IRET | Preserves mutable BDA/VRAM/hooks and saved flags; logical video does not claim host rendering, and present serial/printer devices remain unsupported |
| D48 | Implemented, 2026-10-15 | Original adjust semantics and 3,146 additional pinned hardware rows extend the full projection to 5,701 | All earlier rows preserved; AAM-zero frames compare exactly with no new masks; REP adjust policy remains source-derived |
| D49 | Implemented, 2026-10-15 | Place logical video DEVICECODE at 5000–5FFF and explicitly zero-initialize 4000–4FFF in a contiguous runtime PRG | Keeps screen/fonts/bitmap reservations free of code; distinguish linked allocation from MAIN padding/startup file bytes; isolated hardware configurations remain unchanged |
| D50 | Budgeted, not linked, 2026-10-15 | Optional future UCIBUFFER at C100–C8FF leaves C900–CFFF for extra resident code | Charge its 2 KiB before promising code headroom; clock/native-clock/keyboard/UCI modules are future unlinked work at this checkpoint |

| D51 | Implemented, 2026-10-15 | Original XT INT 1Ah state and bounded explicit tick advancement remain separate from elapsed host time | Coherent mutable BDA, equality-only midnight rollover and original nonzero-AH decrement; no invented AT RTC or IRQ0 pacing |
| D52 | Implemented, 2026-10-15 | Empty INT 16h AH=00 yields only at its owned ROM gate with the guest frame intact | Retry after actual assembly enqueue; preserve ordinary IRET and exact AH=01 RET2 flags; native key scan/IRQ1 remain separate |
| D53 | Implemented generic transport, 2026-10-15 | UCI uses bounded async state/queue/backpressure and caller elapsed deadlines | Link C100–C8FF buffers; source-derived queue limits, exact counters/abort recovery; image-file command semantics/persistence are not implied |
| D54 | Implemented; corrected physical PAL/raster matrix accepted | Native CIA2 chained clock requires explicit exclusive timer/NMI ownership | Raw phi2 tick API with bounded coherent sampling; physical calibration/turbo independence precedes deadline conversion; not CPU/XT throughput |
| D55 | Implemented, 2026-10-15 | Accept only documented absent-board GLOBAL REARM byte writes at 02F2h–02F7h | Pinned Microsoft inherited-3.30 source and original relocated binary audit; arbitrary byte value, no PIC state change, reads/words/unrelated ports unsupported |
| D56 | Functional milestone, 2026-10-15 | Default DOS acceptance is kernel-only; opt-in long lane proves actual COMMAND.COM, VER and exact DIR | Real assembly keyboard input and independent filenames/sizes/count/free-byte oracle; Peddle prompt accepted, full native system still unfinished |

| D57 | Physically verified, 2026-10-15 | Accept raw PAL CIA/raster domain and observed turbo independence at Manual 1/16/64 MHz | 100-frame deltas within ±1,008, zero retries and 28-tick spread on firmware 3.14/FPGA 121/core 1.47; no CPU/REU/XT throughput or wired deadline conversion claim; preserve rejected first run |

| D58 | Implemented and verified, 2026-10-15 | FILE/TEXT share one exclusive C900–CFFF execution window through resident wrappers | Per-variant exact linked payloads, two immutable REU slots, header validation and publish-after-DMA; startup sources released only after complete bootstrap; trusted payloads have no native CRC |
| D59 | Implemented and full-corpus verified, 2026-10-15 | Replace linear opcode dispatch with 256 low/high addresses while preserving opcode A entry ABI | Net +103 MAIN bytes; all 5,701 hardware cases and exact genuine DOS observations/state pass; final combined layout saves 8.3436% CPU-step cycles, not physical time |
| D60 | Phase policy for next slice, 2026-10-15 | Cold import code/state may occupy 7000–7FFF only until bitmap ownership | Native image load must finish and publish resident media state before display overwrites cold bytes; startup assets 6000–6FFF are a different earlier lifetime; runtime reload/save needs a separate design |

| D61 | Linked and functionally verified, 2026-10-15 | Cold 360 KiB import requires exact chunks, EOF, independent native CRC and known closure before publishing media | Startup-only 7000–7FFF; loaded=0 on all failures; original file read-only; no runtime export/persistence or physical UCI claim |

| D62 | Implemented/verified,2026-10-15 | Third INPUT startup asset8000–87FF commits toREU341000 before guest cache/BIOS use | All6144 asset bytes independently checked; guest cache frames become available only after complete bootstrap |
| D63 | Implemented/verified,2026-10-15 | Initialized resident cold_openA5 clears irreversibly before bitmap ownership | Cold public gateways reject before discarded state/code; no init reopens lifetime; TEXT requires release |
| D64 | Implemented/verified,2026-10-15 | TEXT is canonical renderer718+VIC239; fonts are explicit non-executable data | NarrowASCII4×8 improves80-column VICE output; paired colors/extended fallbacks/cursor limits explicit; physical acceptance pending |
| D65 | Implemented/verified,2026-10-15 | Native deadline units are exact rawCIA>>12,4096 phi2 ticks each | Tested banking,wrap and failure publication; caller supplies ownership and bounded polling; runtime use pending |
| D66 | Development tools verified,physical execution pending | Snapshot/restore all first4MiB with sequenced native service and verified local backup; FTP uses a fresh owned directory | Full readback and failure-before-reset capture; never claim CPU/timer execution recovery or native persistence |


| D67 | Implemented/functional proof,2026-10-15 | Explicit D64N configuration gates native startup; initialized started/cold guards reject repeated SYS before mutations | Complete UCI/import/BIOS/input/text/native-tick DOS path accepted in Peddle; shipped config disabled |
| D68 | Implemented/verified,2026-10-15 | ENTRY retains KERNAL until complete RAM NMI vector and CIA2 mask/ack, then RAM+I/O | Closes the incomplete-vector NMI window before hardware; callable APIs retain exclusive-owner preconditions |
| D69 | Implemented/verified,2026-10-15 | Development SNAPSHOT flushes and pauses; bounded READ only while coherent PAUSED; KEY uses real BIOS ring | Guest DOS semantics unchanged; body/ack invalidation before command-last, result before clear-last |
| D70 | Implemented/verified,2026-10-15 | Observe DOS periodically even without AH00 wait, and recognize pagination only at active cursor | Real COMMAND polls AH01; stale prompt elsewhere on screen must not queue extra keys |
| D71 | Physical attempt failed,2026-10-15 | Preserve initial native hardware failure and independently inspect unchanged settings/media | No service/application/DMA loaded, no verified backup; reset/resume/equality does not imply full REU recovery |


| D72 | Measured/rejected bulk proposals,2026-10-15 | Keep bounded600second recovery phase; serial/parallel tiny PUT and256 packed PRG reloads are too slow | Actual RAM-only gates preserve settings/media; extrapolations~20/~17minutes precede REU writes; implement one-file native UCI restore instead |


| D73 | Implemented/host verified,2026-10-15 | Exhaustively scan4MiB and restore changed chunks, then independently compare4MiB | Complete immutable backup remains authority, every retry rescans including unexpected/alias changes; same600second phase/bounded attempts; saves slow unchanged payload uploads |
| D74 | Implemented/actual native Peddle verified,2026-10-15 | Normalize only four exported UCI pointer operand bytes after opcode/buffer checks | AD upload and8D drain self-modify legally; all other resident bytes exact; scoped debug aliases preserve target binary identity |
