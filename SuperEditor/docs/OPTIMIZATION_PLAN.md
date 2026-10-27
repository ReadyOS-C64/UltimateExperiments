# SuperEditor optimization and simplification plan

Updated 2026-10-27. This is the execution priority for the remaining M8 work.
It preserves the original product scope and supersedes any proposal to keep
adding optimization layers to the present renderer. It is a plan, not a claim
that the budgets below have been achieved.

## Current execution checkpoint

Commit `a5af575` completed the first graph replacement: eleven semantic,
query, lexical and rebase capsules plus their observer writers are gone. The
runtime is now51 images and174,889 raw payload bytes, down41,699 bytes from the
connected control, with unchanged resident/BSS/ZP/ReadyOS reservation. R33 is
one checked current-BODY plan rather than another family of cache supervisors.

Commit `ade8326` removes two measured sources of repeated work. C8 passes its
already found Plain GOTO logical start to C23 through a full-key, CRC,
VALID-last descriptor; the66K CPU path falls162,038,336→17,165,027
instructions and22,145→187 loads, with a real D81/FileOpen/IRQ PAL run at
2,344,684 cycles. R33 now keys the BODY plan on29 logical identity bytes, so
transport/window moves do not force reparsing; A/B/A falls1,299,975→694,204
instructions. Neither change adds an image, bank, supervisor or resident state.

The `a5af575` PAL profile exposed 66 C26→R33 event crossings and an11,285,120
cycle WRAPPED TOP, but that diagnosis must be read as the pre-`ade8326` state.
The29-byte logical key keeps the completed plan valid across the warm
BOTTOM→TOP/A→B→A path. Exact current CPU drops to2,431,845 instructions and24
loads, so the proposed C26 batching becomes pure overhead: +33 instructions on
warm TOP, +27–31K on edits/cold construction and +249 code bytes. Preserve its
atomicity failure and corrected guard proof as rejected evidence; do not merge
it. Exact current PAL confirms the composed fix: WRAPPED TOP is9,013,034
cycles/24 loads, down2,272,086 cycles (20.13%) and94 loads from the pre-key
state. Disk or capsule ordering cannot account for that runtime change.

This checkpoint integrates the first bounded R21 inner-loop refactor. It
carries absolute-y, strip-y and band through the nine raster
rows, hoists the packed/native row stride into existing scratch, and collapses
the two style-bit tests. It adds no image, state, call edge or DMA and keeps R21
at4,095 bytes. Exhaustive4,096-case component comparison is exact; public PAL
falls13,060,967→12,854,325 cycles on LONG and9,013,044→8,822,966 on WRAPPED.
R21 remains the largest exact cost. Continue to remove work inside its existing
job lifetime; do not revive the rejected per-glyph REU atlas or add another
checked transport.

Commit `4fc6f45` removes C20's generic measure object and keeps only its fixed
BSW9 PETSCII/width/style path. The complete eight-byte font header is still
checked for every glyph, including corruption between BEGIN and STEP. C20
shrinks4,094→3,934 bytes; exact current LONG falls1.823% and WRAPPED0.164%,
with unchanged pixels, geometry, loads, calls and parser work. Commit `d50545c`
then deletes30 R21 bytes that wrote VALID/baseline/height fields with no linked
reader, saving2,390–3,180 instructions per tested public TOP. Both changes add
no state, cache, image, call edge or supervisor.

Commit `1d78734` follows the same proof through C20 and deletes34 more bytes of
VALID/reverse/index/width/baseline/height stores with no reader, saving11,187
instructions on LONG. An attempted active-hit loader shortcut is rejected even
though PAL improved0.52%/0.32%: raw owner or epoch corruption while active no
longer returned stale, so it weakened a checked invariant without a replacement.

The resident catalog now matches the exact51-image product rather than retaining
thirteen unreachable rows. This deletes78 warm bytes and8,475 instructions across
the complete51-image import sequence, with unchanged PRG/BSS/ZP, full16MiB REU,
lifecycle and stack68 proofs. This closes the catalog-capacity cleanup. Further
disk or catalog rearrangement is not an optimization priority: subsequent work
must remove material foreground edit, parse, layout or raster work and qualify the
whole public operation.

## Product and machine constraints

Design for a stock 1 MHz C64 first. Keep PETSCII/SuperMark, all 40/60/80-column
source views, GEOS-font source editing and formatted preview, session appearance
settings, BASIC/assembler highlighting, folding, keyboard menus, one status
line, file operations, selection, clipboard and undo/redo. Keep assembly
micromodules, D81 development, logical REU allocation, the ReadyOS provider and
suspend/resume boundary, and the untouched $C600–$C9FF reservation. JSON,
UltimateDOS and actual ReadyOS application integration remain outside scope.

The assessment's proposed smaller Core/Deluxe editions are not adopted: they
would remove requested features. Remove unnecessary implementation machinery,
duplicate representations and unrequested extensions instead. No new visible
features are to be added during this work. A source micromodule need not be a
separately swapped runtime image.

The physical Ultimate is a user play session. Upload, mount, reset or load only
after an explicit user request. Development verification stays in isolated VICE
runs with warp/traps, plus CPU probes where useful. Measure emulated stock-speed
cycles even when VICE runs faster than real time.

## Inputs and verified diagnosis

Read both complete discussions: **Assess Screen Refresh Optimization**
(`01a17b30-b9e9-7f03-8ed2-5d53af23c291`) and **Assess Super Edit overlays and bloat**
(`01a17b32-0554-7fa2-aa7f-10950c018c10`). Their user messages and final assessments
are retained locally in
`agentsworking/research/2026-10-27-optimization-thread-inputs.json`.
Recommendations are inputs, not automatic requirements or established facts.

The committed 12bde7a fixture was independently checked for this plan:

| Item | Baseline |
| --- | ---: |
| Registered images |62:24 R-slot,38 C-slot|
| Linked payload, including embedded data and padding |220,651 bytes|
| Reserved fixed image slots |253,952 bytes in four REU banks|
| Images at least3,500 bytes / at least4,000 bytes |46 /30|
| Last16 images' payload |57,350 bytes|
| Available R/C execution windows |Two4 KiB slots|
| General BSS / limit before ReadyOS reserve |1,534 /1,536 bytes|

