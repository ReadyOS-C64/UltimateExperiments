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
