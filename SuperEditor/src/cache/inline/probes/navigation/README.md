# Private retained inline metrics during GEOS navigation

Source-released targeted profile; no canonical production edits or native claim.
The immutable control is canonical54 fixture
`build/cache-editor-product/20261026T033702424844Z/fixture` (2e69c5fa D81,
resident91de02aa, bindingeaccc1c6f5b22f36d8e033f98f1f2c89).

## Repeatable build and integration

`python3 tests/test_cache_inline_navigation.py --targeted --fixture <fixture>`
extracts the fixture's exact product-sources.zip. Both flag-off C26 (3436B) and
normal C23 (4063B) must first byte-match their packaged payloads. It then builds
C26 (4000B) and C23 (3899B), with unchanged C20/C24/C35/C37/C39 and catalog54.
There is no new asset, allocation, BSS or ZP.

The build output `build/tree/src/render/geos/navigation.s` is the exact generated
C23 source. Link it with existing cache.s flags `SE_GP_CACHE_WARM_ONLY=1` and
`SE_GP_CACHE_READ_ONLY=1`; C23 uses only checked GUARD/READ/SLOT. OPEN/WRITE are
unreachable and omitted, not replaced by weaker checks. `short-branches.json`
lists each long branch changed to a ca65-proven in-range short branch. The
generated C26 source is `build/tree/src/render/geos/inline.s`, plus helpers.inc.
For production, rename the include to `render/geos/navigation-cache.inc`.
Enable `SE_EDITOR_INLINE_NAVIGATION=1`, `SE_EDITOR_NAV_TARGETED=1`,
`BCQ_EDITOR_ACTIVE=1`, `BCQ_PAGE_REUSE=1`, together with the existing
`SE_EDITOR_CACHED_INLINE_SOURCE=1`.

Generate NAV_SIZE/NAV_CRC from the complete newly sealed C26 payload, not this
historical binding. C23's existing managed C24 witness scanner is shared with
the exact new C26 size/CRC witness; a wrong pair fails90 before a new opcode is
issued. Existing C24 SEED_SIZE/CRC remains separately checked. The helper adds
C26 operations6 selector and7 capture-return. Old operations0..5 stay unchanged.
The private resident dispatch clone changes exactly one branch displacement:
odd cache completion branches to existing worker_complete (job12=>C23op1,
job11=>C21op1), instead of unconditionally returning to C21. Pending REQUEST/OP
retention is unchanged. No C-to-C nested call is introduced.

## Admission and authority

Only E47 outside the current cached page routes through the new selector.
Plain, cached unstyled geometry, UP/DOWN/PAGE/PAN preserve their old local
branches and original semantic_ready. The rejected broad-selector experiment
regressed small mixed documents; it is not the released default.

Owner4 and actual job12 plus GS_ACTIVE/GS_CONTEXT_VALID zero precede helper
phase use. The selector clears a dead painter GSEM_ACTIVE byte only after
these checks. ARMED, no LOST/MUTATING/ACTIVE, queue0 are required. C35 performs
its existing completed root/page/CR CRC/schema, full source-reader and typed
object proof, including its authenticated committed-source equivalence profile;
this helper invents no replacement identity or parser state. A real initial
geometry MISS falls back through C24.

For an unfolded E47 only, the first actual query targets GN_QUERY directly.
Only successful authenticated C35 completion then sets GN_SCAN to its returned
canonical logical START. This skips preceding logical blocks, not softwrapped
rows inside the target block. Folds never use this target shortcut. On MISS,
the original GN_SCAN query is restored before C24. GN_FLAGS bit128 is temporary
and retired on either outcome; bits16/32/64 are retained/attempted/saved-CP.

After A0, the existing capture helper packs the actual85B page certificate and
publishes global PAGE32 last. Retained windows require that bit, descendingCRC,
exact live13B arena/ticket/incarnation and canonical containment in the actual
GSEM START..END. Every subsequent C20/C39 still executes its real source/typed
transport guards. Any checked typed53 write revokes PAGE32 before DMA. Capture
refusal resumes the real legacy route. Mid-job source/provider errors remain
errors; they are not converted into semantic cache hits.

Real legacy CP bytes29..168 (140B) and its actual discriminator1/2 are saved at
8880..890B with marker890C only before a possible query. These bytes are inactive
R21 scratch and survive C35/R14. Explicit DEY/CPY#$FF loops copy all140 bytes;
BPL would be incorrect for a starting Y139. Successful capture retires the
saved flag before C20/C39 may reuse8880. On refusal, the exact bytes/discriminator
are restored. There is no fake79B checkpoint. The gate exercises an actual
C24-created CP1; incoming discriminator2 is preserved by the same byte copy,
not claimed as an independently successful TRY_SEED2 scenario.

## Qualification and costs

All costs are CPU instructions in complete resident public-operation intervals,
not PAL cycles, physical-key timing or native qualification. Actual BOTTOM uses
command35, while interior3072 uses real W_LOAD followed by exported resident
reveal. Source/history/clipboard/shim and whole16MiB REU are unchanged during
navigation. Post-render pixels/attributes come from independent full-source
models; post-render REU differences must match actual checked DMA masks.

|Case|Control|Targeted candidate|Loads control/candidate|
|---|---:|---:|---:|
|4KiB bold, caret3072|57,952,552|7,044,923|421 /495|
|4KiB bold thenCR, publicBOTTOM|77,375,744|671,795|557 /12|
|65536-byte logical body thenCR, publicBOTTOM|66,861,290|7,266,539|4963 /12|
|Plain caret3072|2,287,044|2,284,435|121 /121|
|Plain publicBOTTOM|3,403,792|3,401,243|163 /163|

52 broad A/B frames cover Plain/Markdown/Full, real headings/BASIC/ASM/regions,
UP/DOWN/PAGE/PAN, collapsed folds and far24 BOTTOM. Small Markdown PAGE is
518334=>518545 with unchanged72 loads, PAN66486=>66537 unchanged8 loads;
there is no material small-path load regression. Ten final fault/mixed groups
cover queued STOP, missing35/missing26/missing39 under real source leases,
source change, checked53 revocation before capture, pending-gap initial59 MISS,
real CP1 restoration through successful completion, newC23/oldC26 safe90 and
oldC23/newC26 successful legacy behavior. The failure-injection bounce is8300,
not DOC_LEAF8400. Control and candidate pixels, targets, TOP/pan/preferred agree.

The first broad experiment and early faults remain in historical build runs;
only the targeted4000/3899 pair below is released. All three authoritative runs
produce byte-identical SEOs:
- `20261026T044457231340Z`:8 public frames +50 broad +9 fault/mixed groups.
- `20261026T044548688541Z`:52 broad frames including far24.
- `20261026T044712100925Z`:10 final fault/mixed groups including missing39.

Remaining limits: this does not speed cold uncached UP/DOWN/PAGE/PAN, does not
skip target-body softwrapped metric work, and does not make source reads free
in the far24 case. More overlay loads inside a long target body can remain.
No general typing/navigation usability completion is claimed.