Payload is not synonymous with executable instructions. The inventory must
separate instructions, tables/fonts, padding and duplicated routines. Source
line counts including probes, generated code and test tools are not product
code size. Host evidence storage is also a separate problem.

Measured problems already justify architectural work:

- Warm local GEOS typing reloads C6→R30→AUX→R14, transferring14,809 code bytes
  per key. The final checkpoint refresh evicts the next key's workers.
- One long Full return-to-page operation uses117 loads,570 calls and467,056
  bytes of overlay fetches. Repeated small jobs and mutually evicting workers
  are more important than the nominal number of disk files.
- That profile spends2.587M of4.047M CPU instructions in R21/C22. It enters
  glyph/measurement1,768 times for862 characters. It performs7,952 invisible
  scanline loop passes, although invisible bitmap decoding is already skipped.
- C22 source/cache guards cost about1.75% of that complete operation. Removing
  correctness checks cannot recover the main delay. Overlay CRC is likewise
  not a universal explanation for every slow path.
- Layout-only page memoization still rerasterizes. The private whole-row and
  REU-atlas probes have real setup, lifetime and clipped-row costs; their narrow
  speedups do not qualify a complete public replacement.
- The private63rd paint image has two actual edit defects. The working alias
  repair fixes CR deletion; live narrow-glyph shadow data still overlaps an
  outgoing checkpoint. It must not be promoted as another permanent layer.

Use [warm input attribution](../src/render/geos/warm-input-profile-probe/README.md),
[raster attribution](../src/render/geos/raster-cost-probe/COST.md), the existing
[cache redesign](REU_CACHE_REDESIGN.md), and the pinned geoWrite source study in
`agentsworking/research/GEOWRITE_REFRESH.md`. Historical measurements are scoped
baselines, not a new common-build benchmark or a measured geoWrite comparison.

The three existing parallel probes were stopped at bounded checkpoints for this
plan. Their results change what gets built next:

| Experiment | Evidence and decision |
| --- | --- |
| Layout-only memo |Whole CPU A→B→A saves2.94–10.91% in Markdown/Full but still rerasterizes. Do not add it as another permanent cache family.|
| Separate-bank page image |Two images fit one optional64 KiB data bank, but the incomplete transfer draft is4,724 bytes:628 over its code slot. Never executed. Treat its storage census as input to a replacement, not a fit claim.|
| Corrected paint shadow mapping |C21 needs4,139 bytes and R63 needs4,152:43/56 over their slots. Never executed. Replace delayed comparison and shadow storage rather than growing the slots.|
| Pre-shifted REU glyph atlas |Synthetic20-row cold CPU work falls3,624,625→3,239,586 instructions, including construction. Complete verification per row costs7,328,001. There are999 checked per-glyph reads. Reject this as a production per-glyph transport layer.|

Source/result notes are under `src/render/geos/{layout-retention-probe,
paint-shadow-probe,logical-row-job-probe/reu-atlas}/`. The measurements are
different scoped experiments; none establishes public native1 MHz latency.

## Rules for choosing work

1. Eliminate unnecessary work before making that work faster. Never rebuild a
   whole viewport merely because a local fast path refused an ordinary edit.
2. Choose residency around an editing group, a logical row or a batch of rows.
   Parser, layout and paint helpers must not evict one another per character.
3. Every production addition names the code, state and path it replaces, its
   deletion step, and the complete cost it removes. An isolated helper speedup
   is insufficient. No additional registered image by default; temporary
   migration images must have an explicit removal gate before release.
4. Keep one clear fallback for each mode. An optimization miss must reach that
   correct bounded path without another chain of speculative caches. Preserve
   required representation differences between fixed and proportional text;
   do not invent one giant generic renderer merely to reduce file count.
5. Preserve source, ownership, extent, generation, font and publication checks
   at real trust and yield boundaries. Hoist repeated checks only after proving
   a closed lifetime. Do not treat standalone REU ownership as proof against
   internal aliases, cancellation or stale derived state.
6. Optional analysis and retained pages have bounded quotas and cheap eviction.
   They may save time; they may not make an ordinary edit fail for cache space.
7. No new allocator, cache supervisor, edition split, setting or abstraction
   without a measured need. Keep the logical provider boundary. A replacement
   linear allocator is not justified by the evidence presently available.
8. Total cycles and input latency decide. Image count, zero parser feeds,
   component percentages and smaller instruction counts are supporting metrics.
   Never add gains from different probes as though they compose automatically.

## Proposed engineering budgets

These are initial targets to test at nominal1 MHz, not achieved results or new
claims about hardware. PAL cycles and approximately equivalent milliseconds
must be reported separately. Missed budgets remain visible; do not quietly increase
them or conceal them with a narrower favorable case.

| Interaction, settled current mode | Cycle target | Code-load target |
| --- | ---: | ---: |
| Warm 40-column caret |15,000|0|
| Warm 60/80-column or GEOS caret |40,000|0|
| Ordinary 40-column same-row edit |30,000|0–2|
| Ordinary 60/80-column or GEOS same-row edit |100,000|0–2|
| Visible paragraph Return/BACK split or merge |250,000|At most 4|
| One-row viewport scroll with retained overlap |300,000|At most 4|
| Unchanged A→B→A return, if retained |150,000|At most 2|
| New diverse GEOS viewport, first coherent completion |500,000|At most 12|

The original modest-document full-redraw goal remains approximately 0.5 s.
A one-million-cycle new GEOS viewport is an intermediate improvement, not
completion of that goal.

Input must be serviced at safe boundaries within 50,000 cycles of foreground
work. A completed obsolete frame is not a prerequisite for applying queued
input. Measure first visible feedback, latest-state completion and cancellation
delay independently. The keyboard ring is finite; prove backpressure/overflow
behavior under repeat and bursts rather than promising unlimited type-ahead.

The initial consolidation target is at most 48 registered images and 176 KiB
linked payload, about 20% below the 62-image baseline. Phase 1 must check the
actual section inventory before fixing the final release ceiling. Count and
payload reductions cannot compensate for missed interaction budgets. More REU
data can be sensible when it deletes CPU work and management code; count its
construction, refresh, pressure and restore costs explicitly.

## Ordered execution

### 0. Freeze a safe baseline and contain the experiments

