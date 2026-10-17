# Decision register

2026-10-17 installer sequencing: retain configuration-last publication for the fresh-file flow. Verify C and B, derive and persist A, build both native assets, persist and fully verify START.PRG, then persist and fully verify DOS64.CFG. CREATE_NEW remains mandatory; no existing installation is overwritten. Before the final CFG is valid, START must refuse launching. This supersedes the private combined-fit sequencing note that proposed CFG then START-last. Partial files are not completion receipts; reconfiguration/conflict handling and CFG body-identity binding still require implementation and end-to-end tests.

2026-10-16 user requirement: START's embedded installation home should locate same-folder emulator options; native startup can perform reading/parsing and pass validated settings through REU. Proposed mechanism: optional editable DOS64.INI, bounded native prelaunch parser overlay, separately versioned launch-bound binary options record, resident copies of frequent options and validated home. Existing D64C/D64R ABI1 remains unchanged until an explicitly versioned implementation. Public START has one byte of headroom, so parser placement and REU ownership require measured integration. Design recorded in docs/NATIVE_SETUP_CONFIG.md; implementation and actual/physical tests remain pending.

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


| D75 | Physically verified,2026-10-15 | Accept genuine native DOS3.3/UCI import/VER/DIR at Manual64MHz for frozen three-overlay647eca target | Exact35entry/9216free/returnedprompt,108screens/14keys, resident/CGA/floppy identity; does not accept new timer/CGA target or human keyboard/readability |
| D76 | Physically verified,2026-10-15 | Exhaustive delta scan plus changed-chunk restoration and full4MiB compare is accepted |37chunks606208bytes,282.119second scan/write, firstattempt, root all-byte equality/config/media/reset proof; protects full scope, not only expected writes |

| D77 | Implemented/Peddle verified,2026-10-15 | Commit all five immutable overlay startup slots before cache/BIOS; relocate only unit helpers to guarded cold memory |10240assetbytes/12overlappedcacheframes;975unitcoldbytes/one resident return sentinel; reject before mutation after any native attempt/bootstrap/release |
| D78 | Implemented/fullCPU verified,2026-10-15 | Deliver PIC IRQ through mutable guest IVT at every eligible REP element, preserving16element scheduling quota | OriginalNMOS segment/STI shadows, IP−2 restart/final-element ordering; independent element16/CX33 proof; fatal partial frame terminal |
| D79 | Implemented/Peddle verified,2026-10-15 | FixedPIT exact rational phase/countdown requestsIRQ0; only default guestINT08 owned gate updatesBDA | Guest hooks/INT1C/EOI remain authoritative; IRRcoalesces missed periods; programmable PITports unsupported; developmentpause rebases |
| D80 | Implemented/Peddle verified,2026-10-15 | GFX presents coherent BIOSmodes4/5/6 in bounded8scanline ticks | GuestVRAMexact;320→160foregroundpairs/640→320OR;palette/cadence compromises explicit; physical/directCGAports unaccepted |
| D81 | Evidence reuse,2026-10-15 | Reuse once-run full5701 CPU proof only with all55sourcehashes and both rootPRGs byte-identical plus independent review | Root reruns408default/native/legacy/threshold/profile; no redundant slowfullgate absentsemanticdivergence; physical647eca remains separately scoped |

| D82 | Implemented/test verified,2026-10-15 | InternalDOS workflows run through nativeENTRY and real keyboard ring on disposableREUfloppy |11commands/complete720sectorcheckpoints,mirroredFATs/exactoriginalcontent+allocation/deletionlogicalstate; sourceimmutable; no nativeDOSshortcuts/persistenceclaim |

| D83 | Implemented/primary-source/Peddle verified,2026-10-15 | OriginalXT INT10 AH10..FF returns all guest state unchanged | Archived11/08/82listing+independentROM path agree; one-bytebranchfix enables genuineMODECO40/CO80; noEGA/VGA implementation or newXTsiliconclaim |

| D84 | Implemented/source and host verified,2026-10-15 | Add explicit opt-in one-file native4MiB recovery while preserving default delta | Source reproduces388069/40fe; immutablebackup/freshFTP/codeCRCknownCLOSE/all4MiBcompare; one600secondphase/max2freshpasses; physicalthroughputpending |

