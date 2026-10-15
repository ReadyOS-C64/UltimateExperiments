# XT performance assessment — 2026-10-15

The emulator has not achieved the intended near-4 MHz 8088 performance. Its current model evidence shows a substantial simple-instruction overhead, but does not establish a measured whole-DOS slowdown factor. The most recent optimization reduced modeled CPU cost of the retained DOS workflow by **8.827%**. For the same modeled work that corresponds to **1.0968×** throughput, not an 8.827% whole-machine speed comparison against an XT.

This assessment concerns runtime22f8209108fca953f783116c0a6cf5bd0c788e08b586421e30406f6129be0369 and unit8a84329ce41850fa42d89c0ee5f42d4e6f77a000a2c0a9abce8cae9c0092d94f. No benchmark, build, hardware action or shared-file edit was executed here. [assessment evidence](../agentworking/evidence/xt-performance-assessment-20261015.json) pins the exact evidence read and all arithmetic.

## What the actual retained model measures

The independent combined-boundary test executes the real linked `dos64_native_timer_step`, after one warm-up NOP establishes sequential fetch. It measures32 further NOPs with IF set and no eligible interrupt, with identical scripted raw-clock inputs in baseline/candidate. Full guest state, RAM and CIA accesses are checked. Costs include the instruction and its native timer/PIC boundary, entry through return; they omit the caller's JSR and outer runtime work.

| Scripted raw tick increment per instruction | Current modeled CPU clocks for32 | Average clocks | Algebraic time at ideal64 MHz |
| --- | ---: | ---: | ---: |
| 0 | 43,136 | 1,348 | 21.0625µs |
| 1 | 56,682 | 1,771.3125 | 27.6768µs |
| 100 | 74,445 | 2,326.40625 | 36.3501µs |

The best fixed-raw case implies about **47,478 NOP/s** if every counted host clock runs at64MHz. It is an optimistic diagnostic conversion, **not a physical rate**: a real CIA clock advances during execution, while these test clocks are deliberately seeded. Real MMIO/REU/VIC stalls and the outer scheduler/display work are also excluded. The older CPU-only429-cycle NOP figure excludes these timer/PIC boundaries and is not a fresh benchmark of the current complete runtime.

The genuine modeled DOS workflow uses598,702 guest instructions and2,616,062,815 modeled CPU clocks, versus2,869,345,809 before this optimization. That workload includes development observation commands. Its mix and cost-derived guest clock prevent extrapolation to a general XT ratio.

## Intel comparison and why “20× slower” needs qualification

Intel's NOP table gives3 clocks/1 byte. Its timing discussion assumes the instruction is already prefetched and warns that actual sequence timing can exceed summed table timings; exact timing requires execution measurement. At4MHz,3 clocks are0.75µs. Comparing that nominal table entry with our best fixed-raw21.0625µs yields28.083×, which is **not an actual sustained8088 throughput comparison**. [Intel8086 Family User's Manual, printed2-50/2-51/2-62](https://www.inf.pucrs.br/~calazans/undergrad/orgcomp_EC/mat_microproc/intel-8086_family_Users_Manual.pdf).

Intel's8088 datasheet specifies an8-bit data bus and at least4 clocks per bus cycle, with wait and idle states possible. Thus an ideal uninterrupted opcode-byte supply at4MHz has a ceiling of1million bytes/s. **If** a long one-byte NOP stream actually sustained one NOP per4 clocks, it would run about21.06× faster than our optimistic fixed-raw model conversion. The bus ceiling alone does not prove that actual sustained rate. This conditional estimate must not be presented as a measured20× whole-DOS slowdown. [Intel8088 datasheet, printed10–11](https://www.ceibo.com/eng/datasheets/Intel-8088-Data-Sheet.pdf).

A simpler useful statement is that our best fixed-raw full instruction boundary takes as much ideal elapsed time as84.25 clocks on a4MHz8088. Simple guest instructions normally require far less work than that nominal comparison budget. Different instruction mixes, memory access, branches, interrupts, graphics and disks will produce different relative speeds.

## Physical workflow timing is not a benchmark

The accepted native VER/DIR run reached645,453 guest instructions at107.320121708s, with33screen observations, native image import and keyboard/pagination waits. Those intentional pauses, captures and start-up costs make instructions/107.320s unsuitable as an emulator compute rate. The later DIR/W observation-heavy run has the same limitation. A single old/new physical workflow time is also not an isolated measurement of the optimization.

## Next matched measurement

1. Build a small original8088-compatible DOS COM benchmark, loaded normally by genuine DOS on both systems. Retain its exact source, binary and results; use deterministic checksums so speed cannot hide incorrect work.
2. Measure fixed register/arithmetic, branch, stack, memory read/write, REP-byte/word, and divide workloads separately. Add working sets that fit and exceed the native cache, plus a DOS text-output workload reported separately from CPU workloads. Include enough repetitions to dwarf start/stop overhead.
3. On the C64U use the existing owned CIA elapsed source around the work, with no intermediate snapshots or key injection; keep all current IRQ/REP sampling semantics. Retain Manual64/PAL/REU/badline settings and executable/source identity. Measure timer and observation overhead explicitly rather than subtracting guessed costs.
4. Run the exact guest binary on a measured4MHz original8088 system, or a reference whose8088 prefetch/bus/wait timing is independently validated. Report4.77MHz separately if that is the available XT. DOSBox configured “cycles” is not a MHz conversion or sufficient timing baseline.
5. Report elapsed-time ratios per workload, output/checksum equality and repeated-run spread. Keep disk loading and terminal rendering separate from core throughput; add a representative DOS workflow only once both timed endpoints are defined.

Suggested concise user wording: “It is still well below our4MHz8088 goal. The latest change cuts modeled DOS CPU work by8.8%; our best warm NOP with timer/interrupt handling still costs1,348host cycles, about21µs at ideal64MHz. That shows a large gap on simple instructions, but we need the same timed benchmark on both systems before quoting an overall XT percentage.”
