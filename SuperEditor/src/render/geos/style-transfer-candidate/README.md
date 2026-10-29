# C32 strip transfer: released unroll8 candidate

The ready production delta is `transaction-unroll8.patch`, against
`src/render/geos/style-typing/transaction.s`. `transaction-unroll8.s` is the full
replacement. Only the internal `scanlines` gather/scatter helper changes.
No source, admission, layout, palette, ownership, or transaction policy changes.

The helper retains the existing 9-line, 40-column transfer and row-base
calculation. It chooses gather/scatter once per scanline and copies eight
columns per loop; bitmap offsets advance by eight and linear offsets by one.
The existing pointer loans finish at exactly the previous addresses. It adds no
BSS, zero page, REU allocations, or workspace.

| Candidate | Helper bytes | C32 raw bytes | Delta | First-prime instructions saved | Warm instructions saved |
|---|---:|---:|---:|---:|---:|
| Baseline | 94 | 3216 | 0 | — | — |
| Unroll4 | 186 | 3308 | +92 | 1.953% | 10.241% |
| **Unroll8 (released)** | **250** | **3372** | **+156** | **1.955%** | **12.631%** |
| Unroll40 | 756 | 3878 | +662 | -4.866% | 14.662% |

The raw-code limit is 4064 bytes before the sealed-stage stamp at `$5FE0`;
unroll8 leaves 692 bytes. Unroll40 is not recommended: the extra verified stage
bytes outweigh its additional transfer saving on first prime. These are actual
Peddle CPU instruction counts, not cycles or native latency measurements.

Verification used immutable 47-image fixture
`build/geos-incremental-editor/20261025T115828132288Z/fixture`:
resident `d69f4f0f01c1547341dc8ae6bfbca175661e0f5cd6e579928260c213c763802f`,
D81 `a49e46c559e06412f66ba469102ecc9e1fa6b438f0c1e25a5493bd75d0cb07e8`.
The baseline C6/R30/C32 images byte-match the actual packaged fixture.

`tests/test_geos_style_transfer.py` passed 1344 helper vectors per variant:
all TOP values 16..183, both directions, and four clean/dirty byte patterns.
Every call compares all 64 KiB, allowing only the stack, existing pointer loans,
LINE byte and exact destination bytes; pointer end values are checked. Actual
source/history, the entire `$C600-$C9FF` shim and 16 MiB REU remain unchanged.
This extracted internal-helper seam is trusted and already admitted; it is not
a separate public API or owner-check claim.

Each of the four variants also passed 12 actual styled C6/R30/C32 transactions
and all 20 existing admission/fault cases. Every pixel, attribute, live source
packet and header matches both an independent source/font model and an actual
forced-full render. The forced-full seam clears both CF90 and CFE8, so it cannot
re-enter the same incremental path. Canonical source/history/shim and full
foreign REU guards remain intact. All 48 PNGs are byte-identical by tag across
variants; all 10 unique images were directly inspected using visual-contact.png.

Run: `python3 tests/test_geos_style_transfer.py`.
Terminal proof: `build/geos-style-transfer/20261025T121023097368Z/result.json`.
No shared product build, native run, production source write, or physical-key
claim is included. Parent owns final integration and public-root/native gates.
