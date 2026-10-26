# Committed-only source identity continuation

Qualification source for C35 → C37 operation3 → C35 operation1. Enable only
`BCQ_COMMITTED_IDENTITY=1` together with editor classification/page/forward seed
profiles. C35 grows4081→4094; C37 grows3491→3599 (empty-inline hint additionally
adds37, giving3636). No resident/catalog/BSS/ZP change is required: existing odd
worker requests retain their own pending operation between foreground slices.

A fresh real R14 lease must already be live in BQ_STATE=PAGE, GSEM_ACTIVE=1,
BQ_READY=0. The helper checks current AUTH13/flags/queue/typed graph and executes
actual R14 GUARD. Admission then requires both old/current pending flags zero,
all29 canonical source-prefix bytes identical, and the merged length equality
already checked by C35. Prefix fields are provider/document epochs, document
generation, allthree typed document tokens, committed length, root count and
visible source revision. Only the hot-window lifetime/geometry tail may differ.

The helper copies the ACTUAL current R14 identity59 to the local query snapshot;
all subsequent source guards and published page certificates remain exact59.
No source reader context is fabricated or relaxed. Failed equivalence is optional
MISS2 with owned END and no semantic output. Changed source/authority is a carry
error with cleanup. Pending edits, REKEY/SPLICE and observer-ticket rebasing are
not authorized by this rule. Existing old C37 page proofs still reject a moved
window; only a fresh C35 baseline admission can establish a new certificate.

`tests/test_cache_committed_identity.py --fixture IMMUTABLE` uses actual current
resident, sealed R14 and the producer/writer. The component fixture omits only
four packaged cache workers before checked import of the private variants. It
follows REQUEST/OP manually; it is not a foreground integration test.102 modeled
positions include an actual W_LOAD beyond64KiB, all29 prefix-byte faults, op3
foreign owners, queue/source/ticket/incarnation changes and boundary CANCEL;
1362 wholeRAM worker calls,20 faultgroups and whole16MiB read-only checks pass.
Default flag-off C35/C37 compile byte-identically to the prior packaged profiles.

Promotion requires actual editor dispatch, cancellation/missing worker paths,
independent pixels and native qualification. Fewer parser feeds alone do not
prove faster drawing; small documents can be cheaper to parse than query.
