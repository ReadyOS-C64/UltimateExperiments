# Current performance

Repeated eligible semantic reuse now takes6.48–6.94million PAL cycles for four
successive ordinary insertions and hot-window flushes after an8KB retained code
BODY. The committed010fb03 control takes9.84–10.04million:30.9–34.1% fewer cycles,
with all four paired screenshots exact. C41/R34 preserve the retained BODY and
reparse only the changed ordinary line (23–26 actual SuperMark feeds). The
source/observer guard is renewed at each yield; up to four typed R34 operations
share a synchronous call. This removes98 loads compared with the initial
unbatched candidate; the final80/81 loads still exceed the control36/37.

| Native PAL repeated edit+flush+repaint | Control | Registered rebase |
|---|---:|---:|
|1|10,044,655|6,939,745|
|2|9,838,779|6,484,229|
|3|9,848,966|6,497,863|
|4|9,863,435|6,512,032|

These are real ROM File/Open/IRQ setup and the disclosed public-input/command
PC/SP stopwatch seam, not physical-key timings. At1MHz the operation still takes
several seconds. The path accepts a narrow flags5 graph and an insertion after
unchanged retained code; general edits and layout retention remain open. See the
[authority, bounded batching and qualification contract](../src/cache/edit-rebase-integration/README.md).

Eligible ordinary GEOS Plain rows now use the existing certified local typing
transaction. In paired nativePAL cases, INSERT improves2,264,434→512,064cycles
(77.4%) and BACK2,254,299→180,750 (92.0%); overlay loads21/22→3/4. All four paired
screenshots are exact. Same-input Full controls remain essentially unchanged.
The46-frame/8-fault CPU matrix, all60-image stack analysis, eight native captures
and precise REU/source/history/font guards pass. C6 and the resident are
unchanged; R30/C32 grow6/34bytes. This optimizes eligible ordinary rows, with
general GEOS reflow still open. See the [admission, timing scope and reproduction
contract](../src/render/geos/style-typing/README.md).

Plain60/80 Return splits and BACK merges now use one R29 transaction when the
complete affected logical paragraph is visible. Eight paired nativePAL cases
improve38.1–39.9% at60 and20.4–22.4% at80, with identical screenshots and overlay
loads9→4. These cases take1.02–1.45million PAL cycles; broader responsiveness
work remains open. Styled, selected, folded and unknown offscreen contexts
retain the ordinary renderer. See the [newline transaction](../src/render/grid/cr/README.md).

| PAL operation | Control cycles | Current cycles |
| --- | ---: | ---: |
|60 short split / merge|1,917,609 /1,862,580|1,187,255 /1,145,053|
|60 wrapped split / merge|2,420,160 /2,391,957|1,453,920 /1,438,077|
|80 short split / merge|1,375,897 /1,316,037|1,068,295 /1,022,135|
|80 wrapped split / merge|1,506,726 /1,476,201|1,192,321 /1,174,858|

These compare the committed944a3e7 control with the actual cold60-image
registered product, using ROM File/Open, public`syntax plain` and the disclosed
PC/SP/public-input-to-quiescent-scheduler stopwatch seam. They include IRQ/VIC/
REU activity and do not measure physical keyboard latency. Every native VIC
pixel, source, sealed catalog asset, settings, reserved1KiB and read-only D81
passes the independent checks. CPU32paired cases separately improve29.4–38.1%
at60/18.7–26.0%at80; instruction counts are distinct from these PAL cycles.

Plain60/80 physical-row insertion/removal separately improves43.9–57.5% in paired
nativePAL cases, with identical screenshots and nine overlay loads. The tested
wrapped physical-row moves take about0.8–1.0seconds. See the
[geometry measurements and contract](../src/render/grid/geometry/README.md).

Same-call lexical batching separately improves retained-code warm PAL repaint
by6.25% BASIC/6.06% assembler. It preserves286 loads and increases per-call
work; long-page responsiveness remains open. See the
[exact paired scope](../src/cache/lexical-batch-native-probe/README.md).

The latest qualified80-column raster skips ink counting and color arbitration
when every effective role is normal. NativePAL short-row insertion improves
255,925→226,807cycles (11.38%) and BACK255,319→226,366 (11.34%), with four overlay
loads unchanged and identical screenshots. Wrapped-quote typing remains
essentially unchanged at365,145/368,335cycles. This is an ordinary-row improvement;
whole-editor responsiveness and large GEOS work remain open. See the
[implementation and exact qualification](../src/render/grid/probes/normal-row80/README.md).

