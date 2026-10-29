# Exact two-color neighbor admission — private release

This is an executable private candidate, not an installed editor feature. It
adds a sound local path for ordinary plain/styled prose edits below a uniform
inverse heading while retaining the LSN190 minority-color refusal. The earlier
730B conservative helper remains historical and is not linked here.

`build-runtime.py OUT FIXTURE` produces sealed C6/window, R30/gtype and
C32/type replacements without writing canonical sources or shared builds.
Frozen input: `build/geos-incremental-editor/20261025T161722424199Z/fixture`.
The existing R30/C32 and original C6 were independently reassembled byte-exact
against those packaged images before interpreting the minimal changes.

## Actual sizes and interface

| Image | Original | Candidate |
|---|---:|---:|
| C6 window |4084|4091|
| R30 gtype |2073|3651|
| C32 type |3553|3772|
| C32 raw executable/data |3521|3740|

No resident bytes, BSS, ZP, asset IDs or allocations are added. The prior six
JMPs at A020/A023/A026/A029/A02C/A02F stay exact. The seventh JMP at A032 calls
`se_tcb_two_check`. It adds 1575B (1431 code +144 immutable tables) to R30;
three bytes add its vector. The fixed stage stamp remains5FE0.

C6 retains its normal neighbor scan. After the glyph/width prefetch,
CRC-covered certificate byte44 changes meaning from temporary screen code to
`0=existing all-role0 proof`, `1=requires exact color election`. No consumer used
that temporary screen code after prefetch: R30 derives its glyph index from
GEC independently. On scan failure C6 restores its captured row before sealing
the certificate; this is required because the old failure path returned while
GTC_ROW named the offending neighbor. Other mode values decline. **Promote
C6/R30/C32 atomically**: old R30 cannot honor the new conditional authority.

Mode0 preserves the old strict attribute validation and single transform.
Mode1 performs source/packet/font/current guards, then gathers the original FE
base, computes the complete provisional caret-free row with no VIC writes,
and calls A032. A decline happens before GCC/header invalidation or any FE/VIC
publication. On admission the unchanged transaction invalidates its derived
publications, regathers the original base, runs the certified transform and
commits exactly as before. The extra transform is paid only for mode1.

The public `se_typing_patch`/`se_typing_validate` entries still clear their
private mode and apply all old GT_FLAGS=0, geometry/glyph/attribute guards.
New private dry/color entries do not change that direct API. Strict direct
entry behavior passed1456 independent pixel cases and17 malformed-frame paths.

## Exact scope of the election

The caller authenticates full source/GCC/GTC/FE/font authority through the
existing R30 guard. The helper additionally validates header/version/owner,
canonical complete CR/EOF rows, ordered nonoverlapping geometry, pan0/no folds,
uniform role/style/flags, actual native-to-screen conversion, all X advances,
first/tail bounds and unclipped 9px coverage for every intersecting row.
Target: role0/flags0, style0..3. Neighbors: uniform role0/flags0 or uniform
heading role2/flags1. Other mixed roles, native-code overlap, partial/overwide
rows and unsupported geometry decline. Empty vertical gaps must have zero ink.

An unchanged-GG1024-case proof establishes full advance coverage and exact
inverse INK behavior for all128 glyphs ×4 styles ×2 inverse states. Inverse is
already present in GG_INK and therefore in the caret-free FE snapshot. It is
**not** XORed away when counting votes. Selection/caret inversion is excluded.

The helper counts actual white/yellow cached ink outside the edited row and
actual provisional white ink inside it, per affected tile in both physical
bands. Yellow wins nonzero ties, following the real palette priority. It
allows publication only if the winning new attribute equals the existing
attribute; this can be16 or76. Both directions of election change refuse.
The LSN190 white-to-cyan counterexample still refuses before publication.

## Memory and publication scope

Declared helper frame:8A00..8A27 (40B). Scratch:8000..833F, votes8580..861F,
X map8640..8783; provisional row8400..8567 is read-only to the checker.
Authenticated original header90CA..9109 and edited packet8D00..9049 survive.
The foreground pointer loans and existing checked-DMA request fields are
clobbered. Source-cache count is invalidated before a DMA overwrites8000.
No phase lease/source/provider/object/canonical writes are introduced.

Successful commits retain the existing typed FE spans:64B header, edited842B
live packet, following32B prefixes, caret-free **body** bitmap bands. FE status
snapshot bytes are intentionally not refreshed (the existing production
contract); they are not authoritative for current status repaint. The actual
VIC status is updated normally. Before a refusal, none of those FE spans,
attributes, or bitmap bytes changes. Stage-window5000 may change on asset
admission failure and is not a VIC pixel publication.

## Evidence and commands

- `tests/test_geos_typing_color_bound_candidate_public.py`:25 public-root
  events, independent pixels/attributes, actual forced-full packet/header/body
  cache equivalence, source/history, whole64KiB/16MiB guards, Undo/Redo. Four
  missing/corrupt asset failures retain source/pixels/REU and recover+Undo.
- `tests/test_geos_typing_color_bound_candidate_runtime.py`:10 transaction
  frames +21 strict eligibility/source/provider/catalog/corruption faults.
- `tests/test_geos_typing_color_bound_candidate_two.py`:54 actual-source
  election cases +60 malformed/owner/provider faults;48 admitted, including
  six natural paragraph events, stable yellow and bold/italic-heading cases.
  Combined headings decline when the independent election actually changes.
- `tests/test_geos_typing_color_bound_candidate_coverage.py`:1024 actual GG
  coverage/inverse cases, source/shim/wholeRAM/REU guards.
- `tests/test_geos_typing_color_bound_candidate_wide.py`:1456 direct primitive
  vectors +17 malformed guards, fullRAM oracle and unchanged wholeREU.

Warm natural deletion:61744 modeled CPU instructions/zero overlay loads versus
809711 for forced full; pangram87396 versus907630; alpha63276 versus804863.
Warm unchanged all-white deletion33192/zero loads. These are CPU-model
instructions, not PAL/NTSC cycles or native latency claims. First use pays the
larger R30 CRC/load. No VICE was launched in this task.

Run with `PYTHONPATH=tools:tests python3 tests/<name>.py`; public accepts
`--fixture`, runtime accepts `--base`. All sources and verifiers are archived in
the adjacent M8 release checkpoint referenced by the session note.
