# Coherent guest and REU range transfers

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


Updated 2026-10-15. `src/range.s` supplies independently authored 6510 assembly for copying between a non-guest REU arena and the linear 20-bit guest bus. It is the coherence boundary for [disk sectors](DISK_IMPLEMENTATION.md), not a bypass that DMA-overwrites guest backing behind dirty cache owners.

## API and bounds

`dos64_range_request` is the 13-byte structure in `include/range.inc`: guest physical address (3 bytes), external REU address (3), remaining length (2), direction (1), status (1), error (1) and bytes done (2). Direction 0 imports REU→guest; direction 1 exports guest→REU. `dos64_range_copy` preserves host P except returned carry, clobbers A/X/Y and public address/DMA scratch, requires the normal RAM/I/O mapping and is non-reentrant.

The initial guest address must be below 1 MiB. It advances linearly with 20-bit wrap; this differs from CPU segmented word-offset wrapping. External REU must begin at 100000–3FFFFF and its complete exclusive end must not exceed 400000. This keeps transfers outside guest backing and within the minimum 4 MiB profile. Length zero means a valid empty operation after descriptor validation, and the largest request is 65,535 bytes. Direction/range errors occur before data access.

The linker reserves `RANGEBUFFER` at C000–C0FF, separate from renderer/bitmap/cache/metadata. It is a 256-byte uninitialized staging allocation, not file payload. Chunks are at most 256 bytes and split at every REU 64 KiB bank seam before calling the conservative low-level DMA primitive. REU-to-REU movement uses this host staging buffer.

## Authority and retry contract

Every guest access goes through `dos64_mem_read`/`dos64_mem_write`, preserving alias, cache, ROM/hole/CGA policy and dirty-page authority. Imports retain untouched dirty neighbors; exports read the actual dirty resident bytes. No flush-after-overwrite shortcut is permitted.

The request mutates to the remaining guest/REU addresses and length. DONE resets on each invocation. Import advances one byte only after its coherent guest write succeeds. Export first collects a whole chunk through coherent reads, DMA-writes it, and advances only after DMA success. Status is 1 complete or 2 error; errors 1 input, 2 REU extent, 3 guest cache and 4 staging DMA accompany returned carry.

A failed DMA may have written a prefix without a reliable exact transferred count. The uncertain current chunk is not counted; a retry repeats it from the retained descriptor. Earlier committed bytes/chunks remain committed. Cache errors are terminal to the current CPU/BIOS operation; DMA retry is useful only while the caller retains source/media ownership. There is no general transaction rollback. The API is not currently safe to call from an IRQ or concurrently with rendering/storage scratch users.

## Verification

Zig/Peddle tests execute the linked routine with one/two frames to force eviction. They assert dirty import neighbors/export bytes, external guards, 64 KiB REU seams, 20-bit guest wrap, a 65,535-byte extent, PC ROM/hole/CGA policy, empty/input rejection and DMA/cache failures with committed progress and retry.

The shared probe imports source REU 34FF00–3504FF into guest 07FD00–0802FF using two frames, validates all bytes, edits the first byte of every 256-byte block while dirty, exports to 35FF00–3604FF, poisons host output and independently reloads all 1,536 destination bytes to 6000–65FF. Native and host oracles both check output. VICE run `logs/vice_auto_20261015_011028` passed all bytes and captured executable identity. A pass mailbox alone is insufficient; tooling rejects stale executables, truncated output and stale dirty bytes.

Physical recovery helpers in `src/range_snapshot.s` preserve the complete touched envelopes: guest 07FC00–0803FF (2,048 bytes), source 34FF00–3504FF (1,536) and destination 35FF00–3604FF (1,536). Six explicitly split DMA descriptors concatenate 5,120 bytes at host 6000–73FF. Backup is read-only; restore writes exactly those ranges and errors identify the first incomplete chunk. A partial restore requires retrying all chunks, then a fresh independent backup/byte comparison. The new range probe passed physical C64U at Manual 64 MHz on firmware 3.14/FPGA 121/core 1.47. All 1,536 result bytes and executable identity matched; a fresh backup independently compared every one of the 5,120 restored bytes, and prior machine/turbo/drive JSON matched. Restore succeeded on its first attempt. Tracked evidence (local development record, not distributed), raw run `agentworking/runs/c64u-range-20261015-013537`. This new range probe was not run physically at 1/16 MHz; the earlier cache probe's physical 1/16/64 MHz matrix remains valid.

Peddle's REU transfers are functional synchronous copies; VICE used 16 MiB REU in warp. Neither result calibrates physical DMA stalls, elapsed host speed, UCI/IEC transport or DOS boot. All range addresses fit below 4 MiB; 4/8/16 MiB model coverage remains separate from physical capacity.
