# Additive lessons log

## 2026-10-14 — planning inspection

1. User clarified target language to 6502 assembly and separately reinforced Zig behavior assertions. This supersedes the planning-stage C/ZeroPage possibilities before any target code was written.
2. Three images are all 360 KiB FAT12. Disk 1 and disk 3 have matching system-file hashes but different config/boot metadata. OEM text does not establish runtime DOS version.
3. Disk 1 refers to a non-existent initial C: installation; plan original-behavior and minimal-config boot lanes separately. Never edit the original to conceal a fixture dependency.
4. Existing Peddle shims provide a useful starting point but not a complete REU/banking/timing model. ReuSQL64 wraps REU addresses by capacity; ZeroPage truncates. Neither behavior can be generalized without device evidence.
5. Ultimate prose docs and inspected upstream code differ on REU transfer length masking. Actual transferred count and installed firmware must govern correctness.
6. A complete bitmap layout must satisfy VIC bank relationships and alignment, not just fit 64 KiB. The proposal places matrix 4000 and bitmap 6000 in bank 4000–7FFF.
7. Parent .gitignore ignores working-record directories recursively. Project-local override is necessary if these planning/continuation records are to be tracked, while scratch/runs stay ignored.
8. DOSBox-X was already installed. Version detection was performed; no guest run or emulator benchmark occurred in planning.
9. D81 SEQ roundtrip was verified using c1541. Its directory output can contain PETSCII bytes and must not be assumed UTF-8; this initially broke the research wrapper, not the container bytes.

## 2026-10-14 — M0 implementation

1. The first runaway fixture hung because Peddle `executeInstruction()` leaves `clock` advancement to the embedding application. Stopped that specific test process, changed the bridge to bounded per-microcycle stepping with explicit increments, and added an exact 8-cycle LDA/RTS assertion. All 10 Zig tests then passed.
2. DOSBox-X works with SDL dummy video/audio for automated reference boot. Copy AUTOEXEC into the disposable image before BOOT, then capture guest-written VER/DIR/DONE from the FAT12 image. The original config remained and the guest reported MS-DOS 3.30.
3. DOSBox-X did not exit promptly on SIGTERM in this run; the wrapper killed only its own process after a bounded wait. The captured files were already closed and verified; this is a functional boot baseline, not clean-shutdown evidence.

## 2026-10-14 — REU primitive and reference investigation

1. A descriptor at E000 cannot be read through KERNAL ROM. Establish RAM/I/O mapping before any request access; restore it after storing status/error. Tests invoke the routine with KERNAL initially visible.
2. Expanded REU increment wraps its low 19-bit REC counter with upper bank latches preserved. Split requests at 64 KiB banks and make higher-level range handling explicit.
3. First VICE attempt failed plan-schema validation because global retry_policy was missing. Adding that required field allowed the run; this was not a target probe failure.
4. A success mailbox is weak evidence alone. Compare every captured byte independently and associate results with captured executable bytes so an old run cannot validate new code.
5. The shared VICE harness selects 16 MiB REU. A successful low-address probe does not prove a 4 MiB configuration; the fast model covers 4/8/16 MiB separately. Physical capacity/firmware/timing remain outstanding.
6. Search hits often describe the opposite direction or independent desktop CPU emulators. NES86 is a verified 6502-hosted 8086 core; Appler runs 6502 emulation on an 8088. Record direction, CPU profile and license explicitly.

## 2026-10-14 — coherent memory implementation

1. A failed new-page load may have overwritten part of the victim's host buffer. Write back dirty data first, remove old ownership before loading, and publish the new tag only on success. On write-back failure retain the dirty old owner. Prefix-transfer fault tests exercise both orders.
2. The first test pass attempt had 38/39 passing; the flag test incorrectly expected 28 after masking P with 0C. The target returned the correct 08. Corrected the assertion, preserving the decimal/interrupt check. Target flag behavior did not require a fix.
3. Import zero-page assembly symbols with `.importzp`; a regular import produced a linker address-size warning and unnecessary absolute-address instructions. Fixed the interface before the successful full run.
4. Distinct pinned-page and replacement-page patterns matter. All-zero buffers could conceal accidental frame reuse even when a retained pointer still reads zero.
5. A direct page map consumes 2 KiB before descriptors. Current BSS/map/frame metadata total 2,302 bytes, leaving 1,794 bytes including alignment gaps for future storage/control needs.
6. Successful VICE eviction across a REC seam strengthens the mock evidence but does not measure physical stalls. Warm public byte reads already cost 221 host cycles, so future instruction fetch must exploit spans rather than call the full bus API for every byte indefinitely.
7. C64U physical discovery succeeded through a Terminal-owned read-only client. Firmware is 3.14; the speed field is 64 but register-controlled turbo means the field alone does not prove current speed. Preserve actual configuration and overwritten REU bytes before a test program.

## 2026-10-14 — physical recovery and firmware options

- Native backup/restore, independent REU re-read and configuration comparison made the failed first physical attempt recoverable. Keep these before/after checks for future hardware tests.
- Firmware speed options can contain leading spaces. `1` produced HTTP 400; ` 1` is the advertised valid value. Normalize only for matching, then send the original advertised string.
- A successful physical integrity matrix does not measure effective elapsed CPU/DMA throughput. Preserve that distinction in results.

## 2026-10-14 — first instruction execution

- Keep IP wrapping, segmented word-byte address calculation and physical 1 MiB wrap separate. Hardware data at FFFE does not prove a word beginning at FFFF; disclose evidence gaps.
- Long prefix streams need bounded host work without inventing a modern 15-byte guest limit. Preserve pending decode state and instruction counts across prefix yields.
- Full 1 MiB RAM comparisons caught the scope of each hardware case, including bytes expected to remain unchanged. Separate the six-second development lane from the 26-second broader corpus run.
- Isolate physical probes from the evolving execution module so CPU-only changes do not invalidate or require repeating unrelated hardware tests.

- A Zig 0.16 readFileAlloc limit equal to the file length produced StreamTooLong in the new boot fixture. Use bounded headroom and assert the expected image size separately.
- Keep full-RAM comparison coverage when improving host test speed; test the comparator's mismatch and bounds paths independently.


## 2026-10-15 — execution expansion

- Original-8088 hardware vectors include undocumented opcode-extension aliases. C7 first row uses /6; rejecting every extension except /0 caused a real conformance failure. Preserve evidence and implement the observed alias, rather than remove failing vectors.
- A decoded operand must survive later immediate fetch and eviction. Store its segment/offset, not a transient cache pointer.
- REU banking preserves DDR/output bits, not necessarily raw input-bit latches. A stack test expected raw $01=35 after DMA but saw F5; assert the established output-bit contract.
- Batching host instruction stepping helps, but compiling the host Peddle engine with optimization is the larger test acceleration. Verify exact target clocks, all memory/write markers, failure precedence and diagnostics before using the faster runner. This does not accelerate the C64 target.
- Explicitly set make's default goal when adding generated-file dependencies before the main target; otherwise a prerequisite can become the default build.


## 2026-10-15 — strings, branches, shifts and interrupts

- Original8088 /6 shifts are SETMO/SETMOC, not later SHL aliases. Follow original hardware vectors and metadata; original CL counts are unmasked. All new functional gates passed on their first execution.
- A host REP yield is not a guest interrupt: retain decoded prefixes/opcode across scheduling and count only a completed instruction. Original multiple-prefix interrupt restart requires separate event work.
- Compare an entire completed hardware string instruction, not one scheduling slice. Keep both per call and aggregate cycle/call budgets, and record maximum slices (currently 8).
- INT/IRET must use guest IVT/stack and preserve mutable hooks; capture a reference-derived IVT target before overlapping stack writes. Test a normal guest handler modifying saved flags, not only a native callback.
- A plain IRET fixture is useful CPU evidence but provides no BIOS disk service. Record real INT 13h entry and the subsequent missing CBW separately from target boot acceptance.
- Freeze owned files after signaling integration readiness; extra assertions arriving after a global run require explicit revalidation and consistent manifests. Three material subagents were coordinated with parent integration/review in this slice.


