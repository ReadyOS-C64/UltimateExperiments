# Bounded C20 inline style window — private candidate

Layer this on the released current-output certificate. `ready.patch` changes
ONLY five existing C20 source/helper files and adds `style-window.s` under
`src/render/geos/`. C21, C26, resident, cfg, object list and root routing are
unchanged. Add the new helper to source-line.o dependencies. The editor's
existing `SE_EDITOR_GEOS_INLINE=1` flag selects this path; non-inline default
source-line emits the identical494-byte generic code. Rendered-ledger mode
remains explicitly unsupported, as in the first certificate release.

Build/rebind only C20 against a first-certificate product fixture:

    python3 src/render/geos/style-window-candidate/build-once.py <privateout> <fixture>

The builder uses the fixture's exact resident binding AND frozen packed font
and widths. `--control` must reconstruct the frozen first-certificate C20 byte
for byte. Current203233 fixture bindingbc032951a4ff040b1cd687f8eb175884 yields:

* control3904B SEOa792c36b55002d513336e4bbd9bce718c8a694a4be63f57639e0dd9a8f748a12
* candidate4096B SEO81497e07b9ff70fc68c1aac121adc56b0a411646d27e5750cb378044701d3ba5

Do not copy a coordinator from another private namespace. All47 other current
sidecars remain unchanged. CPU fixture substitution is disclosed; no D81 or
native validation is claimed here.

## Algorithm and authority

C20 still obtains native source in the original <=32-byte R14 READs and runs
the original strict source guard before every packet. On a style miss it asks
unchanged C26 SOURCE_BEGIN3 for min(160, logicalEND-SCAN) style bytes. C26 still
parses the complete BODY..END with its original bounded feeder, leases, source
keys and token guards, so a closing delimiter beyond the window is honored.
The query never extends past END/EOF; literal prefix bytes before BODY retain
normal base appearance. At/after END the already-read CR packet needs only
normal style/base role and makes no additional style query.

The existing output buffers8300..839F and8F36..8FD5 retain that window while
C20 owns the job. Checked R14 calls write native packet90EC and document
scratch8000..807F/8400 leaf; they do not write those buffers. A real-step guard
proves all320 retained bytes and the original native packet survive the next
R14/measure call. No new raw source read or source packet prefetch is added.
Each hit matches the existing full59-byte current identity/context, strict
window tag1/count<=160 and checked24-bit SCAN-relative offset. A packet that
would extend beyond a window refetches (unless the logical end supplies normal
base bytes). GS_STYLES receives the packet's at most32 style bytes. GS_OVERLAP's
first32 bytes hold corresponding roles only after all R14 calls and before
style_remember; that scratch is dead before the next reader call.

The original396-byte output certificate still accumulates the first161 bytes
of the current line for C21. It is neither extended to another job nor used to
skip actual source guards. There is no retained window across GL_BEGIN.
BEGIN/cancel/error revoke it; successful C26 reattachment checks the original
full59-byte identity before use. STOP still ends only its actual counted lease.
A one-byte TAX at window_count return supplies Z from the count itself; exact
320px/128-byte CR and EOF cases ensure no zero-count C26 query is scheduled.

Additional metadata is six bytes458C..4591. The remaining84-byte ledger suffix,
packed525-byte continuation and13-byte tail retain exact guards. No BSS/ZP,
resident bytes, asset, object/bank or renderer color/layout change.

## Costs and tradeoffs

On current immutable203233 bindingbc03 (all47 other images unchanged),
fair whole-page CPU instruction counts versus the released certificate:

| source | certificate | window | change |
| --- | ---: | ---: | ---: |
| diverse422 | 2,271,569 | 2,238,856 | -1.44% |
| inline406 | 3,365,242 | 3,162,398 | -6.03% |
| long styled863 | 11,414,540 | 8,339,224 | -26.94% |
| styled wide-W200 body | 2,105,353 | 2,179,503 | +3.52% |
| short-word wrapped210 | 2,120,185 | 1,903,917 | -10.20% |

Short/tiny/heading/prefix single rows cost67..293 extra instructions (<0.07%);
plain/empty/CR cost4..28. The wide-W regression is real: one32-byte packet
already completes each row, so initializing160 style outputs cannot save a
parse. No speculative width guess was introduced to hide it. The leaf has
zero code headroom; native cycle/key-latency benefit is not inferred.

C20 raw-source requests remain736/672/1280 bytes in the three main cases.
Long-body C26 calls38→19; R14 calls1095→582; requested C26 bytes32832→16416.
Requested bytes are not actual DMA totals. C20 still parses the same long BODY
once per wrapped row; a certified style result retained across line jobs is
needed to remove that remaining repeated work.

Tests: test_geos_style_window_candidate.py, test_geos_style_window_faults.py,
test_geos_style_window_boundaries.py. Independent current-input inline19 and
recovery22frames/21groups, plus old-input final fold28/incremental15/capacity11,
exactwidth/high24/pending/pan5, complete stack52+16 and generic byte identity.
Source, history, catalog, shim and original typed16MiB guards are retained.