| D85 | Implemented/reference verified,2026-10-15 | Source-complete read-only DOS disk inspector and genuineDOS2/20MiB fixture recipe |17newtests/cleancheckout,actualFDISKFORMAT SYS CHKDSKHDboot/CROSS16,fullhash/chain/allocationchecks; no bundledHDimages/nativepersistenceclaim |

| D86 | Physically verified recovery only,2026-10-15 | Accept one-file native4MiB restore independently of failednew5DOSapplication | Freshbackup/all4194304bytesequal/CRC8192knownCLOSE/strictcode/firstattempt/231.923s/configmediareset; app180secondfailure staysfailed; upper12MiBuncompared |
| D87 | Implemented/host verified,2026-10-15 | Explicit bounded observation cadence/application duration preserve0.25s/180s defaults | Optional0.25–2.0s/10–600s,stableAH00prompt/periodicAH01,allkeys/pagination; distinguishoverallbudgetfrom12sACK; no pendingcommandreissue/performanceclaim |

| D88 | Implemented/Peddle verified,2026-10-15 | SixthHDoverlay plus separately verified F000–FDFF copiedcode for HD/scroll; all23startupcacheframes released onlyaftercopy | Minimum4MiB budget,explicitdisabledD64H,residentconfig,asyncFILElease/readbackauthority;root417/597/218/nativeDOS/MODE/HD and exactreviewedfullproof;physicalpending |
| D89 | Implemented/host verified,2026-10-15 | Physicalrunner requires pinned pairedshadowmetadata andimmutablePRGsource comparison for all3584runbytes/A5guard | LiveA000cache neverauthority;FEvectors excluded;RESTunderlyingRAM cannotproveCPUportbanking;no nativebytechange |

| D90 | Measured research/next experiment,2026-10-15 | Prioritize owned clock ABI and coherent memory/fetch cost before broad runtime translation | Actual DOSprofile601936calls,60.32%memory/fetch/address;register-onlyzero-cost ceiling1.081×diagnostic harness;allIRQ/REP sampling retained;translator unimplemented/noXTclaim |

| D91 | Physically verified,2026-10-15 | Accept six-overlay98fc/config1ff1 floppy-only nativeDOS atManual64,explicit2s/360s observer |37screens/14keys/35entries/9216free/returnedprompt,all3584shadow/A5/fullbitmapmatrix,all4MiBrestore222.093s/configmediareset;HDdisabled,noMODE/readability/XTclaim;failedfive staysfailed |
| D92 | Implemented/host verified,2026-10-15 | OptionalMODErunner requires explicitSHA-bound actualunit proof pluspairedruntime/source/bitmap identity |Root238tooling,independent26testsperlayout/10offlineCLI;defaultVERDIRunchanged,strictshadowand600recovery retained;physicalMODEpending |


| D93 | Physically verified, 2026-10-15 | Accept genuine DOS MODE CO40/CO80 on exact98fc/configuredab50 with complete RAM framebuffer/code proof | Both returned prompts; independent1,443 assertions; first recovery protocol failure retained, second restores all4MiB; observed272.930s across attempts, configured600s per attempt; no human matrix/HDMI/graphics/HD/XT claim |


| D94 | Implemented/host verified, 2026-10-15 | Optional bounded HD collector retains new authority/handoff/image before outer REU restoration | Root273tooling/27native-file host; independent273/no network/no children; interruptions/malformed results cannot skip recovery; original pre-helper appRAM must be preserved by future caller; no physicalHD trace/runner yet |


| D95 | Implemented/model verified, 2026-10-15 | Internal owned-clock ABI plus validated emptyPIC branch preserve every existing IRQ/HLT/REP boundary | Root421/597quick/273tools/focusedHD32; actualprivateDOS/MODE exactbothPRGs+176source proof; independent12combination tests;424cycles emptyboundary/8.8%modeledDOS reduction;shadow2361/PIT1664; no transfer of old physical/full5701 acceptance |


| D96 | Research retained, 2026-10-15 | Native one-shot hint remains observational; full sampling policy unchanged | Independent exact797byteprobe/bothVICECIAcaptures/36observations/all546875phaseedges; deployedFPGA121latency/productionfit unproved; DMA/postnotification and imminentedge fallback limits explicit |