## 2026-10-15 — math, indirect control and genuine storage bootstrap

- Original-8088 math policy differs from later x86 at signed minimum quotient and divide saved IP. Keep zero-divisor, REP IDIV, minimum-quotient and PUSH SP alias rows pinned; no REP MUL/IMUL/unsigned DIV source rows exist at this corpus pin, so label independent coverage correctly.
- Capture indirect near/far targets before stack pushes when pointers and stack overlap. XCHG must preserve the original decoded EA while replacing a base register; POP memory must retain its decoded destination across stack reads/eviction.
- Coherent range import must merge through the guest bus so dirty neighboring bytes survive. Export must read dirty cache authority. Direct REU overwrite followed by cache flush would resurrect stale data.
- The range bounce added a genuine layout allocation: C000–C0FF. The memory gate caught a missing RANGEBUFFER reservation, forcing the complete host map and resident budget to account for it. The extra resident-code window is now C100–CFFF, 3,840 bytes.
- Adding a privately compiled, older object to a Makefile's link list did not trigger relinking when prerequisites omitted the Makefile. Fixed link prerequisites; verify maps and final binaries after changing the object set, not only build exit status.
- A host FAT12 oracle initially counted only the rounded IO.SYS file length (44 sectors); the actual unchanged bootloader reads 51. Preserve and compare the complete raw extent, all padding and overread, rather than changing the guest or relaxing checks.
- BIOS native callbacks must be physically whitelisted at the owned ROM opcode, not merely a port number or INT vector. Ordinary INT/IRET and PUSHF/CALL FAR chaining prove real guest hooks and saved carry behavior.
- INT 11h/12h queries read mutable BDA through normal guest code, including dirty resident bytes. INT 15h on the XT returns unsupported AH=86h/CF=1; pretending an AT configuration pointer exists would send this real kernel down the wrong branch.
- Physical range recovery must cover all three touched envelopes, 5,120 bytes total, not only the previous cache probe's guest 2 KiB. Six descriptors explicitly split bank seams; restore failure can write a prefix, so retry the whole owned snapshot and independently re-read it.
- Real reset→boot sector→IO.SYS handoff is accepted independently from continuation. The next missing PIC OUT 20h at 0070:2BFB is retained rather than faked. Kernel entry and a passing integration test do not establish a COMMAND.COM prompt or native startup/media loading.
- Real-assembly profiles establish a costly pre-optimization baseline (warm register/branch about 1,762 cycles/instruction; 20 KiB REP about 1,081 cycles/byte). Report caller/setup/validation/DMA/VIC/physical exclusions. Unlinked optimization files are not evidence of an optimized runtime.

- 2026-10-15: A fetch optimization must survive one-frame operand eviction and cold cache reset, not merely sequential reads. Compare the entire guest state after each instruction and full RAM at completion against the prior assembled path. Profile short-loop and large REP separately: faster fetch reduced the former substantially while large REP changed negligibly.


## 2026-10-15 — resident logical video and auxiliary BIOS integration

- Moving logical video code to DEVICECODE at 5000–5FFF preserves the 4000–4FFF screen/font and 6000–7FFF bitmap reservations. A contiguous PRG needs MAIN padding and explicit 4000–4FFF startup zeros to reach that code; those bytes must not be reported as linked executable allocations. Standalone hardware configurations/binaries remain separate.
- New mutable scratch belongs in the bounded EA00–EEFF DEVICESTATE allocation rather than overflowing scarce E000 pre-map BSS. Keep CACHEMETA bounded to E900–E9FF and reserve EF00–EFFF; count the conditional future C100–C8FF UCI buffer before promising C000-window code headroom.
- The first combined quick gate exposed two test-fixture mistakes, not target failures: the old unsupported-opcode sentinel D6 is now valid SALC, so the test uses unsupported input port FE instead; a new BIOS gate loop wrote REU backing behind a live dirty cache, so its guest code writes now use the coherent memory API.
- Original XT zero serial/printer base checks precede AH dispatch and preserve AX. A missing device is not a timeout; retain unchecked wrapping DX indexing and fail explicitly for a present-device contract that is unimplemented.
- Logical video mode/page/cursor/scroll/pixel/teletype tests prove BDA/VRAM behavior. They do not prove host fonts, rendering, keyboard input, retrace timing or physical readability. Native POST initializes mode 3 coherently while preserving guest AX.
- Original adjust hardware corrected an AAM-zero flag expectation before acceptance: SZP reflects zero while AX stays unchanged and INT 0 saves the post-immediate IP. Keep undefined-flag masking scoped to actual hardware metadata and disclose source gaps for REP AAM/AAD.


## 2026-10-15 — genuine DOS prompt, VER and DIR

- A later SYSINIT port stop at 9DFD:0A53 was legitimate original relocated code. Binary span/relocation audit plus Microsoft inherited DOS 3.30 comments identified arbitrary-byte GLOBAL REARM writes at 02F2h–02F7h. Preserve narrow absent-board behavior, not blanket unknown-port success.
- The private fast/slow fetch comparison matched every state for 55,583 calls and all coherent conventional/CGA RAM. That rules out regression against the prior fetch path, without claiming universal CPU correctness.
- Original clock AH behavior includes decrementing all nonzero functions, unnormalized sets, full overflow-byte read/clear and equality-only midnight. Native elapsed time and asynchronous ticks are distinct integrations.
- Original keyboard AH=01 loads AX even when empty and exposes exact RET2/CMP flags. Empty AH=00 must retain its guest frame and retry the exact owned OUT without counting completion; key enqueue and host input scanning are separate.
- Separate the short default kernel-handoff test from opt-in interactive DOS acceptance. Ten keys through actual assembly drove the original date/time prompts, VER and DIR; exact names/sizes/count/free bytes plus a returned prompt make a stronger milestone than seeing a substring once.
- The first real COMMAND prompt is at 193,673 instructions; complete VER/DIR/return acceptance takes 588,937. Do not relabel early IO.SYS entry or intermediate screens as the full built-ins proof. Keep CPU-step/support/setup clocks separate from physical elapsed time.
- Generic UCI DONE only completes transport. Streaming/backpressure, saturated FPGA queue limits, stale-state abort and elapsed recovery are required before the separate image-file operation/status/persistence layer can be accepted.
- A CIA counter's unit is phi2, independent from turbo CPU instruction cycles by design but still requiring physical evidence. Destructive timer/NMI ownership cannot be reconstructed from readback; reset/resume is not prior program/timer-state restoration.

- The first physical CIA/VIC clock attempt failed at Manual 1 MHz with error 3 while configuration restoration/reset-resume succeeded. Preserve the failure and fix capture-before-reset diagnosis; functional model/probe success cannot stand in for clock-domain calibration. No 16/64 MHz or timing result follows from a matrix that stops at its first speed.
- Working-tree tooling includes five tests for an unlinked future overlay package. Count the accepted 69-test commit scope separately from the 74-test working set; passing package tooling does not mean a resident overlay runtime is linked.

- Pre-commit clock diagnostic correction: capture full RAM/mailbox/40-byte DCK1 before cleanup resets the evidence. The first error-3 subreason remains unknown. The updated probe's 16-PAL-line endpoint window permits ±1,008 raw ticks, independently checked; six Peddle tests/15 tooling checks do not imply a physical pass. Three added diagnostic cases raise selected feature tooling from 69 to 72 and the working set from 74 to 77 (five unlinked overlay-package tests remain excluded).

- Corrected physical matrix passed all three speeds within independently derived 16-line bounds. This validates raw CIA/raster domain and observed turbo independence, while native deadline conversion and throughput remain separate work. The new 1 MHz 8/8 endpoint observation is a plausible explanation for the first narrow-window failure, not proof of its missing old subreason.

