# Memory budget checkpoint

Status: proposed, no linked artifact exists. Authoritative proposed ranges: [MEMORY.md](../docs/MEMORY.md).

| Resource | Budget | Measured used | Gate |
|---|---:|---:|---|
| Resident/hot executable ranges | 22 KiB | Unknown | Linker map, code/data ownership, no overlap |
| Cold window including vectors | 4 KiB | Unknown | Must preserve IRQ/NMI/reset vectors and return gateways |
| Host guest-cache frames | 16 KiB | Unknown | All frame starts/sizes inside declared ranges |
| Host control/metadata/buffers | 4 KiB | Unknown | Page map + frame/HD descriptors + CPU state + dirty maps + buffers all counted |
| Host low memory | 2 KiB | Unknown | ZP ownership, KERNAL work and stack high-water |
| Video matrix/fonts/bitmap | 12 KiB | Unknown | Correct VIC bank and font/bitmap alignment |
| I/O reservation | 4 KiB | Reserved | Never allocated as RAM |
| REU guest physical arena | 1 MiB | Reserved design | Guest bus holes/ROM enforced |
| REU whole floppies | 2 × 1 MiB | 360 KiB each fixture | Actual image lengths, no tail in exports |
| REU HD cache | At most 2 MiB | Unknown | Metadata fits; force smaller cache in small-disk tests |
| REU assets/staging/trace | 2 MiB | Unknown | Ownership and versioned descriptors |
| REU unallocated | 9 MiB | Unknown | Cannot be borrowed silently |

The 4 KiB metadata budget is particularly tight: a full 512-byte-page map alone takes 2 KiB. Charge disk-cache descriptors and all bounce buffers here; move cold metadata to REU or reduce cache capacity if the measured ledger exceeds the budget. A larger cache advertised without its metadata is not a valid budget.

At each implementation slice record build hash, map path, ZP allocations, maximum stack depth, resident/static bytes, cache frames/page size, REU high-water, and remaining headroom. Do not replace “Unknown” with estimates labeled as measurements.
