# Private COUNT-packed layout memo, version 2

This separate profile is a measured follow-on to the immutable fixed842
release in `src/cache/layout`. It is not registered in canonical startup and
has no C21/lifecycle/UI integration. Do not replace the fixed842 contract
silently: this profile preserves only ABI3's declared live packet fields.

On the latest 53-asset fixture `20261026T021924007962Z`, actual diverse422
produces 19 rows / 283 glyphs. The memo payload is 3,469 bytes rather than
17,406. Capture costs 498,623 instructions. Restore costs 732,827 plus the
actual repaint's 1,175,241 = **1,908,068**, compared with a same-input warm
forced-full **2,605,663** (26.8% fewer instructions). This is one component
comparison, not a native latency or automatic navigation claim.

The sealed private R34 payload is 3,662 bytes. It adds no BSS/ZP, bank or
resident code. All fixed-profile source/provider/FE/font/settings/fold guards,
whole payload CRC before primary writes, per-record CRC, VALID-last,
foreign-owner ordering, explicit REVOKE and foreign-lease rules remain.
No broad compact-profile fault matrix or integrated stack/lifecycle gate has
been run. The fixed profile's 84-case result is not relabeled as this profile.

## Representation and reconstruction

Per row the packed packet contains prefix32, CHARS[COUNT], STYLES[COUNT],
ROLES[COUNT] and X[COUNT+1] 16-bit boundaries. Thus packet bytes = 34+5*COUNT.
An unchanged outgoing64 follows it. Header64 and incoming128 remain exact.
The total is `192 + 98*ROWS + 5*sum(COUNT)`; rows<=22 and COUNT<=161 give a
safe maximum20,058 bytes plus metadata320 =20,378 within scatter20,864.

Authenticated metadata272..293 stores each row's COUNT. Capture first reads
one actual prefix32 per bounded service; it validates COUNT<=161/highbyte0
and checks the actual packet's COUNT again when its full prefix is assembled.
No host packet is supplied. Restore authenticates metadata/counts, checks the
whole packed stream, stages and checks each packed record, then writes only
the exact original live-field ranges. The one-byte gaps and unused tails are
left untouched. Metadata version2 distinguishes this format from fixed842.

`editor.inc` ABI3 names GPR_LEFT/RIGHT non-live and GPR_USED=842. The current
producer writes COUNT chars/styles/roles and COUNT+1 x boundaries. The public
C22 compositor, navigation and edit/caret consumers bound array access by
the checked prefix COUNT. All prefix32 bytes remain preserved, including
caret/tail geometry and reserved language bytes. Outgoing/incoming parser
certificates are copied exactly; no new parser authority is invented.

## Qualified proof scope

```
python3 tests/test_cache_layout_compact.py --fixture build/cache-editor-product/20261026T021924007962Z/fixture
python3 tests/test_cache_layout_compact_boundaries.py --fixture build/cache-editor-product/20261026T021924007962Z/fixture
```

The cost gate uses actual public producer, real POSITION/W_LOAD, checked
R34 capture/restore and real C21/R21 consumption with C20 removed. Zero
C20/C24/C25/C26 entries execute on the restored wrapped-page consumer.
Independent `geos_packet.rows` decoding compares all live fields, and a
canonical source/raw-font oracle compares all64,000 pixels/1,000 attributes.

The five small boundary cases cover empty source, three zero-glyph CR rows,
COUNT161 at pan1, 22 native rows, and 20 inline rows crossing scatter splits.
They poison every primary packet byte before restore, compare independently
decoded live packets, and require every omitted tail/gap to remain poisoned.
Full16MiB outside exact live writes remains unchanged. Actual public C22
BEGIN/STEP consumes restored packets with C20 removed. Its CANCEL initializes
the aliased painter frame first. This direct consumer seam is disclosed:
current C21 intentionally refuses cached repaint in nowrap mode. The signed
nowrap oracle is used for the pan1 case; no wrapping oracle is substituted.

No source/pixel/history oracle or canonical product file was weakened. CPU
clock values are unavailable; no emulated-cycle/hardware claim is made.
REVOKE remains mandatory on freshFE/cold/resume. Automatic admission, page
eviction, real A→B→A routing and lifecycle permission are still future work.
