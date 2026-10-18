# Next performance architecture: measured feasibility, not implementation approval

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


Retained research cohort: `agentworking/scratch/translation-feasibility/`; artifact names below refer to that directory. Root independently checked exact normal-report equality, both complete native-PC histogram sums and all601936 trace-record lengths. Evidence (local development record, not distributed).

Prepared 2026-10-15. Private research only; no production edit, new ISA implementation, hardware, network control, commit, or extra subagent. The actual six-overlay target is frozen at runtime `98fcd115338c43c8976d35f24feea468a040897f11ee143f8c52c9b477d07ff7`, unit `6eba1ee7bf6c872fcb7f4a059cc64f4572243511efa37302026d8ced82b244f8`. The later two-byte empty-PIC fast path is a separate proposal and is not silently included in this profile.

## Recommendation

Do not commit to a broad 8088-to-6510 translator yet. First measure and reduce the exact interrupt-boundary path, then make a disabled, generic runtime block experiment whose purpose is to prove semantics and measure admission costs. A register-only translator cannot deliver the requested near-XT performance on its own. The new real-DOS measurements below show why. Large improvement will require the boundary path **and** coherent guest memory/fetch/word/string paths; a new compiler alone does not remove those costs.

Keep the interpreter as the complete fallback and oracle. No DOS kernel patch, host DOS service, offline DOS precompiler, native COM/EXE loader, application recognition, or interrupt-21 replacement is proposed. Runtime translation must accept ordinary guest bytes regardless of which program loaded them.

## One new actual native DOS profiling pass

The unchanged accepted unit PRG ran native ENTRY, asynchronous real-image import, BIOS/DOS/COMMAND.COM, the empty date/time replies, VER, DIR /P, pagination, and the returned prompt. All ordinary assertions remained active. Host-only counters were added to a private Peddle bridge, at native instruction boundaries; no modeled target instruction or cycle was added. This is profiling of real assembled emulator execution, not replay of an abstract 8088 model.

The instrumented result is **exactly equal in every JSON field** to the frozen uninstrumented six-overlay `native-dos-boot.json`: all observations, keys, names/sizes, timing/counters, 640 KiB guest SHA and CGA SHA. The new exclusive native-PC histogram independently sums to the same whole-call clock count. The frozen target and supplied disk bytes stayed exact.

| Measured quantity | Result |
|---|---:|
| Completed guest instructions | 598,702 |
| Actual CPU-step calls, including continuations | 601,936 |
| CPU-step inclusive clocks | 1,169,895,754 |
| All native call clocks in the harness | 2,869,345,809 |
| Timer callbacks, ordinary and REP element boundaries | 658,267 |
| Timer callback inclusive clocks | 873,806,129 |
| CPU-step calls that perform guest writes | 152,061 |
| Guest byte-write epoch increments within CPU calls | 649,260 |
| Native runtime ticks | 39,903 |
| Test result | 1/1, 40 seconds execution after compilation |

**Do not add CPU-step and timer clocks:** REP timer callbacks are already inside CPU-step time. The all-native total additionally includes import, runtime presentation, diagnostic SNAPSHOT/read commands and other support. Its distribution is specific to this diagnostic workload, not an unattended emulator session. Peddle clocks exclude REU stalls and physical MMIO/VIC waits. There is no new C64U or XT elapsed measurement.

Exclusive native-PC ownership within CPU calls:

| Module | Clocks | Share of CPU-step clocks |
|---|---:|---:|
| Coherent memory/cache | 318,317,022 | 27.21% |
| Instruction fetch | 257,644,879 | 22.02% |
| CPU decode/handlers/completion | 207,256,621 | 17.72% |
| Segment:offset translation | 129,677,582 | 11.08% |
| ModR/M operand helpers | 42,840,176 | 3.66% |
| Stack helpers | 36,747,562 | 3.14% |
| ALU | 34,219,610 | 2.93% |

Memory, fetch and physical-address calculation together own **60.32%** of CPU-step time. Attribution is instruction-PC ownership, not inclusive call time. C900–CFFF is explicitly classified as one shared overlay window; a static address cannot distinguish whichever variant was loaded at that moment.

Highest inclusive opcode call costs: OUT imm8 E6 86,856,298; MOVSW A5 80,731,838; MOVSB A4 59,407,337; CALL E8 50,774,564; LDS C5 37,031,929; RET C3 36,001,676; INT CD 35,081,482; immediate group83 34,052,122. OUT includes BIOS callbacks. REP rows include multiple calls per retired instruction. These rows cannot be interpreted as bare 8088 opcode timings.

## What a small translator would cover

Coverage counts only completed, unprefixed instructions. Immediate/register operands are observed passively from authoritative cache bytes; no extra modeled bus access is made. The last actual decoder opcode is authoritative for continuation calls. These sets describe possible experiments; none is implemented here.

