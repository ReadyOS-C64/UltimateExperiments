# Memory budget checkpoint

Status: current accepted layout passes326 Zig/129 tooling/597 quick cases, dedicated import8, genuine DOS equality and12 profile samples. Runtime/unit CODE12290/13206, RODATA880/904, initialized NATIVESTATE2; unit TESTCODE36. DEVICE3756, fonts3072, FILE1088/TEXT957/INPUT882, cold1821, BSS222, ZP18/30, DEVICESTATE244. All-linked totals29790/30778 include mutually exclusive variants and cold data. Resident excluding variants/cold25042/26030 includes fonts/static reservations; maximum concurrently loaded resident totals26130/27118. These are not executable/file-length totals. [Exact maps](evidence/native-text-input-20261015.json).

| Resource | Budget | Measured used | Gate |
|---|---:|---:|---|
| Resident/hot executable ranges |20223 MAIN/DEVICE/overlay bytes|Resident BASIC/code/data16940 plus max overlay1088 =18028|MAIN free1151 runtime/175 unit; DEVICE340; TEXT835|
| Cold startup lifetime |4096|1821 linked: importer931, BIOS/bootstrap init394, patches496; tail2275|7000–7FFF, irreversible initialized resident guard before every public cold entry|
| Host guest cache |16384|32×512 bytes|8000–BFFF; first2048 initiallyINPUT asset, committed before any cache use|
| Host control |4096|2706 static;1390 gaps/headroom|BSS222+map2048+metadata192+DEVICESTATE244; only34 BSS bytes beforeE100|
| Range staging |256|256|C000–C0FF|
| UCI storage |2048|2048|C100–C8FF, outside overlaid code|
| Host low memory |2048|ZP18 runtime/30 unit|Full-system stack/IRQ bound unmeasured|
| Matrix/fonts/bitmap |12288|Matrix1000+guard24, narrowfont1024, fullfont2048; bitmap8192 reserved|Fonts4400/4800 explicit non-executable PRG data; TEXT only after cold release|
| I/O reservation |4096|Reserved|Never allocated as RAM|
| REU guest arena |1048576|Reserved/functional|640KiB RAM plus holes/ROM/CGA policy|
| REU floppies |2×524288|360KiB fixture slots|Exact image length, no export tail|
| REU HD cache |1048576|Proposed|Not yet implemented|
| REU assets/staging/trace |3×262144|6144 overlay asset bytes340000–3417FF|FILE/TEXT/INPUT headers+exact linked payloads|
| REU unallocated |262144|Reserved|No silent borrowing|

PRGs are32769 bytes, load0801–87FF. Runtime/unit linked file content21833/22809 plus4790/3814 checked padding plus6144 startup assets plus two-byte header equals exact PRG length. Linked file content includes3072 font data and1821 disposable cold bytes; resident emitted code/data is16940/17916. The three linked overlay payloads total2927 but only maximum1088 can occupyC900–CFFF at once. Historical checkpoints below retain their original scope and are superseded by this current ledger.

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


## Verified clock/keyboard/UCI/native-clock map

Runtime CODE 080D–3776 (**12,138**), RODATA 3777–3AD6 (**864**), DEVICECODE 5000–5E63 (**3,684**), BSS E000–E0DD (**222**), ZP 0020–0031 (**18**), DEVICESTATE EA00–EA92 (**147**), PAGEMAP E100–E8FF (**2,048**), CACHEMETA E900–E9BF (**192**), range buffer C000–C0FF (**256**) and linked UCI buffer C100–C8FF (**2,048**). Runtime emitted BASIC/CODE/RODATA/DEVICECODE is **16,698** bytes. MAIN has **1,321** padding bytes and 4000–4FFF contributes **4,096** explicit startup zeros; PRG **22,117** is separate from linked total **21,631**.

Unit CODE 080D–3B0A (**13,054**), RODATA 3B0B–3E82 (**888**), TESTCODE 3E83–3EA6 (**36**), DEVICECODE **3,684**, ZP **30**. Unit MAIN padding is **345** bytes plus **4,096** display startup zeros, producing the same **22,117-byte** PRG from **22,619** linked bytes. Code remains outside 4000–4FFF display/font and 6000–7FFF bitmap reservations. Final source/map identities are retained in [current slice evidence](evidence/clock-keyboard-uci-20261015.json).

DEVICESTATE growth is clock **13**, keyboard **18**, UCI **43** and native CIA clock **12**, added to previous **61** for **147** total. Clock/UCI/native-clock add **390/1,265/333** DEVICECODE bytes; keyboard adds **464** MAIN CODE bytes, with additional BIOS gate/port/ROM glue accounted in final totals. No runtime ZP or pre-map BSS is added by these components. Static control is 222+2,048+192+147=**2,609**, leaving **1,487** bytes including gaps; only **34** are in pre-E100 BSS. DEVICESTATE has **1,133** bytes left before EF00, metadata **64** before EA00.

Remaining runtime code windows are MAIN **1,321**, DEVICECODE **412** and C900–CFFF **1,792** bytes (the latter budget is not yet a linker code segment). Unit MAIN has only **345** bytes. The linked UCI buffer has consumed its previous conditional reservation. Full-system stack/IRQ/KERNAL bounds remain unmeasured; private overlay/render/file-command modules are not linked and cannot be charged as completed functionality.