| D97 | Implemented/VICE verified, 2026-10-15 | Opt-in standalone KERNAL/D81 import lane with proven fresh VICE process ownership |16additive files/minimalMakeZig;3Peddle/13scenarios/29host, fresh full360KiB/720DMA/all4MiB VICE pass; everymonitorcommand rechecksacceptedtuple/PID; missingproductsrebuild; no productionIEC/DOS/persistence/physical64MHz claim |


| D98 | Physically verified, 2026-10-15 | Accept exact22f82091/configuredea93 native DOS VER/DIR with full recovery |33screens/14keys/35entries/9216free/returnedprompt,allshadow/fonts/bitmapmatrix,firstattemptall4MiBrestore226.434s/configmediareset; independent1524audit; actual745preflight/provisional1105retracted; observedone-run107.320vs118.151 finaltime is notXT/isolatedspeedclaim |


| D99 | Implemented/prototype verified, 2026-10-15 | Native whole-floppy create-new/write/CLOSE/reopen/allbyteverify/EOF/CLOSE pipeline as opt-in standalone fixture | Root12Peddle/39scenarios/5host; independent6/8additional; all4MiBauthority/guards, lostreplyuncertainty, noexistingoverwrite; normal22f/8a unchanged; realclock/leases/modal/UI/physicalintegrationpending |


| D100 | Implemented/model verified,2026-10-15 | Genuine DOS loads a small CGA4/5/6 COM fixture; independent reusable pixel oracle validates BDA geometry/palette | Six additive files/opt-in Zig, root286tooling; exact22f/8a+177source nativeproof,8focused/23capture/30additionalcontrols; no physical graphics acceptance |


| D101 | Physically verified,2026-10-15 | Publish same-pause guestDOS/C64pixelpairs fromgenuine40/80 DIR/W, with honestfont/RGB provenance | All35files/9216free/A>, full4MiBdelta/settingsmediareset,54capture/1404recovery/1181evidence; previousnativefilefailures retained andseparatelyrecovered; DIR|MORE pending |


| D102 | Physically verified,2026-10-15 | Genuine DIR|MORE first-page pairs and explicit temporary-file policy | Both40/80, realSPACE/finalDOS;37live→35clean originals;2066 allowed residue bytes; all4MiB/settings restored, remote source exact |
| D103 | User directed,2026-10-15 | Performance minimum50%, stretch85% of4MHz8088 using real elapsed and analytical instruction/bus/prefetch bounds | DOSBox functional only; current3–5% is idealNOP model comparison, not physical whole-DOS measurement; privateCPM example is feasibility signal |
| D104 | User directed,2026-10-15 | Record actualC64U video of GW-BASIC autoplayhangman, LIST, SYSTEM, DIR | Explicit recording request authorizes owned video endpoint/start/stop; stop only own stream, preserve known settings, never claim unknown prior stream restored; no audio/debug needed |

| D105 | Physically verified capture foundation,2026-10-15 | Actual VIC stream left pixel is low nibble; use explicit shared CLOCK_MONOTONIC for host chapter alignment |505 actual frames/383,616 independent known pixels/18tests; owned stream stopped, no game or unknown-prior-stream restoration claim; original wrong-order evidence retained |

| D106 | Implemented/independently reviewed,2026-10-15 | Original XT PPI61 output latch, fixed-PIT same-divisor zero-pair writes, explicitly absent game adapter201h enable genuine suppliedGW-BASIC |425/290root,58571independentchecks/4088cycles; actualnativeWIN/fourLIST/SYSTEM/DIR/fullfloppy proof; programmablePIT/speaker/physicalvideo excluded |

| D107 | User requested/published,2026-10-15 | Private ChatGPT Sites progressdashboard with interactiveperformance/memorydiagrams, realcaptures and highlightedBAS | NativeSitesdeploysucceeded/source2dc2e149; actualgamevideopendingretry; isolatedSiteGit only, no parentrepo push or recurringautomation |
| D108 | Measured host-test policy,2026-10-15 | Reduce intrusive coherentobservations by phase; retain allguess/LIST/video checks and bounded recovery | First.25s attempt cancelled288s/360111guest; full4MiB809ACKrestored. NEW2sutility/.75sBASIC+1800sapp/2400srecording underreview; shared600sdefault/recovery unchanged |