These measurements compare the946e7d3 control with the same59-asset product plus
R16 and its genuine R25/C33 CRC witnesses. They use public `syntax plain`, ROM
File/Open and the documented PC/SP/input-entry stopwatch seam, not physical-key
latency.934component rows plus17invalid inputs per variant,40 public comparison
frames,20 wrapped frames,24 refusals, canonical editor/cache and complete68-byte
relative stack checks retain their exact scopes. Normal componentrows use30.77%
fewer instructions; mixed-role fallback costs1.36% more at that component level.

## Earlier54-asset checkpoint

The earlier cache-redesign runtime is `69720da`, with 54 assets, resident
`a2578487c8a5` and D81 `2ffdb2fc95b1`. Its diverse-document full GEOS repaint
was measured at 10,150,476 PAL cycles in Full and 9,629,277 in Markdown. All
eleven native display captures match the reviewed images. Full still exceeds
the older 9,511,774-cycle path by 6.7%; performance qualification remains open.
These timings were captured on `4c25480`; the subsequent C19 pressure fix
changes only fold allocation and is qualified separately below.

A separate native control loads a 4,102-byte document through File/Open: a long
bold span followed by a short paragraph. These public commands include actual
navigation and repaint, after the semantic baseline has been built:

| PAL command | Control cycles | Current cycles | Loads, control → current |
| --- | ---: | ---: | ---: |
| Markdown bottom | 306,428,091 | 4,087,703 | 577 → 32 |
| Plain bottom | 14,247,606 | 14,229,896 | 176 → 176 |
| Markdown top | 28,352,606 | 22,550,943 | 243 → 249 |

The actual dispatcher trace changes from 13,598 C26 requests and 223 C24
requests during styled bottom to two C26 requests, fifteen bounded C35 steps,
and no C24. The unfolded jump queries its target's retained block state and
starts measuring at that block's logical start. It skips preceding blocks;
softwrapped rows inside the target block still require measurement. Ordinary
UP/DOWN/PAGE/PAN and cached geometry retain their existing paths. All three
current images match the control byte for byte. Bottom improves 98.7%; Top
improves 20.5% despite more loads. Cache hits and parser-feed counts cannot
replace end-to-end timing.
The measurements use the documented public-input PC/SP seam and include
IRQ/VIC/REU activity; they do not measure physical keyboard latency. All three
images, source/history/clipboard/settings, retained typed-cache bytes and the
full REU outside checked renderer storage pass verification.

R21 now intersects the glyph's vertical clip interval once per strip rather
than testing it on every scanline. The same packed-cold control improves from
10,286,041 to 10,150,476 PAL cycles (1.3%) with identical pixels and 149 loads.
The payload remains 4,094 bytes; fixed font data stays identical. Component
coverage includes 2,570 vectors, 65 faults and 720 legal vertical intersections
per side. This improves raster work without claiming to solve overlay traffic.

The latest C19 fix adds 99 bytes and no resident state. Fold allocation retries
once after retiring the optional checked type53 cache, only for actual object
catalog or provider exhaustion. All 28 fold scenarios, 14 allocation and
ownership cases, five editor scenarios and the 68-byte stack bound pass.
A new native Copy/Cut/Undo gate checks three frames, 192,000 VIC pixels,
exact source/clipboard/folds, all 54 assets and the 1 KiB reservation.
TRIED remains set after retirement, so automatic
cache rebuilding stays deferred; normal parsing continues.

Current evidence: `agentsworking/cache-raster-vertical-checkpoint.json` and
`agentsworking/cache-fold-pressure-integration-checkpoint.json`. The native
pressure captures completed successfully; a host module-alias error was repaired
offline against those same captures, with the failed log retained.

Historical navigation integration evidence: `agentsworking/cache-navigation-integration-checkpoint.json` and
`agentsworking/evidence/M8/20261026T045738645714Z-navigation-cache-integration`.
The control archive retains an initial host-evaluator capture-name error and
its repaired offline verification. The new production run passes directly.
Packaged navigation56, parser bypass55, incremental15, stack68, editor5 and
foreground2 pass. Retained lexical colors and edit-aware semantic rebasing
remain private experiments; these measurements do not include them.

## Earlier 48-asset checkpoint

