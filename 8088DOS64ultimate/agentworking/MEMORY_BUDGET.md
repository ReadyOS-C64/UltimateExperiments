## Public startup clock repair — 2026-10-17

Runtimec6e43/unit01d97461,47105B: all linker segment ranges/sizes matchpubliccea5 baseline, COLDINIT0x533 unchanged. Factoredbounded samplehelper fundsfourcalls withzeroallocationgrowth. NMI5882,8physicalslots,fonts/handoff andunitcoldlimits preserved. Actualpublicbuildmemorychecks pass andruntime/unit/release reproduceclosedauthorbyte-exact. No newREUrange. ROOTcleanupc45PUBendsAFFE/free1, otherinstallerbudgetsunchangedfromf75.

## Final root f75 measured fit — 2026-10-17

SETUP40542B; residentends5FF9/free6,FAT_CODE6000..AF96+ROAF97..AFFC/free3; UI BSS A65D..AFFB/free4; AUX C3A0..C6AF784/free336; HIGHF700..FFDF2272/free26; HIGHBSSendsF6DE/free33; STATEendsBF9B/free100; PUBBSS9FA7..AFE3/free28. +11AUX lifecycleclear and PUB-only93B completioncaption included. No newREU/ZPallocation. Positiveflow fits/executes; publicationcollisioncleanup fails and needs a measured successor, not budget waiver.

## Compact SETUP UCI/AUX measured layout — 2026-10-17

Private cc0934a0/40,459B: UCI C000..C39F928B (command160/data512/status256), AUX C3A0..C7FF1120B. Actual test AUX_CODE760+RO8=768; HIGH2205/free93 unchanged. UI_CODE13837/UI_RO1120; UIBSS A60A..AFA8/free87. STATE BF8D/free114; HIGHBSS F6DA/free37; resident5F5E/free161 (UCI-4/FILES+7 = +3), FATfree590/PUB1934 before worker/cleanup changes. Generic descriptor copier reuses existing contiguous ptr1/2/3 with linker assertions; per-byte readback/no SMC. Both serialized HIGH and AUX count toward UI metadata/cacheCRC. Actual FW773 predicts82UIfree; not measured here. Undefined/zero exact parent map. No new REU range or public layout changes.

## Native installer coordinator measured fit — 2026-10-17

Private root5356cd1d/39,678B (first cohort rejected for RunStop handling, not layout): BOOT080D..0833=39B; resident ends5F5B/free164; UIBSS A2FD..AC9B/free868; HIGH_CODE F700..FF9C=2205/free93 before vector area; HIGHBSS E000..F6DA/free37; STATE B000..BF8D/free114; FAT19890/free590; PUBfree1934. Includes1174B/17B cooperative source service, new bootstrap/control and183B retained internal source/output ledger (outputs remain zero). No stack, CRC-table, IO or vector allocation was reduced. RunStop3→27 successor has zero measured code/data growth. Complete FAT/PUB worker integration is not yet fitted; the upcoming SI leaf-first change adds67 resident bytes and is not included in these figures.

## Current measured cold handoff promotion — 2026-10-16

ROOTruntimecea57480/unit13a82a45, each47,105B. LOADERCOLD963B4000..43C2,61B beforefont4400; helper307B run6000..6132/trailingFILEloadCEB8..CFEA, packagedsource65C8..66FA. FILEengine1464B unchanged, combined1771/1792 leaves21. NATIVESTATE6B (requiredflag0default), MAINfree31runtime/30unit. Unitcold4095/4096 leaves1. FixedNMI5882 RTIunchanged. Bothactualmemoryverifiers pass;444source/tool/productinputs/copies exact. Helperreadback comparedall307B to untouchedfull-PRG-CRC-boundsourcebeforeexecution; existingFILEheaderhasno payloadCRC. No newREUarena or ZPallocation. CPU/IRQ/REP/timer policy unchanged. Evidence native-main-cold-root-20261016.json; privateauthor ce482 source/maps plusROOTreviewlogs retained. No physicalnewmain orcompleteSTARTclaim.

## Measured split256 SAVE union — 2026-10-15 20:39 PDT