2026-10-15 verified performance composition: promote only five reviewedCPU/memory/fetch/test files to1a17/4e43 after oldhardwarefreeze fully recovers. Immediate continuations require a fresh successful publicfirstbyte with no interveningcache/device/clock/gueststate mutation; seams use originalslowpath. Full clock/IRQ/REP cadence remains binding. Exactpairednativeproof reuse requires source/model/fixture closure, not just matchingPRGs. Physical acceptance stays perbuild. Firstfailedstartup protocol status must be latched before recovery changes it; later last_status is not causal evidence. Separate read-onlyprobe cannot waive readiness after anotherPRG/reset.


2026-10-15 native command-interface diagnostics: retainoriginalgenericuci.o forstandalonehelpers; normalruntimeusesnative-uci.o withquietguards/stickyUCF1. FirstrecordpublishesA5lastandpersistsacrosscleanuptransactions untilfreshverifiedENTRYreset. This isdiagnostic/fail-closedguarding, notprovenatomicread/PUSHorresetbarrier. Exactnative/genuineBASICproof andnewpurpose-boundphysicalcohort requiredaftertargetchanges. Modeledgenerated6502blocks andearlyhardwarehint aretwoexplicitperformanceexperiments, separatefromproduction; retainfullsampling untilnewownedprofileproof.


2026-10-15 actualPALManual64CIAcalibration: retainfullsamples. Measured64tickearlymarginisinsufficient;256/1024succeedonlyinthenineownedkernels. IRQ-backedRAMhintisthenextprivateobservationalmechanism;currentgloballySEInativeentryandbankvisibilitymustbehandledexplicitly. NeitherfinitecalibrationnorclockmodelauthorizeschangingproductionIRQeligibility.


2026-10-15 promotePITdirectaccumulatoronlyunderexactnoedgeprecondition; allpartialbinarysums<=delta guaranteephasecannotoverflow, remsum<2D needsatmostonesubtract. Preservefullphysicalclock/IRQ/REPboundarycadence. Continuous64:1perPeddlemicrocycle ispreferredcontrolledCPUmodeloverburst-batchedclock; neitherincludesphysicalDMA/VIC/IOwaits. Separatefixedworkfromwholeworkflowguestcountvariation.

2026-10-15: Native REU issues once then observes completion at most256 times, retaining first/final raw status and failing immediately on verify bit20; success requires EOB40 withoutverify. This is a termination bound, not a physical latency guarantee. Generic40fe andall13standalone binaries remain exact. Compactnativeexpiry2B andresidentNMI1B fundfit; no ZPguard widening.

2026-10-15 proposed native-write workaround, not implemented acceptance: investigate public v3.14 direct command-BRAM→USB DMA address truncation as cause of repeated wrong512-byte SAVE sectors. First source-bound ECHO516, then fresh-file512vs256+256 with independent full retrieval. Prepare private split-write exporter but do not waive INFO/complete comparison/EOF/final closure, source authority or paused cache/guest guards. Installed cause and workaround remain unproven. Generic HD512writes require separate physical acceptance. See docs/NATIVE_WRITE_DIAGNOSIS.md.


2026-10-15: Promote independently reviewed split256 floppy SAVE after paired physical discriminator and fresh ROOT428/298/73. Preserve full INFO/compare/EOF/CLOSE,32-frame restoration, guest pause and original-media authority. Generic HD writes remain unchanged/unaccepted; no timer/JIT promotion.


2026-10-15: Use explicit reviewed recovery control-flow derivative for newhardwarehosts after actual second-interrupt bug in oldsharedorchestration. Keep40fe/Delta/transport data algorithms unchanged; perphaseBaseException handling must retain firsterror, continueboundedindependentcleanup, and neverturn exhausted/unknown restore into success. Host-only loading handoff must awaitload-onlycompletion andobservedBASICready beforeSYS, withoutwrong-IDretry/fixedpacing/nativepatch.

2026-10-15: Accept originald883 whole-floppy development SAVE only under complete native comparison/EOF/CLOSE, independent full FTP/REU/FAT and frozen source closure; fresh repeat is passed, prior altered ancillary-metadata run stays failed. Use reviewed acknowledged LOAD-only/observed BASIC READY/SYS2061 host handoff; two physical boots now succeed, installed firmware race cause remains conditional. Do not substitute private compiler/timer behavior or infer power-loss/nativeUI acceptance.

