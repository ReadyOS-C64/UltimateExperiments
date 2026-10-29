# Private 161-glyph inline fix — released

This fixes a real source-mode3 no-wrap/PAN1 error90:200 minimum-width dots followed by a late matched pair produce a legitimate161-glyph row, but C26 rejected counts above160. No last glyph is discarded.

Promote the three hunks in `ready.patch` to `src/render/geos/{inline.s,inline.inc,page.s}`. The page hunks only select the new operation and publish the split final role; they are independent of the semantic-checkpoint publisher hooks. Rebuild C21/C26 together normally; no Makefile, resident, catalog, font, BSS, ZP, or REU allocation change is needed.

`GI_BEGIN_WIDE=4` accepts exactly161. Existing BEGIN0 and SOURCE_BEGIN3 remain max160 and preserve all existing addresses and finish protocols. This gives mixed-generation callers a checked error instead of a wrong final role. Styles161 are contiguous8300..83A0. Roles0..159 stay8F36..8FD5; role160 is separately8FEB. The hidden mask's original20 bytes stay8FD6..8FE9; bit160 is8FEA. Private tail state8EC7..8EC9 is below real FS8EE0. C20/C27 remain unchanged. Output outside COUNT remains untouched, except the fixed21-byte hidden mask, whose unused bits are zero. Each STEP remains bounded to32 feeds or paint/publication cells and one32-byte source read. Initializing the private161st cell adds one bounded initialization STEP compared with the previous160-cell loop.

The exact183509 sealed baseline builds C26 at3327 bytes (+134) and C21 at3597 (+65), with zero resident or additional state bytes. Images on that binding:

- C26 `1469eba7a2dbfd81b4dfba13a999ae06d8ab76f3ec626e51ed8b71a06312d27a`
- C21 `ace4420a8c7a0759469d9dae5360d97da88e522b201d8f194ebf1bb5ebc91e27`

Run `python3 tests/test_geos_inline161_candidate.py --suite fit` (or public/wide/legacy/inline/preview/fold/incremental). The builder compiles unchanged block-independent parser/cache modules from the immutable source ZIP, imports the exact frozen resident report once, and substitutes only C21/C26 in CPU fixtures. Those private fixtures retain the baseline D81/source ZIP and are CPU overlay-substitution inputs, not native-packaged disk claims.

Terminal gates:11 capacity render frames (704k independent pixels/11k attributes),11 wide queries including genuine style/role/hidden bit160,25 original queries/7 fault groups, public inline19, preview68, folded28, incremental15. Wide faults include invalid version/counts/source bounds, source revision changes before/during publication, counted foreign lease/idempotent cancellation, and30 foreign-owner calls. Wide worker REU is unchanged across every call over16MiB. Public capacity frames preserve canonical source/history/clipboard, shim, catalog identity, and all16MiB outside explicit derived FE spans; raw161 glyphs/styles/roles/maps are compared without legacy normalization. Existing tests use only the published managed slot-bit identity helper where necessary.

No canonical source, shared editor/D81 build, native process, or port was modified/used by this candidate. CPU image visualizations are not native VIC screenshots.