D81 `dbc4ecf968ab`, unchanged resident2d87e75e/48assets. geoWrite-style
complete logical-line convergence and source pixel batching are integrated.
The goal remains active; these are incomplete performance improvements.

| Current PAL operation | Cycles |
| --- | ---: |
| Diverse GEOS heading-inline INSERT /BACK |2,557,495 /2,011,074|
| Fresh GEOS diverse TOP0 repaint |9,500,660|
| Ordinary heading insertion |2,206,795|
| Source60 /80 mixed fallback typing |10,557,053 /7,845,115|
| Warm RIGHT40 /60 /80 |12,916 /132,700 /137,077|
| GEOS warm LEFT, zero loads |36,670|
| Preview first /unchanged repaint |7,894,608 /142,368|

The isolated line-convergence A/B changes the diverse INSERT from9,814,874
to2,551,898cycles with identical pixels; the combined current value above
includes separately improved C20. Source paragraph native12 on0340 shares
exact current C14/R14/C33/R25: long60 .920–.935M, long80 .841–.859M cycles.

Regressions are retained: fullTOP0 is slower than6604's9,077,527PAL; ordinary
heading typing is slower than1,984,869. Isolated carry/wrap fallback adds
247,318/116,357cycles. PAL32 pixels exactly match6604; fresh NTSC32 passes with matching320x200 crops.
An earlier preview-page failure during host ENOSPC is retained; cause not assumed.
Fresh fullTOP0 NTSC is9,579,924cycles. Do not treat these changes
as general typing/usability closure or a geoWrite speed benchmark. Reuse still
requires a complete single-visual-row logical line; wrapped convergence is
private work. Screenshots, exact-build scope and receipts are in STATUS.

## Historical6604 measurements

Earlier D81 `66045b585ddb`, resident `2d87e75e`,48 assets/three asset banks.
The standalone goal remains active: full redraws and several editing paths
still miss the responsiveness targets.

| Actual operation | PAL cycles |
| --- | ---: |
| Fresh GEOS diverse page, TOP0, warp off |9,077,527|
| Same TOP0 at preceding e34 checkpoint |10,365,612|
| Warm RIGHT,40 /60 /80 columns |12,662 /132,630 /136,879|
| GEOS warm LEFT, no overlay loads |36,671|
| GEOS first RIGHT, one optional AUX load |41,274|
| Diverse GEOS heading insertion |1,984,869|
| First formatted preview |7,884,262|
| Unchanged preview repaint |141,892|
| Mixed source60/80 insertion, settled |10,831,796 /8,119,655|

Fresh TOP0 is about12.4% faster than e34, but remains roughly nine seconds at
normal C64 speed. NTSC is9,152,893cycles. Matrix full paint uses TOP318 and
costs3,731,541PAL: it must not be compared as the same page. The measured private
fixed-shift change alone contributed only0.26%; avoiding repeated glyph/frame
work and style parsing accounts for the larger combined improvement.

The source60/80 mixed fallback above regresses from roughly9.46M/6.75M before
SP2. Its new complete-paragraph authority checks cost work even on rejected
paragraphs; reducing that cost is active work. Eligible long wrapped prose now
uses a bounded pixel/packet transaction, around0.9–1.0Mcycles in the exact a6fa
native8 proof. Its C14/R14/R25/C33 images are byte-identical in current6604;
only the GEOS C20 worker changed afterward. That is still not ordinary typing
performance. Markup, selections, folds and geometry changes use checked fallbacks.

C20 reuses its completed output in C21, and retains a160-byte style window during
a line job. Current-binding CPU A/B versus the first certificate saves1.44% on
mixed422,6.03% on inline406 and26.94% on long styled863. Styled wideW200 costs
3.52% more; short cases add less than0.07%. Source reads, full-body delimiter
semantics and source identity checks are preserved. There is no cross-line-job
style reuse yet. CPU instructions are not native cycles or DMA byte totals.

Actual after-publication parser-checkpoint refresh prevents repeated lower-row
edits from aging otherwise useful incoming state. The73-frame public test plus
256 readonly publications verifies refresh, rare lowbyte collision, missing
workers and actual Undo recovery. Full16-bit/source/CRC checks remain inside
AUX; the lowbyte resident gate is never treated as authority.

