# Memory, paging, and coherence

These are **proposed budgets**, not linked sizes. M1/M2 must validate them and update [MEMORY_BUDGET](../agentworking/MEMORY_BUDGET.md). All ranges below are inclusive unless a length is explicitly given.

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
| `C000–CFFF` | 4,096 | Additional resident CPU/BIOS/storage code |
| `D000–DFFF` | 4,096 | I/O visible: VIC, SID, color RAM, CIA, REU/UCI |
| `E000–EFFF` | 4,096 | State, page map, descriptors, dirty maps, bounce buffers |
| `F000–FFFF` | 4,096 | Cold-code window / spare; reserve hardware vectors within it |
| **Total** | **65,536** | Hot/resident executable ceiling: 22 KiB |

The VIC bank is `4000–7FFF`: the matrix at 4000 and bitmap at 6000 are in the **same** 16 KiB bank. This must be asserted, not inferred from total free bytes. Font alignment and VIC character-ROM visibility must also be checked. Color RAM is at D800 and is already inside the I/O reservation, not another 1 KiB of ordinary RAM.

Host normal mapping exposes RAM under BASIC/KERNAL while leaving I/O visible. KERNAL calls use a resident gateway outside hidden memory; save/restore `$00/$01`, needed ZP, IRQ state, stack, return registers, and channel state. Guest frames under BASIC and metadata under KERNAL remain protected from accidental CPU access during that mapping. REU staging buffers stay in known visible RAM. Initially avoid DMA into I/O and avoid using RAM under I/O altogether. IRQ/NMI vectors and handlers must remain valid across all maps; test RESTORE/NMI and error exits.

The overlay window is not assumed to solve arbitrary code growth. Only cold operations such as disk selection/help/export can be overlaid initially. The CPU, active BIOS callbacks, pager, and IRQ gateways must stay callable without overlay faults. Record separate CODE/RODATA/BSS boundaries; do not execute embedded constants or overwrite persistent state with an overlay.

## REU arena: 16 MiB profile

| REU range | Capacity | Use |
|---|---:|---|
| `000000–0FFFFF` | 1 MiB | Guest physical backing arena |
| `100000–1FFFFF` | 1 MiB | Complete floppy A image; exact actual length in descriptor |
| `200000–2FFFFF` | 1 MiB | Complete floppy B image |
| `300000–4FFFFF` | 2 MiB | Hard-disk extent cache, independent of guest RAM cache |
| `500000–57FFFF` | 512 KiB | Cold assembly payloads / fonts / immutable assets |
| `580000–5FFFFF` | 512 KiB | Storage transfer/recovery staging |
| `600000–6FFFFF` | 1 MiB | Optional bounded trace/checkpoint scratch |
| `700000–FFFFFF` | 9 MiB | Unallocated reserve; no implicit ownership |

Require/probe 16 MiB for v1. The supplied 360 KiB disks fit easily. A 720 KiB floppy extension fits these slots; 1.2/1.44 MiB images require a revised allocation and tests, not truncation. REU is volatile: arena allocation is not persistence. A 20 MiB hard disk cannot be held wholly in this REU; only its extents are resident.

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
