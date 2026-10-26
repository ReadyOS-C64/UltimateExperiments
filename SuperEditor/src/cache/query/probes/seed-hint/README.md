# Private compact C35 completed-empty hint

This candidate changes only the classification publisher. `BCQ_EMPTY_INLINE_HINT`
enables the same authenticated completed-empty predicate already used by C37:
CR flag bit4 set, all three INLINE-count bytes zero, and all four reference bytes
FF. Eligible kinds0..3 then publish `GSEM_INLINE=0`; other records keep the
existing conservative behavior. No INLINE payload is consumed or certified.
All root/page/CR CRC, schema, source59, AUTH13, typed graph, lease, owner, queue,
presentation and managed-write proof checks remain the frozen query code.

`build.py OUTPUT FIXTURE` extracts the actual source ZIP from the fixture and
links against its exact resident report. The control must byte-match packaged
`inln.seo`; the new file without the flag must match that control. The tested
fixture is `build/cache-editor-product/20261026T023925641413Z/fixture`.
Its control is4094 bytes; enabled candidate4090 bytes (6 free). No BSS or ZP.

The flag-only compactions preserve A/P/SP and output fields: indexed three-field
copy; indexed EOF zeroing with an explicit jump; looped 24-bit BODY addition
(INX/DEY retain carry); copying the already checked absolute BQ_END; and removing
redundant PLA/PHA pairs while the original A is still live. EOF language, level
and marker are normalized to zero even when schema-valid CR metadata is nonzero.
The first4089-byte attempt lacked that explicit EOF jump and is rejected.

Run `python3 -u tests/test_cache_seed_hint.py`. This uses actual producer/writer
baselines and the public renderer, swaps only C35 before cold import, and retains
independent pixels, source/history/clipboard/shim, catalog and full16MiB guards.
The local publication/result seam separately tests1050 output/predicate cases
and14 A/P/SP cases, including malformed-but-valid EOF metadata. Those local
inputs are not authenticated cache-hit claims. Public empty/CR sources may
correctly bypass baseline construction.

The decisive public navigation A/B uses the same frozen committed-identity
fixture on both sides: sparse66012 bytes and actual W_LOAD65999. Candidate
removes198000 C26 source feeds (6223 C26 calls to zero), with identical pixels
and source. Total CPU instructions92066185 to56358149; the remaining66001
C24 feeds are the separate caret-reveal job. The251-byte marked document retains
its real INLINE parsing and differs by only9 instructions. These are CPU model
measurements, not native cycle or physical-key latency claims. Initial baseline
construction is excluded from that navigation interval and remains separate.

Only this private entry file must be merged into canonical `classify-entry.s`;
query/arena sources and build flags otherwise remain unchanged. Parent owns any
promotion, main builds, asset registration and native qualification.
