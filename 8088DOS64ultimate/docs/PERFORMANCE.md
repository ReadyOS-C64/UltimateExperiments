# Performance hypothesis and experiments

**Near-XT speed is unproven.** Target a 4.77 MHz 8088 workload baseline (the user's approximate “4 MHz” PC), not a ratio of CPU MHz or DOSBox cycle settings. The 64 MHz host has about 13.4 nominal host cycles per XT cycle before display/bus/DMA effects. This is a budget, not an instruction-throughput prediction.

Proposed review criterion: report the speed ratio for every benchmark and aim for at least 0.75× XT on a declared representative CPU/utility set, with interactive input/presentation normally within 100 ms. This threshold is a planning definition of “pretty close,” subject to user review and measurement. Never hide a poor working-set result behind a fast disk-copy average. Raw CPU throughput and end-to-end utility latency are separate results.

## Cost model

```text
elapsed ≈ executed_host_CPU_cycles / measured_effective_host_rate
        + REU_transfer_time + UCI_or_IEC_wait_time
        + rendering_and_host_service_time_not_already_counted
```

Avoid double counting if a hardware elapsed measurement already includes DMA/rendering. Peddle clock reports CPU instruction cost; model DMA separately until calibrated. A CPU-cycle count divided by 64,000,000 is only a first estimate for RAM-resident code. VIC contention and I/O accesses do not necessarily run at that rate. [Ultimate turbo documentation](https://1541u-documentation.readthedocs.io/en/latest/config/turbo_mode.html).

The pasted chat's 4 MB/s REU figure is **not verified**. If that were the effective transfer rate, one-way minimum costs would be:

| Page bytes | Transfer at 4,000,000 bytes/s | Nominal 64 MHz cycles lost |
|---:|---:|---:|
| 256 | 64 µs | 4,096 |
| 512 | 128 µs | 8,192 |
| 1,024 | 256 µs | 16,384 |
| 2,048 | 512 µs | 32,768 |

These exclude setup, and dirty eviction adds write-back. At a hypothetical average 12 XT clocks per instruction, matching XT allows roughly 161 host cycles. If the hit path already costs 120, only 41 remain: an 8,192-cycle 512-byte miss could occur roughly once per 200 guest instructions before using that headroom, even before dirty writes/rendering. Those input values are illustrative, not measurements; the calculation explains why cache locality deserves an early experiment.

## M1 measurements

1. **Host baseline:** identical assembly loops in RAM, under BASIC/KERNAL RAM, and with I/O; 1/16/64 MHz; display active/blank and badline settings recorded. Use elapsed hardware timers/host observations with calibrated units, not turbo-scaled delay loops.
2. **REU:** setup overhead and transfers of 1, 16, 64, 256, 512, 1024, 2048, 4096 bytes in both directions; aligned/unaligned/cross-bank; one clean miss and dirty write-back+load; repeated warm runs. Report median, p95, bytes/s and configuration.
3. **Interpreter:** representative assembly handlers plus real dispatch/fetch/address/flags: register MOV, ADD/ADC/CMP, taken/not-taken branches, memory MOV, stack CALL/RET, segment changes, REP, MUL/DIV. Measure realistic sequences, not isolated helper bodies alone.
4. **Paging:** fixed host capacity including metadata, page size sweep, warm/cold starts, tight loop, sequential scan, two-stream copy, random and strided access, aliased segments, working set above cache, repeated code/data eviction. Count misses per guest instruction and per access, dirty evictions, transfer bytes, effective cycles.
5. **Presentation:** full 40/80 redraw, one-cell edit, scroll, palette changes, direct VRAM streams, mode 4/6 conversion; guest CPU share and input latency with display active.
6. **Storage:** whole 360 KiB import/export and small/large HD extent operations, UCI vs IEC, short/failing transfers. Separate underlying file latency from guest BIOS/CPU cost.

## Reference and workload suite

Use an original 4.77 MHz XT measurement when available, or a carefully configured cycle-accurate PC/XT reference such as [MartyPC](https://github.com/dbalsom/martypc), recording machine/ROM/CPU version and whether results are measured or simulated. DOSBox-X is convenient for DOS functional comparisons, but its configurable `cycles` value is not a calibrated original-PC clock.

Start with source-controlled guest microbenchmarks; add actual boot-to-prompt, DIR on known layouts, TYPE/redirect, SORT on fixed data, COMP/FC, CHKDSK, DISKCOPY, and scripted EDLIN/DEBUG workloads as supported. Compare identical images, inputs, warm/cold conditions and stopping criteria. Where host storage deliberately outperforms historical floppies, label that benefit separately from CPU emulation speed.

## Optimization order and proof

1. Optimize common dispatch and register paths; reserve suitable ZP pairs.
2. Fast contiguous instruction fetch and cached segment bases, with generation/boundary checks.
3. Select page size/replacement from observed DOS traces, not a synthetic sequential-copy winner.
4. Specialize common ModR/M paths and stack accesses without duplicating semantic bugs.
5. Bound/coalesce display work, then safe block transfers for REP and BIOS I/O with coherence.
6. Evaluate lazy flags with PUSHF/LAHF/interrupt tests and full corpus coverage.
7. Consider compact predecode only after measuring its RAM cost and invalidation overhead. Dynamic translation is a separate later decision, not a v1 assumption.

For each change save baseline artifact/hash, cycles, elapsed times, linked bytes, cache hit/miss profile, and functional results. Reject optimizations that win a microbenchmark while regressing representative DOS work or persistence correctness. A compiler change is not a substitute for measuring the assembly actually executed.

## Measured interpreter baseline — 2026-10-15

`make profile-cpu` executes six real linked 6510 workloads in cold and warm cache states, producing 12 samples in `build/cpu-profile.json`, retained as [profile evidence](../agentworking/evidence/cpu-profile-baseline-20261015.json). Workloads are a register/branch loop, dirty ModR/M copy, stack calls, 256-byte REP, 20 KiB REP and multiply/divide. The harness validates exact final registers and all 1 MiB RAM against independently constructed expectations, records source/binary identities and bounds each call/sample. All profile state checks passed. This is the pre-optimization baseline; unlinked fetch/PC-port/video work is excluded from accepted performance claims.

| Warm sample | Measured cost |
|---|---:|
| Register/branch loop | 1,762.55 host CPU cycles per guest instruction |
| Dirty memory copy | 2,192.84 host CPU cycles per guest instruction; 5,492.82 per copied byte |
| Stack calls | 1,802.78 host CPU cycles per guest instruction |
| 256-byte REP copy | 1,127.23 host CPU cycles per copied byte |
| 20 KiB REP copy, larger than cache | 1,081.19 host CPU cycles per copied byte |
| Multiply/divide loop | 2,169.74 host CPU cycles per guest instruction |

Each interval starts at the assembly step entry and includes RTS. It excludes the synthetic caller's six-cycle JSR, initialization, final validation flush, REU DMA stalls, VIC contention, rendering, UCI/IEC waits and physical elapsed time. REP instruction count alone gives a misleading per-instruction ratio, so copied bytes and scheduling calls are reported too. Warm means the same fixture/cache after its previous workload and validation flush, with guest state reset; a working set larger than the cache does not become fully resident by that definition.

The warm register result exceeds the illustrative 161-cycle instruction allowance above by about eleven times before missing physical costs. This identifies substantial optimization work; it is not a calibrated XT ratio, since no corresponding guest workload timing on an XT is measured. The earlier 221-cycle public warm byte read remains a helper measurement. Host test-runner speedups reduce validation time without reducing these target costs.

The genuine reset-to-IO.SYS handoff separately reports 392 completed guest instructions and 12,019,126 native step cycles, excluding 20,835,495 setup cycles. Bulk BIOS work and REP make that aggregate unsuitable as a register-dispatch benchmark. Complete boot-to-prompt latency, physical timer/DMA calibration and representative DOS utility ratios remain open.


Final frozen-baseline profile rerun passed 1/1 in 3.27 host seconds: 10,314 guest instructions, 12,902 scheduling calls, 65,680,572 host CPU cycles, 19,297,856 native instructions, 223 DMA operations and 114,176 DMA bytes. All state checks passed. Ordered source identity is `95fd4e36c3744e01fd0ddd61f5bbd2bafdd993c489f2bb70029a00e919df1f02`; final linked unit PRG SHA-256 is `c035afe39e8c25239a7b17664b36c9688186e29b6adbef6ff01d3f3a2c01e6ab`. The table uses this final rerun. Counter totals are not physical timing; the instruction-weighted aggregate combines very different workloads and does not replace their individual costs.

## Integrated fetch comparison

Against source-pinned baseline `49ac73f`, the same 12 workloads and all final-state checks pass after the fetch change. Warm cycles per guest instruction: register loop **1,383.78** (21.49% reduction), dirty memory **1,744.48** (20.45%), stack/calls **1,616.05** (10.36%), multiply/divide **1,774.18** (18.23%). The 20 KiB REP workload increases about 0.08%; its DMA counts are unchanged. Aggregate CPU cycles fall 65,680,572→61,735,896, but this weighted total is not an XT ratio. The same exclusions and lack of calibrated physical timing apply. [Source identities, complete samples and baseline comparison](../agentworking/evidence/fetch-optimization-20261015.json).


## Resident video/adjust/BIOS profile checkpoint

The combined verified slice passes 1/1 profiling in 3.28 host seconds, with all 12 exact-register/full-RAM samples accepted. Ordered identity `9f596825c60881eb349a04b9ca26feccdba29d12eb12f0c4f785ceac8f766a9c` and [current slice evidence](../agentworking/evidence/video-adjust-bios-20261015.json) retain linked/source identities and configuration. Total work is unchanged at 10,314 guest instructions, 12,902 scheduling calls, 223 DMA operations and 114,176 bytes; measured CPU cycles are 62,013,116 and native instructions 18,258,732. This profile superseded earlier costs at that checkpoint; each table remains a pinned historical comparison as later modules are integrated.

| Video/adjust checkpoint warm sample | Measured host CPU cost |
|---|---:|
| Register/branch loop | 1,410.56 cycles per guest instruction |
| Dirty memory copy | 1,770.94 cycles per guest instruction; 4,436.00 per copied byte |
| Stack calls | 1,643.29 cycles per guest instruction |
| 256-byte REP copy | 1,114.48 cycles per copied byte |
| 20 KiB REP copy | 1,082.04 cycles per copied byte |
| Multiply/divide loop | 1,802.75 cycles per guest instruction |

The same step-entry→RTS interval, caller/setup/validation exclusions and unmodeled physical DMA/VIC/UCI/rendering costs apply. Adding linked modules changes address placement and cycle details; do not attribute every difference to a new algorithm. Genuine IO.SYS continuation separately reports 26,023,384 step cycles through missing INT 1Ah after 2,542 instructions, plus 26,360,254 setup cycles; handoff itself is 392 instructions/11,860,775 step cycles. This is still short of boot-to-prompt and is not calibrated physical elapsed time or an XT ratio.


## Clock/keyboard/UCI slice and long DOS cost

The final 12-sample profile passes 1/1 with exact registers/full 1 MiB RAM: source identity `87eab9545143199ee360ca7831af65876e61792424090f891a72300d89927770`, **61,959,008** CPU cycles, **18,258,732** native instructions and unchanged **10,314** guest instructions/**12,902** calls/**223** DMA operations/**114,176** bytes. [Current slice evidence](../agentworking/evidence/clock-keyboard-uci-20261015.json) pins the measured binary and source. Warm register/dirty-memory/stack/multiply-divide costs are respectively **1,409.40 / 1,770.23 / 1,642.62 / 1,797.97** cycles per guest instruction. Warm 256-byte/20 KiB REP costs are **1,113.45 / 1,081.04** cycles per copied byte. Earlier tables remain source-pinned historical comparisons.

The explicit real-DOS command lane passes in **18.83 host wall seconds** (16 test seconds), reaching the first prompt at **193,673** guest instructions and finishing VER/exact DIR/returned prompt at **588,937**. It uses **1,269,694,142 CPU-step cycles**, **9,698,220 support cycles** for coherent screen observations/assembly key enqueue and **26,364,820 setup cycles**, reported separately. CPU cycles exclude caller JSR and DMA stalls; host test duration is not C64U elapsed boot latency. [Built-ins evidence](../agentworking/evidence/dos-command-builtins-20261015.json) records stopping criteria and identities.

The historical first native CIA/VIC attempt failed at Manual 1 MHz, error 3 (`01e1000003000000`); configuration restoration/reset-resume succeeded and 16/64 MHz calibration was not reached. That rejected run accepted no elapsed-clock/turbo-independence calibration or XT-throughput conclusion. The corrected raw-domain validation below supersedes the physical clock uncertainty; native deadline conversion remains a separate integration. The genuine Peddle prompt does not measure native runtime, rendering, storage or keyboard latency.


The [genuine DOS workload research](../agentworking/research/dos-performance-20261015.md) independently instruments the frozen baseline without adding modeled target instructions. Its native-PC histogram sums exactly to the reported step clocks; DIR accounts for 62.40% of this script's step work. This identifies real workload costs beyond the six microbenchmarks. A private optimization experiment in that report measured an 8.276% gain at a net 103 MAIN bytes, but it is not integrated or accepted in this slice. Its result must not be applied to the current source/profile or reported as physical speed.


The corrected [physical clock matrix](../agentworking/evidence/c64u-clock-20261015.json) now passes Manual 1/16/64 MHz on firmware 3.14/FPGA 121/core 1.47. Across 100 PAL raster frames, CIA deltas are **1,965,627 / 1,965,599 / 1,965,600**, all within **1,965,600 ±1,008**, with zero retries and **28 ticks** total cross-speed spread. This accepts raw CIA-versus-raster domain/turbo validation. It does not calibrate interpreter/REU throughput, external absolute time or an XT ratio, and is not yet wired into the native scheduler/UCI deadline conversion. The rejected first attempt remains historical evidence; its exact cause is unproved.