2026-10-16 user scope: Regular A plus complete C archives/convenience DOS utilities, GW-BASIC/Hangman and latest appropriate Turbo Pascal. Select originalEnglish7.01 real-mode TURBO/TPC by primary published DOS3+/all80x86 requirements; TPX protected mode is separate. Complete payload requires supported20MiB profile, not an arbitrary2MiB subset. Preserve original disks and product bytes, execute realDOS loaders/compiler, and repair missing originalXT semantics rather than patch the compiler. PhysicalHD persistence and nativeTPC remain unaccepted.

2026-10-16: Accept independently replayed purpose-specific A+C development host for a physical verification run. Configure only reviewed D64N/D64H envelopes; retain original RAM, complete changed REU and all seven immutable slots before destructive helper loading. Use the target2 readonly CLOSE/reopen helper and strict complete-image FAT/entry/allocation ownership checks. Preserve the first application/retention exception through at most three local budget restoration/report attempts; these are local cleanup attempts, never retries of ambiguous native commands. Keep the unchanged b017 outer recovery and original40fe service with accepted finite batched scheduling. Full physical acceptance remains conditional on the complete run and recovery.

2026-10-16: Accept physical A+C development/persistence milestone only after native backing-file CLOSE/reopen and final independent whole-image comparison. The preclose FTP image retained FAT allocation without the completed rootHELLO entry; nativeCLOSE made the clean complete entry visible. Preserve that first failed inspection rather than treating open-handle FTP visibility as persistence authority. Actual cause below the native file boundary is unproven; no power-loss durability inference. Current4589/a827 fullrun/recovery passed. OriginalTURBO editor remains independently reviewed model work, pending ROOTcomposition and fresh physical acceptance.

2026-10-16: Promote independently reviewed originalCGA MC6845 register aliases/masks/cursor latches, explicit absentMDA probes,3D8 blanking/blink control and canonical virtual3DA status. Derive status from already published48-bit PIT plus normalized rational remainder; reads do not advance time/sampleCIA or alterIRQ cadence. Unsupported raster timings refuse; unusedupperbits deterministiczero is not electricalaccuracy. Bounded pure math uses an existing exclusiveFILE lease and rejects originalreplacement-window callers before nestedJSR hides provenance. BIOS BDA cursor/palette shadows retain originalsoftware semantics. Root4cc/4b82 model/editor accepted; physical4589 milestone does not transfer to newpair.


2026-10-16: Promote public A+C host/helper with frozen dependencies and pre-import cache absence checks; actual poisoned-cache regression preserves old failure. Promote only reviewed address.s/memory.s and additive memory test, preserving all clock/IRQ/REP cadence/public build graphs. ROOT460/304 b3/b995; modeled gain does not transfer physical acceptance or establish XT target. Keyboard/cursor successors remain review candidates.


2026-10-16: Promote independently accepted boundedcanonicalCGA cursor cfec/c325 with capturedfield/latch/attribute-phase oracle, foregroundORbars/full14bitaddress and stale-before-output refusal. Correct docs U12LS393divider/U63resetgate. Preserve IRQ/REP/clockpolicy, ROOTperformance/publicgraphs. Fresh exactpairpurpose/physicalhostadapter required; original4ccIDE/4589physicalacceptance cannottransfer. Combinedda95/bc6ab472/308/69/503closurepass.


2026-10-16 user-directed installer constraints: no dummyD81launcher or largeblankHDfiledistribution; requireUltimateDOS/UCI and allow nativeC SETUP withREU/overlays. UserssupplythreeDOSimages; installerbuildsworkingA/B andraw2/20MiBC natively, noemulatedFORMAT/COPY. Generatepersistentpath-awareSTART.PRG; fixedREUrecord isvolatilehandoffonly. ResearchrecommendsbulkDOS21/22 andnativeFAT12/16writer, preservingrawformat; dynamiccreationdoesnotrequiresparsecontainer. Allimplementation/bulk4MiBqualification/actualtimingspending; do nottreatproposalasdelivered.


