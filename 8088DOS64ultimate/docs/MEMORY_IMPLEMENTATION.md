# Guest memory implementation checkpoint

Implemented 2026-10-14. Target assembly now provides 20-bit address calculation, a coherent byte-oriented guest bus and a 512-byte-page cache. This is a correctness baseline. It is not the full CPU, BIOS loader, disk backend or optimized instruction-fetch path.

## Address and API contracts

`dos64_physical` calculates `((segment * 16) + offset) & FFFFF` from the little-endian words `dos64_segment`/`dos64_offset` into the three-byte `dos64_address`. It preserves the input words, X/Y/P and mapping, clobbering A and the result only. It handles host decimal mode internally. Register IP/SP/SI/DI updates and multi-byte operand boundaries remain separate concerns. No read16 policy has been selected by this implementation.

The memory/cache entry points require the normal runtime mapping: RAM under BASIC/KERNAL and I/O visible (`$01` low bits 5, DDR low bits outputs). They are synchronous, non-reentrant and preserve processor flags except returned carry while clobbering A/X/Y. Carry set and `dos64_memory_error` report failure. IRQ/NMI gateways and resumable event handling remain future system integration; no interrupt handler may call this shared-scratch API concurrently.

| Entry | Input | Result |
|---|---|---|
| `dos64_cache_init` | `dos64_cache_limit` 1..32 | Cold empty cache, PC bus mode, zero dirty/notification state; REU backing untouched |
| `dos64_mem_read` | `dos64_address` | Byte in A; hole reads FF without DMA |
| `dos64_mem_write` | Address and `dos64_mem_value` | Coherent dirty byte write; ROM/hole writes ignored |
| `dos64_cache_acquire` | Address | Read-only page pointer and selected frame handle; pin incremented |
| `dos64_cache_release` | Saved handle in `dos64_cache_selected` | Pin decremented; invalid/unpinned handle rejected |
| `dos64_cache_flush` | None | Dirty valid frames written back, including pinned frames; no invalidation |

The acquire pointer covers only the remainder of its page. Save the returned handle separately: later memory/flush calls can change `cache_selected`. Release before yielding or cold initialization. Acquired pointers are read-only; native writes use `mem_write` until a tested range-commit API exists. Pin count overflow and all-frames-pinned exhaustion are explicit errors.

Cold initialization discards cache ownership and is only valid before use or after successful flush with no outstanding acquisitions. The bus mode and frame limit are fixed while a cache is live. Production starts in PC mode; ALL_RAM mode is solely for CPU conformance fixtures. Future BIOS/image initialization must occur before cache activation or through the coherent API, never by silently replacing REU bytes underneath dirty frames.

Error codes in `include/memory.inc`: 1 invalid physical address, 2 no evictable frame, 3 DMA failure, 4 uninitialized/invalid capacity, 5 invalid bus mode, 6 invalid release, 7 pin overflow. Input physical addresses above FFFFF are rejected; the segment helper performs the architectural wrap explicitly.

## Ownership and failure ordering

The 2,048-entry map at E100–E8FF maps a physical 512-byte page to a frame, or FF for absent. Frames occupy 8000–BFFF. Per-frame physical tags, valid/dirty/reference flags, pin counts and 16-bit generations occupy E900–E9BF. Runtime state uses E000–E03D. Linker checks prohibit overlapping segments and charge all of these against the 4 KiB control budget.

A hit uses direct lookup. A miss scans a clock hand at most twice across the active frames, skipping pinned frames and clearing reference bits. A dirty victim is written back first. If write-back fails, the old map and authoritative dirty frame remain available for retry. After successful write-back, old ownership is removed **before** a load can overwrite frame bytes. If that load fails, the victim stays unpublished and backing remains authoritative; a retry reloads it. New ownership is published only after successful DMA completion.

All DMA addresses derive from a validated physical page number and stay in guest REU arena 000000–0FFFFF. Aligned 512-byte requests never cross an REU 64 KiB bank, including the expanded REC seam. They cannot access floppy, HD or overlay arenas. Cache error handling is tested with synthetic prefix-transfer failures; this models transaction adversity, not a claim that ordinary hardware reports those particular failures.

In PC mode the [guest bus map](MEMORY.md) is enforced: conventional RAM and B8000–BBFFF CGA are writable; F0000–FFFFF reads synthetic BIOS backing but ignores guest writes; other holes read FF and ignore writes. CGA writes set a coarse video-dirty flag. Each accepted write increments a global 32-bit write epoch and frame generation. Generations are diagnostic groundwork; correctness does not currently depend on a cached decoder pointer or counter wrap. Future fetch/predecode paths must invalidate on writes/evictions and cannot assume this alone solves self-modifying code.

## Evidence and remaining work

`make test` passes 41 Zig/Peddle tests and ten tooling tests. Added cases exercise 4,103 segment/offset pairs, every physical page at both ends, seeded random writes/reads against an independent RAM oracle with two frames, aliasing, neighbor preservation, pin exhaustion/overflow, ROM/holes/CGA, rejected inputs, host write ownership and partial DMA failures. Seeds are in the test source and the build manifest pins actual files.

The shared cache probe uses two frames and 1,536 bytes at guest 07FD00–0802FF, forcing dirty eviction across the REC seam. It flushes, cold-initializes, rereads and exports all bytes at host 6000–65FF. Peddle additionally checks untouched bytes in the enclosing partial pages. VICE run `vice_auto_20261014_225535` passed; independent capture verification checks all exported bytes and executable identity. [Compact VICE evidence](../agentworking/evidence/cache-vice-20261014.json) is retained. VICE has 16 MiB REU and warp; no physical timing follows from it.

The first measured warm byte read costs **221 host CPU cycles** in ALL_RAM mode, with 32 active frames and no DMA. It includes the public helper's checks/flag preservation and excludes caller address calculation, instruction decoding, DMA stalls, rendering and hardware effects. This is too much overhead to treat as a finished fast-fetch path. Span-based fetch and measured hot-path optimization remain required; no near-XT speed is established.

Physical read-only discovery succeeded: C64 Ultimate firmware 3.14, FPGA 121, core 1.47, PAL, REU 16 MB enabled, configured CPU speed 64 with turbo controlled by C64U registers and badline timing disabled. [Inventory evidence](../agentworking/evidence/c64u-inventory-20261014.json) records the observation. Configured speed is not measured effective speed. No physical probe was executed. Before that run preserve the overwritten guest REU page envelope 07FC00–0803FF and prior machine/media configuration; restore and verify the REU bytes afterward. The probe resets/uses volatile C64 RAM, so a RAM capture is recovery evidence, not proof of resuming an interrupted program's execution.

Still required: original-8088 word/interrupt semantics, coherent bulk/range interfaces for BIOS storage and rendering, synthetic ROM initialization, CPU fetch/decode/execute, UCI/IEC, physical integrity/timing and page-size experiments. The 512-byte policy remains a candidate, not a measured optimum.