## 2026-10-15 — overlay and dispatch integration

- Measure a real DOS workload before changing dispatch. Preserving the opcode accumulator at family entry is part of the internal ABI; the original unchanged kernel oracle caught the omitted reload in the private prototype. Full hardware cases and complete screen/register/RAM equality then accepted the integrated change.
- Separate linked variant totals, maximum simultaneous overlay bytes, resident file bytes, startup assets and zero padding. Summing two mutually exclusive payloads as permanently resident would misstate the available host RAM.
- Save/restore observable 6510 DDR/output bits. Input-configured port bits are not readable copies of the output latch; exact hidden-latch assertions can reject correct hardware behavior.
- Source freeze plus independent artifact hashes lets full corpus, genuine DOS and profiles run concurrently without racing build mutations. Host wall time from that concurrency is not target throughput.

A run manifest must be generated after every artifact-producing prerequisite, including isolated hardware helpers. A correct native binary does not make an earlier helper-map identity current. Cold startup code/state is another lifetime: exact loaded bytes and zero tails need verification, and a resident publication flag must protect partially loaded media.

- Startup-only memory needs an initialized resident phase guard; checking overwritten cold state cannot prove lifetime. Commit assets that overlap future cache frames before any BIOS/cache access.
- A jointly linked overlay must validate and DMA its complete canonical member sum; a renderer-only length silently omits following VIC code.
- Eighty-column legibility needs a designed narrow font; OR-compressing every full-width glyph loses distinct letters. Keep licensed sources, byte hashes and physical readability separate.
- Establish RAM banking before reading resident outputs under KERNAL ROM; the elapsed adapter owns that precondition rather than relying on its caller's mapping.


2026-10-15 native runtime: convert blink bits to strict0/1 at the target ABI, and exhaust all256 phases. AH01 polling need not set the BIOS AH00-wait flag; coherent periodic observers must still find prompts. Match pagination at the active cursor, not stale scrollback. A normal BIOS scroll can cost>3M CPU cycles; retain bounded measured budgets instead of assuming opcode-sized work. Keep cumulative Peddle clocks separate from incremental external phi2 modeling. Retain KERNAL until the RAM NMI vector and CIA masks are complete. A REST upload failure before PRG load is not native execution; independent settings equality is not full REU restoration. Preserve original failure reports and never delete unknown firmware Temp files to make a test pass.


2026-10-15 physical transport: measure request throughput before committing a multi-megabyte recovery path. Four/eight concurrent requests did not improve a serial firmware server. A file loader that correctly copies16KiB can still cost~2seconds per reset; extrapolate full-workflow work. Full readmem captures can include changing IO while CPU is paused; compare RAM ranges and exact payloads without calling volatile observations corruption. Never execute a known-over-budget restore merely to confirm the estimate.


2026-10-15 recovery/codeidentity: optimize restoration by detecting unchanged data, not reducing protected scope. Every attempt must rescan all bytes after partial failure; unexpected alias changes need a test. Validate explicitly located self-modified operands and their allowed buffers rather than exempting an entire code segment. ca65 global export assignments reset cheap-local scope; scoped routines/local labels plus external export aliases can retain byte-identical target code. Confirm hashes after rebuilding, never rely on stale artifacts left by a failed compile.


## 2026-10-15 — timer/graphics promotion

- Separate a host REP work quota from guest interrupt boundaries:16elements percall can still callback aftereveryeligibleelement. Check last-element/comparison ordering and original restart frames explicitly.
- BDA timer updates belong to executed guest BIOS code. A period counter and guest tick counter differ when PIC requests coalesce or guest hooks replaceINT08.
- A private full gate can be reused only with exact reviewedsource and executable identity. Root integrated lanes and independent adversarial boundaries still test composition; no blanket reuse after code changes.
- Unit helpers can occupy cold space only with host refusal before stack/register mutation and a resident return sentinel. A total memory budget cannot prove per-window fit.
- Returning from graphics must reapply TEXT settings without replacing the saved original VIC owner. Keep physical bitmap correctness distinct from externaldisplay/readability.


## 2026-10-15 — real DOS file workflows

Directory deletion is a logical FAT/root change, not erased sector slack. Verify live names, allocation and original data independently while allowing freed data to remain. Long commands must refill only available slots in the real15-keyBIOSring; coherentPAUSED must transition throughRUN beforeKEY. Supplied MODE probes later BIOS functions before selecting an XT mode: preserve first failure and inspect originalXT unsupported-function return behavior rather than inventing VGA support.


## 2026-10-15 — source-complete whole-file recovery

A CRC-success flag is insufficient restoration evidence: bind the configured PRG to an immutable backup and fresh owned file, require new startup/knownCLOSE/counters, then independently compare every restored byte. Keep one deadline across FTP/native/reload/compare; never turn per-step bounds into unbounded total time. Source-complete helpers with fixed reviewed output hashes permit fast path/host changes without rerunning a five-minute native test when executable/core bytes remain exact. Physical test recovery must use a fresh snapshot of current REU state, never a prior-run backup merely because it already exists.


## 2026-10-15 — physical recovery and observer duty

Coherent screen inspection pauses guest execution across several commands. Measure those intervals before treating end-to-end observer wall time as emulator throughput. A command bounded by min(overalldeadline,12seconds) may have no remaining wait budget; retain both deadline scopes and inspect captured completion rather than calling it a nativehang. An application can fail while complete independently checked restoration succeeds; preserve both statuses. Raw REST RAM0000/0001 is not a trustworthy live6510CPU-port view. Source/guard/functionalexecution and a separately trusted diagnostic must be distinguished from those DMA bytes. Every tool command needs an explicit private workdir: agentcontext alone doesnot change the shared defaultcwd.


2026-10-15 HD promotion: source/linked/runtime identity are separate. Compare every linked source and both whole PRGs before reusing slow corpus/boot evidence; review build dependencies even when initial binaries match. Copied executable expectations must come from immutable packaged bytes, never the live cache source. REST full-RAM bytes at6510 portaddresses are underlying RAM, not trustworthy live DDR/data registers. Preserve newly authoritative uncertain HD writes before restoring the pre-run REU snapshot.


## 2026-10-15 — physical MODE and retry evidence

Use the recorded restoration attempt count when selecting final readback files. Preserve every failed attempt before overwriting helper RAM. A status buffer with declared length zero is stale, even when its bytes resemble a useful firmware error. Check executable/diagnostic equality separately from changing I/O registers in repeated RAM captures. A successful retry establishes final restoration, not the cause of the first failure.

Freeze complete source/artifact input bytes alongside hashes before later target changes. That preserves historical physical proof without pretending an old unit or hardware binary identifies the new target. Distinguish observed total restoration time from a configured per-attempt bound.


## 2026-10-15 — cleanup cannot depend on well-formed evidence

An optional evidence worker must not let interrupted waits, serialization errors or malformed results bypass recovery. Reap the child in all paths and independently validate artifacts in the parent. Preserve partial accepted bytes before publishing progress. A RAM-first collector only guarantees order relative to its own helper; bind the earlier application capture explicitly if another evidence path has already replaced native code.


## 2026-10-15 — combine measured optimizations without changing policy

Compare the combination directly: savings from separate changes can interact through flags, scratch registers and clock-derived guest timing. Keep fixed-clock state differentials separate from workload cost comparisons. An unchanged CPU ISA source is useful retained evidence, but it does not make an old whole-PRG hash identify a newly linked executable. Refresh source-bound application proof bundles when target bytes change.


## 2026-10-15 — alarm evidence needs a boundary invariant

Final RAM observations do not timestamp interrupt assertion during DMA. An arithmetic early-alarm inequality only holds with a proved hardware overhead premise and correct latch/start semantics. Phrase emulator safety at eligible guest boundaries, including every DMA return path. Keep full sampling until hint readiness or an unconditional fallback is proved at every due boundary.