Current d883c678/88669999 PRGs45057 bytes. SAVER1543/2032 (+33), DEVICESTATE1009 (+2); MAIN free1runtime/0unit, DEVICE4082/free14, HDBIOS2810/free774, FILE1170/1792, PIT1764/1792, BSS206, ZP36/48, cold3067/4042 unchanged. No REU region or cache budget changes. Actual runtime/unit linker JSONs and387-file closure retained in runs/split-save-root-promotion-20261015-202600.

## Measured SAVE union, 2026-10-15

ab2d0d5f/06a4eead,45057-byte PRGs: MAIN free1/0, DEVICE4082/free14, HDBIOS2810/free774, FILE1170/1792, PIT1764/1792, SAVER1510/2032, DEVICESTATE1007, BSS206, ZP36/48 within192, cold3067/4042 within4096. Seventh2KiB startup asset REU343000..3437FF; B000..BFFF borrowed only during paused SAVE. Native RAM-only UCI init saves27DEVICE bytes. Both actual linker JSONs and387-file closure in runs/native-save-root-promotion-20261015-181800.

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


## Current six-overlay HD and coherent-scroll maps — 2026-10-15

Supersedes the five-overlay current totals. Runtime/unit PRGs are 42,497 bytes, load0801–ADFF, SHA98fcd115/6eba1ee7. Runtime/unit MAIN free115/114, DEVICE22, cold1093/118. HDBIOS2144bytes in F000–FDFF leaves1440 zero-tail bytes; FE00–FFFF stays excluded. Actual unit975-byte cold helpers and one-byte resident return sentinel are included. Runtime/unit ZP18/30, BSS223 (new bios_disk_is_hd atE0DE), DEVICESTATE659 (growth314 plus BSS1 =315 controlbytes), PAGEMAP2048, CACHEMETA192, range256, UCI2048. Staticcontrol223+2048+192+659=3122,leaving974 includinggaps; pre-mapBSS33. Per-window space remains non-interchangeable.

HD1427 joins FILE1088/TEXT963/INPUT882/PIT1662/GFX1278 as alternative C900 payloads. All12288 startupassetbytes at6000/6800/8000/8800/9000/9800 commit toREU340000–342FFF. Separate A000–ADFF shadow source overlaps7cacheframes; overlay sources8000–9FFF overlap16, for23 total. All commit/copy/byte-verify beforecache/BIOS. Default disabledHD still loads shadow forscroll/modeclear. HostF000 and guestphysicalF000/F0000 are distinct address spaces.

HDextentcacheREU200000–2FFFFF holdsup32×32KiB; authoritativeuncertainsector350000–3501FF and guesthandoff352000–3521FF fit minimum4MiB. No largerREU assumption. Exactrootmaps/package/memory/sourcebinaryproof live in `agentworking/runs/hd-production-20261015-root`; independentnormalreview verifiescomplete65536-bytehostaccounting and both entirePRGs. [Contract](../docs/HD_IMPLEMENTATION.md).


## Current combined clock/PIC maps — 2026-10-15

Supersedes only the current six-overlay target identity and shadow/PIT code totals above. Runtime22f82091/unit8a84329c remain42497bytes,0801–ADFF. HDBIOS2361bytes endsF938,1223zero-tail bytes throughFDFF; copy/verify remains3584bytes excludingFE00–FFFF. Owned clock entries add217bytes without additional ZP/BSS/state or MAIN/DEVICE allocation. PIT1664 leaves128bytes inC900–CFFF. The six alternative payloads total7302bytes:FILE1088,TEXT963,INPUT882,PIT1664,GFX1278,HD1427. Startup asset reservation remains12288bytes;23 startup-overlapped cache frames remain unchanged.

MAIN115/114,DEVICE22,cold1093/118,ZP18/30,BSS223,DEVICESTATE659 remain unchanged. Nine standalone helper PRGs are byte-identical. Full root map/package/memory and executed native DOS/MODE identities are pinned in [performance evidence](evidence/boundary-performance-20261015.json). No pooled headroom or larger REU assumption is introduced.


## Current GW-BASIC compatibility maps — 2026-10-15

