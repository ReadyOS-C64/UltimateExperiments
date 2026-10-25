# Private checkpoint pair refresh

Released component candidate; parent owns the common publication hook and
canonical integration. No shared build, canonical edits, new asset/bank, BSS or
ZP. The first and dual checkpoint/consumer namespaces remain immutable.

## Measured stale fallback

`tests/test_geos_semantic_refresh_profile.py` runs30 actual public edit/render
frames: near/far65800, edited row0/1/2, QR/BACK/BACK then CR split. Below-row0
fast publications do not enter C24; both checkpoint keys stayrevision0 while
canonical source reaches4. The far final CR split then costs12394434/2057READs
on row1 and12397544/2058 on row2. Row0 current updates, but the old producer
invalidates an unobserved predecessor after seeded parsing. All frames still
match independent pixels/attributes/allanchors/bottom with canonical/history,
catalog/shim and whole16MiB strict guards. These are CPU instructions only.

## Placement and build

`build-aux.py OUT FROZEN_FIXTURE` reproduces the sealed original C13/AUX2272B
control byte-for-byte, then links optional **AUX op6 at3398B/4096**. It calls
actual R14 normal op0 for FS BEGIN through the resident loader, then resident
FS END. C13→R14 is legal nesting; renderer→command is never attempted. Current
R14/SP2 ops3/4/5 and its3318B budget remain untouched. No49th asset/fourth code
bank is introduced. A first standalone R14 placement3448B was rejected because
its1117B helper cannot coexist with SP2; its proof is retained as historical.

Compile the helper with **GSR_AUX=1**, minimal `editor-api.inc` imports+binding
(as normal GEOS module objects), link it into AUX and regenerate AUX bindings.
Only AUX's entry dispatch gets `CMP#6/JEQ se_gsr_refresh`. Existing ops1..5 and
all source files/functions remain unchanged. Shared builds are parent-owned.
`build.py` is the intentionally oversized standalone R14 comparison, not the
recommended integration command.

The consumer probe copies the immutable4048B C21 into a private build and adds
11B to its no-observed-predecessor path: when TOP!=0, leave the old CRC-valid
previous record intact; at BOF still explicitly invalidate it. This makes C21
4059B on191455. Parent's later style-certificate C21 is14B larger, so expected
4073B must be linked/tested independently. Producer preservation is not itself
authority: selector1 still rejects full-key mismatch. Never resurrect previous
VALID0 bytes by pretending VALID1 for a CRC calculation.

## Exact invocation window and authority

Call AUX6 only after a successful GEOS source publication, after
`se_er_publish_only` has advanced drawsequence, before another input/publication.
The tests call real `f.render()` to completion FIRST, then this separate actual
AUX entry. No resident/publication hook is installed by these private tests.

Entry refuses before phase access unless owner0, mode3, UI0/source presentation,
no fold/wrap/pan state, pending1, GEC_VALID0 (consumed) and GCC_VALID1. Require:

- GCC_SEQUENCE == actual new drawsequence;
- GEC_SEQUENCE+1 == that same drawsequence, no16-bit wrap;
- actual FS BEGIN validates tokens/epochs/full pending gap shape and acquires
  its own counted source lease; END releases only its own count;
- actual canonical graph/gen/visible revision/merged length/epochs/TOP match
  the published GCC key exactly;
- GEC revision+1 == current revision without wrap, oldlength±1 == actual merged
  length, observer op/old/new semantics and exact source bounds;
- GEC position >= TOP, so incoming state at/before TOP is unchanged;
- full current typed FE handle/physical ownership/epoch and nonretired provider;
- both64B records (one at BOF) have V2/VALID1/fullCRC, bound TOP, current
  START==TOP and preceding START<TOP; each fullkey equals exactly authenticated
  OLD (actual immutable key plus GEC oldrevision/length) or NEW (actual source).

The service changes only the seven visible-key bytes, CRC and VALID publication.
Anchors, all six parser carry bytes, TOP and reserved bytes stay byte-identical.
No guessed source offset rebasing or generation/flush rekey. It claims phase4,
initializes its own FS state and invalidates persistent index/nav phase-cache
witnesses before union reuse. Scratch8880..8921 is caller-phase only; protected
8800..887F and source-style FE1600..16FF remain untouched.

Each record is written VALID0, then a final one-byte VALID1. A partially updated
pair can independently retain a trusted current record, but predecessor stays
untrusted until both fullkeys/CRC/VALID agree. Provider failure is optional A0/
Cclear, never failure of the source edit or last complete paint. A1 means the
pair was refreshed. Foreign owner is opaque and returns A0/Cclear.

## Qualification and costs

`tests/test_geos_semantic_refresh_candidate.py --aux` passes30 actual edit/render
frames plus explicit late refresh: unchanged source/caret/selection/history,
independent allpixels/attributes/anchors/bottom, normalized384B catalog and
protected shim. Whole16MiB render guards exclude only precise schema spans;
refresh itself permits only FE0600..067F and checks anchor/carry/TOP immutability.

Far final CR split: row1 render860307 plus7414 refresh, row2 render859771 plus
7413, both2READs. Warm pair refresh costs7296..7431 CPU instructions; warm BOF
single record4748..4887. The first cold AUX admission costs54432..57094 including
actual code verification; it is not hidden in the warm figure. Switching AUX/
R14 also replaces active C/R images; native cycles are required before claiming
end-to-end typing speed. No native process was launched by this lane.

`tests/test_geos_semantic_refresh_faults.py --candidate RUN` passes22 fault/groups:
stale sequence/revision/length/op/byte/epochs/keys/cache handle, editbeforeTOP,
intervening readonlypublication, foreign phase owner opaque, counted foreign
lease, CRC-correct wrongkey/TOP/anchor and actual badCRC. Genuine checked-provider
refusals on BOTH current and previous VALID-last writes leave no false pair;
actual C24 op3 current/previous probes confirm expected trust/miss outcomes.
All source/shim/foreign16MiB remain exact, no provider/parser/loader API weakened.

Cheap optional root gate: lowbyte `(GEC_SEQUENCE+1)==drawsequence` is necessary
for every accepted operation and costs11B (LDA/CLC/ADC/CMP/BNE). It skips ordinary
caret/readonly publications; a256-draw collision may call AUX unnecessarily,
but full16-bit/nonwrap/source guards inside still reject it. GEC_VALID1 gating
would be wrong because successful local paint already consumed it to0.

Limitations: no integrated root callback, native latency or final combined SP2/
style-certificate lifecycle/stack acceptance is claimed. Folded/panned/nowrap,
committed flush/undo/replay and edits before TOP decline rather than broaden
semantic authority. Parent owns those routes and final qualification.
