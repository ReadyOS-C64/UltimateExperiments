# Memory, paging, and coherence

These are full-system budgets; current measured subsets are recorded in [MEMORY_BUDGET](../agentworking/MEMORY_BUDGET.md) and [MEMORY_IMPLEMENTATION](MEMORY_IMPLEMENTATION.md). The 512-byte coherent byte cache and bytewise coherent guest/REU range transfers are implemented and functionally tested; page size and future optimizations remain candidates. All ranges below are inclusive unless a length is explicitly given.

## Guest address space

| Guest physical range | Behavior |
|---|---|
| `00000–9FFFF` | 640 KiB conventional RAM, including writable IVT/BDA |
| `A0000–B7FFF` | Uninstalled video/RAM for this CGA profile; deterministic reads, writes ignored/logged as specified |
| `B8000–BBFFF` | 16 KiB CGA VRAM; text pages and graphics share backing |
| `BC000–EFFFF` | Reserved/uninstalled space; add aliases or option-ROM data only when the profile requires it |
| `F0000–FFFFF` | Synthetic BIOS ROM and tables; guest writes do not change ROM |

Reserve a full 1 MiB REU backing arena for straightforward physical indexing, but enforce this bus map; do not accidentally make holes writable RAM. CPU-only conformance tests use a separate all-RAM bus mode because their vectors assume 1 MiB writable RAM.

Compute an effective offset with 16-bit arithmetic; then `physical = ((segment << 4) + offset) & 0xFFFFF`. Segment aliases must reach the same cache entry. Instruction IP, stack SP, and string SI/DI updates wrap as 16-bit registers. **Do not conflate those rules with the second byte of every multi-byte memory transfer.** Freeze word/far-pointer boundary behavior at offsets FFFF/FFFE from original-CPU vectors/reference code, including odd-address behavior, before enabling a shared `read16` fast path. Test physical FFFFF→00000 separately. Avoid importing modern protected-mode segment-limit behavior.

## C64 host map: 64 KiB fully accounted for

| Host range | Bytes | Proposed use |
|---|---:|---|
| `0000–01FF` | 512 | 6510 port, allocated ZP, hardware stack |
| `0200–07FF` | 1,536 | KERNAL-compatible work areas, bootstrap, host input/buffers |
| `0800–3FFF` | 14,336 | CPU, hot memory routines, native BIOS/control code |
| `4000–43FF` | 1,024 | VIC bitmap color matrix / text screen |
| `4400–47FF` | 1,024 | Packed 4×8 CP437 font source |
| `4800–4FFF` | 2,048 | 8×8 CP437 font source / aligned character generator |
| `5000–5FFF` | 4,096 | Resident renderer and related code |
| `6000–7FFF` | 8,192 | VIC bitmap reservation (8,000 displayed bytes) |
| `8000–BFFF` | 16,384 | Guest cache frames; includes RAM under BASIC |
| `C000–C0FF` | 256 | Coherent range staging buffer; linker-enforced reservation |
| `C100–CFFF` | 3,840 | Additional resident CPU/BIOS/storage code |
| `D000–DFFF` | 4,096 | I/O visible: VIC, SID, color RAM, CIA, REU/UCI |
| `E000–EFFF` | 4,096 | State, page map, descriptors, dirty maps, bounce buffers |
| `F000–FFFF` | 4,096 | Cold-code window / spare; reserve hardware vectors within it |
| **Total** | **65,536** | Hot/resident executable ceiling: 22,272 bytes (21.75 KiB) |

The VIC bank is `4000–7FFF`: the matrix at 4000 and bitmap at 6000 are in the **same** 16 KiB bank. This must be asserted, not inferred from total free bytes. Font alignment and VIC character-ROM visibility must also be checked. Color RAM is at D800 and is already inside the I/O reservation, not another 1 KiB of ordinary RAM.

Host normal mapping exposes RAM under BASIC/KERNAL while leaving I/O visible. KERNAL calls use a resident gateway outside hidden memory; save/restore `$00/$01`, needed ZP, IRQ state, stack, return registers, and channel state. Guest frames under BASIC and metadata under KERNAL remain protected from accidental CPU access during that mapping. REU staging buffers stay in known visible RAM. Initially avoid DMA into I/O and avoid using RAM under I/O altogether. IRQ/NMI vectors and handlers must remain valid across all maps; test RESTORE/NMI and error exits.

The overlay window is not assumed to solve arbitrary code growth. Only cold operations such as disk selection/help/export can be overlaid initially. The CPU, active BIOS callbacks, pager, and IRQ gateways must stay callable without overlay faults. Record separate CODE/RODATA/BSS boundaries; do not execute embedded constants or overwrite persistent state with an overlay.

## REU arena: 4 MiB minimum profile

| REU range | Capacity | Use |
|---|---:|---|
| `000000–0FFFFF` | 1 MiB | Guest physical backing arena |
| `100000–17FFFF` | 512 KiB | Complete floppy A image; exact actual length in descriptor |
| `180000–1FFFFF` | 512 KiB | Complete floppy B image |
| `200000–2FFFFF` | 1 MiB | Hard-disk extent cache, independent of guest RAM cache |
| `300000–33FFFF` | 256 KiB | Cold assembly payloads / fonts / immutable assets |
| `340000–37FFFF` | 256 KiB | Storage transfer/recovery staging |
| `380000–3BFFFF` | 256 KiB | Optional bounded trace/checkpoint scratch |
| `3C0000–3FFFFF` | 256 KiB | Unallocated reserve; no implicit ownership |

