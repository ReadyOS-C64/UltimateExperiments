# Resident C37/C35 handoff routing — released private candidate

Promote only `dispatch.s` to `src/render/geos/dispatch.s`, or apply `dispatch.patch` to the exact recorded baseline. No source beyond this resident dispatcher changes.

The actual 375-byte frozen resident dispatcher becomes 376 bytes (+1); the parent reports two free CORE bytes before this patch. The cache-worker interval becomes [34,38). Pending even34/36 publishes STEP1; pending odd35/37 preserves its worker-owned REQUEST/OP. In particular C37 can hand off REQUEST35/OP0 without the resident converting it to an uninitialized STEP1.

The original error JMP is shared by three short BCS branches (actual displacements106,51,24), saving9 bytes. The displaced `BEQ painted` becomes the long `JEQ painted` (+3). Pending parity adds7 bytes: PHA,LSR,BCS,STX,PLA,CPX,BEQ. PLA restores the original requested worker in A; CPX1 restores original N/Z/C before the common CLC. X/Y remain exact. The temporary PHA executes after the earlier saved-request/overlay-JSR stack has unwound. Per-instruction probe observes minimum SP=$FA for both old and new service with the same explicit worker stub; this does not replace the parent's whole-product static/IRQ bound.

`python3 tests/test_cache_handoff_candidate.py` assembles all variants privately, proves the unmodified source byte-identical at its frozen resident address, and tests 7,424 new routing vectors against a direct, unoptimized reference. It additionally compares 6,656 unchanged legacy vectors to the original and exercises48 render/navigation entry/error vectors. All comparisons preserve A/X/Y/P/SP/returnPC and all64KiB RAM except relocated code and stack return-address bytes. Four C37→35 handoffs preserve OP0; a following resident service enters an explicit BEGIN counter exactly once and allows that endpoint to publish STEP1.

The overlay/endpoint bodies are deliberately stubbed. This proves resident routing, not an actual C35/C37 loader, source/parser, IRQ or VIC gate. Parent owns the actual product-level forward-query gate. No production file, shared build, Git state, parser contract or cache authority was modified.

Authoritative result: `build/cache-handoff/20261026T012054710150Z/result.json`. Frozen baseline: `build/cache-editor-product/20261026T010418788084Z/fixture`. Earlier first preparation failed a branch-range assembly check; the final long painted branch is explicit and proven.
