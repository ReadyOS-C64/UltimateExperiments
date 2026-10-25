# Private inline half-CRC candidate and dispatch placement proof

No production source, shared build, disk or VICE was changed. This is a private
candidate for parent review, not an integrated editor performance claim.

The candidate uses one half-table CRC byte loop. With a nonzero length whose
low byte isL, startY=-L and bias the staging pointer to4F00+L; process the first
L bytes, then increment the pointer page and process whole256-byte pages. For
a page-aligned length start at5000,Y0 directly. This visits exactly5000..5000+N-1
and removes per-byte JSR/RTS without skipping any CRC/binding check. Header
validation already rejects zero before CRCstage; that public precondition is
proved below. The private flag is PRIVATE_INLINE_HALF_CRC; no default changes.

Actual CPU gate: both original and candidate CRCstage execute every length
1..4096 against binascii.crc_hqx(payload,FFFF), every read address is checked in
order, with69 payload/binding corruptions each and whole64K RAM/source/table/
active/shim guards. Flag-absent editor-half, generic-full and generic-slow cache
binaries are each byte-identical to the original source under the same flags.

Across8,390,656 payload bytes:122,746,039→109,655,370 actual instructions.
At4096 bytes59,566→53,413; at17 bytes368→333; at1 byte123→127 (small setup cost).
The runtime cycle counter is zero; no cycle or native-clock claim is made.

Public cache gate:19 boundary sizes17..4096 import/reload/hit;56 actual payload
or binding corruptions; failed reload preserves the active slot, active tags,
load count and whole512KiB REU while performing only its staging fetch. Cache
hits perform no payload CRC or DMA. Logical asset1 maps to physical2 while a
foreign physical1 is reserved; whole REU compares byte-exactly except imported
owned payloads. Length0/16/4097 reject13 before payload CRC or DMA; bad header
CRC rejects10. The17-byte fixture is only RTS, so its returned carry is the
callee's unspecified carry; admission/CRC/cache behavior is checked separately.

Code grows679→711 bytes (+32), with no added BSS/ZP. It fits the frozen6e
baseline's32-byte gap exactly. New42be correctness work leaves only24 bytes.
A separate private current dispatch copy compiles270→262 bytes, saving8:
1. Share the existing set-job return with navigation via LDA12/BNEset_job (3B).
2. C22 result A0/A1 is already saved inX: TXA/BNEset_operation (3B).
3. Pending workerX1 supplies OP1 via TXA/STAOP/BNEdone (2B).
386 actual assembled before/after contract cases compare identical A/X/Y/P/SP/
PC and whole RAM except private code/stack. Child overlays/endpoints are
explicitly stubbed for that unit equivalence; this is not full editor acceptance.
Current42be gap24 +reclaim8 -CRC32 =0 is placement arithmetic only. Parent must
integrate, link/seal and rerun actual public editor/CRC/recovery/native gates.

Commands:
`python3 tests/test_crc_inline_profile.py`
`python3 tests/test_geos_dispatch_peepholes.py` (uses archived dispatch-fit build)

The first test builds only private products. The dispatch build snapshots source,
resident report/PRG/labels and actual module-bindings aliases in dispatch-fit/.
Candidate source ZIP/diffs and baseline fixture provenance are adjacent.