Current public15/inline19/fold28/capacity12/recovery22 and PAL32+NTSC32 pass.
All32PAL PNGs match reviewed ancestors; NTSC active crops equalPAL. Full48-image
stack remains77/minSPB2 and forced66-output rebuild is byte-exact. Focused
normal-speed intervals bracket warp-off monitor witnesses; boot/setup retain
warp and drive traps. Public-entry PC/SP stopwatch seams include real scheduler,
IRQ,VIC and REU costs, but do not measure physical keyboard latency.

Evidence: `agentsworking/evidence/M8/20261025T205616461479Z-combined-style-refresh-production/manifest.json`.
Final combined lifecycle, media, REU-pressure and gallery acceptance remain
pending alongside responsiveness work. Historical proofs retain their scope.

## Previous renderer checkpoint

Current48 renderer build: resident `b33cc41e`, D81 `57be0ca4350b`,48 assets.
Strip clipping, bounded packet gathering and removal of unused row snapshots
are promoted. No extra REU bank, resident state or zero page is used.

| Same diverse document / operation | PAL cycles | Loads |
| --- | ---: | ---: |
|40-column RIGHT|12,900|0|
|60-column RIGHT|134,657|2|
|80-column RIGHT|138,740|2|
|GEOS heading-prefix insertion|2,315,926|17|
|GEOS fresh full page, TOP0 / warp on|11,262,377|118|
|GEOS fresh full page, TOP0 / warp off|11,262,403|118|
|GEOS fresh full page, TOP318|4,614,962|50|
|First formatted preview|7,771,315|67|
|Unchanged preview repaint|139,978|5|

TOP0 full paint improves about8.1% from the same12.258M-cycle viewport in
the preceding checkpoint. TOP318 contains different content and is not its
comparator. Focused NTSC TOP0 is11,355,937 cycles with warp on versus11,355,981
with warp off. Each normal-speed interval has two actual monitor witnesses
that warp is off; setup/boot use warp and drive traps. Timing runs preserve
the disclosed public-entry PC/SP seam and actual IRQ/scheduler/VIC costs.
They do not measure physical key latency or accelerated hardware.

All64 packaged PAL/NTSC native images match reviewed ancestors/active crops.
Actual CPU heading72, boundary136 and recovery/history gates preserve source,
fonts, pixel/color output and checked REU ownership. Current full stack remains
77bytes/minimumSP B2; forced rebuild reproduces65 outputs byte for byte.

General60/80 typing, GEOS fullpage/CR/softwrap reflow and far-prefix navigation
remain slow. The private short-prose typing and further raster-loop candidates
are not production claims. Lifecycle/media/capacity evidence is inherited in
its declared unchanged-contract scope. Evidence:
`agentsworking/evidence/M8/20261025T182719631618Z-renderer-production/manifest.json`.

## Historical combined48 before renderer deltas

Current48: resident `b33cc41e`, D81 `da5f2235a110`,48 assets. The integrated
build combines retained60/80 caret deltas, heading-body row rebuilds and exact
shared-tile color election. Measurements are emulated C64 cycles including
IRQ/VIC activity, with warp/traps enabled and a disclosed public-input PC/SP
stopwatch seam. They are not physical keyboard latency or hardware acceleration.

| Integrated diverse document, PAL | Cycles to settled idle | Loads |
| --- | ---: | ---: |
|40-column RIGHT |12,899|0|
|60-column RIGHT |134,442|2|
|80-column RIGHT |138,745|2|
|GEOS RIGHT after mode entry |41,245|1|
|GEOS sustained RIGHT |36,504|0|
|GEOS full top page, TOP0 |12,257,971|118|
|GEOS heading-prefix insertion |2,506,384|17|
|First formatted preview |7,771,418|67|
|Unchanged preview repaint |140,194|5|

The preceding60/80 RIGHT costs were875,167/795,756 cycles on the same source.
C33 now changes only certified caret/selection cells and status. Its private
native29 and timing10 additionally cover cross-CR movement, selection, menus,
File owner/STOP and folded planning; source40 retains zero-load navigation.

Private exact-algorithm qualification measured heading-body insertion in the
422-byte diverse document at12,450,919→2,428,706 cycles, and BACK at
12,318,033→2,296,549. Natural prose below a heading measured247,704 cycles
with no overlay load; a longer pangram340,239. These private measurements have
separate identities; the combined48 CPU gates verify integration. Unsupported
color-winner changes and the minority-color counterexample still use full
rendering. General CR/softwrap reflow and long-prefix parsing remain slow.
The heading candidate also adds about458k cycles to one measured new-wrap
refusal; correctness holds, but that regression remains optimization work.