## 2026-10-15 — local monitor ownership and build products

A reserved localhost port and live child do not prove that the accepted monitor belongs to that child. Prove the accepted connection's exact endpoints/PID before every command, and send no cleanup command when ownership is lost. A stamp file does not prove all generated outputs still exist: validate every output and input on explicit build invocation. Preserve valid products without unnecessary regeneration.


## 2026-10-15 — final audit means completed execution

Do not freeze a proposed expanded assertion count as a passed audit before that exact harness finishes. Preserve original executed source/output before extending a verifier; label reconstructed or overwritten-harness records as chronology. A provisional report can be withdrawn without discarding valid earlier checks, provided both provenance and limitations remain explicit. New raw independent rederivation should bind immutable inputs and report only its actually completed checks.


## 2026-10-15 — file success needs reopened content

A successful firmware WRITE can hide a short transfer, and CLOSE can discard underlying errors. Keep REU authoritative until complete native reopen/readback/EOF/knownclosure succeeds. Lost replies remain uncertain even when a model independently sees committed bytes. A source-complete engine with caller ownership attestations is a prototype until actual runtime leases, clock and UI enforce those conditions.

- A reusable capture oracle must reject inconsistent BDA page size, page offset and mode-dependent palette before indexing, even if the original execution test independently checked those fields. Preserve genuine raw capture proofs and regression-test corruption of both bytes.

- Disaster recovery must retain the established attachment-free FtpPutClient even when using original DRS1/DeltaService. BareClient POST memory/config routes fail on this firmware; a mocked entrypoint review did not establish transport compatibility. Separate successful disaster restoration does not change a failed application-run result.
- Put dependent final checks and launches in one checked Python sequence. A shell newline can launch after a preceding guard/read fails; the frozen launcher must independently enforce every input, its own identity and exact host/output.

- Validate DOS pipe live temporary listings separately from final cleanup; retain actual bytes/SHA and permit only deleted-slot/originally-free-cluster residue with exact original allocation, metadata, content and slack.
- Seal source review, physical preflight and postrun logs in separate directories; a reused validate-only stdout path can destroy historical evidence without changing executable inputs.

- 2026-10-15: Two local video implementations disagreed on nibble order. Actual known C64 ROM glyphs established low-first across383,616 pixels. Preserve the original incorrect decoder/video rather than rewriting historical proof. On this Mac Python3.9 monotonic_ns has process-local origin; explicit clock_gettime(CLOCK_MONOTONIC) is required for cross-process ready age and game chapter alignment. Validate clock identity and interval in every chapter consumer.

- 2026-10-15: Genuine GW-BASIC exposed originalXT PPI61, fixedPIT40reload and absentgame201 probes. Implement boundedprimary-source device semantics, exhaustivelyreject unsupportedwidths/highaliases/data beforeeffects, and test actualDOSloadedEXE. CP437FF in GW-BASIC Ok is a blank glyph: normalize only observertext, retainrawCGA/renderedbytes. SourceLISTpages can independently prove all37lines rather than trusting a hostgameimplementation.

- 2026-10-15: A .25s screen interval actually yielded about1.1s of pausedguest observation work per sample, reducingdutycycle andprojectingpast thegamebudget. Phase-based cadence mustaccountforhardwarecontrolcost; actualVICrecordingcontinuesindependently. KeyboardInterrupt canbypass exceptException whilefinallyrestorescorrectly, leavingrawrunningstatus; retainoldraw andfixtruthfulcancellationreportingonlyinnewsuccessor.


2026-10-15: A failed Ultimate OPEN followed by failed transportrecovery can leave a genuinely uncertain ownedhandle even when externalREU/settings/reset recovery succeeds. Capturedfiles_op=CLOSE does not prove CLOSE was sent; inspect actualcommand/upload/drain counters. Retain firstprotocolstatus before recovery overwriteslast_status. Use protocolchallenge/response research and explicitownercontext; never replace readiness withfixedsleep or accept staleempty/84OPEN replies. Paired reviewedperformance changes composed byteexactly and passedroot428tests; strongesthelpergain35% is notwholeworkflowgain8.54% orhardwareXT speed.


2026-10-15 actualUCI diagnostic succeeds despiteearlierstartupfailure: verifiedclose/read-onlyopen/exactsector/knownclose resolvesownedcontext only. A separatePRGsuccess doesnotestablishreadinessafteranotherreset. FourlegitimateSMCoperandbytes mustbevalidatedasownedpointers, notexcludedwithoutbounds; reviewcaught0000falsepassbeforehardware. CancellationneedsboundedRAMcapturebeforeDRShelperoverwrite aswellasrecovery.


2026-10-15: A first-error recorder attached only to transport recovery misses validation failures before transport acceptance. Preserve raw ID and pre-start failure state as distinct diagnostic fields. Current error and zero upload counters can localize rejection without identifying the failed hardware read.


2026-10-15: PhysicalcapturemayexposeROMafteranativeproberestores37. ArawPeddleRAMpeekmodelcannotestablishthatmappedcapturecontract. KeepterminalRAM+IOowned35untilstrictcapture, recordincomingbank separately, andleavefinalreset/bankrecoverytotheexistingouterharness. Neverwaivetheactualprivatevectorcheckorrelabelfailedcaptureasaccepted.

2026-10-15: A matching DMA destination already present before a run cannot prove that transfer completed. Preserve first/raw status; issue DMA once, require observed completion, never turn data-only evidence or guessed delays into success. Keep generic recovery bytes intact when adding a native-only policy.

2026-10-15: A user reboot can end an interactive callback and invalidate its old mounted-media baseline. Retain that cleanup failure; separately recover the original immutable REU backup against the user's new baseline. When all256 chunks differ, the slow inline delta writer exceeded both600s attempts; original byte-frozen whole-file recovery passed in167s including full compare. Use the already verified whole-file path for known complete restoration rather than repeatedly exhausting a delta path intended for sparse changes. Never infer restored memory from reset or a success-looking intermediate progress status.

2026-10-15: Trace a timing counter through the complete language boundary and execute a two-call control before changing accounting. A Zig register struct with cycles0 did NOT reset the actual C++ counter; setRegs ignores those fields. The mistaken subtraction withdrawal and its mistaken numerical successor are preserved, then explicitly superseded by actual cumulative-counter controls. Physical fixed-work clocks and model loop counters remain separate evidence.

2026-10-15: Whole-image write count and reopened exact length are insufficient SAVE acceptance. Actual hardware produced720 repetitions of an unrelated512-byte pattern despite the modeled SAVE pass. Full comparison rejected it, and independent FTP corroborated the failure. Preserve authoritative changed media before restoration and keep native verification failure distinct from successful recovery.

2026-10-15: Installed hardware separates aligned512 WRITE corruption from successful2x256 buffering even withCPU-filled command bytes and exact upload/ECHO. Generic transport success and count/status acknowledgements do not prove file-write correctness. Reopened native reads and independent retrieval are both required. Retain conditional firmware-address explanation separately from empirically verified mitigation; physicalwhole-imageSAVE remains its own gate.


2026-10-15: Actual CPU-filled pairedWRITE proved512 corrupt/2x256 exact, independently before and after recovery. Promote only the reviewed split exporter; full360KiB SAVE comparison remains separate acceptance. Half-progress coordinates apply only during WRITE phase2/3.


2026-10-15: Do not convert a pre-import UCI ID failure into a SAVE regression: guestcount0/uploadpos0 distinguish it. Record live native DDR/port at the actual ID boundary; raw REST RAM addresses0/1 do not establish banking. If no SAVE was attempted, missing-output FTP550 remains honest but must not prevent separate complete post-recovery input/OWNER closure.


2026-10-15: A wide BEFORE/AFTER arm bracket can hide STOP visibility delay. For START-relative K support, compare STOPupper+guard with BEFORE+count+K; for violations use AFTER. Finite inconclusive observations cannot certify an installed universal bound. Native terminal DDR/port publication must precede completion; rawREST RAM0/1 remains diagnostic.