Keep committed 12bde7a as the control. Record its exact sources, D81, fonts and
settings. Preserve the uncommitted63 work and both structural regressions as
evidence, without treating it as the accepted product. Stop opening additional
probe variants until the present probes have a measured accept/reject result.
Keep useful techniques from them, not their accumulated supervisor graph.

Before large code changes, commit a clean, reviewable checkpoint of the actual
source on the dedicated optimization branch. The existing
`supereditor/reu-cache-redesign` branch is suitable; do not sweep unrelated
changes or artifacts into it. Ignored logs, generated binaries and external
GEOS assets stay out of Git. Do not commit a known-broken experiment as a
qualified release. Preserve it separately as a clearly labeled checkpoint if
needed. No worktrees.

Exit: a reproducible control and a list of every retained or rejected probe,
including known faults. No ambiguous mixture of committed and private claims.

### 1. Produce one common-build cost and residency inventory

Capture the same corpus and public operation sequence on the exact baseline:
all four source views, preview, Plain/Markdown/Full, highlighting on/off,
ordinary and styled text, BASIC/assembler, narrow glyphs at maximum row count,
wrapping, selection, folds, and source positions above64 KiB.

Include first/steady typing, caret immediately after typing, CR/BACK at the
viewport bottom with scrolling, line/page navigation, A→B→A, popup open/close,
first/reopened preview, undo/redo and repeated edits through flush. Measure
complete source processing, first pixel and completed publication, overlay
loads/calls/DMA, IRQ/input queue, parsing/layout/glyph counts and exact source
identity. Keep cold setup, warm work and idle analysis separate. CPU profiles
select work; normal-speed emulated PAL cycles qualify it. NTSC is a final gate.

Generate a linked closure inventory and an ordered call graph per operation.
Classify each image and shared state as hot, mode-specific, or cold. Identify
duplicate source readers, copies, CRC loops, semantic stores and fallback
controllers. Budget a new RAM/phase map with real lifetimes and IRQ access;
recover space by deletion instead of squeezing more aliases into spare bytes.

Exit: one concise table containing the current deficits, chosen replacement
boundaries, byte budgets and exact code to retire. This replaces selecting the
next optimization by whichever overlay happens to have a few bytes left.

### 2. Keep the hot editing pair resident

First remove the measured C6→R30→AUX→R14 eviction cycle. Move the small
post-publication freshness update into the owning transaction or defer it with
an explicit invalidation/rebuild contract. Preserve source checkpoint freshness
and undo boundaries. Consolidate source access and common projection work into
the active edit/mode job. Keep cold dialogs/settings/preview/lifecycle in cold
overlays. Do not move an entire large worker into the already-full resident.

Replace the executable$5000 staging arrangement with a budgeted residency map
in which fonts/data cannot silently evict hot code. Source micromodules remain
separate and link into operation-sized images. Removal of the stage stamp and
re-prime paths follows only after the replacement covers their consumers and
meets the complete-operation budget; a slower clean-looking map is not a win.

Exit: ordinary repeated keys meet0–2 loads; no forced post-key eviction; the
replacement deletes obsolete routing/staging code. Local/caret gains must
survive switching modes, opening menus and coming back to typing.

### 3. Replace fallback re-layout with retained lines and exact convergence

Use one bounded retained logical-line/block model containing source anchors,
incoming/outgoing parser and inline state, font/style/width, geometry, baseline,
fold projection and paint inputs. Reuse existing valid records where possible;
do not add a second semantic truth beside type53 and then maintain both.

Restart at the affected logical boundary, including the previous line for CR
deletion. Invalidate the affected complete inline BODY when a delimiter can
change earlier styling. Propagate only until unchanged source and complete
parser/font/style/geometry state converge. Fences can legitimately propagate
to EOF; do that incrementally with cancellation, not in a blocking repaint.
Retain an unaffected horizontal prefix where its pixels and attributes remain
valid. Long lines require continuations rather than repeated scans from BOF.

Retain visible and adjacent lines under one bounded replacement policy. Move
overlapping bitmap rows/attributes and regenerate only newly exposed rows on
scroll. View/caret/selection changes must not restart parsing. Palette changes
retain semantic/layout data; metric changes retain parsing but invalidate
dependent geometry. Highlighting disabled must execute no lexer feeds; an
unchanged block must not be lexed again merely because the viewport changed.

Compare each genuine newly completed row with its old packet at the row-ready
boundary. A proven single842B old-row scratch plus accumulated dirty strips
can replace 22 persistent shadows, their scattered addressing, the delayed
comparison pass and duplicate publication certificates. This is a replacement
design to prove, not an implemented fix: C20/source/parser leases must have
ended before the scratch is borrowed, and source/font/provider/publication
authority must survive the whole comparison and commit.

Replace the semantic/lexical rebase chain and its duplicated routing as the
new model proves coverage. A prototype page memo that saves10% but leaves the
dominant raster work and adds another full supervisor is not the endpoint.
Store a prior page image only if it fits the same bounded policy, cheaply
reuses genuine caret-free geometry and deletes work/code overall. Handle cache
pressure as a miss, with no extra bank assumed to be available.

Exit: public ordinary/wrapped/CR/scroll operations stop at proven convergence;
retained A→B→A skips both measurement and rasterization when its image is valid.
Trace deletion of displaced semantic/lexical/paint paths, not just their bypass.

### 4. Replace strip-by-strip glyph preparation with a whole-row compositor

Compose each8/9px logical row once into its containing VIC bands. Bind the
source/packet/font authority once per closed job, prepare glyph descriptors
once, and carry the exact ink weights across shared8x8 color cells. Preserve
bold, italic, underline, reverse, native fallback, selection/caret union,
clipping and role priority/ties. Keep foreign font metrics correct.

Batch enough work while the compositor remains loaded to avoid a helper swap
per glyph or band. Prefer ordinary lookup tables and fixed shift chains where
they remove real work. The present raw-bit decode already skips invisible
rows: do not claim a50% gain from eliminating invisible loop passes alone.

Judge the existing whole-row and REU-atlas probes on complete public rendering,
including packet gathering, actual checked DMA, first-build/readback, styles,
fault checks and every yield. A pre-shifted font cache that saves a synthetic
steady job but doubles cost when revalidated per row is not ready to ship.
Prefer a small per-font/per-job prepared representation to another permanent
glyph cache manager. Reject variants whose setup or memory ownership cannot
be amortized safely. Share source/preview primitives where their semantics
actually agree; do not force formatted and literal layout into one state union.