Current packaged PAL32+NTSC32 pass64 independent native images/4.096M pixels;
all PAL images equal reviewed predecessors and NTSC active crops equal PAL.
The original matrix's source-GEOS `m3-full` retained a caret-cache hit: its
38,893-cycle cost is not full paint. The canonical benchmark now invalidates
the authenticated GEOS bitmap/edit witnesses and width before source full paint;
focused corrected PAL/NTSC measurements are12,257,971/12,360,021 cycles at
TOP0. The earlier4.915M full figure used TOP318 and is a different viewport,
not a before/after comparator. Preview hit remains a
separate operation. Forced rebuild reproduces65 existing outputs exactly.
Evidence: M8/20261025T171958460619Z-combined48-production.

## Historical47 span-color checkpoint

Historical47: resident `4e64d113`, D81 `ed098bf5c005`, 47 assets. These are
emulated C64 cycles with IRQ/VIC activity, warp and drive traps. Timing uses a
disclosed public-input PC/SP seam through real foreground quiescence; it does
not measure physical keyboard latency or accelerated hardware.

C14 source coloring now seeks visible row intersections instead of scanning
all screen cells for every span. The promoted payload is4047 bytes (+124),
with no new state. Exact actual-root and native A/B checks preserve all colors,
source/history/REU and ownership behavior. Settled PAL costs on the same edit:

| Source mode | Before | After |
| --- | ---: | ---: |
|40 columns |11.551M|2.947M|
|60 columns |22.340M|9.463M|
|80 columns |23.726M|6.750M|

The first publication is essentially unchanged; these figures measure less
background styling. The current packaged PAL+NTSC32+32 also passes64 frames,
with unchanged reviewed raster output. All64 existing build outputs reproduce
exactly. Evidence: M8/20261025T162303429392Z-style-span-production and
M8/20261025T161651340930Z-style-span-editor-candidate.

The local GEOS styled-edit numbers below retain their measured893dc fixture;
its R30/C32 and all other46 assets are byte-identical to currented098. C14 does
not participate in those local GEOS transactions.

| Current shared styled/plain document | PAL cycles | Overlay loads |
| --- | ---: | ---: |
| Cold first bold insert |608,368|1|
| Italic insert after font-window refill |491,298|1|
| Combined insert with retained staged code |193,007|1|
| Bold / italic / combined BACK |170,137 /152,119 /157,164|0|
| Plain BACK |152,849|0|
| Wide bold W insert / BACK |179,811 /152,552|1 /0|
| Wide combined M insert / BACK |192,814 /157,862|1 /0|

Both PAL and NTSC pass all12 captures and six complete16MiB/source/history
intervals; all current PAL PNGs match their individually reviewed same-document
predecessors. NTSC active pixels match PAL. C32 splits advances8–11 into one
byte plus0–3 bit shifts. This adds149 bytes/no state. Warm wide deletion saves
19.2k–26.7k PALcycles; cold prime adds about13.7k, while narrow edits are nearly
flat. These costs include staging and validation rather than just the shift loop.
Evidence: M8/20261025T140416711643Z-style-typing-profile-native and
M8/20261025T140623218510Z-style-typing-ntsc-native.

The current full32 PAL+NTSC matrices also pass64 independent captures. The
corrected fresh-page seam measures source-GEOS full paint at4,915,488 PALcycles;
clearing only the old grid-valid bytes previously allowed a38,741-cycle caret
cache hit, which must not be called full paint.

| Current diverse workload | PAL first publication | PAL settled idle |
| --- | ---: | ---: |
|40-column insertion before heading |279,733|11,551,172|
|60-column warm RIGHT |875,368|875,476|
|80-column warm RIGHT |795,995|796,103|
|GEOS fresh full paint |4,915,488|4,915,572|
|GEOS mixed prose insertion below heading |2,666,197|2,666,281|
|GEOS heading interior insertion |12,328,587|12,328,671|
|GEOS CR line split |12,159,611|12,159,738|
|GEOS real softwrap314+8→322pixels |7,764,343|7,764,427|

First publication and settled styling are separate: input may be processed
while background styling progresses, so these are not interchangeable with
physical key latency. The60/80 caret rescan and slow GEOS structural paths are
remaining implementation problems. The mixed-prose target is itself plain;
a colored heading shares its physical8px tile band. Its fallback preserves
minority-color correctness; simply removing that guard would reintroduce a
proved wrong-color regression. A bounded color-vote repair is future work.