2026-10-15: A timestamp-valid .pyc can run before bootstrap disablescache in a fresh child. Configure source-only import before FIRST project import in every production child. Distinguish generated proof outputs from executed inputs beforeattestation; a random temporary pathname does not change semantics, but firstclosurefailure mustremain and a fresh declared-output replay closes the corrected scope.


2026-10-15: Guest-step success with transientHC_SAMPLE4 is not proof that deferred time is reconciled. Retain debt/lastaccepted epoch until a valid source sample; require a settled fence before ownership restoration/SAVE. A successful later catch-up cannot retrospectively authorize an earlier observable fence. Private model cost gains stay measurements when new correctness controls fail.

2026-10-15: A shell cwd must be asserted in the SAME tool invocation as every private build. A previous cd in a separate invocation does not persist. During a physical freeze even generated metadata is immutable. Preserve mismatches and complete hardware recovery before restoring reports; repeat with a fresh owned fixture rather than retroactively accepting altered input closure.

2026-10-16: CPUunsupported at OUT does not identify a missing ordinaryhardwareport until CS:IP and exactport are decoded. SyntheticF000:0150/F3 gate plusAH0B proved an unsupportedBIOSvideooperation in the humanGW-BASICfailure. Keep originalruntime/alloverlayidentity and coherentfullRAM beforehelpers, then run oldnative negative and independentBDA/VRAM envelope tests.

2026-10-16: Explicit toolworkdir alone is easy to omit when adaptive scriptsmixROOT andprivate paths. Allprivatebuildcommands nowalso assert exactPWD beforeMake/Zig in sameinvocation; Zigsearchesupward ifno build.zig. Preserve mistaken invocation/log and assessactualchangedproducts. CurrentincidentsonlyregeneratedignoredROOTbuild/cachemetadata, exactnative44d54/2635 and recovery388069 unchanged, noROOTsourcereset needed.

2026-10-16: Protect budget installation as well as restoration. An exception in a finally-block property setter can replace the original cancellation and skip reporting before outer recovery. Reproduce the exact first-object loss, then assert bounded independent local restoration/reporting, exhaustion truthfulness and preserved original exception identity. Test application and retention boundaries separately.

2026-10-16: An independent FTP read of a still-open backing image can expose an incomplete DOS directory entry even after DOSCHKDSK passes. Retain the preclose image, then explicitly nativeCLOSE/reopen before inspecting persistence. In this run, FAT3391→3392→FFFF was visible while rootHELLO.EXE had cluster0/size0; postCLOSE the entry was3391/2224 and all strict checks passed. Native readbacks plus full independent postclose/postrecovery images establish a narrower, reviewable claim than assuming each open-handle snapshot is durable.

2026-10-16: A GitHEAD does not identify a concurrently modified source tree. Promotion graph generation raced ROOT's raw candidate copy and duplicated Zig declarations while dropping earlier additive targets; make build reproduced nativebytes without parsing the Zig graph. Preserve exact pre-copy authority, merge only required additions, then execute the affected graph targets. Record the rejected graph/proof honestly.


2026-10-16: Nested host dependency capture must include non-Python assets; exact97-file inventory exposed seven omissions. Source-only checking must precede bootstrap imports because -B can load existing poisoned bytecode. Pending keyboard commitment after release must not mark a key held unconditionally; ordinary/Fn old-target controls exposed an inherited suppression bug. Keep rejected seals and author-versus-independent replay labels separate.


2026-10-16: Copying reviewed files with preserved mtimes can make incrementalmake reuse older incompatibleobjects. The cursorcompositionfirstlinkfailedmissingnewexports; touchingall25promotedfiles without changinghashes forcedproperrebuild. Preservefirstfailure, verifyfullnewpair, and usefreshmtimesorcleanprivatebuilds whencomposing sealedsource.


2026-10-16 installerresearch: distinguish DOSfreeclusters, hostfileallocation and zeroedcontents. Our20MiBrawC isfullallocated anddeletedCROSS16patterns remaininfreeDOSclusters; seekingtogrowFatFsalso doesnotinitializegap. RemovinglargeemptydownloaddoesnotrequiresparseHDformat: generateonUltimate withdirectREUfiletransfers. AhomepathstoredonlyinvolatileREUdoesnotpersist; generatedSTARTmustcarrydurableanchor, and firstSETUPbrowsermustnotdependonunknownoverlaypaths. Firmwaretwofilecontextsdo notautomaticallymaketheexistingglobalFILESadapterconcurrent.

2026-10-16 native configuration: firmware address width is not installed REU capacity. Store configured capacity explicitly, validate every owned range, and extend physical recovery coverage before using larger arenas. Host path canonicalization must match the actual backing filesystem: pinned FatFs strips trailing spaces/dots and rejects its forbidden characters. A pure slash/dot-dot check can approve a spelling different from the file later opened. Native old/new controls now expose this gap while preserving internal spaces, original DOS source names and harmless embedded consecutive dots. A successful code library fixture is not a working SETUP/START product.

2026-10-16 dualfloppy: swap the descriptor to a separately validated incoming arena and rotate allthree arenas; a permanently hardcoded spare overwrites a later live disk. Independent tests must write B and compare every A byte, including failures, rather than infer symmetry from successful A writes/B reads. Native test executables read PRGs at runtime, so their build steps must declare those files and force execution; a cached test summary is not a fresh target run. BulkLOAD verification likewise needs a deliberately different, verified destination before reload: returning the expected count while leaving already-correct memory untouched previously passed the standalone diagnostic, independently reproduced and rejected before hardware.


2026-10-16 realUltimate EOF text pads hexzero with zeroes whereas model used spaces. Native parser acceptedbothbut stricthostverifier rejectedfirsthardware run. Preservefailedrun, prove narrowlyexactformatswithwrongcount/address negatives, rerunfresh andrequirefullrecovery. A nativeA5 alone isnotacceptance.

2026-10-16 CRC identity: CRC(message || itsstoredCRC) has a fixedresidue andcannotbindrecordidentity. Bind CFG bytes0..571, comparestored572..575 separately. Actualhost control demonstrates two differentvalidcodewords yield the sameresidue. NativeinstallationchecksumCPUcost mustbemeasured, not hidden by fewerbulkcommands: original360KiB writerused3.05Bmodelcycles; tableASM preservesoutput with75.7M. This is not a guest8088speedup.

2026-10-16 single-ownership metadata must come from privateFILEShandle/state, not publicresult observations. Actual oldtwo-context controls wronglyallowed samepathoutput andbrowserlease after alteredobservation; separateprivateledger successor andconsumerregression nowprotect both. A re-signed CFG reserved-byte test alsoexposed an ASMjump skippingLDX afterREUclobber; per-byteCRC faults alone wouldmissit. Keep signedsemanticcontrols andactualNMIdelivery.

2026-10-16: Maincoldcode can borrow displaymatrixbeforetexttakeover, but growthmustfitactualfontbound; relocate onlyverifiedtrailingFILEhelper afterbootstrapcommits sources. Accountforfullhelper inpackager/managedcopy/header count andcompareagainstuntouchedfullPRG-CRC-boundsource; overlayheadershere containno payloadCRC. ModelrealNMIdelivery atbothcoldphases, not justvectorinspection. Incrementalrules mustdependon allincluded.incfiles.

2026-10-16: Connectionresetafter successfulnativebulk leaves bothindependentverification and originalmemoryrestoration unproven. Finiteambiguous-command attempts exhausted meansreviewanotherestablished recoverymechanism, not blindretry. Returnedretentionfailures mustretainfirstexceptionobject beforelatercleanupfailure; equalreprstrings donotprovecausalorder.

