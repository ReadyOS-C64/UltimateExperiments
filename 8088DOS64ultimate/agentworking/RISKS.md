# Risks and unanswered questions

| ID | Risk / unknown | Severity | Next resolution / fallback |
|---|---|---|---|
| K01 | Host instruction/translation cost prevents near-XT speed | High | M1/M3 handler+memory measurements; specialize hot paths; report achievable speed without changing real-DOS scope |
| K02 | REU misses dominate elapsed time | High | Measure DMA by size/direction, page-size sweep and actual DOS locality; smaller pages/prefetch only if data supports them |
| K03 | Resident code + metadata exceed host map | High | Map gate at every slice; static ABI; cold overlays; explicitly trade cache size, never silently overwrite memory |
| K04 | Real DOS boot/drivers need additional BIOS/ports | High | DOSBox/reference and target trace; implement bounded documented subset with tests; do not fake success |
| K05 | Incorrect mock makes unit tests misleading | High | Model conformance vectors + VICE/hardware; distinguish unimplemented register paths from valid defaults |
| K06 | Dirty-cache/UCI failure loses image data | High | Original images immutable; owned copies; exact count/status checks; new output and verification; fault injection and retained recovery state |
| K07 | 80-column colors/font are unreadable | Medium | Early physical font chart and editor test; monochrome/contrast policy; preserve all 80 columns and exact guest state |
| K08 | Turbo causes UCI timeout/protocol failures | High | Asynchronous handshake, elapsed deadlines, 1/16/64 MHz replay; no fixed-delay pacing |
| K09 | VICE traps hide IEC issues | Medium | Smaller true-drive/KERNAL lane and independent extracted-file comparisons |
| K10 | 2 MiB tests accidentally never evict HD cache | Medium | Force 64–256 KiB cache; random reads/writes; compare persisted bytes after reopen |
| K11 | File offsets silently truncate above 16 MiB | High | Explicit 32-bit arithmetic, boundary/final-sector tests in M9 |
| K12 | Original CPU boundary/interrupt quirks missing in vectors | Medium | Intel/Microsoft references, 8088/8086 corpora, independent hand-authored event tests before fast paths |
| K13 | Dirty sibling compiler/harness evolves during work | Medium | Pin/copy needed Peddle sources, hash references, tool manifest; avoid modifying sibling project |
| K14 | Installed C64U firmware differs from current upstream docs | Medium | Capture firmware/config, validate actual command behavior; bounded transfers and fallbacks |
| K15 | 2/20 MiB experimental CHS conflicts with supplied FDISK | Medium | Test exact binaries; use documented conventional geometry if needed and record actual bytes |
| K16 | Scope expands to all DOS utilities/peripheral modes | Medium | Explicit applicability matrix; no printer/network/EGA dependency; record unsupported operation instead of dropping entire useful utility |

No risk is marked resolved by the existence of this plan. Add measurements/evidence and dated state changes as work proceeds.

2026-10-14 checkpoint: K01 remains high. A public warm byte read costs 221 host CPU cycles in ALL_RAM mode, before address generation/decoding; span fetch/hot-path work is required. K05/K06 have stronger functional evidence from all-page/random/partial-failure cache tests and a native VICE eviction probe, but UCI/persistence/physical effects remain unverified. K14 now has a real device inventory (firmware 3.14, FPGA 121, core 1.47, enabled 16 MB REU); actual UCI behavior, active turbo speed and DMA timing remain open. Read-only discovery made no hardware/media changes.

2026-10-15: arithmetic, effective-address and stack functional coverage expanded; K12 remains open for traps, prefetch, undocumented memory forms and original hardware boundary corners. Faster host testing does not resolve K01 physical throughput. Host-memory failure can leave partially committed CPU/stack state and is currently terminal rather than retryable.