2026-10-16 floppyproposal: retainstandardrawIMGsloadedwholeinREU, noD81wrapper. Userexplicitlyrequiresimage-swapping andpersistence. RecommendwholeverifiedSave with modifieddrive/generationbinding andSave/Discard/Cancel on swap/eject/exit; readonlyoriginals/workingcopies, trueindependentB, no silentautosaveclaim. CurrentC-onlineSAVErestriction requiresreviewedintegration. NativeREUflushdoesnotflushguestDOS/applicationbuffers; DOS3.3mediarevalidationrequiresactualtests. Proposalnotimplemented.


2026-10-16: Userexplicitlyauthorizesalllast-hournativeinstaller/floppydiskmanagementimplementation. Promoteindependentlyacceptedkeyboard4c39/0525 afterROOT484/308/503closure, preservingclock/IRQ/REPpolicy; no typematic claim. NativeCsetup/START, nativebulkREUIO/FATbuilder andtrueA/Bcore proceedasparallelprivateverticalslices; originalfullscope/performance remainsbinding.

2026-10-16 user-directed REU budget: use more REU when restricting allocation would slow the emulator. Retain the 4 MiB supported minimum and explicit configured-capacity bounds; larger profiles may use disjoint extra arenas for measured cache/overlay improvements. Firmware 16 MiB addressing is not capacity detection. Extend physical backup/recovery coverage before testing above 4 MiB. No allocation or speed claim is implied by this policy alone. See docs/REU_ALLOCATION_POLICY.md.

2026-10-16: Promote independently reviewed A/B core957276ef after ROOT14focused controls plus genuineDOS and exact mixed-cohort500/308/14/1/6 gates. Rotate three complete arenas100000/180000/380000; never stage over either mountedimage. Mount/content generations and caller-verified CLEAN preserve dirty authority. Reserve immutableDISK343800, spare380000–3D9FFF, installer3Ebank and3FFanchor; eightphysicalslots and47105Bpackage now binding. Preserve nativeCFG/keyboard/publicgraphs in surgical merge. LegacyAstartup/SAVE remain guarded integration work, not userSwapUI acceptance. Force native test execution and declarePRG/labels inputs; cachedhosttest results cannot establish behavior of a newly assembledPRG.


2026-10-16 user hardware direction: Peddle is for fast iteration; final claims require the real Ultimate. Delegate one exclusive hardware worker while ROOT and other workers continue implementation. Accept fresh32K native bulk only after strict native source/count/CRC-independent fullbytes/verifiedpoison/EOF/knownclose plus completeFTP and fulloriginal4MiB/settings/media/reset recovery. Retain the first space-vs-zero-padding verifier failure; accept only the two observed exact35-byte EOF forms in the fresh successor. Do not generalize via stripping text. Larger128K/2M qualify separately.

2026-10-16 launcher: release-bound64-byteD64L validates sizes, addresses, disjointpatchranges andCRC, while caller separately verifies stagedwholemain anddisabledtemplates.32-byteD64R binds CFG CRC over0..571, not whole576-byte CRCcodeword (fixedresidue). PublishreadyA5 last, consume once; required flag prevents silentlegacyfallback. FILE coldhelper307B is covered byexplicit1771-byte assetlength andfullsource/readbackcompare; existingheaderhasno payloadCRC. This coldimplementation remainsprivate pendingROOTpromotion.

2026-10-16: Promote ce482 maincoldhandoff only after ROOT exactruntime/unit reproduction,500base/314tooling/11loader/14legacy/1genuineDOS plus14repeatedA-B controls and444input/copyclosure. Lifetime4000cold+6000relocatedhelper permitsfixedfonts andNMI5882; explicitFILE1771 count andfull307Bcompare, no inventedoverlayCRC. RequiredA5 refusesfallback; legacy0 remains. BfailuremayleaveA mountedbut no BIOS/guest execution; terminalreloadonly. PublicnamedMakegates andincremental.incdependencies addedwithoutchangingnativebytes. StandaloneSTART/physicalnewmain remainpending.

2026-10-16: Native2MiB success is not physicalacceptance when independentFTP andrestoration fail. Preserve76bdcampaignfailed withoriginalac43backup,11215sourceclosure, Reset54 andtwointerruptedboundedrestores. Keepsolehardwareowner/recoverypending untilindependentall4MiB equality andsettings/media/reset closure; existing3880 whole-filefallbackrequiresconcrete frozenauthorityreview. The earlierretentionfirstexception-object reporting bug is separatefutureorchestrationwork, not cause to waivefailure.