2026-10-16: RAM-initialized FILES handles are not evidence that firmware file pointers are closed. Native START must explicitly close both owned firmware contexts before opening its configuration. Also test the actual C64 glyph output: distinct ASCII filenames such as underscore and dash can become identical after transliteration. Preserve raw names and use an injective display escape. Separate mutable progress observations from private terminal/error authority; cancellation must keep polling until real cleanup ends.

## 2026-10-16 — repeated installer outputs

A completed file writer and its readonly source cache each need explicit clean-session rearm. Require private DONE, consumed producer and both known-closed contexts; retain output facts before clearing observations. Failed or uncertain transactions cannot be reset into a fresh output. Keep rearm code in the active FAT phase and state getters resident. Measure growth against the actual parent map: this slice adds54 resident bytes and212 FAT bytes with no BSS growth. Inherited exact-size fixture constants must change only with a measured layout change; retain the old failing oracle and keep all CRC, full-byte, EOF and closure checks.

2026-10-16: A successful DMA FETCH must not be checked against preexisting identical CPU-buffer contents. Replace the CPU destination with the opposite expected value before verification. Clock failure must permanently arm the bounded emergency-drain counter for that job; intermittent later coherent samples with no elapsed time must not reset it. Sample fresh time before leaf polling but preserve leaf failure before same-poll Run/Stop. Repeated same-path LOADs can reproduce the same wrong byte; source verification should compare independent ordinary READ04 against staged bulk data, not claim identical bulk reads prove original bytes.

2026-10-16 source bootstrap: compare only processor-port banking bits; unused input highbits can readF5 after writing35. Linker C extern synthetic symbols receive compiler underscore prefix. Derive phase-private fixture storage from exact object map rather than assuming it remains the last BSS allocation. CPU READ04 verification needs explicit larger host pollbudgets than32KiB bulk replies; keep target elapsed deadlines unchanged. Before source wrappers add HIGH_CODE helpers, document/setup-only-gate the build so existing public START layouts remain exact.

2026-10-16: Reset doesnotprove old RAM mailboxzero; initializeonlyowned32B DRF whilepaused afterobservedBASICREADY, readback thenverifyfullcoldprogram beforeSYS. Two staleCPUverificationbuffers muststartdifferently andbothFETCH beforecomparison; thencompareexpectedCRC. A combinedlinkfit isnot end-to-endbehaviororprivatefactauthority. Monolithiccc65 config objectkeepsunusedmaker/validator records/code: explicitdefaultOFF path-onlyprofile canreclaim3280UIbytes withoutnewREUoverlays orstackshrink; preserveexistingdefaultnativebytes.

2026-10-17 native coordinator: initialize SU timeout only after SOprepare restores/zeroes UIBSS. cc65 associates extern declarations with their default storage segment when reading headers; a definition pragma did not relocate those observations. Compile the capture translation unit with default resident BSS, and explicitly place its consthome pointer outside UI_RO. Verify retained bytes after actual phase replacement. Physical RunStop maps27 in this native platform, whereas Ctrl-C is3; delegated SU cancellation tests do not cover the root startup/overlay loop. Test each ownership phase's actual matrix edge. Keep source verification receipts distinct from durable output receipts and retain private phase tickets on successful entry.

2026-10-17 compact profile: shrinking transport buffers requires updating adapter defaults as well as upper-bound checks; FILES hardcoded896 rejected legitimate startupCLOSE on compact512. Preserve packet saturation separately from destination capacity, drain excess bytes, and interpret native consumer truncation flags. A generic two-descriptor ASM copier with per-byte readback saved68 UI bytes while avoiding SMC that would invalidate immutablephase CRC. Actual fault injection at first/last HIGH/AUX bytes catches readiness-before-verification mistakes.

2026-10-17 fullrootnegatives: nativeCREATE_NEW refusal preserves existingbytes but FILES must conservatively retain uncertainhandle2. A publisher that immediately returnsFAILED can leave ownedoutputpending even though no modelhandle isopen; knownclosure requires the sameowner to attempt/drain oneCLOSE under existingbounds, preservefirstcause and keepunknownfailuresblocked. Do not infer nohandle solely from hostmodelcollision semantics or clearfailedownership as a shortcut. Raw underlying RAM D800 is not colorRAM: use existing separateIO oracle. GeneratedSTART+mountedC exposed stale main elapsedepoch hidden by noHD/start fixtures; refresh before nativeIO rather than widening timeouts or patchingmodeltime.

2026-10-17: Compiler staging is a second source graph. Pin originals and staged copies before compilation, then verify both before publishing. Exact public PRG reproduction is useful only after full native positive/failure composition has passed; it does not replace physical acceptance. Refactored internal labels can break behavior-test entrypoints: use the stable full continuation and preserve its assertions rather than bypassing initialization.

2026-10-17: Distinguish helper staging limits from transport limits: old40fe16KiB cap isnot RESTmachine:readmem64KiB cap. ROOT corrected that mistakenreviewbeforeanycode/devicechange. OptionalINI missing-file defaults mustfollow OPEN'sactual filesystemstatus, exact18-byte FILE DOESN'T EXIST; static82 DOSstatus belongsothercommands. PairedfunctionalDOS workloads canretain retirement/stepcounts whilecost-derivedtimers alter instructionhistograms; separatelytest fixedexternalcadence andneverclaimidenticalstreams orphysicalXTspeed frommodeledcycles.

2026-10-17: A serialized relocation payload and its permanent RUN copy have different lifetimes. Reusing LOAD-only bytes after verified copying and cache commit freed3,060 UI staging bytes without reducing buffers or expanding REU. Validate the full original image before retirement, then validate only the live immutable UI core; keep the full cache checksum over zero-padded state. Never zero aliased BSS during bootstrap. CRC-negative fixtures must not corrupt a relocation descriptor before it is used and then claim to test later unused data: our first UI_RO byte was the live12-byte descriptor, not a UI string. Preserve that failed fixture and the pre-CRC trust boundary.

2026-10-17: A folder-only browser can still detect file conflicts by accumulating exact raw names before display filtering and pagination, then committing the private result only after the entire listing and quiet lease release. Testing a conflict at raw entry1024 beyond the displayed page and forging the public page/result distinguishes authority from presentation. Keep the final create-new guard because an early scan cannot resolve aliases or prevent concurrent changes. Mixed-case native UI screen assertions must independently convert lowercase glyphs; host ASCII bytes are not the screen buffer.


2026-10-17: A passing native component can still fail its complete release graph. Match initialized-state verifier schemas and actual capture tooling to every inserted state byte, retaining strict legacy contracts. Keep optional bundle tests outside default discovery when their generated inputs are optional. A moved unit helper must still execute through an explicit, guarded sidecar; assert total retained code and exact lifetime bounds instead of deleting tests to regain space. Capture artifacts after their producing prerequisites, and distinguish an intentionally rebuilt ancillary map from changed executed code. Preserve failed source/test snapshots and qualify the specific drift instead of rerunning every unchanged slow lane.

2026-10-17: Software handle zero is insufficient cleanup authority after startup recovery is canceled. Actual CLOSE1/2 cancellation can leave firmware handles closed and BCclosed true while private SCready is false. Public cleanup observation must include both authorities; getter/private readiness remain the admission controls. Generic status85 was a different case with BCclosed false, so it did not establish that counterexample.

2026-10-17: Retain bounded successful write acknowledgment bytes before validating their semantic fields. A later address predicate can fail after HTTP200/errors=[] and after a real write; retaining transport errors alone loses the concrete offending response. RAM prefix equality cannot reconstruct that acknowledgment or prove the absence of additional writes. Keep the first campaign failed and instrument a separate successor without weakening the predicate from speculation.

2026-10-17: Guarding each cleanup operation is insufficient if cleanup's surrounding clock/deadline or frame raises first. Give independent owned restoration a structural finally and its original finite timebase; preserve primary failure while separately retaining restore acknowledgment/readback/inventory. An actual model counterexample caught this before hardware.