User clarification 2026-10-14: assume **4 MiB or larger**, including room for overlays. This supersedes the initial 16 MiB minimum proposal. The supplied 360 KiB disks fit both 512 KiB slots. Larger REUs can expand the HD cache and floppy slots through a capacity-aware allocator; 720 KiB and larger floppy support requires that expanded profile, never truncation. No runtime feature may require memory above the 4 MiB baseline. REU is volatile: arena allocation is not persistence. A 20 MiB hard disk remains file-backed.

Expanded REC DMA counters may wrap within 512 KiB without carrying into the upper bank latch. The implemented low-level routine accepts only a nonzero, single-64-KiB-bank chunk and rejects crossing ranges; implemented range operations split and explicitly reload the bank. This is conservative for differing firmware and keeps page transfers safe. See [implemented REU contract](REU_IMPLEMENTATION.md) and [coherent range contract](RANGE_IMPLEMENTATION.md).

## Guest page cache

Start with **512-byte pages, 32 frames in 16 KiB**, solely as a benchmark candidate. Sweep 256/512/1024/2048 bytes with the same total cache budget. Use physical-page tags and a direct page→frame table where practical: 1 MiB/512 = 2,048 byte entries, with FF meaning absent. A 256-byte global table needs 4,096 entries before descriptors; either use a sparse/two-level table or charge the extra storage against cache/working RAM. Do not compare page sizes while ignoring metadata cost.

Per-frame state: physical tag, valid/dirty, pin/reference count, replacement reference bit, generation. A simple clock replacement policy is the baseline; measure alternatives. CS fetch, current stack, and recent data may receive preference, but do not permanently pin whole segments. Eviction must always be possible. Acquire two-frame word operands in a deterministic order or use a safe scratch copy so a small cache cannot deadlock or invalidate the first byte's pointer.

Fast fetch stores a host pointer, physical tag, valid span, and generation. The span ends at page, instruction-IP, and address-space boundaries. Segment changes, taken control transfers, eviction, and overlapping writes invalidate relevant cached pointers. Avoid a 32-entry linear tag scan for every byte. Measure full translation cost as well as warm register-only dispatch.

## Coherence invariants

1. A physical guest page has at most one authoritative dirty host frame. REU is current only when no newer dirty frame exists.
2. Every writer, including BIOS disk reads, native text helpers, debugger injection, REP fast paths, and memory initialization, uses the memory API or a range-acquire/commit API with equivalent semantics.
3. Before a disk **write** reads a guest range, include its dirty resident bytes. Before a disk **read** replaces guest bytes, preserve untouched dirty bytes and merge/update or invalidate the destination frames. Flushing after overwriting REU can restore stale data and is forbidden.
4. Renderers see dirty host VRAM frames, not stale REU copies. All VRAM changes mark display regions; palette/start-address/mode changes can invalidate the entire visible image without changing VRAM.
5. Any guest write to executable bytes invalidates decoded/fetch state for all segment aliases. A predecode cache added later keys by physical bytes/generations, not just CS:IP.
6. REU-to-REU copies use a host bounce buffer. Ordinary REU registers do not provide a direct REU-to-REU copy command.
7. REP acceleration preserves the actual forward/backward sequence. Overlapping MOVS is not automatically `memmove`: forward overlap can deliberately replicate bytes. Split at segment/index/page/physical-wrap boundaries and event checkpoints; preserve CX/SI/DI/flags at interruption.
8. Reads/writes crossing RAM/ROM/video boundaries dispatch each affected byte/part under the bus contract. An optimization may not bypass ROM protection or dirty-video notification.

Tests include alias writes, eviction during instruction fetch, dirty code replacement, BIOS DMA into partial cached pages, dirty video reads, zero-length bulk operations, 64 KiB count encoding, pin exhaustion, forced minimum-frame tests, and fault injection before/after each ownership transition.

## Current BIOS and storage ownership

The BIOS initializer owns guest IVT/BDA 00000–004FF and ROM F0000–FFFFF. It uses the coherent bus under a temporary all-RAM initialization mode and restores the prior mode; normal guest writes cannot change ROM. Conventional RAM outside IVT/BDA and configured media remain caller-owned. INT 11h/12h ordinary ROM code reads mutable BDA through the CPU bus, including dirty resident bytes.

Whole floppy A begins at REU 100000 and must be explicitly loaded before setting its loaded flag. Disk reads/writes use [range copying](RANGE_IMPLEMENTATION.md), so partial cached-page neighbors and dirty export bytes retain their authority. C000–C0FF is a separate 256-byte host bounce buffer, unavailable to resident code. It is not embedded in the PRG. The remaining C100–CFFF code budget is 3,840 bytes; the full inclusive host map above still totals 65,536.

A range is linear physical guest memory with 20-bit wrap, unlike CPU segmented word helpers that wrap a 16-bit offset. The disk BIOS checks the translated physical 64 KiB DMA boundary independently from ES:BX wrapping. REU ranges must be outside guest backing and within the minimum 4 MiB arena; range length zero means no bytes, whereas the low-level DMA primitive rejects zero.
