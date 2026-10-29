# Checked source-fold services (isolated M5 foundation)

The real40/60/80 editor now consumes these services through
[editor_fold](../editor_fold/README.md). The test below remains an isolated
foundation test; its private addresses are not the editor's placement contract.

These are actual ca65/6510 services, with an independent CPU test:

```
python3 tests/test_folds.py
```

The command assembles only `build/folds`. It links the existing generational
logical-object and REU provider/DMA implementation, and never builds the editor,
runs VICE, or changes its disk. The addresses in `probe.cfg` are isolated probe
placements, **not editor memory reservations**. This foundation test alone does
not prove editor integration, source transformation, rendering or finished M5.

## Storage and lifetime

The caller exclusively owns a private typed logical object (`SF_OBJECT_TYPE=$46`,
provisional standalone tag) and a disposable pointer-free service context.
`se_fold_token[5]` is the existing ID/generation16/provider-epoch16 token;
`se_fold_count[2]` is at most32768 records. Each32-byte transfer authenticates the
complete token, every logical/physical ownership mapping, committed object size,
record bounds and legal C64 DMA buffer through `se_object_copy`. Offset24 is
`index*32`, including records beyond64KiB and the exact1MiB exclusive capacity.
No physical bank belongs to this module. The caller allocates/resizes/releases
the object using the existing object service, and cannot lend it or modify its
bytes while the map is trusted or an operation is active.

The initial emitted service context is197 bytes plus a32-byte caller DMA buffer;
there is no zero-page use or resident BSS allocation. These are linker-owned
segments `FOLD_STATE` and `FOLD_BUFFER`. Later integration must place/checkpoint
these in an explicitly owned phase union. A fold token, source revision and
lifecycle still need integration-side storage. Do not add197 bytes to today's
resident BSS or borrow the ReadyOS shim. A checkpoint copies the entire context;
provider/object tables, logical object bytes and caller ownership remain live.

The caller sets authoritative immutable source length24 and document revision32
in `se_fold_length` and `se_fold_epoch`. OPEN, edits and undo/redo must change that
revision and call `se_fold_invalidate` before using a prior tree. This first
service fails closed and requires a rebuilt candidate; it does not yet transform
anchors or retain unaffected collapse states. Revision wrap requires explicit
invalidation/rebuild. A live context cannot be rebound to another token/count/
length: validation binds all three and each later operation checks the binding.

## Record v1 (little endian)

| Byte | Field |
| --- | --- |
|0..2|Summary/opener source anchor|
|3..5|First hidden canonical source byte|
|6..8|Exclusive hidden end (may equal source EOF)|
|9..10|Parent preorder record index; `$FFFF` for a root|
|11|Depth0..15|
|12|Kind1 heading,2 fenced code,3 explicit region|
|13|Flags: bit0 collapsed; bit1 saved inner caret valid|
|14..16|Saved inner caret source anchor|
|17..19|Derived hidden-line count, supplied by builder|
|20|Heading level1..6; zero for other kinds|
|21..24|Caller movement serial associated with saved caret|
|25..31|Reserved zero|

Intervals obey `summary < hidden < end <= source length`. Records are strictly
preordered by summary. A child is wholly within its parent's hidden interval;
siblings do not overlap, and the advertised parent/depth must match the active
ancestry. Crossing regions, inconsistent depths, malformed flags/reserved bytes,
and saved carets outside a collapsed interval are rejected. An empty body is not
a fold record. All source anchors remain canonical and24-bit; no row number is
stored. Neither selection endpoint is ever rewritten by a service.

The parser-driven builder below now implements parent-selected policy D093:
explicit-region and fenced-code fold intervals have priority. A heading fold
that crosses one is omitted from the optional fold projection; heading style
and its ordinary global section semantics do not change. Containing, nested and
disjoint heading folds survive. This is not truncation or rewriting of source.

## Calls and bounded operations

All calls require D=0, foreground nonreentrant ownership, and clobber A/X/Y/P.
Carry clear is success; carry set/A is `se_fold_error` (B0 malformed, B1 stale,
B2 busy, B3 cancelled, or an unchanged object/provider error). Busy rejection
preserves an active job. Inputs must remain unchanged through its STEP loop.