2026-10-17: Real native leaf calls from a fixture prove composition, not the on-machine app's automatic flow. Test the actual BASIC entry and only keyboard/firmware inputs before advertising that UI. Keep code and RO in separate ld65 segments even when both share one relocated arena; cc65 function-local static data can otherwise precede an entry instruction.

2026-10-17: An assembly caller of a C u8 function must test returned A explicitly; return flags are not part of that ABI. Add CMP#0 before branching, even when an earlier positive run happens to work. Retain the old positive result honestly; source-contract defects need not be described as observed failures. Independent generated-output consumer runs prove more than matching fixture oracles.


2026-10-17: A safety operation's own guard must sit inside structural cleanup. ROOT's one-shot real line trace caught an exception between the outer eligibility test and guarded call, bypassing scratch and turbo restoration. Separate local pre-attempt entry from the actual once-only side-effect flag; retain the first cause and original deadline, and put independent profile cleanup in an outer finally. This is evidence for the tested boundary, not a promise that arbitrary process termination is recoverable.


2026-10-17: A compiler environment can add an unrecorded source even when all staged files/tool hashes are pinned. Peer actually changed CONFIG through CC65_INC/string.h while the old source ledger still passed. Sanitize inherited search variables or explicitly capture their full source closure; retain supported explicit tool overrides. Validate original source asset membership before copying, since validating only selected copies silently weakens an exact-set rule.


2026-10-17: Release acceptance should follow an actual user's complete workflow. Opening unchanged Pascal source and compiling to memory proves less than editing, saving source, compiling an EXE to disk and recovering both after a fresh launch. Label historical evidence precisely and freeze a finite V1 endpoint when the user defers optimization; preserve deferred prototypes and first failures without promoting or continuing them.


2026-10-17: Test multiple user operations in one machine. Fresh-machine cancellation tests missed an exporter cancel bit that prevented everylater C-online save. Clear stalejob state onlyafteradmission ofthenewoperation, preservingnewcancelinputs and rejectedownership state. A valid checksum ofzero and an invalidbindingwith fullyverifiedoutput are separatecases: contentidentity mustnot silently grantgeneration/persistence authority.

- 2026-10-17: NativeCUIROMglyph mapping requires lower/uppercharset D018=16; defaultuppercase/graphics charsetmisrendersASCIIuppercase. RestoreobservableregisterswithoutCIAclockinitialization, thenfullyredrawguestcolor/pixelstatebeforeRUN. CbyteAPIreturnsareAvalues, notcarrycontracts. IsolatedSaveAsfixturesremaincoldA5: borrowtestsneedactualBIOS+coldrelease, andBIOSusesexisting40Minstructionbound. Sourceclosedfrontendtestsandbrokercompositionprovehandoff, notfilesystem/backendcompletion.

2026-10-17: A successful reopened IDE may legitimately alter an already-deleted temporary directory entry while all live files remain byte-identical. Inspect exact changed offsets and FAT ownership; do not require whole-image identity or silently waive live-file changes. An inherited HTTP transport that rejects non200 before retaining status/body cannot retrospectively support a numeric status or firmware-cause diagnosis. Preserve this uncertainty and fix diagnostics in a fresh transport before future calls.

2026-10-17: A separately scoped, source-documented single-item configuration PUT restored our temporary turbo setting with fresh exact identity/settings/media guards and full readback. This closes that setting independently; it does not relabel the earlier failed memory campaign. New transports retain numeric HTTP status/headers/bounded error body before throwing, without inventing the old unrecorded status.

2026-10-17: Returning from the modal UI requires explicit colorRAM restoration: normal hires text redraw does not rewrite D800. Retain all1000 low-nibble colors in an owned REU span and restore before resident full redraw; test with actual display model. Also suppress nonmodifier menu exit keys until release, and do not invoke C error presentation until its full load and initialization succeed. Native INPUT acquire failure must clear pending menu entry before resident terminal failure to prevent an unintended automatic retry.

## 2026-10-17 — worker cleanup and cold phase boundaries

- A terminal worker owns the truth about its file cleanup. Passing an uncertain recovery CLOSE into a general loader failure handler caused an actual second CLOSE. Preserve its cleanup result, clear boot readiness and stop without rearming the transport. Test the outer frontend drain as well as the worker.
- Run pending-journal validation before ordinary CFG acquisition: first-rename interruption legitimately leaves CFG absent. Restore and reverify the original INO only after every recovery frame has returned.
- A model cycle-budget return can be live progress. Retain the same machine and inspect command/state progress before changing a whole-SYS test bound. Here772→1467 READ/file commands completed at1.145B cycles; native deadlines did not need changing.
- Generated non-emitting import aliases are build outputs. Adding a debug export changed the alias ledger without changing any linked instruction. Keep the strict initial rejection and qualify the exact2-line difference explicitly; avoid rerunning the same36s suite to hide a metadata-only delta.
- Native CIA keyboard menus do not consume the KERNAL keyboard buffer or guest XT queue. Those input lanes cannot substitute for real SETUP/CONFIG keyboard acceptance. A paused stage5 also proves neither C FILES closure nor safe helper takeover.

2026-10-17 overlay tests: a numeric breakpoint is not proof that a particular function is installed. RCV and INO legitimately execute different instructions at the same address. Before injecting a modal_copy fault, require the actual resident phase and exact installed INO identity; step genuine earlier instructions normally. Reject apparent passes caused by faulting the wrong phase.


2026-10-17: Test denied actions at the actual capability boundary. Root public can_resume0 passed observation checks while native modal_release still succeeded after committedCFG/BINDload failure; assert actual release rejection, retain oldtrace and revoke stage8. Also distinguish known restored C from stage8/freshclock permission: collision preserves C but native terminalE1 remains authoritative. CRC over a complete self-checksummed record may be a fixed residue; bind original body identities/exactbytes, as currentBIND and pending recovery counterexamples demonstrate.

2026-10-17: Link-derived UI byte counts and actual CFG base matter across composition. CFG starts3FF020; B presence is descriptor+9, and an unsigned133-byte copy cannot use signedDEX/BPL. Capture private delivered UI intent once while its code is live, then return every C frame before phase exchange. Treat Peddle sentinel status2 at an exact nested-PC breakpoint separately from an actual top-level stack failure. A returned public denial must be backed by native release revocation.

2026-10-17: Confirmation pauses separate admission epochs: use fresh UI time for first OPEN. Failed normal CLOSE must not enter generic repeated-CLOSE cleanup. Preserve worker input ownership. Compare captured6510 ports2F/F5, not literal35. Keep bad-oracle failures and additive replays honest. Include handASM platform.s when platform.c outputs platform_c.s; basename filtering can omit real source.


2026-10-17 Root Finish integration: a cc65-compatible assembly getter that returns A and sets X0 does not preserve A-derived Z. Actual unknownCLOSE error4 was replaced by genericFC through BNE after fn_error; explicit CMP0 restored first-error reporting. Both versions withheld Safe/Resume and retried nothing; retain the actual failed assertion. Also restrict new fn_ aliases to the Finish table, because unrelated native internal labels can have the same names. Standalone backend proof does not replace actual menu routing/final Safepark tests.


2026-10-17 controls: use the linker complete segment list for memory totals; per-object BSS omitted platform/lib state and understated CUI by23B. Actual CUI always remained below7D00; corrected old docs without changing frozen binaries. Capture compiler -M system/C++ SDK dependencies as well as native cc65 inputs; final1415-input controls closure includes fresh native/model rebuild and actual14 after full BEFORE capture. Older scoped428 Finish window is explicitly qualified. Retain startup binding on session-only Eject; otherwise later other-drive Save would mismatch oldCFG despite unchanged durable media. Current actual emptyB→SaveA test proves composition.