2026-10-16: Accept original4MiB restoration onlyafter activeFTPsuccessor85c7/0ce2 physicalclosure andROOT325seal/allbytecomparison. Passive0-byteReset+226 andprior2MiB/wholefilefailures remainfailed. ActivePORT isapurpose-bounddevelopmenttransportchoice, notaguestnetworkfeature orprovenfirmwarecause. Wholefile3880nativeCRC/knownCLOSE plus40feall256 andfullFTP/source/config/media/reset remainrequired. FutureUltimatejobs musttrulydetach asuserdirected; userauthorizesRESTfullresetswhenneededbutresetisnot restorationproof.

2026-10-16: Promote true native START8b68/bb14 only after ROOT source-only46-group replay, public46-group replay/all16product closure, default10Zig/fourhost and324tooling checks, plus independent compiler/path/closure review85895c62. Default template stays disabled until persistenthome configured; no physicalacceptance transfer. Shared FILES/UCI source matches main exactly; explicitstartupCLOSE1/2 establishes firmwareownership beforeOPEN. Preserve default codec bytes whenfast/decoder-only flags areOFF. Payloadone-byteheadroombelow5000 is binding. No push.

2026-10-16: SETUP filename presentation must distinguish legal names that C64glyphtransliteration wouldalias. Percent-escape ambiguous symbols andpercent itself; horizontaloffset counts encoded cells, while selections retainrawcanonicalbytes. UI/privatebrowser state controlsdrain andfirstcause, observationbytes do not. Selectioncapsuleproposal reservesSETUP-only2C0000..2C03FF, ready-last704B record plusprivatecurrent-sessionauthority; actualimplementation/linkproofpending.

2026-10-16: Accept source-loader33db model component after independent25-group review and ROOT55+9 closure, retaining rejected twoLOAD1dda. Source identity is validated through private D64Q, full stagedbytes/CRC and independent ordinaryREAD04/EOF/finalknownCLOSE; no trusted external digest/common-mode immunity claim. UI codec BSS is phase-local, while source receipts and copied HIGH code survive phase retirement. HIGH_CODE READ wrapper is installer-only; preserve publicSTART/native default graph during promotion. NF writers overwrite200000/208000, so derive/publish A only after C/B outputs complete. Physical acceptance and actual fullinstaller coordinator remain required.

2026-10-16: Accept PUB-only dualinitialized-FETCH repair3eed/2f2e afterpeer32+ROOTfresh7nativegroups. Original72e4/27e0 remainsNOT_READY underqualifiedsynthetic faultyREC; reviewedrawPRE wouldnormallycatchCRC mismatch, so thisisassetreadinessbug, notprovenfinalpublicationorhardwarefault. UI/FAT/PUB fitdoesnotreplaceactualprivateproducerledger. Require actualcooperativeNFkey/clock service beforeenduserclaim. Hardwareef7bd failedbeforestager: preservefirstReset54/prefix/settingsclosure, leavefull4M/deviceunverifiedandreserved, noambiguousretry. Preferlowerroundtripread-onlyretentionresearch overrepeatingunchangedfailedcampaign.

2026-10-17: Compact nativeSETUP UCI profile remains defaultOFF and preserves generic895-byte packet-drain saturation independently of512-byte receive capacity. FILES wrapper must validate command payload/path and receive limits beforewire. Generic UCI truncation can finish transportDONE with flags; consumers must reject before minting private facts. AUX code has a measured1120-byte range; serializedHIGH/AUX are verified perbyte beforeinstalledA5 and included in the UI CRC/cache extent. Do not use self-modifying copier bytes inside immutable UI. Same-home INI remains optional editable input read at every cold launch; SETUP may share parser/prepare REU settings, but volatile REU cannot substitute for reading edits on later starts.

2026-10-17: Promote public native SETUP source/build only after corrected full ROOTc45 composition, independent RAW-owned cleanup review0abde600, and exact source-closed public reproduction of all phase/metadata/symbol addresses. This acceptance covers model fresh-install and safe collision cleanup; retain explicit physical/error-UI/reconfiguration limitations. Latest user reiterates same-home optional INI, parsed before emulation and compactly handed through REU; parser4328093 foundation is accepted only as a component, without an allocated record or consumer.

