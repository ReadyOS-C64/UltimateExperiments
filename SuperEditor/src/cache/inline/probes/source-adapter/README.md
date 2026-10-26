# Private C20 SOURCE continuation adapter

This is a private, unregistered C39 probe, not a production routing change.
`tests/test_cache_inline_source.py` builds the actual frozen C20 twice and proves
that the control matches its packaged payload. The candidate changes only the
two SOURCE request operands, 26/3 to 39/0; both C20 images are4096 bytes. The
separate C39 adapter is4088 bytes including its resident binding.

The actual GL frame is832 bytes at8D00..903F. C39's576-byte query overwrites GL,
so the real C20 SOURCE bridge first saves its live110-byte core,324-byte map,
59-byte source identity and32-byte packet in45E6..47FF. The prefix4400..45E5 is
C20's source ledger/certificate, not free staging. C39 stage8880..89FF is inactive
R21/glyph work during this layout operation, not the live GL frame. C39 preserves
both backup and ledger. On success it clears GI_ACTIVE/GSEM_ACTIVE and returns
REQUEST20/OP1/A1 after actual source END. The real C20 inline_resume restores its
backup, acquires a new R14 source context, and compares all59 old identity bytes
before consuming the cached styles. A changed revision is rejected as74.

An optional cache miss cancels only its owned reader and returns REQUEST26/OP3/A1
when INLINE_CONT is1. Other callers retain the component's ordinary A0/A2 result.
Errors and cancellation do not resume a potentially invalid C20 continuation.
Normal C21 PS8 and all legacy C26 entry paths are unchanged in this experiment.
The external root dispatcher must retain odd worker-owned OP values; this test
follows actual REQUEST/OP sequentially and does not claim resident integration.

The private core/page copies omit redundant inner owner checks only because the
entry guards owner4 before every operation and none of those internal services
can yield or change owner. Full source59/AUTH13, typed logical/physical object
checks, queue/revocation, CR/INLINE schema and every page/event CRC remain.

Run `python3 tests/test_cache_inline_source.py` from the repository root. It uses
actual producer/writer/C35 and the actual C37 empty-inline-hint profile, then
compares C20 geometry and every map boundary with an independent source/style
oracle. Cases include short/nested/code/heading, long wrapped continuation,
pending source, revoked-proof real-C26 fallback, and source mutation between END
and actual C20 restore. Each service checks RAM writes against explicit scopes;
canonical source/history, shim and full16MiB remain exact. No R leaf except14 is
used by this pipeline. The component's separately archived34-window/11-fault gate
covers output styles/roles/hidden masks independently.

## Cost decision

With the current empty-inline C37 hint, plain27B calls neither C26 nor C39.
Direct C39 SOURCE routing is **not suitable as the default**:14/15B small inline
rows regress12%,41B nested/code regresses22%,29B heading regresses14%. A998B
wrapped paragraph improves37% (362192 to227458 instructions; same3 overlay loads,
DMA5 to11); a235B paragraph improves only2%. These are actual C20 frontend totals,
including worker swaps and typed DMA, excluding common baseline/classification.
They are CPU instruction measurements, not native PAL latency. An adaptive
long-body admission policy needs a separate measured probe before promotion.
