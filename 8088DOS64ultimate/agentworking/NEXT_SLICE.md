# Next bounded slice: guest physical addressing and coherent paging

M0 and the REU functional primitive are verified. Continue the full plan with local commits and no pushes. Target is original 8088 / XT, assembly runtime, Zig/Peddle assertions and minimum 4 MiB REU.

1. Implement segment-base/offset to 20-bit physical-address helpers and independently test aliases, carry and 1 MiB wrap. Keep multi-byte boundary policy explicit; check original-8088 hardware vectors/manuals before selecting it. An 8086/C reference's linear word load is not proof.
2. Implement a coherent REU-backed page cache before instruction decode. Cover clean/dirty eviction, physical aliases, pinned frames, failures and metadata ownership. Start with 512-byte candidate pages; do not present that as a measured optimum. Enforce REU capacity/ownership above the trusted primitive.
3. Inventory actual C64U firmware/configuration through the established Terminal-owned harness workflow, then run the shared probe preserving prior state and using owned paths. A default host in another project is not proof of current configuration. Add elapsed-time measurements after calibrating timer behavior at turbo speeds.
4. Add host CPU setup-cycle summaries separate from mock DMA bytes/stalls; compare page sizes and interpreter costs as real routines become available. Do not infer physical 64 MHz speed from Peddle CPU clocks.
5. Grow DOS image helpers (inventory/list/extract/geometry/check), then safe owned-clone mutations when integration fixtures require them. Current inventory and DOSBox reader are not complete general disk helpers. Preserve actual DOS boot scope; no native INT 21h replacement.

Before CPU design consult [existing emulator references](../docs/EXISTING_EMULATORS.md). NES86 supplies useful techniques; implement required behavior regardless of reference coverage. Substantial reuse requires pinning, notices, explicit license treatment and independent tests.

Normal loop: `make test` (26 Zig/Peddle + nine tooling tests at this checkpoint). Use `make test-reference` when reference fixtures/workflow change; `make test-vice` when DMA/banking/probe behavior changes. Existing VICE results can be rechecked without a new slow run:

```sh
python3 build_support/vice_probe.py --verify-existing logs/vice_auto_20261014_222223
```

The checker rejects mismatched executable bytes; retain/rebuild the corresponding probe before checking old evidence. Compact results are tracked in `agentworking/evidence/`; raw DOSBox runs and VICE logs stay ignored here.

Limits: ROM sentinels are a banking test aid, not executable ROM; unknown I/O fails; DMA does not stall the mock CPU. The primitive depends on its future caller for splitting and allocator ownership. No guest instructions, UCI protocol, target boot or physical performance result exists. Budget failures retain last host registers and stack high-water; richer guest traces come with the interpreter.