| Cumulative admitted set | Calls | CPU clocks currently consumed | CPU share | All-native harness share |
|---|---:|---:|---:|---:|
| NOP and MOV register, immediate | 21,205 | 16,757,336 | 1.43% | 0.58% |
| Also INC/DEC register, Jcc and LOOP family | 128,327 | 101,088,025 | 8.64% | 3.52% |
| Also selected register-only ModR/M ALU/MOV/TEST/XCHG | 209,310 | 213,977,617 | 18.29% | 7.46% |

Even replacing the last set with **zero-cost execution** would improve this all-native diagnostic harness by at most 1.081×, before translation, admission, lookup, cache-capacity, and invalidation costs. This is an optimistic Amdahl calculation for this exact script, not a hardware speed forecast. The CPU-only ceiling for removing that set is 1.224×. Other applications may have a different mix.

An ideal trace partition into same-page runs, ending at branches or unsupported instructions and capped at16 instructions, yields mean run lengths **1.28 / 1.04 / 1.48** for the three sets. This model ignores source invalidation, intervening IRQ writes, compile time and byte storage. For the broadest set, ideal16/32/64-entry block LRU hits are49.49%/64.11%/75.86%. These are optimistic locality estimates, not a decoded-cache benchmark. They warn against assuming that a small register translator will usually amortize checks over16 instructions.

There is one useful generic memory loop: physical0D47C/0D47D/0D47F/0D482 repeatedly executes LODSW, ADD DX,AX, ADC DX,imm8 and LOOP. Its four addresses each execute15,972 times and consume85,498,633 CPU clocks. That is7.31% of CPU-step clocks and2.98% of all harness clocks. A memory-capable translator or span-specialized interpreter could help it. Recognizing its DOS address/signature or replacing the whole routine is not proposed.

## Timer boundary is a separate architectural problem

The reviewed `cpu-timer-performance` research measured a genuine sequential warm NOP at429 CPU-step clocks; redirecting IP to the same byte costs796 because it really refills the fetch span. With its proposed empty-PIC return, an IF=1, no-request, unchanged-raw-time callback still costs1,021 clocks. The32 sequential native-NOP case costs46,752 clocks, or1,461 per guest instruction. These are explicitly scripted functional-clock cases.

In that measured regime, eliminating the entire429-clock interpreter body still leaves about1,032 clocks per boundary, including wrapper overhead:16.125 microseconds at an ideal64MHz before any physical waits. This is a lower bound **for retaining that measured callback implementation in that regime**, not a universal minimum for all implementations or IF states.

At nominal XT clock52,500,000/11Hz, a host budget is approximately13.41 native clocks per XT clock, or17.88 at the provisional0.75× acceptance threshold. Intel's1979 table gives NOP3 and MOV-register-immediate4 execution clocks, but explicitly assumes prefetched instructions and warns that instruction-queue/bus effects can extend execution. Thus those table entries are analytic illustrations only: they cannot be used as the elapsed timing of an8088 NOP/MOV stream. [Intel primary manual, sections2.7/2.8 and table2-21, pages2-50/2-61/2-62](https://bitsavers.org/components/intel/8086/9800722-03_The_8086_Family_Users_Manual_Oct79.pdf).

A calibrated XT or cycle-accurate reference must run the same source-controlled workloads. Physical C64U timing must include boundary MMIO, display and REU stalls. A fast generated MOV body cannot establish a workload ratio while this boundary remains expensive.

### First bounded performance slice: owned internal clock ABI

Add a private internal clock/sample gateway that requires already-owned CIA2, RAM+I/O mapping, CLD and non-reentrancy. Preserve the public bank-safe, A/X/Y-preserving API unchanged. The internal gateway may clobber A/X/Y and avoid redundant nested banking/register preservation, but must retain the **same control validation, coherent sample register sequence, bounded retry count, reload exclusion, success/error publication and elapsed/PIT outputs**. Keep every ordinary/HLT and eligible REP-element callback; do not change event cadence or coalesce reads across guest instructions.

This is a small, reviewable optimization with a real path to remove repeated work. No savings number is asserted before assembled measurement. Even a100–200-clock reduction would not close the current gap; it is a prerequisite for learning how much remains, not the final answer.

Measure the internal gateway on Peddle with an independent sampler and every existing tear/reload/control/owner case, then physically at Manual64 with MMIO counts and actual elapsed time. If MMIO remains the dominant floor, a hardware deadline latch or a changed virtual-PC-clock policy requires a separate decision and proof. A CIA timer cannot simply be programmed with a rounded18.2Hz period and called equivalent: fractional phase, reload latency, missed/coalesced edges, pause rebasing, competing CIA ownership and early/late IRQ boundaries all matter. Replacing per-boundary physical sampling with occasional polling is **not** approved by this proposal.