Replace C22/R21 preparation and the eligible old raster path together. If the
new compositor subsumes paint convergence, delete the private R63 supervisor
and its shadow/certificate copies. If it does not, no permanent R63 addition
is justified until the net image/bytes/load budgets and correctness gates pass.

Exit: one traversal per glyph per logical row, exact color-cell output, public
cold/warm cycle wins, and retired old preparation/staging paths. Do not preserve
every historical shortcut as another fallback beneath the new implementation.

### 5. Make responsiveness independent of renderer throughput

At safe yield boundaries, detect queued editing input, stop obsolete paint,
apply a bounded batch and merge damage against the newest revision. Preserve
command ordering, modifiers, physical key identity and undo grouping. A held
key must neither starve all publication nor force every intermediate state to
paint. Do not roll back an accepted edit when an optional derived job stops.

Retain the existing visible publication until a correctly sourced replacement
is ready; stage and commit bounded dirty regions using a proven memory map.
Logical publication atomicity is not a claim of tear-free VIC frame timing.
Menus restore their covered rectangle; help/status changes do not reparse the
document. Test typing during worst-case reflow and scrolling at stock speed,
including buffer saturation, not just injected keys after every idle state.

Exit: bounded input service/cancellation latency, exact accepted text, no
starvation, no stale result published after a newer edit, and no unnecessary
full-page redraw on popup dismissal.

### 6. Cut startup and distribution baggage

Separate a lean runtime D81 from the existing diagnostic/fault-fixture D81.
Remove test PRGs, malformed overlays and probe assets from the runtime disk;
retain them in the development package. Keep all requested runtime features.

Measure startup by disk open/read, CRC/import, code installation and font
installation. Bring up40-column editing without eagerly loading proportional
fonts, preview workers, lifecycle copy code and every other cold feature.
Evaluate a simple sequential indexed overlay pack against many sidecar opens,
using actual KERNAL/D81 capabilities; do not assume random seek or UltimateDOS.
Retain per-image bounds/identity checks and meaningful missing-asset errors.
Warm REU swaps remain distinct from disk first-use loads.

Exit: no unrelated eager assets before first useful edit, at least80% less
time-to-ready than the measured approximately11m32 hardware baseline on the
same configuration, and separate measured first-use times. This is an initial
reduction target, not acceptance of a multi-minute editor startup. First-use
costs must be disclosed rather than hidden after the initial screen.

### 7. Delete, qualify and publish one result

After each replacement, delete its retired production images, state, build
paths and dispatch branches. Keep historical probes outside the runtime closure.
Use a short before/after table: bytes, images, actual loads and code DMA,
cold/steady cycles, input delay, memory and remaining failure cases. If a
candidate adds machinery without meeting a complete-operation budget, reject
it or redesign the boundary; do not promote it because qualification took work.

Require one common final source/settings/font cohort for all-mode editing,
scroll/CR/selection/folds/menus/open-save/undo-redo/preview, PAL and NTSC, lower
REU pressure and16 MiB, and the existing lifecycle seam. Keep independent pixels,
exact source/history/clipboard, ReadyOS reserve, typed memory, ownership and
fault/cancellation checks. Preserve the two new structural regressions.
Update maps and stack analysis after actual call-graph changes.

Run focused CPU/probe tests while choosing a design; run the affected native
matrix when a candidate is credible; run the complete final cohort after
integration. Do not recapture unchanged broad galleries or run huge evidence
seals for every small rejected experiment. Retain representative raw evidence,
source identities and failure records without duplicating large artifacts.

## Parallel ownership and immediate next action

Use at most three concurrent agents in this repository, without worktrees.
Root owns production integration, shared builds, Git and native launches.
Independent lanes own only their private sources/results: residency/code
census; retained-line/scroll design; compositor measurements. Each closes with
one accept/reject recommendation and a deletion list. Serialize overlapping
memory-map decisions. Do not message the two assessment threads or deploy to
hardware as part of adopting this plan.

Immediate next action: finish the bounded current probes, preserve their
findings, and produce Phase 1's common-build cost/residency table and replacement
map. Then tackle the hot-key eviction loop and retained-line fallback. Do not
continue filling the64-entry catalog with independent optimization supervisors.

## Current ruthless deletion pass

The catalog-capacity change is closed. Current production work must delete live
instructions, state, repeated validation or raster work and report the effect on
the complete foreground operation. Disk order and catalog layout do not qualify
as performance work in this pass.

The first resident deletion removes the 28-byte clipboard compatibility
dispatcher, routes its sole live COPY STEP caller through the controller's
existing C10 dispatcher, and deletes eight unread state bytes. The linked result
is 26 fewer CODE bytes and eight fewer resident state bytes. A successful copy
step saves 15 CPU cycles and one resident call; overlay calls and loads stay
unchanged. This is a code-graph simplification, not a redraw claim.

The next two independently measured candidates target foreground work directly:
C32 typing removes repeated guards and validation wrappers, while R21 raster
specializes its production-only full-width contract and deletes generic clipping.
They must retain exact pixels, source and fault behavior after composition before
promotion. Continue from whole-operation PAL attribution after those cuts; do not
return to overlay-file rearrangement.

The C32 cut qualifies independently: it removes 26 staged bytes, saves 2,111
instructions on steady INSERT and 2,008 on steady BACK, and improves native PAL
steady operations by 5.53% and 5.64%. The 46-frame public matrix, eight API fault
cases, exact pixels/source/REU checks and the composed 51-capsule package pass.
Caret work and overlay loads/calls remain unchanged.

The R21 cut also qualifies: C22's sole row setup always supplies LEFT=0 and
RIGHT=320, so R21 now rejects any other pair and deletes the unused partial-width
implementation. It removes 191 executable bytes and 1,200 pairs of horizontal
resolver calls per full TOP operation. Public CPU work falls 2.34–3.73%; native
PAL LONG and WRAPPED fall 1.68% and 2.40%. Exact pixels, attributes, source,
fault-before-write behavior, stack, overlay traffic and DMA remain unchanged.
The role-zero shortcut remains rejected because it regressed Markdown and Full.

