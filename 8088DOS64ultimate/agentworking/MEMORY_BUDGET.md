# Memory budget checkpoint

Status: current CPU/BIOS/coherent floppy baseline measured; full CPU/devices/display/native file transport remain unfinished. Authoritative full-system ranges: [MEMORY.md](../docs/MEMORY.md). Storage/bootstrap baseline maps `build/dos64.map` / `build/dos64-tests.map`: runtime CODE **9,702**, RODATA **673**, BASIC **12**, BSS **211**, PAGEMAP **2,048**, CACHEMETA **192**, RANGEBUFFER **256**, ZP **16**, header **2**; PRG **10,389 bytes**. Unit CODE **10,618**, RODATA **697**, TESTCODE **36**, BASIC **12**, ZP **28**, PRG **11,365 bytes**. Final quick/helper integration passed; runtime bytes are unchanged and the extra recovery code is unit-only.


| Resource | Budget | Measured used | Gate |
|---|---:|---:|---|
| Resident/hot executable ranges | 22,272 bytes | 9,999 CODE + 673 RODATA + 12 BASIC = 10,684 emitted | C000 staging removes 256 bytes from old 22 KiB code ceiling; additional window C100–CFFF |
| Cold window including vectors | 4 KiB | Unknown | Must preserve IRQ/NMI/reset vectors and return gateways |
| Host guest-cache frames | 16 KiB | 32 × 512 bytes reserved/used | 8000–BFFF, direct physical tags; tests cover all frames |
| Host control/metadata | 4 KiB | 2,462 static bytes; 1,634 remaining including gaps | BSS 222 + map 2,048 + frame metadata 192; only 34 BSS bytes before E100 |
| Host range staging | 256 bytes | 256 reserved, not PRG payload | C000–C0FF; linker/map gate forbids graphics/cache overlap |
| Host low memory | 2 KiB | Runtime ZP 18; stack measured by probe | Full-system stack/IRQ/KERNAL bound not established |
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

CPU checkpoint supersedes earlier runtime totals: CODE 2,019 + RODATA 8 + BASIC 12, BSS 84, PAGEMAP 2,048, CACHEMETA 192, runtime ZP 16; PRG 2,041 bytes. Static control usage is now 2,324 bytes, leaving 1,772 including alignment gaps. Unit CODE 2,442 + RODATA 8 + TESTCODE 36, ZP 23, PRG 2,500. Hardware cache/backup/restore builds exclude the new CPU execution module; their tested binaries remain unchanged.


2026-10-15 arithmetic/operand/stack checkpoint supersedes runtime totals above: CODE **4,394**, RODATA **305** (includes parity and addressing/dispatch tables), BASIC 12, BSS **116**, PAGEMAP 2,048, CACHEMETA 192, ZP 16 (20–2F); PRG **4,713 bytes**. Unit CODE 4,817 + RODATA 305 + TESTCODE 36, ZP 23 (20–36), PRG 5,172. `build/dos64.map` / `build/dos64-tests.map` verify these ranges. Static control usage 2,356 leaves 1,740 including gaps; BSS ends E073 before the E100 map. Resident emitted code/data/BASIC total 4,711. No new REU arena or ZP allocation. Standalone hardware probes exclude these modules and retain their verified executable identity. The shared cache stack high-water remains 14; no full-system IRQ/KERNAL stack bound is claimed.


2026-10-15 strings/control/shift checkpoint supersedes prior runtime totals: CODE **6,094** (080D–1FDA), RODATA **305** (1FDB–210B), BASIC 12, BSS **137** (E000–E088), PAGEMAP 2,048, CACHEMETA 192, ZP 16 (20–2F); PRG **6,413** bytes. Unit CODE 6,517, RODATA 305, TESTCODE 36, ZP 23, PRG 6,872. New control/string/shift BSS 9+5+7=21; no new ZP or REU arena. Static control usage 2,377 leaves 1,719 including gaps; 119 BSS bytes remain before E100 map. Runtime emitted BASIC/code/data total 6,411. Maps in the slice evidence verify boundaries. Full-system stack bound and physical timing remain unknown; standalone hardware helpers/probes are unchanged.


## 2026-10-15 CPU/BIOS/range/disk checkpoint

This supersedes runtime totals in the historical checkpoints above. Runtime CODE 080D–2DF2 (**9,702**), RODATA 2DF3–3093 (**673**), BASIC 0801–080C (**12**), ZP 0020–002F (**16**), BSS E000–E0D2 (**211**), PAGEMAP E100–E8FF (**2,048**), CACHEMETA E900–E9BF (**192**) and RANGEBUFFER C000–C0FF (**256**). Runtime PRG **10,389**; map-verifier linked total **13,112** includes non-file reservations/header/ZP and must not be confused with PRG length. Current MAIN ends at 3093, leaving 3,948 bytes through 3FFF in its configured load region; 0800 is outside the PRG load area.

Unit CODE 080D–3186 (**10,618**), RODATA 3187–343F (**697**), TESTCODE 3440–3463 (**36**), ZP 0020–003B (**28**); shared BSS/page map/metadata/staging unchanged. Unit PRG **11,365**, linked verifier total **14,100**. Extra snapshot/test modules are unit-only. All current code remains below the 4000 video reservation.

The full host table remains contiguous and totals 65,536 bytes after splitting C000–CFFF into **256-byte staging plus 3,840-byte code window**. Resident/hot executable ceiling is now **22,272 bytes (21.75 KiB)** across 0800–3FFF, 5000–5FFF and C100–CFFF, before future linker placement/overlays. It is a full-system budget; current linker CODE still uses MAIN, not those future windows. Static control usage 211+2,048+192=2,451 leaves 1,645 bytes including gaps. The E000 pre-map BSS region has only **45** bytes left; total free bytes elsewhere do not permit BSS to cross E100.

Standalone range probe map: CODE 080D–0FAE (**1,954**), BSS **81**, ZP **21**, staging **256**, map **2,048**, frame metadata **192**; PRG **1,968**, linked total **4,566**. It reserves two cache frames during execution but keeps the full 16 KiB cache address window. Source/destination REU ranges remain below 4 MiB. Existing cache/REU/backup/restore identities are unchanged.

New physical range snapshot uses host 6000–73FF for a 5,120-byte recovery payload only while the standalone runner exclusively owns the machine; it is not production bitmap RAM available for resident growth. REU envelopes are guest 07FC00–0803FF, source 34FF00–3504FF and destination 35FF00–3604FF. The six bank-split descriptors recover all touched bytes; physical Manual 64 MHz integrity and exact 5,120-byte/configuration restoration passed. No new runtime REU arena or runtime ZP was added. Full-system IRQ/KERNAL/renderer stack bounds remain unmeasured.

## Fetch optimization superseding current totals

Runtime CODE080D–2F1B **9,999**, RODATA2F1C–31BC **673**, BSS E000–E0DD **222**, ZP0020–0031 **18**, PRG **10,686**. UnitCODE **10,915**, RODATA **697**, TESTCODE **36**, ends 358C, ZP **30**, PRG **11,662**. The module plus calls/wrapper cost 297 executable bytes,11BSS and 2ZP. Staticcontrol 222+2048+192=**2,462**, leaving **1,634** including gaps; pre-mapBSS headroom **34** bytes. MAIN runtime headroom 3,651. Range buffer/map/frame metadata remain unchanged. [Exact maps/evidence](evidence/fetch-optimization-20261015.json).
