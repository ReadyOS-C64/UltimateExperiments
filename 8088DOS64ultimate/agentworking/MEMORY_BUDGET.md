# Memory budget checkpoint

Status: current verified slice includes coherent fetch, PIC, logical video, original adjust and absent serial/printer BIOS. Full CPU/devices/host display/native file transport remain unfinished. Runtime and unit use `cfg/dos64-runtime.cfg`; standalone hardware helpers retain `cfg/dos64.cfg`. Current runtime CODE **11,443**, RODATA **808**, DEVICECODE **1,696**, BASIC **12**, BSS **222**, DEVICESTATE **61**, PAGEMAP **2,048**, CACHEMETA **192**, RANGEBUFFER **256**, ZP **18**. Runtime linked total **16,758**, PRG **20,129** including **6,168** padding/startup-zero bytes. Unit CODE **12,359**, RODATA **832**, TESTCODE **36**, DEVICECODE **1,696**, ZP **30**; linked total **17,746**, PRG **20,129** including **5,192** padding/startup-zero bytes. [Exact maps/evidence](evidence/video-adjust-bios-20261015.json). The full-system [host map](../docs/MEMORY.md) and final checkpoint below explain allocation separately from PRG length.


| Resource | Budget | Measured used | Gate |
|---|---:|---:|---|
| Resident/hot executable ranges | 20,224 bytes with future UCI buffer budgeted | CODE 11,443 + RODATA 808 + BASIC 12 + DEVICECODE 1,696 = 13,959 | MAIN/DEVICECODE boundaries; C000 staging and conditional C100–C8FF UCI buffer leave C900–CFFF |
| Cold window including vectors | 4 KiB | Unknown | Must preserve IRQ/NMI/reset vectors and return gateways |
| Host guest-cache frames | 16 KiB | 32 × 512 bytes reserved/used | 8000–BFFF, direct physical tags; tests cover all frames |
| Host control/metadata | 4 KiB | 2,523 static bytes; 1,573 remaining including gaps | BSS 222 + map 2,048 + frame metadata 192 + DEVICESTATE 61; only 34 BSS bytes before E100 |
| Host range staging | 256 bytes | 256 reserved, not PRG payload | C000–C0FF; linker/map gate forbids graphics/cache overlap |
| Host low memory | 2 KiB | Runtime ZP 18; stack measured by probe | Full-system stack/IRQ/KERNAL bound not established |
| Video matrix/fonts/bitmap | 12 KiB | 4 KiB startup zero initialization; no renderer/font yet | Startup zeros are file bytes; preserve VIC bank/font/bitmap alignment |
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

## Fetch optimization checkpoint

Runtime CODE 080D–2F1B **9,999**, RODATA 2F1C–31BC **673**, BSS E000–E0DD **222**, ZP 0020–0031 **18**, PRG **10,686**. Unit CODE **10,915**, RODATA **697**, TESTCODE **36**, ends 358C, ZP **30**, PRG **11,662**. The module plus calls/wrapper cost 297 executable bytes, 11 BSS and 2 ZP. Static control 222+2,048+192=**2,462**, leaving **1,634** including gaps; pre-map BSS headroom **34** bytes. MAIN runtime headroom is 3,651 bytes. Range buffer/map/frame metadata remain unchanged. [Exact maps/evidence](evidence/fetch-optimization-20261015.json).

## PIC/device layout checkpoint

Runtime CODE **10,586**, RODATA **681**, BSS **222**, ZP **18**, DEVICESTATE **20** at EA00–EA13; PRG **11,281**. Unit CODE **11,502**, RODATA **705**, TESTCODE **36**, ZP **30**, ends 37DF, PRG **12,257**. Static control usage 222+2,048+192+20=**2,482**, leaving **1,614** bytes including gaps. The E000 BSS ceiling remains unchanged with 34 bytes free. Device scratch is relocated into the EA00–EEFF allocation, while frame metadata is bounded to E900–E9FF and EF00–EFFF remains reserved. [Exact maps](evidence/pic-io-20261015.json).


## Verified resident video/adjust/auxiliary-BIOS layout

Final verified maps: runtime CODE 080D–34BF **11,443**, RODATA 34C0–37E7 **808**, DEVICECODE 5000–569F **1,696**, BASIC **12**, BSS E000–E0DD **222**, ZP 0020–0031 **18**, DEVICESTATE EA00–EA3C **61**, PAGEMAP **2,048**, CACHEMETA **192** and RANGEBUFFER **256**. Unit CODE 080D–3853 **12,359**, RODATA 3854–3B93 **832**, TESTCODE 3B94–3BB7 **36**, DEVICECODE **1,696**, ZP **30**; other static allocations match runtime. The 205-test/57-tooling and expanded 5,701-case full gates accept these maps, superseding the historical checkpoint totals above.

Runtime allocated MAIN payload is 11,443+808+12=**12,263** bytes; MAIN zero padding through 3FFF contributes **2,072** file bytes. Unit allocated MAIN payload is 12,359+832+36+12=**13,239**, with **1,096** padding bytes. Both append **4,096** startup zero bytes at 4000–4FFF and **1,696** DEVICECODE bytes at 5000–569F. Including the two-byte load header, both PRGs are **20,129 bytes**; their equal file length does not mean equal linked CODE usage. Actual linked totals excluding padding/startup zeros are runtime **16,758** / unit **17,746**, including header/ZP/static reservations. INITVIDEO is a file-memory region, not a linked executable segment.

Runtime emitted BASIC/CODE/RODATA/DEVICECODE is **13,959** bytes. Static control usage 222+2,048+192+61=**2,523**, leaving **1,573** bytes across the control region including gaps; only **34** bytes remain in pre-E100 BSS. DEVICESTATE has **1,219** bytes left before EF00; CACHEMETA leaves **64** bytes before EA00. The optional future **2,048-byte** UCIBUFFER at C100–C8FF is not linked; reserving its budget leaves **1,792** bytes at C900–CFFF. The full host map totals 65,536 bytes and conservative resident/hot code capacity becomes **20,224 bytes**, including the shared 5000–5FFF code window. Remaining per-window space cannot be treated as interchangeable without linker changes.

Standalone hardware probes/helpers retain `cfg/dos64.cfg`; runtime and unit use `cfg/dos64-runtime.cfg`. The new file layout does not invalidate physically tested standalone binaries. Logical video adds no runtime ZP or E000 BSS; DEVICESTATE 61 comprises PIC 20, video 33, adjust 6 and auxiliary BIOS 2 bytes. Full-system IRQ/KERNAL/renderer stack bounds and physical timing remain unmeasured.