2026-10-15 strings/control checkpoint: functional CPU evidence now includes original shifts/Jcc aliases, bounded REP and software interrupt routing. K12 remains open for hardware IRQ/traps, REP interrupted-prefix behavior, segment-register inhibition and other timing corners. K04 remains high: no actual BIOS disk service or target DOS boot. Runtime CODE 6,094+BSS 137 remain inside link gates; future BIOS/storage/display still consume the host budget.


2026-10-15 CPU/BIOS/storage checkpoint: K04 now has actual native disk/bootstrap/query contracts and genuine unchanged reset→IO.SYS entry, but remains high: COMMAND.COM is unaccepted and the current first failure is PIC OUT 20h at 0070:2BFB after 2,335 instructions. Video/keyboard/clock BIOS, ports/events, native execution loop and UCI/IEC image import are still required. Tests seed a complete immutable image in REU; they do not establish target file loading or persistence.

K03 remains high. Current runtime CODE 9,702, RODATA 673, BSS 211 and the new C000–C0FF 256-byte range staging fit current gates. Only 45 BSS bytes remain before E100; additional resident code is limited to C100–CFFF. Future metadata/state growth needs explicit layout work rather than silently consuming alignment gaps or graphics memory.

K05/K06 have stronger independent evidence: all 720 CHS addresses, coherent range dirty/partial-page/error tests, complete raw DOS extent identity and native range probe in VICE. New physical range recovery includes 5,120 guest/source/destination bytes; physical Manual 64 MHz integrity and independent restored-byte/configuration comparison passed; calibrated timing remains absent. Guest disk writes remain volatile REU mutations. Ultimate/IEC transferred-count, persistence/reopen/export and failure recovery are still unverified.

K01/K02 remain high. Twelve real-assembly profile samples show warm register/branch cost 1,762.55 host CPU cycles/instruction and 20 KiB REP 1,081.19 cycles/copied byte before unmodeled DMA stalls. No physical timer/DMA calibration or XT benchmark ratio exists. Unlinked fetch optimization does not resolve this risk.

K12 remains open despite 2,555 pinned hardware cases: absent FE control forms, POP CS, BCD/remaining ISA, exact word-FFFF original-hardware evidence, asynchronous IRQ/traps, REP interrupted-prefix behavior and segment inhibition timing remain gaps. Corpus masks and unsupported encoding policies must be retained as scope expands.


2026-10-15 accepted fetch/PIC follow-up: K01 has measured target-cycle improvement (about 21% for warm register/memory loops, 10% stack and 18% multiply/divide), while large REP is nearly unchanged. Physical elapsed timing and XT ratios remain unmeasured. K04 progresses past PIC OUT 20h to absent INT 14h after 2,347 instructions; asynchronous IRQ/INTA, PIT/keyboard/CGA ports and complete BIOS remain required. Logical video/adjust/auxiliary-BIOS integration is under final verification. Its resident layout must distinguish linked DEVICECODE from MAIN padding and display startup zeros, and the optional UCI buffer must be charged before allocating remaining C000-window code.


2026-10-15 verified video/adjust/auxiliary-BIOS checkpoint: K04 advances to missing clock INT 1Ah after 2,542 instructions, with all kernel/raw extent bytes still exact and prompt false. Logical CGA state and absent serial/printer contracts pass, but the C64 font/renderer/keyboard, native execution/file transport, asynchronous events and complete DOS remain unfinished. Future clock/native-clock/keyboard/UCI modules are unlinked. The new runtime binary has no physical acceptance; unchanged standalone probe hashes preserve the earlier hardware evidence only.

K03 remains high: runtime linked usage is 16,758 bytes, while its 20,129-byte contiguous PRG includes 6,168 padding/startup-zero bytes. DEVICECODE occupies 5000–569F; DEVICESTATE EA00–EA3C has 61 bytes, with only 34 pre-E100 BSS bytes free. The optional UCI buffer is budgeted C100–C8FF, leaving 1,792 bytes at C900–CFFF. All ranges and file-versus-allocation distinctions are guarded by tooling. The new `video.inc` include still needs its explicit Makefile dependency in the following slice; current verified artifacts/hashes are pinned.