Supersedes currentproductionidentity only: runtimeed7462bad54947a32092cf7cd3f6ac4e6f962cea98757555e104c0ebffdcedd8/unitd530c37556d148e0972766b5f9a7bbdc7bba39d83d06792ce22661163a8e03ea,42497bytes0801–ADFF. Actual CODE13418(+95), MAIN20runtime/19unitfree, DEVICE4074/22free, BSS223,ZP18/30, DEVICESTATE661(+2PPI/PITwritephase). Staticcontrol3124leaves972includinggaps; pre-mapBSS33. Shadow2361/1223tail,PIT1664 and allsixoverlay lengths/12288startupreservation unchanged. [Exactrootmaps/evidence](evidence/gwbasic-hangman-20261015.json). LayoutmakesnoextraREUassumption; full-systemstackboundremainsunmeasured. Privateperformanceunion10/9MAIN isnotproductionorbehavioraccepted.


## Current word/fetch union maps — 2026-10-15

Supersedes current identity above: runtime1a17831879058a363d9581e49b6c796ea7d90c9bf7c022a81e1643bcc037e5ae/unit4e4301ef2cb9f40aabe99bdf478da488ea58a32816076f0b6bc74aaf7e823402,42497bytes0801–ADFF. CODE13412,RODATA880,NATIVESTATE5, MAIN26runtime/25unitfree; DEVICE4074/22free. BSS205 (18privateCPU/fetch bytes moved to ZP), ZP36/48; DEVICESTATE661 unchanged. Staticcontrol205+2048+192+661=3106 leaves990 includinggaps; zero page separately accounted. Shadow2361/1223tail, sixoverlay lengths includingPIT1664/max128tail,12288startupreservation and23overlappedcacheframes unchanged. No publicguest/mailboxABI or addedtotalstate. Allmaps/package verified byrootmake test and bothPRGs exactly reproduce independent review; [evidence](evidence/word-fetch-performance-20261015.json). No pooledheadroom, largerREU or fullstackbound claim.


## Current native UCI guards/trace maps — 2026-10-15

Runtime9ed3bc7b198d90ab3ef24c50ea0ce25f664457fed70a08e3382e9efb2ee11dda/unit8aa2defb9a2ee35a87f0a8293e97ca88edf1d68c4689ac3407a7f7cc43d9ed74 supersede1a17/4e43. Both42497bytes0801–ADFF. Native-only19-byteuci_expiredmovesDEVICE→MAIN: CODE13431,MAIN7/6free. DEVICE4080/free16 includesquietguards andready-checkedtracehook. HDBIOS2418/free1166, full3584copy stillendsFDFF/excludesFEvectors.176DEVICESTATEbytes addUCF1trace, now837EA00–ED44; BSS205,ZP36/48 unchanged. Staticcontrol3282leaves814includinggaps. No newREUreservation or borroweddisplay/cachecapacity. Nativecold+3resetcall: unitlinked3981/115tail; normal3006/1090tail. Allsixoverlaylengths/PIT1664 and12288startupreservation/23overlappedframes unchanged. All10standalonehelpers remainbyteexact. Actualrootmaps/365-inputmanifest andindependentreproductiona1ff bind[evidence](evidence/uci-quiet-trace-20261015.json). SAVEFILEINFOcomposition4095DEVICE/2786shadow/1005state/unitcold54 isprivateLAYOUTONLY.


2026-10-15 currentexactPITaccumulator: runtimeb29cb1a166c9939da35594af36656962d9e9ed8b5622a07dc20737cb87131841/unite374bb33c2d3e2a918346a2c4742fa5fb5dc338e3918fcbfd7d971651dac40a9. Both42497bytes; MAIN7/6,DEVICE4080/free16,HDBIOS2418/free1166,BSS205,DEVSTATE837,ZP36 unchanged. PITpayload1664→1764 in1792window/free28; totalsixpayload7302→7402. StartupREUreservation12288/23overlappedframes unchanged. Exactmaps/root367manifest+13standalonePRGsverified. Additional100bytesmustloadoneachPITmiss; CPUprofilingexcludesDMAstalls. Evidence:pit-inplace-performance-20261015.json.