The next R21 pass hoists band-invariant role initialization and VIC attribute
address calculation out of the 1,200-tile resolver. It removes 27,690 R21
instructions from LONG and WRAPPED, saving 99,052 and 99,398 native PAL cycles.
It is one executable byte smaller, adds no state or calls, and keeps component,
fault, stack, package, pixel, load and DMA checks exact. The histogram-pointer
variant remains rejected because it added code for a weaker resume contract.

C32 now writes each caret-free edited row directly into the existing two-band
cache-block layout and reuses that copier for VIC publication. This deletes the
separate 9x40 scatter pass and shrinks TYPE by 37 bytes. Complete steady edits
remove 1,845 instructions and improve native PAL INSERT/BACK by 4.14–5.03%
across Plain, Markdown, Full and styled text. No state, stack, overlay or steady
DMA work is added; the full edit/fault and native pixel matrices pass.

Resident input routing now releases style ownership once before dispatch and
bypasses the public command cleanup wrapper on internal routes. Direct command
callers keep the wrapper. This removes 25–28 cycles and one call frame from each
accepted input command and deletes two resident CODE bytes. It is a small common
path cleanup alongside the material edit/raster cuts; it does not change overlay
or REU traffic and is not counted as a redraw solution.

R21 glyph measure/decode now consumes the fixed BSW9 contract already certified
at job admission. It deletes per-glyph style, pointer, width, start/end and
vertical-visibility revalidation plus two private pointer helpers. This removes
189 executable bytes and 9,647/9,240 helper calls, reducing native PAL LONG and
WRAPPED by 6.10% and 8.45%. Job-level validation, malformed-job refusal, pixels,
source, stack, overlays and DMA remain exact; no table, cache or REU path is added.

Cold state initialization now relies on its linker-bounded complete BSS clear
instead of zeroing six render bytes again, and it reuses the loop's proven X=0.
Zero-byte linker assertions keep those fields inside BSS. This removes 16 live
COLD bytes and 51 startup cycles with identical dirty-RAM results. It is recorded
as bloat cleanup only and carries no foreground performance claim.

## Material replacement boundary after the bounded cuts

The bounded instruction deletions above are complete. Further leaf-loop and
overlay-routing variants are closed unless a new whole-operation profile shows
them to be material. Three exact-current experiments establish that boundary:

- specializing C32 for six-byte shifts made the complete cold operations slower
  after payload authentication and left stale pixels on the next public caret;
- keeping the edit pair hot removed later overlay loads but required 546 new
  bytes while the generic rekey path still served other modes; and
- both a fused R21 decoder/compositor and a terminal byte-row cut saved less
  than 3% of their complete public operations.

An R33/C26 direct span accumulator removed 66 event crossings and reduced a
forced WRAPPED insertion by 149,077 instructions, but that was only 4.13% of the
complete operation and grew the two images by 408 bytes. It is rejected. This
is the decisive lesson for the next work: crossing, load and DMA counts are
diagnostics; only deleted live bytes and complete foreground PAL cycles qualify
a production change.

### Implemented Plain direct-row slice

The first replacement is intentionally smaller than the proposed retained LRV3
object. The proposed persistent 96-byte header, 24-record directory, style
canvas, parser carries and manifests had no next-edit reader: every Plain edit
would have rebuilt and written them before consuming the same information once.
That storage and its REU DMA/CRC work are deleted from the live design. Internal
`lrv3` source names remain temporarily, but they describe a local transaction,
not a persistent retained-line cache.

C6 captures a one-edit certificate from the last completely published resident
layout before mutation. After mutation it supplies only a physical-row hint.
R25 frame 18 rechecks the certificate, Plain capabilities, width, post-edit
length and revision, document/REU epochs, and the hinted `se_v_rows` start and
following anchor. It derives that row's CR-exclusive length, proves its CR/EOF
terminator and the edit position, and accepts only a row that remains shorter
than the active 40/60/80-column width. The selected start, length, flags, row and
caret inputs are stored in the existing `$8D00` phase union; `PREPARED` is
written last. There is no syntax parse, styled carry, directory scan, REU LRV
publication or manifest authentication on this Plain path.

C33 frame 1 enters the direct painter only for a current prepared transaction;
otherwise it preserves the ordinary warm-caret path. The painter rebuilds and
publishes one row, commits the existing native row packet for 60/80 columns,
shifts later resident row anchors and the bottom anchor by one byte, and retires
the transaction. CR edits, wrap/row-count changes, selection, folds, styled
content, stale witnesses and faults take the established cold fallback. This is
a deliberately narrow first slice; Markdown, Full and GEOS retain their current
correct renderers until a later replacement can delete their live work.

The obsolete fixed-grid graph is gone, including SP2, its C14/R14 dispatch and
reader glue, the R14 paragraph shifter, and the displaced C33/R25 type/long
families. Current linked sizes are resident `main.o` 271 bytes (three bytes
smaller), C6 3,570, R25 3,231 and C33 3,784 bytes before its fixed native-font
segment, leaving 56 bytes before `$BF00`. Against the exact 5,220-byte retired
graph, additions are C33 1,348, R25 1,106 including 12 bytes of RODATA, and C6
343; the resident saves three bytes. Replacement code is 2,794 bytes and the
net deletion is 2,426 bytes. The change adds no BSS or zero-page state and no
image, bank or catalog entry. Do not revive a persistent directory or styled
publisher until it replaces a measured live consumer and remains a net deletion.

Static actual-6510 probes pass 23 certificate cases and 12 row-hint boundary
cases; a separate check proves stale `PREPARED` transactions are retired. The
actual-product Peddle gate also passes exact source, pixels, attributes, row
anchors and caret: insert/delete costs are 10,548/10,243 instructions at 40
columns, 87,619/87,345 at 60, and 50,689/50,460 at 80. Those ordinary Plain
operations meet the 30K narrow and 100K wide instruction targets. They use
3/3, 6/6 and 6/6 overlay loads and 6/6, 8/8 and 8/8 calls respectively, so the
wide-mode load target remains open. Warm caret is 5,179/33,698/34,859
instructions. Correct cold fallback costs 317,297 for an 80-column CR insertion
and 426,997 for the 60-column wrap-boundary refusal.