2026-10-17: Promote reviewed ownedfetch/framepointer/PIT composition onto currentc6 onlyafter exactsource-only8711/56b1 reproduction andROOT503/17/11/1/layout17, withauthor2631source/product closure. Sameclock/IRQ/REP/coherencepolicy; report4.25–4.35% modeledDOS/builtinCPUcost reduction withhistogramdifferences explicit. AcceptportableoptionalSETUPtestgraph sourceidentity/publiclayout actualMake4+5/hostcontrols; normalbuild remainsindependent. Readonly95f96 physicalattemptfailed pre-native; retainreservedstate/no automaticretry orwriteback. NarrowINIoverlayfitsprivately, butno newABI/recordaddress allocateduntilmatchedfunctionalproof.

2026-10-17: The user's same-home config suggestion remains the accepted cold-launch contract. START rereads current DOS64.INI at each cold launch using its embedded validated home; SETUP may share the parser, while surviving REU contents never replace reading later edits. Store validated binary settings in an explicitly allocated launch-bound record and copy frequent options into resident state. Native I/O/parser/record/main consumer must be qualified together before public acceptance.

2026-10-17: Private SETUP may reuse initial serialized HIGH/AUX source as UI BSS only after full initial CRC, complete byte-readback relocation, and verified core-plus-zero UI cache commit. Keep separate full initial and live-core CRC identities. New permanent AUX error rendering is gated by private successful phase preparation; it must never run on a pre-verification failure. Capture same-engine file closure truth before terminal entry, preserve first cause, and never close/retry/rearm from the presentation path. Eight direct controls pass; full installer and independent review required before promotion.

2026-10-17: Promote terminal/lifetime SETUP4da only after full4+8 actual integration, independent8+3/512 formatter cases, ROOT474/951 source-product closure, exact public seven-file copy/rebuild and actual public8. Keep full initial CRC distinct from runtime core CRC and explicitly retain the trusted earlier bootstrap/relocation boundary. Do not call this complete early error UI, INI, reconfiguration or physical acceptance.

2026-10-17: Accept public early destination-conflict check0df after ROOT4+5+11, peer5+3+11, source/product closure and exact public copy/rebuild+5+11. The mask is private, computed before filtering/page selection, committed only on complete clean directory/quiet lease release, and path-bound. A public page/result cannot authorize home selection. Exact names cannot detect every filesystem alias or later creation; retain CREATE_NEW. This is not full reconfiguration.

2026-10-17: Existing-installation reconfiguration uses a fresh launch-generation folder and private readonly-media inspection receipts, existing absolute A/B/C paths, fresh A/B CRCs, matched small runtime assets and CFG-last publication. Avoid FAT import for paths/options-only changes. Native rename is not an atomic replace primitive and cannot justify power-cut rollback claims. Old/new launch configuration rollback does not roll back shared writable disk contents.


2026-10-17: Promote matched same-home INI only as the complete source/build cohort: START79bb +INOeebb +mainf7ea +D64S45b68eaf +D64L2 3b454d75. Keep default START8b68/v1 exact. Reread current file each cold launch, qualify exact missing-file defaults through owned closure, validate required one-shot D64O32 at3FF500 and prove consumption. Preserve D64C/R/S ABI1 reserved rules. Strict explicit8-byte NATIVESTATE and guarded251-byte unit-only sidecar keep the real consumer in unit execution. ROOT334/503 and43 focused native groups passed; preserve all verifier/discovery/old-test failures and one ancillary rebuilt-map qualification. No physical acceptance transfers; generation-home reconfiguration and preferences UI remain separate work.

2026-10-17: Promote reviewed666/b9 fetch/map/decode/privateCLD successor only after ROOT507/334/focusedcoldINI and fresh genuineDOS loader check. Public physical and exported byte operand APIs retain decimal-safe fullP preservation; private CLD entry belongs only to proven CPU-owned call sites. Live fetch reads actual resident bytes, so generation changes need no invalidation while valid/tag/frame/IP ownership checks remain. No clock/IRQ/REP policy or state budget change. Preserve rejectedD1 and historicalstrictbuiltins work-count failures; report3.56% fewer modeledfixedwork cycles, not physicalXT speed.