All-mode measured intervals total651 loads,29,609 overlay calls,3444 DMAs and
2,660,651 DMA bytes per standard. These are sums of32 measured windows,
excluding setup/boot. Full tables, exact IRQ/trap/seam/guard scopes and reviewed
image ancestry: M8/20261025T142349107759Z-current-all-mode-timing.
Diverse7: M8/20261025T141546628739Z-display-timing-pal. Real softwrap:
M8/20261025T141826196287Z-display-timing-pal. Native source/asset/pixel guards
are retained; those gates do not assert arbitrary whole16MiB immutability.

The immediately preceding D81 `46b137568169` has the same resident and45
identical assets; only `gtype`/`type` differ. Its unchanged-renderer measurements
remain scoped to that disk:

| Event on diverse document | PAL cycles | Loads |
| --- | ---: | ---: |
| Warm caret left |36,501|0|
| Unchanged preview repaint |140,035|5|
| First preview |7,769,787|67|
| Return to previous preview page |6,758,066|67|
| Single alpha before a complete heading |2,411,793|17|

Warm caret updates old/new tiles and one status row. Certified typing shifts
only its row suffix; code edits repaint a complete short row with the actual
lexer. Neither requires a full page. Narrow heading transitions rebuild the
actual changed row before reusing the tail; general structural edits still
use checked full reflow. First preview and general reflow remain slow.
Current all-mode scrolling/full-redraw and diverse reflow costs are measured
above; end-to-end file open/save costs are recorded below. No universal latency bound
or completion of the provisional frame/redraw targets is claimed.

Managed preview-body reuse cut an unchanged repaint from1,488,860 to378k cycles;
chrome batching then cut378,176 to140,035. Body/source/settings/font/fold/FE
guards remain, and checked writes revoke before hardware publication. R23 caches
compact BSW9 glyphs in4160 bytes of the existing typedFE tail; immediate wrapper
fetch reuse retains the guarded direct API. First preview fell8.51M→8.01M
before chrome batching. Early FE allocation was deferred because empty/short
pages regressed despite some larger-document gains.

Chrome rows0/1/24 use three checked row calls instead of120 cell calls. Popup
rectangles retain the cell API. C16=4096/R27=4053; no new BSS/ZP. STATUS adds167
modeled instructions, a small caret regression (36,021→36,501 in the measured
PAL fixtures). Source/history/16MiB/stack/shim guards remain. Preview evidence:
M8/20261025T135131738122Z-display-timing-pal and
M8/20261025T135321963581Z-display-timing-ntsc.
The full scoped checkpoint, including reproducible64-output build and native
gallery43/F8five/lifecycle6 ancestry, is linked by
`agentsworking/byte-render-checkpoint.json`.

The following earlier measurements retain their historical identity.

Latest47 local-style increment: resident `d69f4f0f`, D81 `a49e46c559e0`.
The following newer measurements use one shared styled/plain document and
supersede only the corresponding local-typing results, not other workloads.

| Actual event | PAL cycles | Overlay loads |
| --- | ---: | ---: |
| First bold insert, cold R30 and staged capsule |601,770|1|
| Italic insert after a font-window refill |484,149|1|
| Combined-style insert with retained staged code |212,508|1|
| Bold BACK |189,446|0|
| Italic BACK |193,518|0|
| Combined-style BACK |204,063|0|
| Plain BACK in this shared fixture |172,687|0|
| Wide bold W insert/BACK |199,302 /191,870|1 /0|
| Wide combined M insert/BACK |212,329 /204,051|1 /0|

These12 native frames pass exact source/history and six full16MiB intervals.
All images are byte-identical to the individually reviewed preceding47 frames;
the new bold/combined images were also directly viewed. Evidence:
`agentsworking/evidence/M8/20261025T115900566566Z-style-typing-profile-native`.
C6 currently requires an unchanged alphabetic line opener and certifies
conservative alphanumeric interiors; a line beginning with a style marker can
still use the slower fallback. R30 authenticates and runs a
C32 transaction from5000. It uses real bold/italic ink and updates full packet
styles/X geometry. Each admitted edit patches its row, with no page, semantic,
inline, source-provider or raster producer calls. Spaces and markup edges can
still fall back; this is not a universal latency bound.

