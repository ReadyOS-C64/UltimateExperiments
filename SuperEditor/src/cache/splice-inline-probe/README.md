# Private sparse mapped INLINE consumption

This extends the sealed `splice-editor-probe` qualification, not production.
All input imports/source come from immutable packedcold54 fixture
`build/cache-editor-product/20261026T051042908519Z/fixture`:
PRG `a2578487c8a552b0c7fbc41f8b965fad8fa05020d7dd90be3820c30d3cbd8ce7`,
binding `f50620a2a2594b3617209b3ad36ed32a`, disk
`774437a337e1d488f1b3e9892f8b4808114ab270dcf3d7f804d5fdfc4124a7a4`.
No canonical source, shared build, disk, Git state or native process is modified.

## Reproduce

```
python3 tests/test_cache_splice_inline.py --case long-inline
python3 tests/test_cache_splice_inline.py --case long-inline --smoke --legacy
python3 tests/test_cache_splice_inline.py --case edge4095 --smoke
python3 tests/test_cache_splice_inline.py --case edge4096 --smoke
python3 tests/test_cache_splice_inline.py --case events8 --smoke
python3 tests/test_cache_splice_inline.py --case events9 --smoke
python3 tests/test_cache_splice_inline.py --case events --smoke
python3 tests/test_cache_splice_inline.py --case wide --smoke
python3 tests/test_cache_splice_inline.py --case nested --smoke
```

`--legacy` selects original C26/C23 and the previous private C21 selector route
before genuine import. Merely changing a Python asset dictionary after import
would not replace executable REU bytes; early exploratory runs that did this are
not qualification or A/B evidence. Both variants use actual source/edit/cache
producer/root services, and the same input, pending edit and independent oracle.

## Executable interface and budget

The unchanged C40/R34 one-insert producer and C41 classifier remain separate.
New C43 independently performs the released source/root/map/base-CR proof, then
reads INLINE references of an unchanged CR through new read-only R35. Dirty CR
falls back; no stored CR ticket is rewritten. Relative events are converted using
the authenticated current CR START; suffix START+1 mapping leaves original relative
event offsets intact. Unknown root features 5/7 are refused, not interpreted as 3.

C43 op0 NORMAL, op1 STEP, op2 CANCEL, op3 SOURCE and op4 WIDE. Pending is A1,
REQUEST43/OP1. Successful NORMAL explicitly hands off to C21/STEP1; SOURCE to
C20/STEP1. Inapplicability hands off to actual C26 normal/WIDE or SOURCE_FALLBACK5.
All handoffs are sequential through root; there is no C-to-C/R-to-R nesting.
Odd ID43 is required: the resident even-worker branch would overwrite child OP5
with STEP1. Plain BEGINs return opaque A2 before phase access. Owner4 precedes all
phase access; CANCEL can end an owned reader after capabilities change.

R35 retains original read-only OPEN/map/metadata operations 0/1/2/3/6/7/8; op9
begins an INLINE page and op10 performs one bounded validation step. Producer
publication ops4/5 are absent. C40 keeps its original R34. Page headers, directory,
logical capability/physical maps, complete payload CRC and event schema/count/
monotonic page traversal remain checked. Event references are not assumed sorted
by source position: a disjoint event is skipped, never the rest of the stream.
Intersecting events seek their first window index and stop at their own end.
Each STEP paints at most32 cells or validates at most128 payload bytes. Final
publication is one fixed <=161-cell operation after actual source END, as with
existing C39. This is bounded packet publication, not a32-cell publication claim.

Current raw sizes: C43 2598 bytes; R35 3040; C26 delegate4022; C21 route4092;
C23 witness3899. No new BSS/ZP, object or logical bank. Existing phase576 and
inactive R21 stage8880..89FF are reused; old output-role aliases are saved in
9030..9039 before source calls. Parent9137..9177, source packet8200, source
continuation4400..47FF and saved FS9040..9095 are guarded unchanged.

The builder proves original C21, resident dispatch, DMA module, C23, C24/25/26
and five cache assets byte-identical to frozen packaged inputs before adapting
them. C23's actual C26 size/CRC witness is regenerated; using the old witness
correctly failed navigation90 and that failure is retained.

## Scoped reader revocation (bit64)

