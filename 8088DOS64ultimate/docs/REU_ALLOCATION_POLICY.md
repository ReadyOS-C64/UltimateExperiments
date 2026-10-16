# REU allocation and performance

The user explicitly authorized additional REU use on 2026-10-16 whenever saving that memory would make the emulator slower. Speed takes priority over a small REU footprint. The supported minimum remains 4 MiB; larger configured REUs may enable larger caches or additional resident assets. This permission changes the allocation policy, not the installed hardware size or any measured performance result.

Every allocation must name its owner, lifetime, bounds, and overlap rules. Use the configured, validated capacity for all DMA and Ultimate DOS direct transfers. The firmware's 16 MiB address limit does not prove that 16 MiB is installed or enabled. Do not probe capacity destructively while guest memory or user media occupies REU.

Within the 4 MiB profile, spend available memory on distinct live floppy buffers, safe incoming-media staging, immutable code overlays and useful disk caches before reducing cache capacity. SETUP and the emulator have different lifetimes and may use separate maps. Do not reserve all three installation source images permanently after SETUP exits.

For larger profiles, assign additional memory to a disjoint optional arena above the 4 MiB baseline. Candidates include more HD extents, cached replacement floppy images, larger verified I/O slabs, and additional immutable or compiled code blocks. These require explicit backend/metadata changes and measurements: simply increasing the address reservation does not accelerate the current emulator. The current HD backend supports at most 32 cached 32 KiB extents; allocating more REU does not automatically increase that limit. A complete 20 MiB HD will still require backing-file access on a 16 MiB REU.

Keep the 4 MiB guest-address mappings and live-media semantics stable across capacity profiles. A selected larger profile must fail before modifying guest state if the configured capacity cannot support it. Tests must cover minimum capacity, larger capacity, exact final-byte bounds, overflow/wraparound, overlapping owners, and both successful and failed transfers. Preserve whole baseline REU contents during physical testing; extending a test beyond the first 4 MiB requires extending its backup, retention and recovery coverage first.

Prefer measured reductions in physical elapsed time and transfer counts over guessed gains. Larger caches cannot by themselves fix instruction dispatch, guest-memory translation, or overlay churn. Keep the existing IRQ, REP and clock sampling policy until a separately verified optimization permits a change. Peddle CPU clocks remain model evidence, not C64 Ultimate elapsed-time or 4 MHz 8088 equivalence.

The current production layout is recorded in `agentworking/MEMORY_BUDGET.md`. The independent A/B overlay, incoming-floppy arena and START handoff reservations remain private implementation candidates until their combined linker maps and runtime ownership tests pass.
