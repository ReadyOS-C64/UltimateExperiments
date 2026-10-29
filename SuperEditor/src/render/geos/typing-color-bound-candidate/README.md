# Private color-bound typing proof — not suitable for promotion

Run:

```sh
PYTHONPATH=tools:tests python3 tests/test_geos_typing_color_bound_candidate.py \
  --fixture build/geos-incremental-editor/20261025T140326098391Z/fixture
```

`bound.s` is a real read-only 6510 component. Existing C6 and all canonical files
are unchanged. The test uses the actual pending C6 edit (which still refuses
mixed neighbors), real checked FE transfers, the actual current suffix-shift
algorithm in a **provisional** private copy, and an explicit publisher called
only after admission. These are direct component calls in a CPU fixture, not
an integrated R30/C32 controller, staged security proof, or native timing claim.

For each of the two affected physical tile bands, every colored neighbor pixel
row contributes an upper bound of eight votes per tile. All nonzero roles are
treated as colored, conservatively including palette aliases to white. The
checker accepts only when post-edit target white BASE-INK votes strictly exceed
that aggregate bound in every affected column; bound zero needs no positive
votes. Old attributes must already be white-on-blue `$16`. Reverse headings
are permitted via vertical coverage, never inferred from displayed inverse
bitmap pixels. Flags other than inverse1, unsupported heights/counts/roles,
wrong owner/provider ownership and doubtful ranges refuse before VIC writes.
Prefixes must be ordered/nonoverlapping, with kind/height agreement and native8
alignment; malformed geometry cannot understate the visible code-row coverage.

This bound is safe but too conservative for the intended general paragraph:
all six natural-paragraph insert/delete cases refuse, as do three dense-row
backspaces whose vacated final tile has zero white votes. It admits dense
insertions and one combined-style interior insertion. LSN190 still refuses;
actual full rendering changes its formerly white attribute16 to cyan36.

## Caller contract / placement

Before this helper, a future caller must retain **all** existing source/GCC/GTC,
font, typed FE and ordinary-inline-edit authority checks. `se_tcb_check` does
not replace those checks. Its header count input is the authenticated C32 header
copy at `$90CA`. The passed row is the exact independently checked target row.
Post-edit `$8400..$8567` is nine times40 genuine target BASE-INK bytes, without
caret/selection/inverse. FIRST/LAST are inclusive changed tile columns, bounded
by the maximum old/new canonical glyph width. There is no claim that arbitrary
host-supplied ink proves a real document.

Owner4 is checked before any phase access. Caller frame `$8A00..$8A17` holds
row/top/first/last/expected attribute and private scratch. `$8580..$85CF` contains
80 vote counts; this deliberately aliases provisional GT_TEMP only after the
shift is finished. Checked prefix/role transfers use `$8100..$811F` and
`$8200..$82A0`. Existing foreground text_ptr/screen_ptr are borrowed, with no new
ZP/BSS. The caller must not nest/yield to another foreground user while these
scratch values are live.

`wide-provisional.s` removes only the old immediate VIC writer and its old
blanket attribute check from a private copy. It computes the genuine complete
post-edit base first. `se_tcb_publish` then writes the nine target scanlines with
the new caret. Rejected proofs leave every bitmap/attribute byte unchanged.
Status/chrome remain byte-exact at their old values in this component; the
normal future transaction would still publish status and cache metadata.

## Measured fit failure

| Item | Bytes |
| --- | ---: |
| Checked bound helper (714 code +16 table) | 730 |
| Provisional shift plus explicit publisher | 1123 |
| Existing canonical wide module | 1113 |
| Net additional raw bytes | 740 |
| Current C32 raw | 3521 |
| Projected raw before hook glue | **4261** |
| Legal raw before `$5FE0` stamp | 4064 |
| Overage before glue | **197** |

The private complete component is2170 bytes including317 bytes of checked
transport; transport is already supplied by the existing R30 vector seam and
is not double-counted in the projection. The projection does not include
additional caller plumbing or moving the existing header invalidation behind
admission. C6 has only12 spare bytes, so moving this proof there is not viable.
Do not install or relax the current neighbor guard on the strength of this
component. No complete in-budget transaction has been established.


A separately **assembled-only** placement experiment links the checker into the
same R30 image at a new helper vector `$A032`. It reproduces the immutable
original2073-byte R30 byte-for-byte before modification; the augmented image is
2806 bytes, with the old six vector addresses unchanged. C32 would then contain
3531 raw bytes before hook glue. This demonstrates available placement, **not**
an integrated candidate: no new C32 caller, C6 deferral, prepublication header
reorder or runtime test of that augmented supervisor exists. It also does not
solve the six natural-paragraph false misses. See `measure-supervisor.py` and
its retained result; do not call it production-ready.