Root reserved BC flag64 for this optional derived reader; bit128 is unused.
This is distinct from PAGE32 and never grants/forges an old BCQP85 certificate.
C43 arms64 before root/page validation, requires it after every yielded resume,
and clears it on completion/miss/error/cancel. Actual source59/AUTH13, queue,
source lease, object generation/epoch/owner, root/map/record/page proof still run.

The private resident profile contains exactly three source-matched operand
substitutions, with no size change: dispatcher upper bound40→44 at $1D52;
missing-worker/STOP cleanup AND $F7→$B7 at $1DE7; managed checked owner53 write
mask AND $DF→$9F at $2183. The last revokes32|64 before DF01. Generic-off DMA
before/after is independently assembled and byte-compared. These are disclosed
runtime seams on the input binding, not a newly sealed production PRG/D81.
The actual checked same-value type53 stash after payload CRC proves revocation
before consumption without mutating semantic bytes. Missing C43 cleanup is
resident and does not depend on loading C43 to release its86-byte reader.

## Admission and measured result

This private release requires BODY>=4096 bytes and an authenticated completed
INLINE count<=8. Shorter/dense blocks keep the real parser. This is a deliberately
narrow useful path; dense retained INLINE indexing is still open.

For the4269-byte sparse-tail source, old mapped repaint is21,766,487 CPU
instructions and76,032 C26 feeds. New repaint is10,462,470 instructions and zero
C26 feeds (51.9% less instruction work). The original baseline PAGE/C39 path is
6,386,022→6,386,076 (+54). These are instructions, not PAL cycles or native latency.
C41 classification is still repeated; this is not a claim to complete cache reuse.

The full long run passes13 measured frames and12 fault groups:30 wrong-owner
calls;3 Plain BEGIN refusals; actual checked53 post-CRC revocation; missing R35,
C43, R34 and C41; queued STOP in both reader types; valid-CRC unknown flags5/7;
unread REKEY fallback; public BOTTOM flush/reveal and Undo. All independent
pixels/maps, source/history/selection/queued events/shim and complete16MiB outside
exact existing FE outputs are checked. No semantic/checkpoint/layout result is a
host seed. Changed outgoing64 certificates get independent type/key/CRC/canonical
validation before their exact spans are admitted.

After flush, no REKEY composition is pretended: actual block/inline parser work
returns. Public BOTTOM remains about63.3M instructions/299,904 C26 feeds and Undo
restores original bytes. Those navigation costs and true mapped E47/REKEY reuse
remain prerequisites for production.

## Capacity, fault ancestry and remaining integration

The genuine wide page has161 intersecting glyphs. An additional caller-transport
case stops after a real C41 classification and sets only legitimate QUERY/COUNT
inputs for161 bytes, including a bold161st byte; it compares all styles, roles and
hidden bits with independent source events, checks complete16MiB read-only, and
then resumes the actual parent to exact full pixels. This is explicitly a caller
input seam, not a claim that C20 naturally requests161 bytes in that run.

Both original/candidate PAN1/caret0 failures remain in the archive: same9 bitmap
bytes differ, attributes identical; source caret0/TOP0/PAN1/manual1 and actual
se_v_seen1/row0/col0. The eight bytes at640..647 and byte960 differ by the caret
mask. Partial-caret semantics are unresolved/pre-existing; the oracle was not
changed. The passing wide case uses an actually visible caret and explicit odd
pixel pan input, so it is not a general PAN/caret claim.

Pre-policy dense300 events exposed a25,000-step timeout, then an explicitly
recorded continuation completed at137M instructions. Intersection clipping reduced
that to38.5M but old parser was22.2M for that shorter vector. Those experiments
are retained, not called a win. Final policy sends300 events to the real parser.
Final release cases retain the original25,000-step limit and all semantic guards.

Production would require five registrations relative to input54 (C40/R34/C41
plus R35/C43), not two; total59<=64. Packed-cold table delta10 bytes leaves48 of
58 free bytes if names alias existing EDIT/TAIL/PAINT/ROW/NAV substrings. No
registration/full resident link is claimed here. A real rebase job/admission,
coherent sealing, bit64 reservation/cleanup integration and whole-product gates
are still required. Existing C35/C37/C39 must continue rejecting unknown mapped
formats rather than consuming stale original query frames.