K12 has stronger evidence from 5,701 selected hardware cases, including 3,146 adjust cases and all 47 exact AAM-zero frames. Source gaps for REP adjust, original word-FFFF and event timing remain. K01/K02 remain high despite coherent-fetch gains: current warm register cost is 1,410.56 cycles/instruction and 20 KiB REP 1,082.04 cycles/byte before physical DMA/VIC costs; no calibrated XT ratio exists. K07 remains open because logical video service tests do not establish host readability.


2026-10-15 clock/keyboard/UCI and genuine DOS milestone: K04 now has actual COMMAND.COM, VER and exact 35-entry DIR/returned-prompt evidence in Peddle, with source/media unchanged. This resolves that functional boot uncertainty for the exercised image/path, not all DOS utilities or the native machine. Native startup still idles; file import/persistence, C64 font/VIC/input scan, asynchronous events and HD remain unfinished. Private file/render/overlay components are unlinked.

K08/K14: generic UCI async transport is linked and tested against its independent model, including saturated queue/status lengths, missed BUSY/MORE, backpressure, elapsed wrapping deadlines and abort recovery. Actual installed firmware file commands/import/persistence remain unvalidated. Native CIA2 time is linked, but the first physical Manual 1 MHz probe failed with error 3; 16/64 MHz calibration was not reached and no progress/turbo-independence calibration is accepted; do not derive deadline microseconds from host CPU polls.

K03: UCI now consumes the measured C100–C8FF 2 KiB buffer and leaves C900–CFFF (1,792 bytes). Current runtime DEVICECODE reaches 5E63 (412 bytes left) and MAIN ends 3AD6 (1,321 bytes left); unit MAIN ends 3EA6 (345 bytes left). Static control grows to 2,609 bytes with DEVICESTATE 147; pre-E100 BSS still has only 34 bytes. Final global maps confirm these allocations; linker validity does not resolve physical timer behavior. Code growth/overlay ownership needs explicit validation before additional private components are linked.


The failed physical clock attempt restored machine/turbo/media configuration and reset/resumed the C64U, but did not establish prior timer/NMI/CPU-state restoration. Preserve the original failure with unknown error-3 subreason. The runner now captures full RAM/mailbox/40-byte DCK1 before reset and the 16-line endpoint window uses ±1,008-tick bounds, but a successful physical rerun remains necessary before trusting native elapsed deadline conversion. Functional Peddle DOS success and native timer calibration are independent gates.


Corrected physical clock matrix: K14's raw CIA-versus-PAL-raster/turbo-independence uncertainty is resolved for firmware 3.14/FPGA 121/core 1.47 at Manual 1/16/64 MHz. Deltas 1,965,627/1,965,599/1,965,600 over 100 frames meet ±1,008-tick bounds with zero retries and 28-tick spread; configuration restoration/reset-resume passed. Native clock→scheduler/UCI deadline conversion remains unwired. K01/K02 CPU/REU/XT throughput, absolute-time fidelity and physical native DOS remain open. The initial error-3 cause remains unproven despite the corrected 1 MHz 8/8 post-read raster endpoints suggesting the former narrow window.

## Current overlay/dispatch boundary

Full 298/all 5,701 and exact genuine DOS equality resolve the integrated dispatch regression risk for the exercised profile; near-XT speed remains unproved. FILE/TEXT share one bounded window with tested failures, but assets are trusted immutable after bootstrap and native payload corruption is not CRC-detected. Unit MAIN 76 bytes/DEVICE 49 bytes make additional resident wrappers/scheduling a layout risk. Cold startup code must never be called after bitmap takeover. File READ/WRITE/CLOSE firmware limitations still require import CRC and reopen/read verification before accepting persistence; physical UCI and VIC/input/runtime remain unfinished.

The cold importer mitigates stale READ status with exact length/EOF/CRC, but is not yet connected to native startup or physically validated. Its 931 bytes include all recovery state and are destroyed by bitmap ownership. Do not release that lifetime while import is active; guarded resident gateways and native elapsed conversion are the next integration.


