# Private actual publication-hook composition

The authoritative input is immutable e34:
`build/geos-incremental-editor/20261025T194101943594Z/fixture`.
No canonical files or shared outputs are edited. `build.py` makes a copied
project under build/, replaces all product sources from the input ZIP, and
first reproduces the exact original resident/all48/fontpack/D81. Seeded build
artifacts are only bootstrap inputs; sealed byte equality is mandatory before
any mutation. Build-tool source hashes are recorded. No Git worktree.

## Exact composition and budget

Recommended build command:

`python3 src/editor/checkpoint-refresh-hook-candidate/build.py --base FIXTURE`

Qualified private project:
`build/checkpoint-refresh-hook/20261025T201118482734Z/project`.
Resident2d87e75ed511556c437021bc6919bb2bb78e6acb73f48f3f9f52edfeda9e270c,
bindingbc032951a4ff040b1cd687f8eb175884, D8191f28ea81598 prefix. Actual source
certificate C20=3904, C21=4073; AUX=3398. BSS1533/ZP24 unchanged,48assets,
threeassetbanks. RODATA ends3EF9 (six bytes before CRC table3F00); no ReadyOS
C600..C9FF change. New resident route adds22B, four fixed copies save28B.

Files deliberately changed in the copied project:

- editor/main.s: post-publication mode3 route plus11B lowbyte necessary gate;
- editor/commands.s: four dead-X fixed COPY24 replacements (below);
- overlays/aux.s: optionalop6 -> se_gsr_refresh;
- render/geos/checkpoint/rekey.s: released AUX helper compiled GSR_AUX=1;
- checkpoint/publish.inc: preserve priorVALID1 when not observed/TOP!=0 (+11B);
- source-line/source-inline and three source-certificate includes: released
  current-output style/role certificate, not a new grammar;
- page.s: released14B SC_CONSUME route and include;
- private Makefile: helper object/bindings and exact source dependencies.

The helper must compile with minimal GEOS editor-api imports/binding, not the
broad absolute-alias include: `-D GSR_AUX=1 -I build/geos-prod -I src`.
Append it to AUX_CONTROL_OBJ BEFORE its bindings prerequisites are parsed.
Normal R14ops0/1/2 and separate SP2ops3/4/5 are untouched; actual C13→resident→
R14 BEGIN nesting is legal. No new overlay or bank.

## Resident route

Immediately after `jsr se_er_publish_only`, mode0 still skips overlays; mode1/2
still call C33op0 with A0. Mode3 performs the lowbyte necessary check
GEC_SEQUENCE+1==new drawsequence, then calls AUX13/slot1/op6. Mode>=4 retains
the old no-overlay behavior. Every path returns A0/Cclear as before. AUX failure
is optional retention failure, never rejection of already completed paint.

The lowbyte gate is not authority. The unchanged helper requires exact16-bit
nonwrapping sequence/full source/GCC/typedFE/key/CRC guards and sourceprefix
proof. It runs AFTER publication, so GCC_SEQUENCE==drawsequence and
GEC_SEQUENCE+1==drawsequence. Consumed GEC_VALID is0. A gate requiringVALID1
would incorrectly disable real local edits. Every256 readonly publications can
have a lowbyte collision; the helper must reject stale full sequence.

## Dead-X copy proof

Each original three-byte COPY24 emits18B; replacement indexed loop emits11B:
LDX#2; LDA source,X; STA target,X; DEX; BPL. Four save28B. LDA/STA/LDX/DEX/BPL
preserve carry exactly; the old copy also preserved carry. Source/target spans
are disjoint and the loop direction is harmless. No caller relies on old A/NZ:

- `history`: next LDA se_e_command replaces A/NZ, SEC defines neededcarry;
  se_history_call resets X to slot1 before child invocation.
- `reload`: next LDA#W_LOAD replaces A/NZ; se_hot_call resets X to slot1.
- `@history_done`: next unconditional JMP reload reaches the new reload loop
  then LDA#W_LOAD; no branch observes prior A/X/NZ.
- `@flushed`: same unconditional reload path. The zero-after-load branch skips
  the copy entirely, retaining its old behavior.

New loop labels are local to their original global function scopes. The full
actual selection/history/mode matrix and emitted stack graph qualify the
changed call paths, rather than treating source reasoning alone as proof.

## Gates and limits

`tests/test_geos_checkpoint_refresh_hook.py --project PROJECT` freezes the
coherently packaged project and runs actual public key/render paths. It never
calls AUX from the host or replaces individual SEO bytes. The first68-frame
gate passes near/far row0/1/2 QR/BACK/BACK/CR/read-only, all four modes with
Undo/Redo/reversed selection/copy/paste/restore, plus direct invalidmode>=4
publication seam. Eligible publications enter AUX exactly once; ordinary
readonly publications do not. Pair keys equal current source after each edit.
Independent pixels/attributes/allanchors/bottom, canonical/history/selection/
clipboard/catalog/shim and exact declared full16MiB intervals remain strict.
Narrow allows only its22*240 inputcache plus256B NCheader; source40 is wholeREU
readonly. Dead R28 backup span stays exact in GEOS.

Extended gate adds optional missing AUX/R14 recovery,256 actual readonly
publications to exercise a lowbyte collision, and source40 CPU raster images.
The earlier missing-AUX verifier profiler lookup was corrected to allow an
absent catalog entry; product admission behavior was not changed.

`tests/test_geos_refresh_hook_inline.py` retains original independent inline19
source/styles/navigation/menu/pending/history oracles with full16MiB and the
stricter current FE spans. It passes on the actual composed4073/3904 pair.

All48 staged stack proof passes: foreground52 + one IRQ/NMI16 = relative68,
no new opaque edge, actual C31/C32 byte-identical reassembly and fixed-helper
vectors checked. Matching-new-PRG natural BASIC idle evidence is not yet
captured, so no new absolute77/native/hardware claim. Parent owns native timing,
lifecycle/fullcombined qualification and canonical promotion.


## Released exact qualification

Final public gate: `build/geos-refresh-hook-editor/20261025T202151642919Z`
(73 checked frames plus256 actual readonly publications). Inline19:
`build/geos-refresh-hook-inline/20261025T202121576021Z`. Declared staged stack:
`build/editor-staged-stack/20261025T201638222750Z`. These are actual coherent
product tests; no host refresh calls or individual SEO substitutions.

The92 CPU images have60 unique hashes; all were inspected on three contact
sheets. Menu/help, reversed selections, source40, source60/80 and proportional
GEOS show the expected layout. They are CPU-derived images, not new VICE
screenshots. Exact released recipe/patch and results are archived at
`agentsworking/evidence/M8/20261025T202740138881Z-checkpoint-refresh-hook`.
`ready.patch` is a manual integration recipe against e34, not an instruction to
replace a newer canonical Makefile wholesale. `release.json` records all exact
source/binary hashes and remaining limits.
