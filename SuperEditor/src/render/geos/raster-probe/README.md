# Private R21 empty-ink scanline candidate

Release only `row.s` to `src/render/geos/literal-byte/row.s`, or apply `ready.patch`.
Source SHA256 88d73b52a0cded61d078c7c14e1d031d0b13e58523fb324181042177290514fd.
Other glyph/measure/assets files are unchanged frozen source witnesses.

A decoded scanline with `(inkhi | inklo | flags)==0` changes neither base-ink
histogram nor bitmap. It may bypass horizontal addressing/compositing entirely.
Nonzero flags conservatively keep the original inverse/selection/caret path.
All source bytes still advance and map identically; no clipping, font, palette,
owner, pointer, style, or frame guard is removed. Moving the existing row advance
beside vertical tests shortens safe ca65 branches; the more distant pixel exits
use ca65 long-branch macros. No new call/indirect target/state is introduced.

CODE grows8B into the original8B pre-font alignment gap. Payload remains4094B;
fonts stayABF3/AEDB, clear/helperAF5B, tailendsAFFD. Caller704B/frame, BSS/ZP,
asset catalog and resident code are unchanged. The literal API retains its B/I
styles0..3; genuine variable-font underline/preview uses a different R23 path,
which is unchanged rather than reinterpreted here.

```
python3 tests/profile_geos_raster_current.py --fixture build/cache-editor-product/20261026T015634252154Z/fixture
python3 tests/test_geos_raster_probe.py --suite fit
python3 tests/test_geos_raster_probe.py --suite component --variant control
python3 tests/test_geos_raster_probe.py --suite component
python3 tests/test_geos_raster_public_probe.py
python3 tests/test_geos_raster_probe.py --suite incremental
```

2570 isolated strips/65 refusal cases compare independent pixels, attributes,
saturating vote histograms, maps, full64KiB write guards and unchanged16MiB.
Both control/candidate aggregate479721386e237ace5a0f7f96c47465446cb45af5500bd4a7ee5df38dbce4dd28.
18 public-render A/B frames include actual semantic baseline, Full/Markdown,
selection, collapsed/nested folds, manualpan/clipped glyphs and pending typing.
They assert independent bitmap/attrs plus full16MiB equality outside precisely
listed FE derived spans (semantic53 arena immutable); no whole-bank masking.
The stock inline/fold legacy guards fail identically for baseline/candidate on
initial new type53 allocation, so their failures are retained and not counted
as candidate success. The owned observer-aware equivalent vectors pass.
Incremental15 existing public gate passes without assertion changes.

422Markdown forced repaint2582884→2480653 CPUinstructions (-3.96% total);
422Full2707206→2604975. Isolated dense-selected+648instr(+0.53%), nestedfold+176
(+0.024%) are disclosed. No native cycle or physical-key latency claim.

`row-vote-only.s` and `row-zero-fragments.s` preserve earlier smaller experiments,
not promotion sources; they saved less. No further mutations to release row.s.
