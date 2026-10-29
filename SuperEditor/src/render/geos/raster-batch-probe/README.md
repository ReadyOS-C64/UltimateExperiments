# R21 resolver tile-range batch and histogram clear

Single-file release: copy `row.s` to `src/render/geos/literal-byte/row.s`, or apply
`ready.patch` to frozen021924. Do not copy old raster-probe or intermediate
row-bounds-only.s. All glyph/measure/assets witnesses remain unchanged.

SOURCE SHA2562536a8345fa1b7314127b51dd7223ee0558748275ad559f922adaac4d3e6f979
PATCH SHA2567f65c1e6ac247c455ed85b0425c3e427de7dbaa8d11eb7f01a66053811da808d
SEALED SEO SHA256fc3d235ca559914ba0a9b8a111599d1a09e867863c0ab3fa44d1c7ff04e3e183

The old color resolver recalculated x/tile geometry and called left/right clip
checks for every one of40cells. The replacement converts already-validated
0<=LEFT<=RIGHT<=320 once to first=floor(LEFT/8), end=ceil(RIGHT/8). It elects the
same histogram winner only for those intersecting cells. It preserves the old
attribute-intersection policy even for equal unaligned clip bounds. GR_TOP==
GR_BOTTOM still returns before resolver writes. Existing pixel scratch holds
exclusive end only during resolve; no new caller/BSS/ZP storage.

That saves21CODE bytes. They fund an eight-store unroll of the existing512-byte
histogram reset, preserving exactly the same addresses/order andY0 at each page.
The internal clear_slot assertion moves by21; it is not a public API or fixed
font/helper entry. CODE net0, payload4094, fixedABF3/AEDB/AF5B and downstream
measure/glyph entries remain unchanged. No new JSR/indirect target or guard
removal; per-glyph clips/styles/inverse/selection/caret and all14 saturating
color votes retain their exact behavior.

```
python3 tests/profile_geos_raster_current.py --fixture build/cache-editor-product/20261026T021924007962Z/fixture
python3 tests/test_geos_raster_batch_probe.py --suite fit --variant control
python3 tests/test_geos_raster_batch_probe.py --suite component --variant control
python3 tests/test_geos_raster_batch_probe.py --suite component
python3 tests/test_geos_raster_batch_probe.py --suite public
python3 tests/test_geos_raster_batch_probe.py --suite incremental
python3 tests/test_geos_raster_batch_geometry.py
```

2570strips/65faults match the original aggregate exactly;18 actual public A/B
frames use independent pixels plus full16MiB equality outside exact FE spans,
including selected/hidden/nested folds, styled prose/code, pending typing and
signed manualpan. Incremental15 passes. The51,681 scalar constructor cases use
an explicitly pure CPU seam, not authenticated application state: all0..320
clip pairs and2,067,240tile memberships match independent inequalities; every
runtime store is checked to the two existing scratch bytes. Terminal wholeRAM
and unchanged16MiB also pass. Application ownership/font/source validation is
proved by the complete component/public entry gates, not this scalar seam.

422Markdown2480653→2431404 CPUinstructions (-49,249/-1.985% total), Full2604975→
2555726; all9 public pairs improve, blank strip6238→4331. No native cycle or
latency claim. Images byte-identical both to control and the reviewed predecessor.
