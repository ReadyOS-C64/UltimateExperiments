# Next bounded slice: REU transfer contract and measurement probe

M0 foundation is verified. Continue implementing the full plan; user authorized local commits and no pushes.

1. Implement a bounded assembly REU transfer interface with explicit addresses/counts and bank/IRQ preservation. Keep all used register semantics documented.
2. Build a register-level REU model in the project Peddle bridge, checking the relevant original/VICE/Ultimate semantics rather than inheriting simplified sibling shims blindly.
3. Zig tests execute the real transfer routine for round trips, unaligned/cross-bank ranges, 64 KiB length encoding, fixed-address modes if used, register/status postconditions, and rejected ranges. DMA cycle cost remains separate from CPU cycle counts.
4. Add host benchmark summaries for setup/transfer/translation candidates. Prepare the same vectors as a standalone physical/VICE probe, then inventory the actual C64U firmware/configuration using existing harness controls before scheduling its slower run.
5. Continue into the guest 20-bit address helpers and coherent page cache. Preserve whole-image and real-DOS scope; no native INT 21h replacement.

Normal loop: `make test`; use the slower `make test-reference` only when reference fixtures/workflow change. Existing reference boot is recorded in `agentworking/evidence/dosbox-reference-20261014.json` and raw run files remain under `agentworking/runs/reference-20261014-220319`.

Foundation limitations: ordinary-RAM Peddle bus; no C64 ROM/banking/IRQ timing, REU/UCI behavior, guest instructions or target DOS boot yet. Budget failures retain last host registers and stack high-water; richer guest traces come with the interpreter.
