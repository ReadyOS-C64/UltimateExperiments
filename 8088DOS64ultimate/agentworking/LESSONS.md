# Current lessons

- Execute the real DOS kernel. Native BIOS acceleration and guest DOS-call replacement are different architectures; only the former fits this scope.
- The target is assembly. ZeroPage's value here is its Zig/Peddle test structure, labels, bounded execution and assertions.
- Test the actual linked machine code; separately test the oracle, fixture parser and hardware mocks. A permissive mock can make incorrect assembly look right.
- Peddle delegates clock advancement to its embedder. Step bounded microcycles, increment clock explicitly, and assert known instruction timings before relying on cycle budgets.
- Existing REU shims are deliberately incomplete and differ at their memory boundary. Validate the used register subset before inheriting it.
- Keep guest page-cache ownership coherent across BIOS transfers, rendering, debugger writes and REP. REU can contain stale bytes while a dirty frame exists.
- Budget code, cache metadata, fonts, bitmap, stack and I/O explicitly. A valid total does not ensure the bitmap and screen share a VIC bank.
- File offsets and REU addresses have different widths. The 20 MiB milestone must cross 16 MiB in tests.
- UCI is asynchronous; completion is a state/queue protocol, not a fast CPU polling count or an initial return to IDLE. Verify transferred byte counts.
- The supplied disk images are useful real fixtures, not pristine configuration templates. Preserve them and record derivative changes.
- DOSBox boot is required for a DOS reference; its built-in shell/reported version and cycle setting prove neither real DOS behavior nor XT timing.
- 80-column text preserves guest attributes even when its rendered colors are approximated. Never corrupt guest VRAM to make the host picture easier.
- VICE warp accelerates development; real C64U measurements determine 64 MHz/REU/UCI performance.
- Keep all new context and scratch inside this project. A dirty sibling toolchain cannot be identified by HEAD alone.