2026-10-15 currentUCF2+PIT7122c4e1/22b45779: normal/unit42497bytes. NativeUCIrawIDstore+3 andguardedprestarttrace+10→DEVICE4093/free3. HDBIOS2442/free1142; full3584copy/paddedtailstrict. UCF2record177+separatelastID1→DEVSTATE839(+2). MAIN7/6,ZP36,BSS205,cold3006/3981,PIT1764/free28 unchanged.13standalonePRGsbyteexact. Root367manifest/maps andindepunion28c0verified. NoSAVE/FILEINFO/nativecompilercompositionclaimed.

2026-10-15: Native-only REU completion observer: bc195f39/84e51c94, CODE13437; MAIN free1runtime/0unit, DEVICE4094/free2, BSS206 (+1first-status), oldZP36/48 unchanged; NMI RTI residentDEVICE5884 asserted. HDBIOS2442/1142tail andPIT1764/28tail unchanged.

2026-10-16 HDsplit256 ROOT71972b7e/729111fa: HDCODE1472/1792 (+45,320free); HDBIOS2810/3584, DEVICESTATE1009/1280, MAIN1runtime/0unitfree, DEVICE4082/free14,ZP36/48 unchanged. Both actuallinker memoryverifiers pass. Privatepalette adds56HDBIOS not includedhere. See evidence/hd-split256-root-20261016.json.

2026-10-16 ROOTpalette44d54c35/2635a47e:56newbytesinpermanentcopiedHDBIOS,2866/3584with718zerotail. MAIN1runtime/0unitfree, DEVICE4082/14free, HDCODE1472/320free, allstate/ZP/cold/REUunchanged. Bothactuallinker memoryverifiers pass. SourceallocatedinsideF000..FDFF, excludedFEvectorspreserved.

2026-10-16 ROOT45896d10/a8274e7c acceptedESC/WAIT+palette+HD: MAIN1runtime/0unitfree, DEVICE4082/14free, HDBIOS2866/718free, HDCODE1472/320free, DEVICESTATE1009, ZP36/48. CorrectedWAIT fitsbyneutralfetch-forwarderalias andotherzero-state savings; allmemoryverifierspass. Immutablemaps/currentmanifestclosure in runs/esc-palette-root-promotion-20261016. No NEW REUreservation.

2026-10-16 ROOT4cc3035f/4b82fe0d CGA core: CODE13405; MAIN50runtime/49unitfree, DEVICE4042/4096 (54free), HDBIOS3541/3584 (43free), FILE1461/1792 (331free), HDCODE1472/1792 (320free), DEVICESTATE1041/1280, ZP36runtime/48unit. Both linker verifiers pass;394manifest source/products plus immutable copies retained runs/cga-status-root-promotion-20261016. Status math leases existing FILE overlay only; sevenREU source slots/reservation unchanged. MAIN/DEVICE unchanged wording in peer status addendum refers allocations, not blanket assembled-byte equality after8B state relocation. No clock-policy change.


2026-10-16 ROOT memory/address b3d17d02/b995c5e1: both45057B, MAIN49runtime/48unitfree (+1byte versus4cc), DEVICE4042/54free, HDBIOS3541/43free, FILE1461/331free, HDCODE1472/320free, DEVICESTATE1041, ZP36runtime/48unit. Both actual linker verifiers pass. SevenREU slots/reservation unchanged;498source/product closure and copies in scratch/ac-development-root-promotion-20261016. Private cursor/keyboard budgets do not describe ROOT.


2026-10-16 ROOTcursor+memory da95caf7/bc6ab7fd both45057B: MAIN34runtime/33unitfree; DEVICE4080/16free; HDB3577/7free; FILE1464/328free; TEXT1003+245=1248/544free; INPUT882unchanged; HDCODE1472/320free; DEVICESTATE1049/1280; ZP36runtime/48unit. Both actualverifierspass,503source/products/copies exact. No newREU source slot/reservation. Keyboard1182/private state+3 notyetincluded.


2026-10-16: ROOTkeyboard+cursor+memory417c/3838:45057B;MAIN34runtime/33unitfree,DEVICE4080/16free,HDB3577/7free,INPUT1182/610free,FILE1464,TEXT1248,HDCODE1472,DEVICESTATE1052/1280,ZP36/48. Bothmapsverified;503pins/copiesexact. NoREUreservationchange.