2026-10-17: A successful C call does not export its private staticstate into ld65 labels. Assert actual exported error/result/output or call the real API through its ABI; retain a mistaken observer failure separately from SUT failure. Cold recovery has effective CPUportF5, so compare the captured owned ports rather than nominal written35. FirstB insertion changes CFG presence; validate OLD descriptor against OLDpresence, then require NEW selectedpresence independently. CRC0 is valid data identity, not a missing-verification marker. SETUP's direct FAT creation does not satisfy the independently required guest FORMAT/BIOSAH05 gate.


2026-10-17: Clear bridge observation before controller entry guard: an early refusal can bypass zerobss and otherwise advertise stale Resume even when the native release guard correctly blocks it. Source graph tags are whole-source identities; moving to a portable build changes tags/whole assets and requires cold descriptors to be regenerated. Metadata named MANIFEST.json nested inside a copied runtime must not silently escape filename closure; retain the first failure and create an exact clean child instead of mutating the seal. A nonexistent command cwd fails before process creation: stage from an existing cwd, then launch the dependent test.


2026-10-17: elapsed_poll carry/status4 is an expected bounded-sampler seam, not always a broken clock. Admission sites need the same boundedretry distinction as active job polls, before mutating ownership. A host debugpoke does not necessarily model an I/O write: use real CPU STA for the control-fault fixture. Independent leaf pumping has different coordinator overhead and must have its own measured bound; retain the first short host budget failure, and do not change the SUT merely to meet it.


2026-10-17: Native UI keyboard tests must hold BOTH matrix press and release until a real successful scan, not one modal_wait return: pendingclock may skip scanning. The olddriver lost7characters and nativeIncoming correctly refused the wrongpath; preserve that counter and prove exacttypedpath beforeworker admission. CIAreadquota is not literal fullscan count during backendSTOP polls; qualify observations. Existing genericunknownselector tests must adopt newly supported named8FORMAT and reject9 rather than obscure legitimatecontract expansion. A runtime-only source inventory omits unrelatedtestdriver/VICEpreparation; stage exact neededfixture and report partial commandfailure honestly.


## 2026-10-17 — new optional Make include requires all staged inventories

The first public cold-builder promotion exposed the runtime's intentional missing-include check: adding cold_start.mk to Makefile also requires declaring it in both native-media source inventories, even when the selected target never executes it. Preserve the failure; extend the inventories rather than weaken validation. Rebuild truthful source-cohort tags; exact code equality does not transfer previous whole-hash workflow acceptance.


## 2026-10-17 — separate actual runtime tests from complete UNIT layout limits

The optionalFORMAT1 runtime can be tested directly with both PythonABI andZig assertions even though the fullUNIT1 linkoverflows. A clean test command must compile the publicdevice model, bind everyusedctypes pointer API, load theactualruntimePRG/labels, andcheck thoseproducts/sourceinputs afterexecution. Pin Zig's actualcompiler/distribution andclang'sactualSDKdependency list; do not let a privateprebuiltmodel or a cleanclone'sunrelatedoptionalfixture become an implicit prerequisite.


2026-10-17: After exclusive lock creation, record ownership before closing its descriptor. An error from close must preserve its exact first cause while cleanup removes the newly owned lock. Never remove a preexisting foreign lock. The small host regression suite tests these boundaries without rerunning native CPU suites.


## 2026-10-17 — bind metadata through the actual result schema

A source-built cold bundle publishes named START/DOS labels/maps with paths+hashes; the priorcopiedbundle laid them in start/ and main/build. Resolve checkeddeclaredproducts and require ownedrun membership; retain only recordedlegacyfallback. Validate unuseddeclaredproducts too. Closureledgers differ (listrecords, scalarSHA maps, SHA+size maps); preserve firstformatmistakes, normalize theactualschema without weakening hashchecks or rerunning unchangednativework.


2026-10-17 TF correctness: check original Intel2-28 before copying modern/reference suppression behavior; original8088 nests type1 before an interrupt routine's first opcode. CurrentTF and a sampled/pendingtrace are different, including POPFclear and newly-enabledTF→INTR. Keep fullTF fuzz fixtures and run a real guestISR/IRET; flush/invalidate coherent setup before subsequentrawREU seed writes. OldMake can reuse same-second objects even after a changedcontentstamp: explicitly force the graph from parse-time profile comparison, and test0→1→0 with no sleeps. Full5701corpus excludesIF/TF/0F and cannot establish complete8088compatibility.


## 2026-10-17 — composition needs its own positive workflow

Named-path diagnostics can reuse request scratch even on successful operations. Complete failure-pane tests and old positive installation evidence do not establish the merged positive path; execute the new actual SETUP producer and generated START/DOS consumer before release claims. Manifest readers must distinguish flatmaps from schema/files wrappers. Keep release requirements short and current; preserve historical evidence separately rather than making users reconstruct scope from an append-only endpoint.


## 2026-10-17 — preserve a failed oracle and reuse only known-closed output

DOS LABEL may create an archive-marked volume label beside a same-named directory. Treating labels as live filenames makes a valid disk fail inspection. Retain the first failed host cohort, separately establish an actual native known CLOSE under safe guards, and continue only from that closed image. Test label namespace and malformed metadata independently; repair the host parser without changing emulated DOS or rerunning unchanged long workloads.

2026-10-17: A current default-disabled source may still be an unconditional Make link input (trap.s). Test source inventory against actual linked ASM_SOURCES; do not let unused untracked probe files hide clean-checkout failures. FDISK restart uses farJMPFFFF:0, not INT19: DOS-hooked IVT and loaded lowRAM code have different lifetimes. A BIOS reset template captured before HDmount loses later INT41; finalize after allcolddevices. Nativeproductionfit does not prove fullUNITfit when both share tight coldwindow.

### 2026-10-17 Reset fixtures and identical descriptor occurrences

A guest restart can legally jump toFFFF:0000 after CLI/CLD. Direct bootstrapping retains DOS IVT hooks into code overwritten by IO.SYS; finalized vectors must be restored by the reset path, including HD vectors. Tests that assumed two guest steps or tiny cold budgets must exercise the real ROM sequence. Cold-clock negative tests need valid BIOS/cache/REU prerequisites to isolate clock failure.

When sharing LOAD/STORE request descriptors, a repeated local label is not a safe text-edit anchor. The rejected layout successor modified live sav_begin rather than cold sav_boot, inverting both operations; a full2048B cold-SAVER/one-DMA assertion and source peer caught it. Keep that failed attempt and qualify both descriptor users.

### 2026-10-17 Root consumer review expectations

Read the frozen producer's literal program/output before asserting a guessed string. Compare clock progression only within the same VM/session; fresh START seeds a new epoch and its absolute BDA ticks need not exceed a previous VM's. Two Root read-only review draft failures are retained in the final Turbo/FDISK archives; neither required native changes or replay.

### 2026-10-17 Do not equate a GUI wait label with delivered input

The sameone-poll helper sometimes made20 CIA reads, but originalDISKCOPY timing made10 reads forB, zero forL/A/N/K/./I/M, then10 forG; intended /Home/SWAPBLANK.IMG became /Home/SWAPG. Pre/postDOS and a shiftedtiming targetprompt allpassed, so those positives alone could not isolate the firstfailure. Reproduce precise chronology, logscan deltas and validate the exact private editor path beforeReturn. Hold both keypress/release until observed scanner progress within a budget; no fixeddelay pacing. GUI errors require GUI-aware closure, never an unrelated DOSpause command.

### 2026-10-17 — distinguish native completion from host validation errors

The narrow readonly recovery completed CLOSE successfully, then its host passed bytearray to a bytes-only source verifier. Preserve the failed controller result and repair readonly validation against captured fullRAM; never replay a successful close merely to fix a host type. C64U CPU speed enums below10 are padded (" 1"), so REST must encode the leading space. Match actual configuration literals rather than guessing display labels. The first rejected400 occurred before native mutation and original settings were restored. A single high operand change from JMP082E to JMP402E avoids mixed-address risk while redirecting an owned stopped loop. This is development cleanup, not a release feature or general uncertain-writer recovery authority.
