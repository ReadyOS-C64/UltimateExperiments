# Next bounded slice: strings and conditional flow toward the real boot sector

Implementation is authorized: progress with verified local commits and no pushes. Preserve original 8088/XT, assembly runtime, Zig/Peddle actual-code assertions, minimum 4 MiB REU and real DOS3.3. Read STATUS, DECISIONS and CPU_IMPLEMENTATION before continuing.

1. The unchanged disk-1 sector now completes16 instructions through arithmetic, SS/SP setup, segment moves, LDS and stack operations; next missing instruction is LODSB AC at 0000:7C51. Implement string loads/stores/moves/compares/scans, DF progression, segment rules and bounded REP continuation; add Jcc/LOOP/JCXZ and needed arithmetic/shift/exchange forms. Use actual sector traces to choose the next bounded family, without replacing DOS behavior.
2. Expand the pinned original 8088 corpus deliberately for each family, retaining source hashes, masks and aliases. Current quick 338/full 1,622 hardware cases plus independent boundary tests pass. Tests compare full 1 MiB RAM. Opcode0F POP CS, indirect stack/call forms and undocumented LEA/LES/LDS register forms still need an explicit audited policy. Trap/interrupt delivery is absent even though IF/TF and shadows are represented.
3. Add normal INT/IRET routing and synthetic BIOS ROM/IVT/BDA initialization. The current host-loaded sector uses a zero IVT and is not a boot result. Preserve guest interrupt hooks; never replace INT21h or native-load COM/EXE as a shortcut.
4. Add coherent range access for BIOS disk reads/writes and ROM loading before any direct REU path. Whole floppy slots and file persistence/UCI/IEC are still future work. Preserve original images and mutate owned clones only.
5. Measure dispatch/address generation and implement fast span fetch based on evidence. Public ALL_RAM warm byte read still costs 221 CPU cycles; host test acceleration is not target optimization. Calibrated physical DMA/timer costs and XT workload ratios remain outstanding.

Normal loop: `make test` (75 Zig/Peddle + 15 tooling, measured 5.21 seconds with 338 hardware cases). Broader gate `make test-cpu-corpus` passes 1,622 cases in 11.57 seconds including build checks. Reuse user-authorized 2–3 subagents for disjoint material work and coordinate file ownership/global checks.

Slow lanes only when behavior warrants them: `make test-reference` for reference fixture changes, `make test-vice` for DMA changes, `make test-cache-vice` for pager/probe changes, Terminal-owned physical runner for hardware behavior. Prior physical cache integrity passed 1/16/64 MHz with verified recovery; it does not establish throughput. Existing captures were rechecked against unchanged executable bytes on 2026-10-15:

```sh
python3 build_support/vice_probe.py --verify-existing logs/vice_auto_20261014_222223
python3 build_support/vice_probe.py --kind cache --verify-existing logs/vice_auto_20261014_225535
```

All scratch/runs stay in this project's agentworking. Errors remain terminal host diagnostics with possible partial CPU/memory effects; no automatic retry. Startup still initializes and waits, no target BIOS/UCI/IEC/display/DOS boot yet.