The22-byte suffix-bounds optimization cuts warm styled BACK from238–279k to
189–204k cycles on the same fixture. It preserves unused-tail clearing and
shared-tile color checks. Further transfer and preview work remains private.

The following managed46 measurements remain exact historical comparisons.

Measured in native VICE with IRQ/VIC activity, warp and drive traps. These are
emulated PAL C64 cycles to completed bitmap, attributes and status, not physical
keyboard latency or accelerated-hardware measurements. Current build:
resident `bdef9dd0`, D81 `b3813f5d4fae`,46 images.

| Operation and workload | PAL cycles | Overlay loads |
| --- | ---: | ---: |
| Warm GEOS caret LEFT, diverse422-byte document |35,984|0|
| First caret RIGHT in that profile |40,317|1|
| First ordinary insert,61-byte/four-row document |454,941|1|
| Warm ordinary insert, same document |189,316|0|
| Warm ordinary BACK, same document |186,450–206,496|0|
| Insert/BACK in its second row |205,072–212,972|0–1|
| First BASIC string insert, direct R31 |641,460|1|
| BASIC string BACK, direct R31 |128,829|0|
| Assembler comment insert/BACK, direct R31 |407,265 /111,692|1 /0|
| BASIC number insert/BACK after retained stage |116,768 /111,714|1 /0|
| Structural/styled insert requiring full redraw, diverse document |13,711,876|120|
| First formatted preview, diverse422-byte document |8,756,113|67|
| Next preview page |7,737,297|77|
| Return to first preview page |8,299,256|67|
| Unchanged preview repaint using body cache |1,488,845|5|

Warm caret updates only old/new caret tiles and the single status line. Ordinary
admitted typing shifts the affected bitmap suffix, updates its row packet and
later source positions, then updates caret/status. It does not run the source,
semantic, inline, page or raster producers. Current plain timing includes the
neighbor-role guard: every glyph intersecting the physical tile bands must be
plain before colors can remain unchanged. A white displayed attribute alone is
insufficient. Other cases retain the checked color-voting fallback.

R31 recomputes a complete short aligned BASIC/assembler row using the actual
lexer and native8 painter in sealed C31 code at `$5000`. Warm edits retain it.
The six-case profile deliberately includes different first-use states: its
BASIC-number insertion benefits from a previously verified overlay and retained
staged code. It is not a universal cold-load result. All six actual publications
match independent full pixels, source/history and complete REU guards.

The editor now remembers verified immutable overlay assets and copies warm
images directly to their execution slots. This removes repeated payload CRCs
and preserves the font window. Imports/unverified loads still check fullCRC;
every entry checks its resident binding. Checked code writes, provider changes
and fresh resume revoke verification. The generic loader remains strict.

On the same preview fixture, first preview improves from21,689,902 to8,756,113
cycles (60% reduction); unchanged repaint improves from2,462,433 to1,488,845
(40%). The screenshots are byte-identical to the previously reviewed images.
This is useful progress, but a roughly8.9-second cold preview at standard PAL
speed and the structural redraw above remain performance blockers. Warm plain
editing is roughly0.19–0.21seconds; it also exceeds the original provisional
six-frame typing target. These scoped improvements do not close M8.

The body cache stores7040 bitmap bytes and880 attributes in the existing typed
FE allocation. It verifies source/settings/folds/fonts/provider context and
full bodyCRC before two live display DMAs; no semantic/inline/lexer/font worker
runs on a hit. The retained font fast path relies on the actual checked window
capability, not the number of unrelated overlay loads.

Evidence:

- `agentsworking/evidence/M8/20261025T112838129760Z-display-timing-pal`: seven
  preview/caret/structural publications and cost profiles.
- `agentsworking/evidence/M8/20261025T112849904736Z-incremental-profile-native`:
  six ordinary edits, paired full16MiB REU intervals and source/history checks.
- `agentsworking/evidence/M8/20261025T113512024238Z-code-typing-profile-native`:
  six BASIC/assembler edits, three paired whole-REU intervals.

Every listed screenshot was visually inspected. Native timing enters the public
foreground service through a disclosed measurement seam; separate lifecycle and
editing automation proves actual IRQ-delivered typing. CPU pixel gates compare
the optimized editor with a forced actual full renderer and an independent
source/font oracle. Physical keyboard and Ultimate acceleration remain separate.

## End-to-end file costs on current893dc

