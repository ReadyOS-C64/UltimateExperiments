# Next bounded slice: physical cache probe and original-8088 execution

Foundation, REU primitive, 20-bit addressing and coherent byte cache are verified in Peddle; shared DMA/cache probes pass VICE. Continue the full plan with local commits and no pushes. Target remains original 8088 / XT, assembly runtime, Zig/Peddle assertions and minimum 4 MiB REU.

1. Physical integrity at 1/16/64 MHz has now passed with verified REU/configuration recovery. Reuse the documented Terminal-owned runner only when target behavior warrants another slow run. Calibrated timer/DMA measurements remain outstanding; do not infer throughput from REST timing.

2. Freeze original-8088 multi-byte operand behavior from hardware vectors/primary manuals before a read16 fast path. Segment/IP updates and 20-bit wrap are already implemented separately. Pin the imported corpus and its license.
3. Start actual CPU execution through the memory API: instruction fetch, prefixes/ModR/M, arithmetic/flags and a bounded single-step interface. Build small guest programs and original-8088 instruction cases around linked assembly. Expand toward executing the supplied boot sector and synthetic BIOS; no native DOS INT 21h replacement.
4. Add coherent range access for later BIOS disk reads/writes and ROM loading before using any direct REU path. Grow DOS image helpers as integration fixtures need them. Preserve originals and own all mutation clones.
5. Measure address generation, dispatch and fast span fetch with real assembly. Public ALL_RAM warm byte read currently costs 221 host CPU cycles; every-byte use is not the final optimized fetch design. Calibrate physical DMA/timer costs before extrapolating throughput; 512-byte pages remain a candidate.

Before CPU design consult [existing emulator references](../docs/EXISTING_EMULATORS.md). NES86 supplies useful techniques; implement required behavior regardless of reference coverage. Substantial reuse requires pinning, notices, explicit license treatment and independent tests.

Normal loop: `make test` (41 Zig/Peddle + ten tooling tests at this checkpoint, about four seconds warm). Use `make test-reference` when reference fixtures change; `make test-vice` for low-level DMA changes, `make test-cache-vice` for pager/probe changes. Existing VICE captures can be rechecked without another slow run:

```sh
python3 build_support/vice_probe.py --verify-existing logs/vice_auto_20261014_222223
python3 build_support/vice_probe.py --kind cache --verify-existing logs/vice_auto_20261014_225535
```

The checker rejects mismatched executable bytes; retain/rebuild the corresponding probe before checking old evidence. Compact results are tracked in `agentworking/evidence/`; raw DOSBox runs and VICE logs stay ignored here.

Limits: ROM sentinels are a banking test aid; unknown I/O fails; DMA does not stall the mock CPU. Cache owns REU guest arena only. API is non-reentrant, requires normal RAM/I/O mapping, and has no bulk/native-writer bypass. Cold init discards ownership; flush/unpin first. No guest instructions, BIOS/UCI/IEC, target boot or physical performance result exists. See [memory contract](../docs/MEMORY_IMPLEMENTATION.md).
