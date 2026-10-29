# Single-fetch private cache variant

`build-once.py OUT FROZEN_FIXTURE` builds4095B/1free, no new BSS/ZP. It links
NEW `once-entry.s` and `once-preview.s` with unchanged released
`premeasure-codec.s` and `stylehash-controller.s`, actual font-store, generated
font metadata and matching resident bindings. All4089B sources stay immutable.

The wrapper already authenticates/refills its selected face through actual
se_gf_fetch_preview. Between that return and the internal glyph entry it executes
only font-pointer/length stores into8800 and register loads; there is no yield,
window writer, capability writer or overlay call. `se_geos_catalog_ink_fetched`
is an INTERNAL cross-object seam for only this wrapper. Its nonzero packed-font
high byte marks bit6 in existing8AA0 before the unchanged scalar/native/span
checks. `preview_authenticate` still requires5000 and exact verified length;
it consumes that immediate-call witness instead of fetching twice. GET resets
8AA0 before its own eligibility/FE checks. No witness is accepted across a yield.

Native font0 routes through `se_geos_catalog_ink_preview`, which retains its
owner4/exact8800/scalar/native/span checks and clears the immediate witness.
All DIRECT callers keep that same guarded symbol and must perform a real fetch,
even if8AA0 has a stale fetched marker. The new internal seam is not a new public
overlay operation or resident API. Wrapper owner checking precedes every frame
write; the fetch itself repeats its real owner/capability authority check.

The internal-only intermediate VALID1 store is omitted to fit. No caller can
observe that measurement separately: successful raster publishes2, entry/error
initialization stays0. Original generic catalogue APIs and original498Bcodec
remain unchanged.

Actual6510 trace proves packedwrapperonefetch/nativezero/directguardedone.
Fontwindow4210B and entire FDdescriptor64B are exact between FETCHreturn and
internalentry. All79480 packed/all43faces,4096native and70directguard/fault groups
pass, as do4096cachekeys/328cachefaults,6recomputedinvalidmetricCRC faults and
coldFE firstpage/secondpage limitation. Actual125409 public68 A/B passes every
pixel/attribute/source/history/catalog/shim and precisewhole16MiB REU guard.
Firstdiverse2341886→2304986instructions (-1.58%);pending -7.31%,inline -6.91%;
page0 -14.02%,pages1..4 -17.70/-17.49/-17.40/-17.07%. These are modeled6510
instruction counts, not native PAL cycles. FEabsencefirstpage caveat and parent
promotion decision from README-cache.md still apply. The two representative
candidate diverse/page0 images were directly inspected and remain pixel-identical
with control. No shared production/build/native operation was performed.
