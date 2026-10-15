# Next bounded slice: physical cache probe and original-8088 execution

Foundation, REU primitive, 20-bit addressing and coherent byte cache are verified in Peddle; shared DMA/cache probes pass VICE. Continue the full plan with local commits and no pushes. Target remains original 8088 / XT, assembly runtime, Zig/Peddle assertions and minimum 4 MiB REU.

1. Physical integrity at 1/16/64 MHz has now passed with verified REU/configuration recovery. Reuse the documented Terminal-owned runner only when target behavior warrants another slow run. Calibrated timer/DMA measurements remain outstanding; do not infer throughput from REST timing.

2. Initial segmented word helpers and CPU execution are implemented; see CPU_IMPLEMENTATION.md. The real disk-1 entry now reaches unsupported XOR at 0000:7C37 after its jump and CLI. Expand arithmetic/defined flags and ModR/M register/memory operands next, then segment moves, stack/call/return and interrupt routing toward the real boot sector. Preserve the original-8088 corner policy and add direct hardware edge evidence where the imported corpus is silent.
3. Use the existing step interface, guest-program tests and pinned hardware corpus for each opcode family. Default tests include 41 representative/boundary hardware cases; make test-cpu-corpus runs all 481 current cases. Add families/rows deliberately from the pinned source, preserving license/hash evidence. No native DOS INT 21h replacement.
4. Add coherent range access for later BIOS disk reads/writes and ROM loading before using any direct REU path. Grow DOS image helpers as integration fixtures need them. Preserve originals and own all mutation clones.
5. Measure address generation, dispatch and fast span fetch with real assembly. Public ALL_RAM warm byte read currently costs 221 host CPU cycles; every-byte use is not the final optimized fetch design. Calibrate physical DMA/timer costs before extrapolating throughput; 512-byte pages remain a candidate.

Before CPU design consult [existing emulator references](../docs/EXISTING_EMULATORS.md). NES86 supplies useful techniques; implement required behavior regardless of reference coverage. Substantial reuse requires pinning, notices, explicit license treatment and independent tests.

Normal loop: `make test` (55 Zig/Peddle + 15 tooling tests at this checkpoint, about six seconds warm). Use `make test-reference` when reference fixtures change; `make test-vice` for low-level DMA changes, `make test-cache-vice` for pager/probe changes. Existing VICE captures can be rechecked without another slow run:

```sh
python3 build_support/vice_probe.py --verify-existing logs/vice_auto_20261014_222223
python3 build_support/vice_probe.py --kind cache --verify-existing logs/vice_auto_20261014_225535
```

The checker rejects mismatched executable bytes; retain/rebuild the corresponding probe before checking old evidence. Compact results are tracked in `agentworking/evidence/`; raw DOSBox runs and VICE logs stay ignored here.

Limits: ROM sentinels are a banking test aid; unknown I/O fails; DMA does not stall the mock CPU. Cache owns REU guest arena only. API is non-reentrant, requires normal RAM/I/O mapping, and has no bulk/native-writer bypass. Cold init discards ownership; flush/unpin first. Only the documented initial instruction subset exists; BIOS/UCI/IEC, target boot and physical throughput remain absent. See [memory contract](../docs/MEMORY_IMPLEMENTATION.md).