Cold-import extension supersedes only the file/startup totals above: IMPORTCODE 931 bytes at 7000–73A2 (905 code + 26 cold state), checked tail 3,165 bytes, final PRG 30,721 bytes. Resident/main/device/overlay bytes remain exactly 28e4290. All-linked-variant totals 25,238 runtime/26,226 unit include the cold image; do not charge its 26 state bytes as resident metadata or reuse them after bitmap takeover. [Exact map/package evidence](evidence/image-import-linked-20261015.json).


## Configured native runtime — actual2026-10-15 maps

Runtime CODE12452, RODATA880, initialized NATIVESTATE3, DEVICE4084. Unit CODE13368, RODATA904, TEST36, NATIVESTATE3, DEVICE4084. MAIN free988runtime/12unit; DEVICE free12. Cold IMPORT931+COLDINIT898+COLDRODATA642=2471,7000–79A6;1625-byte checked tail. Configuration7919/142bytes and diagnosticEAF4/19bytes are this build's labels. BSS222, DEVICESTATE263, ZP18runtime/30unit, PAGEMAP2048, CACHEMETA192, range256, UCI2048. Static control222+2048+192+263=2725, leaving1371 including gaps; pre-map BSS still34.

Both packaged PRGs32769 load0801–87FF. Linked file content22974runtime/23950unit; padding3649/2673=MAIN988/12+display1024+DEVICE12+coldtail1625. All-linked totals30950/31938 include alternative overlay payloads and disposable cold bytes. Excluding cold2471 and alternative payloads2927, resident allocation25552/26540 includes3072fonts/static reservations; max loaded FILE1088 gives26640/27628. Resident emitted BASIC/CODE/RODATA/NATIVESTATE/DEVICE17431/18407 excludes cold/fonts. FILE1088,TEXT957,INPUT882 and all6144 startup assets are unchanged. Future unit-cold relocation/PIT/GFX/HD layouts are private and unaccepted. Exact artifacts/manifest in `agentworking/runs/native-runtime-20261015-root`; [evidence](evidence/native-runtime-20261015.json).


## Current five-overlay timer/CGA maps — 2026-10-15

Supersedes earlier current totals. Runtime/unit CODE13223,RODATA880,NATIVESTATE3,DEVICECODE4042; unitTESTCODE1 remains resident. MAIN free217/216; DEVICE54. ColdIMPORT931+COLDINIT991+COLDRODATA718=2640 at7000–7A4F; config79C2/142bytes. Unit-only975helpers7A50–7E1E leave481coldtail; runtimecoldtail1456. Only fresh PRG reopens cold lifetime; fixture guard rejects before stack/register/evidence mutation after any native attempt/bootstrap/release. Seven standalone helperPRGs byte-identical.

BSS222,ZP18runtime/30unit,DEVICESTATE345atEA00–EB58,PAGEMAP2048,CACHEMETA192,range256,UCI2048. Staticcontrol222+2048+192+345=2807,remaining1289includinggaps; pre-mapBSS34. NoF000hostshadow is linked in this target.

FILE1088,TEXT963(renderer718+VIC245),INPUT882,PIT1662,GFX1278 are alternativeC900–CFFF payloads; maxPIT leaves130. Sources6000/6800/8000/8800/9000 commitALL10240bytes toREU340000–3427FF before cache/BIOS. They initially overlap12cacheframes. Runtime/unitPRGs36865load0801–97FF; linkedinitialfile23872/24848,padding2751/1775; all-linked34876/35864 includesalternativeoverlays5873+cold2640+unit975.

Residentallocation excludingdiscardablecold/unithelpers andalternativeoverlays is26363/26376includingfonts/static; maxloadedPIT1662 gives28025/28038. ResidentemittedBASIC/CODE/RODATA/NSTATE/DEVICE18160/18161,with3072fontdata separate. Exact maps/manifest are retained in `agentworking/runs/timer-graphics-20261015-root/`; [evidence](evidence/timer-graphics-integration-20261015.json). FutureHDshadow/scrollrelocation remains a private proposal; per-window free bytes cannot be pooled without actual linking.


MODE/XTcompatibility follow-up: runtime3c2627a4/unit6280024d changes only loadedbyte5014(31h→25h) fromfiveoverlaycheckpoint. Allsegments/PRGlength/padding/fonts/overlaylengths/coldlifetimebudgets unchanged. Bothmaps independently verified byrootmakebuild/default. This is not an HDshadow allocation.


Opt-in standalone native-file restore is separate from emulator resident allocation:4624bytePRG0801–1A0E,DRFconfig1985/138,ZP20–25,2KiBstaging8000–87FF,UCI C100–C8FF,descriptorE000–E009,stateEA00–EA78,32bytemailbox6000–601F. No overlays/cache/guest/renderer. Exactly2048×2048byteDMAs addressREU[0,4MiB); uppercapacityexcluded. Source/export-onlyFILEalias changesnoemulator/helperbytes. OriginalstandaloneDRS1592bytesunchanged. [Sourcebuild/contract](../docs/NATIVE_FILE_RECOVERY.md).