## Concrete generic runtime block experiment

After the boundary measurement, add an explicit disabled experiment with the following restrictive admission policy. Its initial purpose is correctness and admission-cost measurement, not a shipping speed claim.

1. Runtime6502 code reads ordinary guest bytes through the coherent memory API. Initially accept only NOP and MOV register,immediate, no prefixes, no segment writes, no memory operands, no trap-mode entry, and no current REP/prefix continuation. Keep1–8 instructions wholly within one512-byte physical source page and a nonwrapping16-bit IP interval. First instructions crossing a source-page/IP/20-bit boundary take the interpreter path unchanged. Later register ALU and branches require their own acceptance slices.
2. Acquire/pin the source page before inspection. Only bytes already available in that pinned page may be inspected ahead. Never resolve a future page or raise an unsupported/future-instruction error during compilation. Stop before the first inadmissible instruction. Release compiler overlay ownership before executing generated code. No C900 lease survives into a guest boundary or scheduler return.
3. Emit6510 bytes at runtime into a separately owned host execution cache. The host never translates DOS files. Emit per-instruction commit points: full materialized guest state/IP, exact32-bit instruction counter, strict original8088 shadow decrement, then the next normal timer/IRQ boundary. Preserve public host P except C at the outer entry/return. A/X/Y remain clobbered as already allowed.
4. Before every admitted guest instruction, invoke the actual native timer/IRQ path. Accepted IRQ immediately exits the translated block without executing its next instruction. Mutable IVT, stack/frame failure, IF and incoming shadows remain owned by the existing callback. Recheck CPU status/result; carry/fatal faults are terminal and preserve already-committed guest work. There is no direct chaining past this boundary.
5. A block is valid only after a **fresh byte-for-byte source comparison** against its saved guest-byte snapshot under the newly acquired page pin. Include CS/IP, physical source interval, memory mode and source-byte count in its descriptor. A generation check may reject cheaply but must not establish validity by itself. This handles physical aliases, evict/reload, init resets and16-bit generation ABA without a new persistent version array.
6. Retain the source pin only within a bounded block invocation, never over a scheduler return. Since the initial admitted instructions cannot write guest memory and an accepted IRQ exits immediately, an empty callback cannot modify source/cache authority. Release the pin on success, fallback and terminal exits under the existing cache failure contract. Host/debug writes, BIOS DMA and code mutation between invocations are seen by the next fresh comparison.
7. Bound compilation by source bytes/instruction count and execution by the existing host quantum. Unsupported, expired, unready, mismatched or unallocatable optimizer state falls back before guest mutations. A real memory fault retains the scalar interpreter's first-failure/partial-commit semantics; it is not swallowed as a cache miss.

This byte-comparison design deliberately avoids assuming that the global32-bit write epoch is a collision-proof translation version. Global invalidation would also discard useful blocks on stack/data/BDA writes;152,061 CPU calls in this trace perform writes, and ordinary IRQ writes are additional. Existing per-frame16-bit generations can wrap or repeat after init/eviction. A later cheap page-watch scheme needs explicit invalidation hooks in every scalar/range/BIOS/REP writer plus saturation/flush-before-wrap rules; it cannot be inferred from the current generation counters.

QEMU's primary translator documentation supplies useful design precedents: translation keys include execution state, self-modifying code requires explicit invalidation, interrupt-unmasking state changes require exits, and precise exceptions require guest-state restoration points. Its design and source are **not** adopted as6510 code or as proof of our behavior. [QEMU Translator Internals, version11.1.50](https://www.qemu.org/docs/master/devel/tcg.html).

### Fully charged minimum-memory experiment

Actual accepted baseline: MAIN115 bytes free(runtime)/114(unit); DEVICE22; host F000–FDFF shadow2144/3584, leaving1440 bytes; DEVICESTATE659; BSS223; ZP18/30. Cold1093/118 bytes are not resident space. Current23 startup-overlapped cache frames must be committed before use.

| Resource | Proposed experimental allocation | Consequence |
|---|---|---|
| HostB000–BFFF |4096-byte generated-code/descriptor/guest-byte cache |cache_limit24, leaving12KiB guest frames8000–AFFF;25% less guest cache |
| HostF860–FDFF |up to1440 bytes resident entry, guard, dispatcher and exit support |existing F000–F85F HD/scroll code stays; FE00–FFFF vectors remain reserved |
| C900–CFFF |new compiler overlay, at most1792 bytes |compile only; release before execution/IRQ; never a second active window |
| HostB000–B7FF during startup |one additional2048-byte compiler asset slot |after bootstrap it becomes part of the execution cache;27 startup-overlapped cache frames instead of23 |
| REU343000–3437FF |2048-byte immutable compiler slot |within current4MiB staging/asset arena; exact header, packing and ownership extensions required |
| HostEC93–EEFF |at most621 available bytes, explicit state budget required |EF00–EFFF stays reserved; descriptors preferably live in charged B000 cache |
| REU3C0000–3FFFFF |optional256KiB backing code cache, **not initially allocated** |ordinary execution still needs host RAM/DMA; no speed benefit assumed |
| ZP |provisional2-byte emitter pointer, only after linker proof |never assume undeclared spare ZP is usable |

