# Private mapped classification → actual GEOS repaint

This is an executable qualification profile, not a production registration or a
performance release. It uses immutable input
`build/cache-editor-product/20261026T051042908519Z/fixture`:
editor PRG `a2578487c8a552b0c7fbc41f8b965fad8fa05020d7dd90be3820c30d3cbd8ce7`,
resident binding `f50620a2a2594b3617209b3ad36ed32a`, D81
`774437a337e1d488f1b3e9892f8b4808114ab270dcf3d7f804d5fdfc4124a7a4`.

## Reproduce

```
python3 tests/test_cache_splice_editor.py --case ordinary
python3 tests/test_cache_splice_editor.py --case mixed
python3 tests/test_cache_splice_editor.py --case region
python3 tests/test_cache_splice_editor.py --case inline
python3 tests/test_cache_splice_editor.py --case long-inline --smoke
python3 tests/test_cache_splice_editor.py --case mixed --full --smoke
```

The builder extracts source from that fixture, rebuilds original C21, resident
GEOS dispatch, C24/25/26 and five cache workers and compares their packaged/raw
bytes before using their symbols. Private C21 remains 4092 bytes: request C41
instead of C35 and explicitly initialize the opaque query-miss result to 2.
The resident dispatch remains 376 bytes: its comparison upper limit changes
40→42, one operand at $1D52. The verifier applies this assembled substitution
after ordinary source/import. It retains the input binding and discloses this
runtime routing seam; it does not claim a newly sealed PRG/D81 or full startup.

Released dependencies are `splice-probe` (C40 3909, R34 4082 bytes) and
`splice-query-probe` (C41 1211 bytes). No additional BSS, ZP, object or bank.
The packed input has 58 cold bytes free; three private registrations need six
table bytes and can alias EDIT, TAIL, PAINT within existing names, leaving 52.
These registrations have not been implemented in this profile.

## Authority and scheduling

A genuine public inserted Q creates the observed pending SPLICE. C40 reparses
the complete affected line with actual SuperMark, requires outgoing carry
convergence, publishes the mapped root VALID-last and retires the RAM event
only after its durable journal. C41 validates actual source59/AUTH13, typed
root/manifest/base CR pages, record CRCs and explicit base→live mapping. No
semantic record, parser checkpoint, layout result or page proof is host-seeded.

Root flags 1 uses C41→original C35→C37. Flags 3 uses actual mapped C41 queries.
Mapped publication clears PAGE_PROOF and parser CP validity. C21 therefore
refuses the old BQ page-capture path before reading its incompatible frame.
Following rows query C41 again; mapped C37/C39 calls are zero. Actual C26 takes
its guarded legacy inline parser path. Unknown root flags 5/7 fail closed;
lexical flag 4 is reserved, not accepted implicitly.

## Terminal results

All costs below are CPU instructions, not PAL cycles or native latency.

| Source/capabilities | original baseline path | mapped repaint | Meaning |
|---|---:|---:|---|
| ordinary / Markdown | 670,110 | 1,081,235 | 86 C41 calls, zero block-parser work |
| mixed / Markdown | 1,274,583 | 2,985,002 | 341 C41 calls, zero block-parser work |
| region / Markdown | 862,699 | 1,573,490 | real nonzero region carry |
| inline tail / Markdown | 861,300 | 1,272,335 | 72 real C26 feeds |
| 4269-byte inline tail / Markdown | 6,386,022 | 21,766,488 | 76,032 C26 feeds: material regression |
| mixed / Full | 1,302,733 | 3,013,805 | real BASIC lexer: 12 feeds, one init |

The ordinary/mixed/region/inline runs each pass six fault/recovery groups:
queued STOP during C41 lease; missing R34; missing C41; valid-CRC unknown root
features 5 and 7; pending flush to unread REKEY. The last case uses real C24
fallback, preserving the uncomposed event. Mapped frames require completed C41
hits and zero C24/C34 entries/feeds, not merely correct fallback pixels.

Every counted repaint checks independent 8000 bitmap bytes/1000 attributes,
canonical row START/END/NEXT and geometry, canonical source/history/selection,
observation queue, ReadyOS shim and complete 16 MiB outside exact typed FE
outputs. Changed 64-byte outgoing row certificates are admitted only after
independent type, CRC, source-key and canonical-anchor validation. Producer
writes are confined to the alternate root, two-byte directory entry, 32-byte
journal and 288-byte shadow page; the old root remains exact.

The long case also exercises actual public BOTTOM and Undo. BOTTOM flushes a
REKEY and reveals EOF through real legacy parsing: 63,351,798 instructions,
299,904 C26 feeds, caret/TOP 4269; Undo restores all original 4268 source bytes
and independent pixels. This proves safe fallback, not mapped navigation reuse.

## Limits and promotion requirements

This is useful functional reuse with substantial current cost regressions.
Before production, implement authenticated mapped INLINE references for unchanged
blocks; real E47/SPLICE+REKEY composition; coherent sealed registration/root
routing; and whole-editor requalification. Current source59 includes pending
view geometry, so arbitrary pending-window movement is not proven equivalent.
Dirty-line classes remain the narrow one-letter insertion supported by C40.
Inline data allocated after the first plain line can coexist with CR page 1;
inline on the first line allocates CR page 2 and is refused by the existing
one-page producer. No edit class was widened here.

Directly reviewed PNGs include mixed Full, inline tail, long wrapped tail and
public BOTTOM EOF. No native or editable production-feature claim is made.
