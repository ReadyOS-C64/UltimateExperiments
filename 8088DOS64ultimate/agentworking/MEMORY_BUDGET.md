# Memory budget checkpoint

Status: foundation, REU primitive and byte cache measured; full interpreter/display/storage allocation remains unfinished. Authoritative ranges: [MEMORY.md](../docs/MEMORY.md). Runtime map reports CODE 1,109, BASIC 12, BSS 62, PAGEMAP 2,048, CACHEMETA 192, header 2, ZP 16 (20–2F); PRG 1,123 bytes. Cache probe CODE 1,284, ZP 21, PRG 1,298. Unit build CODE 1,439 plus TESTCODE 36, ZP 23 (20–36), PRG 1,489. All use the same control allocations. Cache frames are a runtime reservation at 8000–BFFF, not bytes embedded in the PRG. The independent REU-only probe remains 430 bytes, with no pager linked.

| Resource | Budget | Measured used | Gate |
|---|---:|---:|---|
| Resident/hot executable ranges | 22 KiB | 1,109 CODE + 12 BASIC | Linker map; renderer/BIOS/storage not yet implemented |
| Cold window including vectors | 4 KiB | Unknown | Must preserve IRQ/NMI/reset vectors and return gateways |
| Host guest-cache frames | 16 KiB | 32 × 512 bytes reserved/used | 8000–BFFF, direct physical tags; tests cover all frames |
| Host control/metadata/buffers | 4 KiB | 2,302 static bytes; 1,794 remaining | BSS 62 + map 2,048 + frame metadata 192; remaining includes alignment gaps |
| Host low memory | 2 KiB | Runtime ZP 16; stack measured by probe | Full-system stack/IRQ/KERNAL bound not established |
| Video matrix/fonts/bitmap | 12 KiB | Unknown | Correct VIC bank and font/bitmap alignment |
| I/O reservation | 4 KiB | Reserved | Never allocated as RAM |
| REU guest physical arena | 1 MiB | Reserved design | Guest bus holes/ROM enforced |
| REU whole floppies | 2 × 512 KiB | 360 KiB each fixture | Actual image lengths, no tail in exports |
| REU HD cache | 1 MiB at baseline | Unknown | Metadata fits; force smaller cache in small-disk tests |
| REU assets/staging/trace | 3 × 256 KiB | Unknown | Ownership and versioned descriptors |
| REU unallocated | 256 KiB at baseline | Unknown | Cannot be borrowed silently |

The 4 KiB metadata budget is particularly tight: a full 512-byte-page map alone takes 2 KiB. Charge disk-cache descriptors and all bounce buffers here; move cold metadata to REU or reduce cache capacity if the measured ledger exceeds the budget. A larger cache advertised without its metadata is not a valid budget.

Shared cache probe stack high-water is 14 bytes including the synthetic host return sentinel, over 1,103,632 CPU cycles and 12 transfers/6,144 DMA bytes. This is exercised-path evidence, not the complete future CPU/IRQ/KERNAL stack bound. The warm ALL_RAM read costs 221 CPU cycles; physical DMA timing is unmodeled.

At each implementation slice record build hash, map path, ZP allocations, maximum stack depth, resident/static bytes, cache frames/page size, REU high-water, and remaining headroom. Do not replace “Unknown” with estimates labeled as measurements.

Physical-helper checkpoint: standalone backup/restore each occupy 415 linked bytes including BSS/ZP, with unchanged normal runtime layout. They use host 6000–67FF only for owned snapshot/recovery data. Unit fixture code grew; consult its current map rather than reusing the older fixture PRG length.