PAL modal Open422B settles in12,444,142 cycles; SaveAs423B in14,478,856;
a separate fresh-process reopen423B in12,446,796. Their first publications
are about1.20M/3.21M/1.20M respectively. Settled costs include rendering and
background styling; these are not isolated IEC transfer rates. Exact saved
SEQ bytes and fresh reopened source agree, alongside independent native pixels,
owned catalog/payload/fontpack/history/savepoint/shim/lowerstack/probe guards.
The read-only reopen disk is unchanged. Warp and device8 traps are enabled;
PAL VIC0/50Hz resources and a16-cycle calibration are retained. Evidence:
M8/20261025T142629350991Z-file-throughput-native. No physical latency or
worst-case claim is made.

## Warm GEOS byte shifts on the registered62 editor

A bounded bitmap suffix change removes the second neighbor from1..7-bit shifts
and performs an8-bit insertion shift as a byte displacement before its0..3-bit
remainder. The payload is3 bytes smaller (C32 raw3771, sealed3803); R30 remains
3662 bytes with updated stage length/CRC constants. Admission, color voting,
source/history certificates and publication checks remain in place.

Actual PAL native measurements through the disclosed public service PC/SP
stopwatch, with IRQs running:

| Case | Control cycles | Optimized cycles |
| --- | ---: | ---: |
| Plain steady INSERT |175856–175890|169637–169888|
| Plain BACK |170707–170928|164599–164621|
| Full strong steady INSERT |186356–189569|178295–181178|
| Full strong BACK |181049–184271|173407–176108|
| Plain first INSERT |717300|711039|
| Full strong first INSERT |515393|507786|

Steady keys improve3.4–4.4%; first insertion improves0.9–1.5%. Caret code is
unchanged and its IRQ-phase variation includes a0.6% regression. The48 native
captures have24 byte-identical control/candidate PNG pairs and8 distinct images,
all visually reviewed. Both packages retain actual cold62 registration, fonts,
source/history, settings, clipboard, the reserved shim, and precise whole16MiB
REU checks. The provider is explicitly configured as256 banks. These timings
measure service cost rather than physical keyboard latency.

The native pair keeps the same earlier C41 in both variants. The combined
7654 correctness fix plus new TYPE/GTYPE pair is separately authenticated and
passes canonical rebase protocols/faults, real24-COW journal boundaries, public
pixel/authority gates, complete62-image stack analysis and no-op build checks.
Only those two packaged images differ from7654. Evidence: native
build/warm-shift-native-adapter/ready8 and canonical
build/warm-shift-canonical-{protocol,guards,journal,stack}; source-matched working
fixture build/warm-shift-canonical-working-v2/20261027T001110182649Z/fixture.
The provisional overall latency targets and broad redraw gate remain open.

## VIC scatter in groups of eight columns

A second warm-typing change replaces40 pointer updates per raster line with
five8-column groups. It retains all40 writes, nine raster lines, original tail
zeroing, caret-free base, color rules, source certificates and publication order.
The staged payload grows53 bytes to3824 (sealed3856); R30 remains3662 with its
regenerated length/CRC witness. No state, allocation or overlay is added.

Actual native PAL service measurements, committed1612523 control versus the
coherent two-asset candidate, both with the corrected C41:

| Case | Control cycles | Optimized cycles |
| --- | ---: | ---: |
| Plain steady INSERT |169627–169856|163818–163859|
| Plain BACK |164597–164622|158693–158927|
| Full strong steady INSERT |178297–181173|172983–175726|
| Full strong BACK |173393–176320|167661–170640|
| Plain first INSERT |710767|709393|
| Full strong first INSERT |507786|506770|

Steady keys improve3.0–3.6%; first insertion improves about0.2%. Caret code
is unchanged; three measured caret intervals regress by1/6/4 cycles, retained
as IRQ-phase variation. All48 actual captures agree with independent native
pixels and24 paired activeRGB comparisons. Their eight distinct PNGs hash
exactly to previously root-reviewed originals. Configured provider256 and tight
whole16MiB guards, font/catalog/source/history/shim and actual stage capability
checks remain. Source-rebuilt coherent D81 matches the canonical package byte
for byte, not merely its logical files. Native evidence:
`build/vic-stride-probe/native-ready3`; CPU differential/negative evidence:
`build/vic-stride-probe/receipt.json`. General redraw and latency targets remain
open. CPU instruction savings4.48–5.18% are deliberately separate from native
cycle savings3.0–3.6%.
