# Complete private R23 BSW cache candidate

This directory also contains a complete optional cache, separate from the
original released `codec.s`. No production source or shared build is changed.

The best tested build is `build-stylehash.py`: unchanged cache-entry wrapper,
`premeasure-preview.s`, `premeasure-codec.s`, `stylehash-controller.s`, existing
real font-store object and generated resident bindings/font metadata. Invoke:

```
python3 src/render/geos/preview-glyph-cache-candidate/build-stylehash.py OUT FROZEN_FIXTURE
```

The result is 4089 bytes (7 free), no new BSS/ZP. Retain the actual sealed entry
and regenerate its binding and exact BSW CRC from the chosen frozen GFC1 pack;
never copy a previously bound image into another resident build. The builder
records all segment sizes. The 3319-byte control is independently reassembled
byte-identical to its packaged R23 image in the acceptance wrappers.

GET runs only after owner4/exact8800 context, scalar/native/span/encoding bounds
and the real FD/font-window authority check. Its exact BSW9 predicate requires
namespace2/familyFFFF/point9,744 bytes,native4800,encoding0,fullclip. This is the
explicit guard-boundary decision: a CRC-authenticated record of metrics produced
by the same genuine immutable font need not repeat raw-header/index measurement.
On a miss, the original complete measure/raster path runs. Native and other faces
retain that path. Each entry clears ARMED before any native bypass. GET verifies
screen identity, style/inverse/fixed-role key, reserved zeros, dimensions9/base6,
width<12 and advance==width+(style&3), then record CRC before live output stores.
The internal PUT follows successful real measurement/raster; it therefore omits
its duplicate metric checks but retains the no-loss low-ink check. Original
`codec.s` and its standalone input guards are unchanged.

FE storage is exactly [EB69,FBA9):64-byte header and128x32 records. No allocation
or fixed physical bank. Actual FE logical+physical ownership/map and full epoch
are checked. Header binds resident16-byte seal, FEhandle/map/epoch, the nine-byte
full FDgraph/face/length witness and generated exact font CRC. Every header byte
is checked; its unused expected zeros are produced only on initialization.
Initialization clears all128 records before publishing the new header. Partial
DMA failure is an optional miss. Header version3 uses screen XOR(style<<4) as a
128-slot index; full native/style/inverse/fixed-role keys still prevent collision
hits. Header/index changes cannot give old records new authority.

Scratch is frame8800..88EF plus8A00..8AAF, existing foreground pointer loans,
CRC/DMA service frames and actual font buffer5000..6071. It shares no resident
state. C27's8A00 page-transport chunk is used outside glyph calls; actual public
68-frame tests exercise this phase boundary. Source/history/catalog/shim and
all16MiB except the pre-existing declared preview cache and these4160 owned FE
bytes stay exact.

The current125409 public68 comparison passes every pixel/attribute, canonical
source/history/catalog and precise REU guard. First diverse page improvement is
only0.76%; pending/inline improve6.5/6.24%; successive pages12.87–16.44%. These
are modeled6510 instruction counts, not native PAL cycles. First source40→mode
hires→preview with no intervening source paint has no FE bank during glyphs;
existing capture allocates it only afterwards. Its first glyph cache remains
untouched, then the next page can populate it. No allocation-policy change or
native performance claim is included. Parent decides whether the small initial
page gain justifies production promotion.