1. Fill token/count/source length/revision and a candidate logical object. Call
   `se_fold_validate_begin`, then `se_fold_validate_step` until `busy=0`.
   Validation never writes metadata and publishes `valid=1` only after every
   record has passed. Each STEP reads at most one32-byte record.
2. With `valid=1`, set `query[3]`, `mode` and canonical selection endpoints
   `select_a[3]`/`select_b[3]`, then query BEGIN/STEP. Mode0 projects a hidden byte
   to the first enclosing collapsed summary. Mode1 skips to its exclusive end;
   mode2 skips backward to its summary. A visible byte, including EOF, maps to
   itself. `result[3]`, `hidden` and `selected` are outputs on successful
   completion. `selected` means the nonempty normalized selection intersects
   the hidden source interval; reverse selections preserve their endpoints.
3. Set `action`, `target[2]`, canonical `caret[3]`, caller `motion[4]` and optional
   `query[3]`, then action BEGIN/STEP. Actions0 toggle target,1 collapse target,
   2 expand target,3 collapse all,4 expand all,5 reveal query by opening every
   enclosing collapsed ancestor. Each STEP reads one record and writes at most
   one record; all and reveal scan incrementally. `result` is a proposed caret
   for the caller to adopt only on successful completion; `caret` and selection
   inputs stay unchanged.

Collapse moves a caret only if it is actually inside the newly hidden interval.
It remembers that inner position and the caller movement serial. Expand restores
it only if the caret is still at that exact summary and the serial still matches.
The caller must advance serial on navigation/edit, even if it later returns to
the same summary; the fold projection itself does not advance serial. Reveal
opens ancestors and preserves the current caret, allowing the find/navigation
caller to adopt its own target afterward.

Metadata actions set `valid=0` before their first potential write. On complete
success they publish the updated map and proposed caret together. Cancellation,
source revision changes or I/O failure leave the map untrusted; earlier metadata
writes may remain in that private object, and it must be rebuilt/revalidated
before queries. The public caret result is not published on failure. This is
fail-closed publication, **not transactional metadata rollback or copy-on-write**.
A caller needing uninterrupted old-map availability must stage a distinct object.
`se_fold_cancel` preserves a trusted map only when cancelling a read-only query.
`se_fold_invalidate` stops any job and revokes trust immediately.

## Verification scope

`tests/test_folds.py` independently derives nested interval validity, visibility,
selection intersection and caret/action behavior. It exercises actual REU DMA
through noncontiguous logical mappings, nested/disjoint/EOF source anchors,
24-bit coordinates, record64KiB boundaries and capacity checks. It retains exact
module/source hashes and instruction observations in `build/folds/result.json`.
CPU instruction counts are not PAL/NTSC latency, VIC output or keyboard proof.
No source provider or SuperMark builder is simulated as integrated editor code.


## Bounded parser-driven builder

Run `python3 tests/test_fold_builder.py` to assemble only
`build/folds/builder`. This links the **actual** SuperMark block parser, fold
foundation and generational object/REU services. `builder-probe.cfg` placements
are probe-only and reserve no editor RAM. No editor source reader, fold command
routing or renderer integration is claimed.

Zero a newly owned builder context before first use. Supply:

- `se_fold_token[5]`: private candidate fold object, already committed to
  `se_fb_capacity *32` bytes; capacity0..32768. Allocate it separately from a
  retained old map. Its unused tail is private and ignored by published count.
- `se_fb_source[5]`: an immutable flat source object token of another private
  type; its committed size must exactly equal `se_fold_length[3]`.
- `se_fold_epoch[4]`: authoritative document identity/revision. Source bytes,
  tokens, lengths and inputs stay fixed throughout the operation.
- Optional old-map proof described below; otherwise `se_fb_old_valid=0`.

Call `se_fb_begin`, then `se_fb_step` until `se_fb_busy=0`. A successful complete
operation publishes `se_fold_valid=1`, `se_fold_count[2]` and `se_fb_count[2]`.
`se_fb_omitted[2]` counts distinct crossed heading folds (each counted once);
`se_fb_empty[2]` separately counts headings with no hidden bytes. Canonical
source/caret/selection are never modified. `se_fb_cancel` stops bounded work,
leaving the private candidate untrusted. Carry/error conventions follow the
foundation; additional errors are B4 capacity, B5 incomplete recognized explicit
pair, B6 combined nesting depth beyond16. A cancellation call itself succeeds
while recording B3. Busy rejection preserves the current operation.