2026-10-16 native C SETUP codec is a separate optional test fixture, not linked into the emulator: `build/setup-config.prg` c874e8f0, 3,305 bytes; actual map CODE $0801–$14E7 (3,303), BSS $14E8–$1DA8 (2,241), ZP $0002–$001B (26). Software stack starts at $C000 and tests constrain all software-stack writes to $BF00–$BFFF; hardware-stack restoration/bounds and all writes are checked. No REU allocation/DMA is performed by this codec. Its 576-byte durable configuration includes explicit configured capacity at offset 538. Runtime417c/unit3838 and all emulator allocations remain unchanged. User-authorized additional REU use is recorded in docs/REU_ALLOCATION_POLICY.md; larger runtime caches remain separate implementation work.

2026-10-16 ROOT A/B+keyboard+cursor+memory f17558cb/aa4bb083 supersedes priorcurrentemulator:47,105Bpayload47,103/0801–BFFF; CODE13,423/RODATA863/NSTATE5, MAINfree32runtime/31unit;DEVICE4080/free16,HDBIOS3577/free7,BSS207,DEVICESTATE1160/1280/free120,ZP36/48. FILE1464,TEXT1248,INPUT1182,PIT1764,GFX1303,HD1472,DISK1475 share1792C900window. NewDISKsourceB800–BFFF commits343800–343FFF; totalphysicalstartupslots8/16384B. SAVER343000 remainsseparate. Eightassetend344000 isassertedbelowHDauthoritative350000. Three360KiB arenas100000/180000/380000 rotate; spareends3DA000; installer3E0000–3EFFFF andanchor3FF000–3FFFFFexplicitlyreserved. Bothactualmapsverified;539pre/postinputs+copies. NoextraREUabove4MiB ornewIRQ/REP/clockpolicy assumption; no pooledresidentheadroom.



## Native installer components — 2026-10-16

Publicreleasefixture99c5:CODE0801..1095,RODATA1096..109A,BSS109B..111B129B,ZP2..1B26B,CstackBF00..BFFF;2204BPRG. ROOTemulatorf175/aa4 layoutunchanged. PrivateSTARTcontroller80cb:CODE0801..3834,DEVICE3835..3D25,FILE3D26..41B7,RODATA41B8..422D,DATA422E..4336;BSS8000..8FE7(4072),DEV8FE8..902A67B,UCI C000..C7FF,ZP26. NotcompleteSTART. Privatecoldcea5:963B4000..43C2 +307Bhelperrun6000/loadFILE tail, FILEtotal1771/1792, nativeNMI5882, unitcold4095/4096,MAINserializedrequiredflag adds1B; notROOTpromoted.

FastCRCportableassembly411B, scalar12B,ZP2,tablespage-aligned1024B; standaloneCABIfixture97323fdd756B. NativeSETUPwriter successor reserves C900..CCFFtables andCD00..CFFF768Bsoftwarestack (observedcurrentworst103B; futurefrontend boundsrequired). This tablelayout mustneverbeused duringmainDISKC900 ownership. MoreREU authorizedwhenneededforspeed; configuredcapacityguardandwholephysicalrecovery remainbinding.

## Standalone START measured promotion — 2026-10-16

Actual public8b68/bb14 map: completePRG18,432B, payload0801..4FFE; one byte free below5000. CODE080D..43A2, DEVICE43A3..4893, FILE4894..4D25, RODATA4D26..4E83, initialized DATA4E84..4F8E, serialized112B trampoline4F8F..4FFE/run0200..026F. BSS8000..8DEB(3564B), DEVICE8DEC..8E2E(67B); UCI C000..C7FF, CRCtablesC900..CCFF, softwarestackCD00..CFFF768B, actualZP20..3D30B. This is a separate native launcher, not the emulator allocation. ROOTsource-build/public46-group proofs reproduce exactbytes; no physicalspeed inference.

Reviewed private SETUP selection7194 adds phase-only UI code and787B UIBSS to the measured overlay fixture; state is zeroed by checked UI cache restoration, not assumed CRT clearing. Browser private-ledger successor adds10B HIGHBSS and245B UI code, leaving280B HIGH and143B STATE. Capsule2C0000..2C03FF and~20B permanent authority are still budgets pending actual link. Selected UI pointers must not survive FAT replacement.

