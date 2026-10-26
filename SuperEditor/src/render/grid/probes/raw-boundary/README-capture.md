# Released private capture-cost variant

First release only: single-byte full-table CRC loop. `build-capture-release.py` reconstructs the immutable corrected raw boundary release, requires original C33/R25 byte identity, and builds the changed C33. Unroll experiments in `build-capture.py` and separate `crc4-fit` artifacts are not this release. Corrected boundary files and its verifier remain exact committed ea1910e.

Only product source delta is `src/render/grid/caret/caret.s`; R25/R14/Make/resident/BSS/ZP/assets are unchanged. C33 is4096 padded bytes, CODE+RODATA endsBEAF (80B before the fixedBF00 font); tailBFD0 unchanged. SEO SHA256 `db2de0588aacefd8e946a5059b14f1f6cfcf473a5842c1415de39dfab4313daf`. Three existing resident imports (`se_overlay_active`, `se_crc_table_low/high`) are resolved by normal module bindings; no old private address aliases are embedded. The only direct service address is public SEO R-slot entryA010.

Two capture-only changes retain every existing field, source/owner/capability check and all22 complete240B packet CRCs:

* Ordinary entry resets privateC+62. Actual normal R25 authentication and `admit` execute through the real resident loader exactly as before. At CAPTURE, record the now-active R25 catalogue index inC+62. Subsequent helper calls can jump to its realA010 entry only whenOP0, that saved index is nonzero, and `se_overlay_active` still matches. Otherwise use the original loader dispatch. Caret/typingOP1 always use ordinary dispatch, independent ofC+62/SIGN overlap. Actual R25 entry still checks owner4 on every call.
* CAPTURE freshly expands the sealed resident half-CRC tables to low256@8D00 and high256@8E00. Link assertions require the original aligned128+128 half-table layout; upper values use the exact CCITT linearity XOR9188. Capture packet CRC uses this full table directly. Other operations retain the original R25 CRC helper. No table lifetime is assumed across calls or yields.

Lifetime proof: initial `admit` already requires owner0→4, job0, drawbusy0, redraw0 before frame capture, no doc read locks, no pending semantic request1, no hot phase/navigation/document busy and checked source objects/provider/FE. Thus legacy source-reader phase8EE0 is not leased. Existing private phase8D00..8EFF (512 bytes, including only the inactive legacyFS prefix) is exclusive capture data scratch. CAPTURE never calls R14 or a parser. Between helper calls, C33 invokes resident view/CRC/DMA only; R25's entire actual static graph has **zero opaque overlay calls**. Its selected R-slot code therefore stays loaded during this uninterrupted C33 call. The active-index comparison retains the original loader fallback if the slot changes. Managed source/capability/CRC checks are not skipped. No executable RAM is modified.

The static proof supplies the actual authenticated R25 payload only in `C:grid`'s address map. All its instructions are decoded, not treated as an opaque call. Every other C module retains the original unknown-R-entry rejection. Existing full54/staged graph remains R23/C37/foreground52/combined68. This extension is isolated in NEW `tests/test_grid_capture_stack.py`; no general verifier was modified.

Frozen first variant: `build/grid-raw-boundary-capture-crc-fit/fixture`; executable/source/labels `candidate/`, `tree/`. Release-only recipe output `build/grid-capture-release-recipe` was separately rebuilt and both SEOs byte-match that fixture. This is CPU/component qualification, not native/hardware integration.

Checks:40 exact native-scenario CPU Plain/Full60/80 frames,44 raw wrapped/boundary frames,24 prewrite faults,8 capture admission/phase refusals,8 source40/GEOS cases,20 diverse Full/Plain60/80 frames,132 independent random/fixed CRC vectors with whole64KiB guards, and8 exact pixel/source/whole16MiB A/B profiling intervals. All source/history/packet/anchor/style-role/VIC checks remain enabled. The CRC component independently derives all256 table words with `binascii` and permits only the512B phase plus stack writes; each CRC permits only the2 CRC bytes plus stack. Wrong owner/read lease/pending semantic/drawbusy CAPTURE refuses before phase/REU/pixel changes.

Precisely instrumented PC observer costs (CPU instructions, not PAL cycles or physical key latency), corrected boundary control→candidate:

|Edit|First publication control→candidate|Settled control→candidate|
|---|---:|---:|
|60 new row insert|403858→403876|541114→482630|
|60 new row BACK|415077→415098|551819→493755|
|60 CR insert|590498→590520|725971→668790|
|60 CR BACK|575805→575820|709850→653842|
|80 new row insert|330117→330135|465962→408652|
|80 new row BACK|343334→343355|478611→421742|
|80 CR insert|457519→457541|592155→535742|
|80 CR BACK|441816→441830|574899→519723|

Savings55–58k settled; first publication costs14–22 extra instructions. Post-publication capture falls134–137k→78–79k. Original052628 unoptimized Plain still settles80 new-row/CR insert at303277/415139, so general structural performance remains open. This release does not claim to remove the postpaint22-packet capture or implement physical-row geometry changes. No blank-row shortcut is present.