Native PAL VICE now confirms the wide Plain path with exact source and reviewed
screenshots. At 60 columns insert/delete publish first at 364,043/363,415 cycles
and settle at 364,191/363,520; at 80 they publish at 218,387/217,945 and settle
at 218,492/218,050. Each operation publishes one draw sequence and uses six
loads, eight calls, nine DMAs and 23,072 DMA bytes, with only the expected
grid60/grid80, R25, C6 and C33 groups. The tracked native scenario now explicitly
issues `syntax plain` after opening the fixture; the prior setup did not prove a
Plain route. These spans run from public input entry to foreground quiescence;
they are not physical keyboard latency. NTSC and physical-hardware timing remain
pending. Overlay counts remain diagnostic; rearranging disk overlays earns no
optimization credit.

The original product scope remains unchanged. After the Plain slice finishes
native qualification, the next work is whichever measured styled fixed-grid or
GEOS parse/layout/raster boundary can delete the most live work without adding
another parallel authority.

### Styled wide-grid single-publication checkpoint

Full and Markdown 60/80-column edits previously published an unstyled bitmap,
then completed the one full style pass and published the same viewport again.
The wide C16 producer now returns `ST_PENDING` after checked leaf admission and
style-context binding but before any cell or cache write. Resident clears the
strict draw-busy flag and returns to the normal idle loop, so queued input is
checked before C14 receives its first bounded slice. Once the style plan is
valid, C16 paints and finalizes once. Nonzero UI bypasses withholding, and an
exact-context planner failure schedules one plain fallback redraw. The unsafe
40-column variant was removed because R1 produces wrapped anchors during paint;
prepaint styling there bound a valid plan to stale anchors.

This is a scheduling deletion, not parser convergence. Full 60-column work falls
from 2,649,645 to 1,000,409 instructions (62.24%); Full 80 falls from 1,805,177
to 1,010,676 (44.01%). Loads fall 29 to 27 and DMA falls from 126 calls/135,025
bytes to 76/116,181. C16 `GRID_FINALIZE` falls from two to one. The linked
ledger is exactly neutral: resident +14 bytes, text40 -15 and gridedit +1; no
BSS, zero-page, REU, image or catalog growth. Full pixels/attributes, Plain
40/60/80, structural CR, UI/input interleaving, D81 and ReadyOS-reservation
gates pass.

Normal-speed PAL VICE confirms the whole-operation reduction. Full60 settles at
3,996,868 cycles instead of 9,897,057 (59.61% lower); Full80 settles at
4,043,622 instead of 6,813,027 (40.65% lower). Both preserve independent
source/bitmap/attribute, catalog, stack and REU oracles and publish exactly
once. Loads fall 29 to 27 and PAL DMA falls from 123 calls/134,123 bytes to
75/115,759. The remaining roughly 310K-cycle tail is the existing post-frame
C33 cache capture with nested R25 authentication, not syntax parsing; retaining
that next-input authority is a separate replacement decision, not an overlay
placement exercise. Evidence:
`agentsworking/evidence/M8/20261027T101239594697Z-display-timing-full60-80-normal-pal-post-change/normal-speed-full60-80-result.json`.

The remaining styled boundary is still material: C14/C15 continue a complete
visible style pass before that single publication. Their current 7,864 linked
bytes contain 4,837 bytes of parser cores and 3,027 bytes of replaceable
orchestration. The next replacement must reuse the dormant checkpoint region
for authenticated incoming/outgoing logical-line carries, stop at exact parser
state convergence, skip lexical work for unchanged code lines, and delete the
displaced orchestration in the same change. Overlay placement alone earns no
credit.

### Styled row transaction: implemented replacement

The first convergence prototype proves the useful part of the idea and also
defines what must be deleted. On an admitted Markdown 80-column edit it stops
the block and inline parsers at the changed logical-line boundary: 24 and 23
feeds for the representative prose insertion, versus 129 and 52 on the
structural CR fallback. The complete CPU operation is 337,407 instructions,
versus 803,220 for that fallback, with exact source, pixels, attributes,
anchors, caret, undo and redo. The prototype is not the production endpoint.
`styler` plus `viewsource` grows from 6,373 to 7,456 linked bytes, an exact
1,083-byte increase, and the accepted path still runs the old C11 layout and
post-publication C33/R25 capture. Moving parser code between disk images is
size-neutral and receives no optimization credit.

The retained no-preclear cut is independently proven. Sixty poisoned cold jobs
cover Full/Markdown, all three widths, empty/EOF/CR/wrapped/BASIC/assembler
documents and two poison values. No unwritten plan byte is read. Removing the
grid fill loop and its counter saves 63 C14 bytes and up to 1,760 stores per
build. The former two-byte counter is currently inert
reserved padding so sealed parser/source addresses do not move; linked BSS is
unchanged. This deletion survives regardless of which styled transaction
replaces the prototype.

The production boundary now admits the one-byte edit directly in C6, seals a
compact ticket and packed row carries in the fixed `$4770` checkpoint window,
and never enters R25 frame18 or C11 on an accepted edit. C14/R14 restores the
incoming block state, performs bounded parse and planning, and marks the ticket
ready. C33 frame1 authenticates that result, builds and paints the affected row
transaction, calls the existing R25 native painter where required, rebases the
suffix anchors and publishes exactly once. No accepted path runs C16 full-page
render, C11 layout, frame15, post-publication capture or other work after the
commit. This deletes work from the foreground edit graph; disk placement is
unchanged and receives no performance credit.

The final checkpoint uses five-byte packed carry records and a CRC16 over all
110 carry bytes. The CRC occupies two bytes that the plan originally reserved
as slack, leaving seven spare checkpoint bytes. This is an intentional change
to the byte gate: arbitrary carry corruption is now detected before admission,
with no new BSS, zero-page, REU object, image, bank or supervisor. C33 also
applies native roles while it constructs valid source-cell packets. The former
separate 40/60/80-cell style pass is gone, and padding cells receive role zero.
Cold style construction no longer clears 880/1320/1760 plan cells or 566 state
bytes that are proven overwritten.

Structural convergence refusal no longer reparses against pre-edit anchors.
It retires the ticket and source lease, returns `ST_RETRY`, lets ordinary layout
publish the new geometry, and only then starts a fresh cold style build. This
ordering fixed the real 40-column `:::region` row-growth witness while deleting
31 C14 bytes. Wrapped row growth is also rejected before mutation when the new
source length exceeds the ticket's certified row geometry.