2026-10-16 D64S native UI helper, separatefixture abb9592d: CODE2539B,RO33B,BSS674B, sharedCRCtablesC900..CCFF; zero resident START bytes. Future SETUP composition must place this state in explicitUIBSS and measure fit. Byte callbacks avoid reserving a whole18,432-byte template in C64RAM. START.RELc835 records actualcontrol fileoffset18188, DATAoffset18053/267B; consumers validate offsets instead of hardcoding these current values.

2026-10-16 private repeated-writerce0fca70: measured resident ends5AF9 versus parent overlay-manager5AC3, growth54B (an earlier informal21B estimate was wrong). CODE1190..598E, RO598F..5A71, DATA5A72..5AF9;1286B remain below6000. FAT_CODE6000..A914 plus ROA915..A96E totals18799B,212B above parent18587B. STATEB000..BF70/free143 and HIGHE000..FED7/free290 are unchanged; ZP20..3F32B. Rearm functions execute only in the FAT phase; private state getters remain resident. This is the old browser/overlay fixture plus repeated-writer changes, not a combined selection/capsule/dispatcher link. Do not add its apparent headroom to other private-component budgets. Seal a9ed0ab9.

2026-10-16 raw publisher0129594a actual map: resident end5F7A,133B free below6000; FAT19,058B with unit writer fixture; PUB CODE4798/RO30/BSS1160 ends7763, no new permanent sector buffer (borrows NF512 only after private SI_DONE/knownclose). PUB cache2D0000..2D7FFF includes64-byte header+20KiB padded payload; readback260000..267FFF; raw source200000..259FFF or3F8000..3FEFFF. NF writes reuse200000/208000, so derive A only after C/B writing. Whole SETUP composition not linked yet.

2026-10-16 source loader33db actual map: resident5FA7/free88; STATEBF70/free143; HIGHBSS E000..F61B/free228 beforeF700. HIGH_CODE420B runsF700..F8A3/free1882 throughFFF9; initial UI serialized9AB9..9C5C is included in full immutable UI CRC and bootstrap-byte-compared. UIBSS9C5D..ACB0/free847; moved actual2241B install_config UI-only BSS, omitted unused UI D64L1327code/129BSS/5RO. Source controller permanent overhead96B. Main/START unchanged. Three immutableDOS100000/180000/380000, template2E0000..2E47FF anddescriptor3FEC00..3FEC3F remain disjoint; ordinary READ verification uses existing UCI_data, no extra REU allocation. Full coordinator/combinedFAT+PUB not yet accepted.

2026-10-16 correction: HIGH_CODE420 runF700..F8A3 leaves1878 bytes throughFFF9 (08FA2298total−420), not1882 earlierprose. Actualaddresses inoldseals unchanged; recorderrata ratherthanrewritesealedproof. Combinedno-test-writer e1be actualFAT19890/free590,PUB18438/free2042,resident5FA6/free89,HIGHBSS237,STATEBF7A/free133. OriginalPB inthatfitisNOT_READY; newerUI43c9 includes108-bytePUBrepair (PUBendA871/free1934), UIendAFDF/free32. Path-onlyfirstlinkaab37ccf reclaims3280UIbytes (1552code+1728BSS), UIendA30F/free3312, verificationpending. Cooperativehelperfirstlinkreclaims179residentbytes butuses883HIGH+14HIGHBSS, enabledbehaviorpending; actualcoordinatorfit mustbe measured.

2026-10-17 public SETUP c45dea7b actual linker: PRG40,542B; resident ends5FF9/free6; FAT CODE6000..AF96,ROAF97..AFFC/free3; UI BSS A65D..AFFB/free4; AUX C3A0..C6AF/784/free336; HIGHF700..FFDF/2272/free26; HIGHBSS E000..F6DE/free33; STATE endsBF9B/free100; PUBBSS9FC2..AFFE/free1. Source-closed public builder confirms all bounds. No new REU/ZP reservation. Independent INI parser1377CODE+32RO+208BSS, fixture1682B is NOT allocated into product; START still has one byte headroom.