The builder reads at most128 source bytes per fetch and feeds at most32 bytes
per STEP, stopping on each real parser event. Raw records are appended by source
opener and patched at closure: headings end at the next equal/higher heading or
EOF; explicit regions/fences end after their exact closing line, including CR
when present. Unclosed recognized region/fence pairs fail closed until syntax is
corrected; unmatched end markers that the parser classifies as literal remain
literal. Code precedence and native-case rules are the existing parser's rules.
There is no second host/ASCII parser in the emitted code.

The D093 filter is bounded by active depth, not all-pairs rescanning. It tracks
up to6 active heading intervals and16 explicit intervals; for each explicit
interval it checks one active heading per STEP. Crossed headings are privately
marked once, compacted away, and descendants are reparented to surviving
ancestors. A final actual foundation validation precedes trust publication.
Each STEP performs at most2 bounded DMA transfers (one record read plus optional
write, two retention reads in separate steps, or one source slice). The logical
hidden-line count is source lines after the opener, including a closing marker
line, never a wrapped display-row count; a terminal CR does not invent another
parser line. Empty sections do not create invalid zero-width records.

Examples of the projection rule:

```
:::region R       # H
# H               :::region R
:::end            # Next
text              :::end
# Next
```

In the left example `H` crosses the region's closing boundary. In the right,
`H` ends inside the region while the region continues. Each omits that heading
fold and retains the exact region; `Next` survives when otherwise valid.
An outer heading containing the whole region, or a child heading wholly inside
one, remains foldable. Other source constructs retain their style behavior.

### Safe unchanged-snapshot retention

The optional read-only old map is another typed logical object. The caller must
certify it was fully validated and exclusively owned under the same v1 schema,
using `se_fb_old_valid=1`, `se_fb_old_token[5]`, `se_fb_old_count[2]` and its
source proof `se_fb_old_source[5]`, `se_fb_old_length[3]`,
`se_fb_old_epoch[4]`. The old source proof must equal the complete current
immutable token/generation/provider epoch, source length and document revision.
A different proof defaults the new map to expanded, even if numeric anchors
happen to match. An admitted old token is authenticated on each STEP and must
be distinct from the candidate; source, old map and token lifetime remain live.

After compaction, a bounded sorted merge matches exact fresh
summary/hidden/end/parent/depth/kind/line-count/heading-level identity. It copies
only the collapsed bit; saved inner caret/motion are reset. `se_fb_retained[2]`
counts copied collapsed flags. Unmatched records remain expanded, and old bytes
are never written. Failed retention I/O revokes the candidate rather than
publishing a partly retained tree. This is safe unchanged-source retention,
**not edited-anchor matching**. After edits/undo/replaced source, reset-expanded
is the deliberate default until a checked edit transform and structural
identity scheme are integrated. Reusing positions or a short text hash alone
is insufficient proof of unchanged folding intent.

### Working set and future integration

Measured builder control89B + existing block parser79B + foundation197B +
record32B + source/old-record buffers160B = **557B caller phase workspace**,
0ZP and no additive resident allocation. The builder overlays its parse/filter
stacks onto the foundation's128B validation stack while that service is idle.
Code is operation-sized: parse/control, filter/compact and optional retention
are separate linker segments; loading all parser/builder/foundation code as a
single4KiB overlay is not assumed.

A checkpoint must copy all557B, including parser state, pending source chunk and
record buffers; provider tables and logical object leases remain live. There
is no hidden pointer/stack/self-modified continuation. Editor integration must
replace the flat source-object adapter with the checked canonical/merged-source
reader and its read lease, bind revision to real document publication, and
place/checkpoint this phase union explicitly. A pending edit or undo must revoke
the old map before source-to-visible projection; successful build then hands the
validated record token/count/revision to the existing query/action service.
Source movement computes canonical targets first, then queries visibility;
selection/copy/cut continue to use canonical endpoints and include hidden bytes.
No rendered row number becomes an edit anchor.

The optional actual editor source callback is now CPU-tested separately; see
[source-README.md](source-README.md). It streams the actual fragmented piece table
and pending gap without flattening. Production job/render wiring and placement
remain open; its full-identity lease adds86 caller bytes, making643 phase bytes.
The direct-object default remains exactly the frozen builder binary.