The linked result meets the replacement byte gate: `styler.bin` is 3,311 bytes
and `viewsource.bin` is 3,283, for 6,594 of the 6,630-byte combined allowance.
`window.bin` is 4,071/4,096, `grid.bin` is 4,096 and `geostail.bin` is 3,965;
resident state remains 1,533 bytes and the change adds zero BSS and zero-page
bytes. The complete matrix passes all 72 cases. Its 48 admitted cases preserve
source, pixels, colors, anchors, caret and history, publish once, use 6–10 loads
and execute 24,065–129,441 instructions. Twenty-four structural cases, five
stale/corrupt carry cases and queued-edit/F6 cancellation all pass. Registered
stack use is 52 foreground plus 16 IRQ/NMI bytes, or 68 total. Evidence is in
`build/styled-grid-carry-matrix/20261027T121902469141Z/result.json` and
`build/editor-registered-stack/20261027T1219-current51/proof/qualified-result.json`.
The exact final styled transaction still needs normal-speed PAL qualification;
no PAL claim is inferred from the instruction-count harness.

The next measured cuts stay inside this transaction instead of rearranging its
overlays. Replace per-cell 24-bit range, selection and caret comparisons with
row-relative counters (estimated 2.5–4.5K instructions per 80-column row).
After proving uninterrupted ownership, remove repeated 59-byte guards between
serialized fast slices (2–5K/edit), eliminate empty C14 phase-transition yields
(1–3K plus fewer calls), and stop copying then generically rebuilding the
256-byte cache header (about 2.8–3.5K). A sequential suffix-anchor walk can save
another 300–500 instructions. The largest, riskier step is a native dirty-span
row renderer, which could remove 30–70% of leaf paint work. CRC removal is not a
candidate: it is now the tested corruption policy for persistent semantic state.
The detailed implementation and acceptance record is maintained in
`agentsworking/STYLED_ROW_TRANSACTION_PLAN.md`.

### Row-relative packet construction and completion-guard deletion

The first post-transaction cut removes work inside the accepted foreground
path. C33 now computes the 24-bit row offset, remaining content count, endpoint
state and caret column once per row. Its cell loop no longer repeats 24-bit
range, selection and caret comparisons for every one of 40, 60 or 80 cells.
It clears character, role and selector bytes as it produces each owned cell, so
padding cannot retain stale reverse or selection flags. Selection is rejected
at the authenticated R25 admission boundary and is no longer retested inside
the admitted packet loop.

The packet builder itself falls from 2,634 to 1,347 instructions for the
ordinary 40-column case, 3,275 to 1,668 at 60 columns and 3,915 to 1,988 at 80
columns. Near-full rows fall from 3,266/4,897/6,527 to
1,639/2,420/3,200. The complete styled consumer now uses
7,498/7,306 instructions at 40 columns, 84,030/83,854 at 60 and
55,295/55,147 at 80 for insert/delete, with the same two or three loads. This
is a ten-byte C33 code increase over the required packet-flag clear baseline;
it adds no state, zero-page, image, bank or catalog entry and leaves 17 bytes
before the fixed `$BF00` boundary.

The focused production oracle covers an empty line, first/live/end/padding
caret positions, width-minus-one content, exact-width CR/EOF refusal, wrapped
and panned rows, a retained row beginning at source offset 66,000, poisoned
character/role/selector planes, and selection refusal with the full 16 MiB REU
unchanged. Evidence is in
`build/lrv-row-relative/20261027T124658181333Z/result.json`. The complete
72-case styled matrix, including five corruption classes, queued input, F6
cancellation and stack 68, passes at
`build/styled-grid-carry-matrix/20261027T124651196416Z/result.json`.

C14 also removes a second source guard at `complete:`. Every path to that label
remains inside the same uninterrupted `se_style_step` that already authenticated
the source, so the second R14 call could not observe a new source authority. The
deletion removes eight linked bytes and 945–946 instructions plus one R14 call
from every completed planner, without changing overlay loads. Structural wrap
routes that complete two planners remove 1,892 instructions. The larger private
guard/yield fusion experiment is deliberately not shipped: although it saved
more instructions, it added 23 linked bytes and slightly lengthened the measured
input-response bound.

The next admitted change must meet the same standard. A direct authenticated
header update is under proof because it can delete two 256-byte CPU copies and
the generic header rebuild while retaining both CRCs and valid-last publication.
Dirty-span painting and dead graph removal remain candidates only if their
complete-operation savings exceed their code cost. Moving the same work between
disk members or overlays remains outside the optimization ledger.

### Wide raster, header and dead-graph cuts

The next three cuts remove more work from the same transaction. The native
60/80-column leaf already clears all 320 bitmap bytes and 40 attributes before
glyph painting. C33 now passes the authenticated live-cell count rather than the
physical column width to the glyph loop, so blank padding is not converted and
painted a second time. A poison oracle fills the entire old row and its
attributes before insert and delete; exact output proves the unconditional clear
still erases a longer old suffix. This costs three C33 bytes and removes
30,023–32,409 instructions at 60 columns and 17,493–18,157 at 80. The
40-column path is unchanged.

The wide NC header is now updated in place after its existing authentication.
The transaction writes changed row CRCs, suffix anchors, bottom, caret,
revision, source/style lengths and publication fields directly into the live
header, then retains the existing final header CRC, guarded DMA store and
valid-last publication. It no longer copies 256 bytes to `$8500`, copies them
back, and calls the generic full-header rebuild. Twelve styled transactions
cover 60/80 columns, rows zero through two and insert/delete; all 256 final
header bytes are byte-identical to the control, and independent checks recompute
the header CRC and every changed packet CRC. Header corruption, forged magic
with a recomputed CRC, and physical-owner/DMA faults refuse without publishing.

An added Plain bottom-row oracle caught an inactive-descriptor mismatch that the
styled cases could not expose: unconditional revision and length writes changed
the inactive style key when `FIRST+ROWS==22`. The final code gates those style
stores on the styled transaction bit while retaining unconditional source-key
updates. All four 60/80 insert/delete bottom-boundary cases then match the full
256-byte control header. This failure is why a byte-exact final-object oracle is
required in addition to screen equivalence.

Finally, four record-flag stores and their two reverse consumers are deleted:
no current producer can set `LRRF_REVERSE`. Two `se_selection_range` calls are
also gone because R25 already refuses marked selection before admission and C33
no longer reads the computed range. This removes 49 linked executable bytes and
147–193 instructions from each admitted edit without changing state, calls,
DMA or resources.