This is a proposed ledger, not linked evidence. If the compiler/support cannot fit these bounds, reduce the experiment's admitted set or reject it. Do not quietly borrow bitmap/font/UCI/cache/HD/vector storage. Loading a seventh startup asset must precede cache initialization; source B000 must not be executed before its asset is committed.

Benchmark cache_limit24 against32 **before** implementing translation. A4KiB execution cache can lose more through guest-cache misses than it wins through decode. Do not add an REU code cache until physical DMA/load costs and measured block reuse justify it. REU is storage, not an executable address space.

### Required prototype acceptance

The first actual prototype must generate code with runtime6510 instructions, then execute that generated code in Peddle. Host oracles may assemble inputs and calculate expected results but must not emit target code or bypass the runtime compiler. Compare all28 guest register/flag bytes, CPU status/opcode/count/shadows/pending/REP state, PIC/PIT state, source authority/pins and the full1MiB guest image with independently expected results. Test every register, boundary immediate, all256 native entry P values, counter carries, all admitted lengths, and fallback without mutation.

Inject an IRQ at every translated instruction boundary, incoming shadows0/1/2, IF0/1, mutable IRQ vectors, timer tear/transient/fatal/control failure, overlay-load failure, page acquire/pin overflow/fault, alias self-modification, eviction/reload and explicit cold/cache reinit. Compare fault prefixes at the first byte/first instruction before any broadened memory form. Existing REP element16/final-element and original IP−2 restart behavior must remain exact on interpreter fallback. A new memory/ALU/branch translation slice requires the full5701 CPU corpus plus focused differential tests and real-DOS regression.

**No translated-block prototype was built or timed in this research.** The measured work is the exact real-target DOS profiling pass. A trivial straight-line emitter without these interrupt, invalidation and failure checks would give an attractive but unusable cycle count; the task explicitly made that prototype conditional on independent full-state/failure validation. The narrow coverage and timer floor make the owned-boundary experiment the better next concrete implementation slice.

## Larger-gain follow-on after measurement

The profile favors coherent internal operand/word/string span paths over a NOP/MOV-only translator. Investigate an internal RAM-hit ABI with public wrappers intact, cached segment bases keyed by the actual current segment value, and same-page word transfers that avoid a second full segment translation while preserving offsetFFFF, physicalFFFFF, holes/ROM/CGA and low-byte failure prefixes. Reuse the proven coherent scroll span discipline for REP only after preserving read/write order, overlap replication, per-byte metadata and every per-element interrupt checkpoint. These are generic CPU/memory improvements, not BIOS/DOS recognition.

A broad translator may eventually combine these paths with decoded operands and native branching. It must then solve stores into its own source, runtime segment changes, precise faults and bounded REP using the same semantic contracts. There is no credible measured near-XT estimate for that larger design yet.

## Retained artifacts and provenance

- `profile-summary.json`: complete opcode/module/coverage/locality results.
- `work/build/native-dos-boot.json`: actual successful native DOS report, exactly equal to the frozen uninstrumented counterpart.
- `work/build/native-profile-records.bin`:601,936 packed24-byte records, schema `<IIIIHHBBBB`: physical, cycles, completed, epoch_delta, CS, IP, actual final opcode, passive following byte, passive prefix count, script phase.
- `work/build/{native,cpu}-pc-cycles.bin`:65536 little-endian64-bit native-PC counters; independent exact summation assertions in `analyze.py`.
- `instrument.py`: reproducible private host instrumentation; `analyze.py`: deterministic calculations; `frozen-input-manifest.json`: pre-instrumentation source/target hashes; `manifest.json`: final source/output identities and equality proof.
- `instrumented-native-dos.log`: actual1/1 pass, no full5701 repetition.
- First wrong-directory `zig build` failed before any build because the enclosing repository has no build.zig; its log was moved immediately into this scratch directory. It did not modify shared source or targets. Intel PDF direct fetch returned403 and local `pdftotext` was unavailable; no manual binary was retained. Source facts above use the search-indexed primary Intel scan and accessible primary QEMU documentation. No third-party source code or license-bearing implementation was copied into a proposed target change.
