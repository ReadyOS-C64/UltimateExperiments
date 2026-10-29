# Private batched GEOS chrome rows

No production/sharedbuild/native changes. `build.py OUT IMMUTABLE_FIXTURE`
reassembles actual controls byte-identical (R273933/C164095 when thirdargument
`control` is supplied), then builds the candidatepair R274053/C164096 with no new
BSS/ZP. Residentbinding generation and SEOwrapping remain actual. `integration.patch`
is the precise released source delta against immutable131207; parent owns promotion.

R27 opcode4: owner0/1 only, overlay_frame+1 physicalrow0/1/24. Each accepted call
consumes40existing logicalmatrix/color cells and writes thatrow's320bitmapbytes
plus40attributes. Font is existing native4800/inversehighbit, background6, lower
color nybble; no phase/source/REU access. InvalidrowA90/Cset orforeignownerAB2/Cset
before scratch/output; successA0/Cclear. Existing CELL1/rootTRY3/owner4cache APIs
remain. Three UIbytes CFE2..CFE4 within existing declared88-byte GCC/UI extent
are used; no newstate. Nativefont/source/shim/body outside selectedrow unchanged.

STATUS retains shared logicalstatus generation then common glyph/pixel loop.
A directabsolute row24 prefix preserves most of its previous cost: normal4221
→4388instructions (+167); all313status states remain exact. No self-modifying
code. The initial generic row24 version (+487instructions) is retained privately
as caret-ui-general.s and is NOT the released helper.

C16 batches only g_backend27(GEOS) and g_skip0(fullchrome), inside the ORIGINAL
rowloop AFTER its original coordinate calculation. It calls ROWthree times for
top0/1 andstatus24. Popupskip1 retains original per-cell rectangle/skip behavior;
60/80 leaves retain originalcellpath. Existing geometry/refusal checks remain.
Eleven jxx→bxx conversions reclaim33B. Each was assembled and linked against the
actualB000 objects, retaining only actualsize reductions; final4096 image links
with every displacement inrange. short-branches.json/patch and relax.py record
the proof. No TUIshared source change is needed. `short/` contains finalcopies;
finalize-row.s alone lacks the branchsize edits, use integration.patch.

Tests:4609ROWvectors cover all256raw/inverse codes,16colors/40columns/three rows,
owner0/1, invalidrows andforeignowners; eachcall full64KiBRAM +balancedstack/
lower64canary, whole16MiBREU unchanged.313STATUS states pass independentstatus/
fontoracle/fullRAM/stack/REU. Actualpublic68preview A/B allpixels/source/history/
catalog/shim/precisefull16MiB PASS; -117overlaycalls/frame, cached106090→31173
instructions(-70.62%),diverse2304986→2230072(-3.25%). Actualsemantic19 including
GEOSmenus/help/fourmodemoves passes. NEWcurrent4modegate36frames passes body/menu/
help/prompt/Fileowner1/help in0/40,1/60,2/80,3/GEOS plus realF8fourmodecycles both
ways. FiletestholdsproviderbeforeDOS; phase1152exact andUIREUunchanged.

Two historical gridwrapper failures are verifierissues, retained: raw image_slot
comparison didn't mask managedbit2; old F8 expected2→0 rather than current2→3.
We do not weaken those expectations or claim the old gate passes. The newfocused
currentfourmodegate is authoritative. No nativePAL/NTSC speed claim is included;
parent can measure after promotion. AllCPU drawings are exact to independent
models; representative preview/Filemodal images directly reviewed in the archive.