With all three cuts composed, the focused styled consumer uses
7,327/7,141 instructions at 40 columns, 49,754/47,198 at 60 and
33,529/32,723 at 80 for insert/delete. Relative to the row-relative checkpoint,
that removes another 171/165, 34,276/36,656 and 21,766/22,424 instructions.
Plain wide insert/delete falls to 46,353/44,111 at 60 and 30,783/30,065 at 80;
warm caret routing is unchanged. `geostail` remains below its 4 KiB limit and
the fixed C33 image retains 41 contiguous bytes before `$BF00`; there is no
BSS, zero-page, resident, image, bank or catalog growth. Exact-current full
matrix, stack and normal-speed PAL qualification are the final gates for this
composed slice.

Those gates now pass on D81
`28e6041abecc16025e90c50d8cc525cac521b472b57dfed6923cf0c195ba185a`.
The fresh 72-case matrix contains 48 admitted and 24 structural cases with zero
failures, all five stale/corrupt classes and both cancellation cases pass, and
the registered bound remains 52 foreground plus 16 IRQ/NMI bytes. Admitted
operations use 6–10 loads and 22,065–91,396 instructions. Evidence is in
`build/styled-grid-carry-matrix/20261027T130013415847Z/result.json` and
`build/editor-registered-stack/20261027T125955250755Z/qualified-result.json`.

Normal-speed PAL VICE passes Full/Markdown, insert/delete and all three widths
with exact source, pixels, colors, anchors, history, catalog, payload, stack and
shim witnesses. Every case publishes once and executes no parser or overlay call
after publication. Settled 40-column time is 201,893–203,665 cycles, 60-column
time is 394,267–400,529, and 80-column time is 317,301–320,254. This is about
5% faster at 40, 23.0–23.9% at 60 and 20.9–21.3% at 80 than the preceding
qualified transaction. The exact native artifact is
`agentsworking/evidence/M8/20261027T125939500129Z-display-timing-styled-grid-convergence-baseline/normal-speed-pal-styled-transaction.json`.

The matching normal-speed NTSC cohort also passes all 12 cases. Settled
40-column time is 203,915–205,245 cycles, 60-column time is
397,662–403,870, and 80-column time is 320,381–323,205. Publication is followed
by a constant 104-cycle quiescence tail with no parser or overlay work. The
complete oracle and screenshots are in
`agentsworking/evidence/M8/20261027T130055318500Z-display-timing-styled-grid-convergence-baseline/normal-speed-ntsc-styled-transaction.json`
and its sibling `ntsc-styled-transaction-contact-sheet.png`.

### Deletion-only transaction cleanup

The next pass removes state and branches whose values are invariant in the live
row transaction. `LT_CLIP` was always zero, so its stores, 16-bit additions and
carry refusal are gone. Success no longer normalizes unused `A`/carry values or
rewrites `se_st_cp_valid` and `se_st_request` to values already required by
admission. The styled descriptor update is fused with the authenticated wide
header loops; 40-column mode retains its required local copy because it bypasses
that header path. The orphan `LRV3` magic and geometry constants are also gone.

This deletes 69 linked bytes: 30 executable bytes from `grid`, plus 30
executable and nine read-only bytes from `geostail`. No BSS, zero-page,
resident state, image, bank, catalog entry, load or DMA is added. Focused
insert/delete work falls from 7,327/7,141 to 7,309/7,123 instructions at 40
columns, from 49,754/47,198 to 49,711/47,155 at 60, and from 33,529/32,723 to
33,486/32,680 at 80. This is a small hot-path saving coupled to a real code
deletion, with no credit assigned to packaging or overlay placement.

The exact-current D81 is
`b6ceb3089774a55c7be5b9d0396341e6fde0e71b303b32aeabdd8a860af03552`.
The 72-case matrix, all five corruption classes and both cancellation cases pass
at `build/styled-grid-carry-matrix/20261027T132718007905Z/result.json`. The
byte-exact 256-byte header/CRC oracle passes at
`build/lrv-header-direct/20261027T132700114530Z/result.json`, and the focused
consumer and row-relative gates pass at
`build/styled-ticket-consumer/20261027T132708785100Z/result.json` and
`build/lrv-row-relative/20261027T132710997907Z/result.json`. The established
68-byte stack bound remains conservative because this pass only deletes
instructions and checked branches from existing leaves and introduces no call,
push, interrupt or recursion edge.

### Strict 60-column renderer

The 60-column leaf no longer carries the generic 80-column branches and three
per-scanline helper calls. Its strict renderer selects the fragment shift table
once, runs one fused eight-scanline loop, restores the patched operand before
return, and refuses every non-60 mode. It retains the existing 68-byte caller
frame, four borrowed zero-page bytes, full-row bitmap and attribute clears,
fixed font addresses, color arbitration, inverse, selection and caret behavior.

R17 executable code shrinks from 1,266 to 1,205 bytes, freeing 61 bytes before
the fixed `$A800` font. The standalone row differential passes 1,117 valid
cases, 17 shared invalid frames, 32 random fonts, full output poisoning and a
whole-RAM guard. The integrated styled consumer falls from 49,711/47,155 to
47,092/44,796 instructions for 60-column insert/delete, a 5.27%/5.00% cut.
The full 72-case matrix passes at
`build/styled-grid-carry-matrix/20261027T132919561136Z/result.json`; structural
60-column fallbacks also remove about 124,000 instructions. Modes 40 and 80 are
unchanged.

Normal-speed PAL 60-column insert/backspace now settles in 378,794/373,471
cycles for Full and 378,895/373,495 for Markdown. This is 5.27–5.41% faster
than the preceding qualified product. NTSC settles in 381,917/376,750 and
382,157/376,445 cycles, 5.28–5.43% faster. Both 12-case cohorts preserve exact
source, pixels, colors, anchors, history, catalog, payload, stack and shim,
publish once, and perform no parser or overlay work after publication. Evidence
and screenshots are in
`agentsworking/evidence/M8/20261027T133119318729Z-display-timing-styled-grid-convergence-baseline`
and
`agentsworking/evidence/M8/20261027T133313781696Z-display-timing-styled-grid-convergence-baseline`.
The NTSC verifier now selects the native `(32,23)` 320x200 viewport for its
384x247 capture instead of assuming PAL's `(32,35)` viewport.
