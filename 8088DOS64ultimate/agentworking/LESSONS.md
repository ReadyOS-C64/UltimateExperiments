# Current lessons

- Execute the real DOS kernel. Native BIOS acceleration and guest DOS-call replacement are different architectures; only the former fits this scope.
- The target is assembly. ZeroPage's value here is its Zig/Peddle test structure, labels, bounded execution and assertions.
- Test the actual linked machine code; separately test the oracle, fixture parser and hardware mocks. A permissive mock can make incorrect assembly look right.
- Peddle delegates clock advancement to its embedder. Step bounded microcycles, increment clock explicitly, and assert known instruction timings before relying on cycle budgets.
- Existing REU shims are deliberately incomplete and differ at their memory boundary. Validate the used register subset before inheriting it.
- Keep guest page-cache ownership coherent across BIOS transfers, rendering, debugger writes and REP. REU can contain stale bytes while a dirty frame exists.
- Write back before discarding a dirty owner; unpublish it before a new DMA load can overwrite the frame, and publish the new owner only on success. Retain dirty authority when write-back fails.
- Pin acquired pointers, save frame handles across calls, and release before yielding. Use distinct page patterns in pin tests; zero-filled pages can hide incorrect reuse.
- Budget code, cache metadata, fonts, bitmap, stack and I/O explicitly. A valid total does not ensure the bitmap and screen share a VIC bank.
- File offsets and REU addresses have different widths. The 20 MiB milestone must cross 16 MiB in tests.
- UCI is asynchronous; completion is a state/queue protocol, not a fast CPU polling count or an initial return to IDLE. Verify transferred byte counts.
- The supplied disk images are useful real fixtures, not pristine configuration templates. Preserve them and record derivative changes.
- DOSBox boot is required for a DOS reference; its built-in shell/reported version and cycle setting prove neither real DOS behavior nor XT timing.
- 80-column text preserves guest attributes even when its rendered colors are approximated. Never corrupt guest VRAM to make the host picture easier.
- VICE warp accelerates development; real C64U measurements determine 64 MHz/REU/UCI performance.
- Keep all new context and scratch inside this project. A dirty sibling toolchain cannot be identified by HEAD alone.

- Preserve original-8088 alias evidence; do not filter failing undocumented cases merely to fit a documented-only decoder.
- Keep decoded segment/offset destinations stable across immediate fetch and cache eviction.

- Separate bounded host REP continuation from original-CPU interrupt restart; compare completed instructions with aggregate budgets.
- Preserve guest interrupt routing through IVT/stack; a guest IRET test stub is not a native BIOS service.

- Keep the complete raw bootloader read extent in the oracle. IO.SYS file length rounds to 44 sectors, but this sector reads 51; compare padding/overread as observed.
- Reset→IO.SYS through actual BIOS is a useful milestone. COMMAND.COM prompt, native media loading, runtime execution and the remaining machine/storage requirements still determine completion.
- Recognize native BIOS service only at exact owned physical ROM opcodes, and patch saved guest flags before ordinary IRET. INT 11h/12h must see mutable dirty BDA.
- A zero range length differs from zero low-level DMA count. Validate before touching bytes, split REU banks and publish only committed progress; a failed DMA's uncertain chunk must be repeated.
- Charge every linked staging reservation to the full host map. C000–C0FF belongs to range staging; the linked UCI buffer uses C100–C8FF, leaving C900–CFFF for further resident growth; pre-map BSS headroom must follow the current ledger.
- Listing an already older object in a changed Makefile does not force a relink without the Makefile/object prerequisites. Check linker/map/binary identity, not compilation messages alone.
- Preserve every physical range a probe mutates, including dirty guest-page neighbors and external source/destination arenas. Backup read-only, restore exact bytes, then independently compare a fresh readback.
- State the profile interval and omitted costs. Peddle CPU cycles are target instruction work, while faster host testing, REU stalls and physical elapsed time are different measurements.

- Instruction fetch spans remain unpinned across operand work. Validate tag/generation/CS/IP/cache state before each dereference, and compare against the prior assembled fetch path after eviction and self-modification.
- Preserve original adjust semantics rather than modern AX-wide assumptions. AAM-zero hardware flags, BCD thresholds and REP evidence gaps require separate assertions.
- A zero serial/printer BDA base returns before AH dispatch on the XT. Preserve the actual register result and wrapping index behavior; do not invent a timeout for absent hardware.
- Logical video memory services do not prove a C64 renderer or readable display. Keep CP437/attributes exact and test coherent scroll/pixel/page behavior before presentation.
- Separate PRG file padding and startup zero initialization from linked CODE/RODATA/reservations. A larger contiguous PRG does not imply every byte is executable or occupied by linked modules.

- Keep kernel-only default acceptance separate from the opt-in long real-DOS command lane. A prompt is stronger evidence when actual keyboard enqueue drives VER and DIR and independent output checks require a returned prompt.
- A surprising original DOS port access needs binary/relocation and primary-source audit before diagnosing fetch corruption. The 02F2h–02F7h GLOBAL REARM broadcast is narrow absent-board behavior; reads/words/unrelated ports remain unsupported.
- Preserve the guest interrupt frame across an empty keyboard wait and retry only its exact owned ROM instruction; do not increment completed instructions or fabricate keys.
- Generic UCI completion is transport state, not image-file success. Operation-specific status, exact byte counts and persistence remain separate native integration work.
- CIA phi2 ticks, native CPU cycles, guest timer ticks and REST duration are different clocks. Establish physical timer progress/turbo independence before using real-time deadlines.

Current overlays are exclusive native owners, not arbitrary function-pointer storage. Keep every return and persistent state resident, release startup sources only after bootstrap, and preserve exact DOS observation/RAM oracles after performance changes. Unit MAIN has 76 bytes and DEVICE 49; cold lifetime design must precede further resident growth.