2026-10-15 physical native checkpoint: K04 now has actual real DOS boot/COMMAND.COM/VER/DIR onC64U Manual64MHz through native whole-file UCI, with exact media/code/output and recovered4MiB. K05/K08 gain direct firmware3.14 import/protocol/deadline evidence at64MHz; other speeds/fault recovery remain separately scoped. K06 gains full4MiB physical backup/delta restore/fullreadback but persistent guest image writes/save/reopen remain unaccepted. K07 remains open: physical80column bitmap bytes match independent narrow-font oracle, but external readability/input/40column evidence remains pending. K01/K02 stay HIGH: observed109second script includesRESTpauses/evidence and cannot establish XT throughput; newly integrated timer/CGA target is still physical-unverified.


2026-10-15 currenttimer/CGA integration: MAIN217/216andDEVICE54 leave little code headroom; HD needs measured relocation. Timercallbacks materiallyincrease hotpathCPUcost (NOP796 versus timer+NOP2141–5283); graphics idealcadencefloor~416msbeforecosts. Neither acceptedphysicalDOSobserverelapsed nor Peddleprofiles establishesnearXTthroughput. FixedPITports/directCGA unsupported; physicalnewtarget/input/readability/graphics/persistenceHDIEC remain open. Source-derivedNMOSinterruptbehavior lacksneworiginalsiliconcapture; keep evidencegap explicit.


Physicalnew5run080121 fails180secondfunctionalobservationbudgetwhilefullnativefile4MiBrecoverypasses. Journalsshowmaterialguest-pausedobserverduty,butdonotisolateinterpreter/PIT/MMIO/REUcost; noXTspeedratiofollows. Optional2s/360stestbudgetneedsafresh-backedretry,notreclassificationofoldfailure. RawRESTlowportbytescannotproveCPUbank; hostshadowproofmustusesource-to-runidentityandscopebankingevidenceseparately.


2026-10-15 six-overlay HD/scroll: K03 remains HIGH despite successful fit: MAIN115/114,DEVICE22,cold1093/118,shadow1440tail,BSS33pre-map. Runtime expansion must charge real windows. K10/K11 now have forced-cache,complete2/20MiB nativeDOS andabove16MiB addressing/reopen mock evidence; physicalHDremainopen. K15 geometry uncertainty is resolved for actualsuppliedDOSBox-XFDISK/FORMAT/SYS/CHKDSK fixtures, not arbitraryDOSversions. K06 requires preserving newly authoritative uncertainREU350000sector/handoff352000 before restoringoldbackup.

K01/K02 remain HIGH. Actual nativeDOS profile has1169895754CPUstepclocks/601936calls and60.32%memory/fetch/address;658267timer callbacks cost873806129inclusiveclocks withREPoverlap. Broadregister-onlytranslator's idealzero-costceiling is only1.081×thisdiagnostic harness. Nextowned-clockABI experiment retains everyIRQ/REPboundary; no physicalspeedratio is established. IECtrapcoldimportprivatefourcaseproofawaitsreview; K09truedrive/serial remainsseparate.


2026-10-15 MODE: physical CO40/CO80 framebuffer/code evidence now passes. External readability and human matrix input remain open. First native restore protocol failure before DMA required a second attempt; cause is unknown because declared reply lengths were zero. Both attempts and all4MiB final equality are retained.600seconds is configured per attempt, not a global two-attempt guarantee.


2026-10-15 combined boundary optimization: shadow headroom decreases1440→1223, PIT tail130→128; MAIN/DEVICE/state unchanged. K03 remainsHIGH. ModeledDOS CPU cost falls8.8%, but C64U elapsed and XT ratio remainunproved. Full5701whole-PRG/longHD/physical proofs remainold98fc; newtarget has421default/597quick/nativeDOS/MODE/focusedHD evidence. Every existing sampling boundary is retained.
