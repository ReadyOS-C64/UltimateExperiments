# VIC scatter benchmark controls

The candidate below is now integrated in the canonical working renderer.
Native ready3 passed48 captures/24 pairedRGB comparisons; canonical D81 is
byte-identical to its coherent candidate package. These preserved source and
builder files reproduce the original private differential proof. Historical
CPU substitution claims below remain scoped to that earlier release. See
../style-typing/README.md and docs/PERFORMANCE.md for measured native costs.

## Original private VIC stride8 release

Pinned input: committed1612523, `build/warm-shift-committed/20261027T002602997186Z/fixture`.
Only `wide.s` changes. Baseline source SHA2562a2b64fd064fe8bc64d2f8223afed97699706872b057a1ccc8144bff22e97684.
Candidate SHA25650ddbbbfa077494f96a2dab68da3efee74786be5eea373690cdcd6715ca6a55b.

The existing nine-raster-line,40-column VIC scatter replaces40 pointer increments with five8-column groups. Every group stores temporary columns X..X+7 at Y0,8,..56, then advances the same pointer64 and X8. Indirect indexed stores supply the intra-group low-byte carry. The fifth group ends X40/pointer+320, matching old state. Y56 rather than0 is allowed by the existing clobberedXY/P primitive ABI; subsequent code does not readY. Address derivation, sourcebase copy, shifts, caret masks, attributes, dirtytail zeroing, validation and publication remain unchanged. No state/font/BSS/ZP/bank/asset addition.

Actual link: wide1153→1206 (+53); C32 image3803→3856/raw3771→3824,240 bytes before the5FE0 stamp. R30 stays3662; its generated CRC/length witness changes, so rebuild TYPE+GTYPE together. No new resident binding required. Code costs53 extra stage bytes to verify/copy on cold prime; measured whole first INSERT still saves1117 instructions and first BACK saves952.

Qualification: `build/vic-stride-probe/receipt.json`, `primitive1/result.json`, `public1/result.json`, `public1/guards/result.json`, `visual-review.json`. Primitive2154+17 per side; all56 paired public operations;26 actual style/fallback full-reference frames+18 authority faults. Configured provider256, actual full16MiB read/compare plus checked-DMA observer and source/history/shim/declared64KiB guards. Public paired savedPNGs exact.38 generated CPU-oracle PNGs inspected1:1 through contacts. These are CPU snapshots, not actual native captures.

Every valid primitive saves2034 instructions, reducing measured bitmap-address/blit self3907→1873. Steady whole edit saves2034 (~4.48–5.19% across measured profiles). Caret counts/loads unchanged; edit loads remain4. No native cycle claim. No further variant requested.

Reproduce without shared writes:

```sh
python3 tests/test_geos_vic_stride.py --out build/vic-stride-probe/recheck-primitive
python3 tests/test_geos_vic_stride.py --public --pairs 5 --out build/vic-stride-probe/recheck-public
```


Promotion is parent-only: verify baseline SHA, apply `ready.patch` to `src/render/geos/style-typing/wide.s`, then rebuild actual `src/render/geos/style-typing/build.py` using current full binding and publish both TYPE/GTYPE. Do not copy just TYPE or reuse an old workerCRC. Source-rebuilt pair under `public1/build-after/assets` is qualified only on pinned resident. Privatefixture keeps oldD81 intentionally: CPU catalog substitution seam, not packaged/native proof. Parent must build/freeze coherent D81 and independently qualify native/stack as appropriate.
