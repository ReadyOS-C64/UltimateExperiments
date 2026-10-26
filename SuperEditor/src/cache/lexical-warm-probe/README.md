# Same-call lexical batching candidate

Private source release; canonical files, Makefile, catalog, resident and hardware
are unchanged by this lane. No native speed claim is made for this candidate.

The pinned input is
`build/capture-index-fixed/20261026T183928480377Z/fixture`: PRG
`93832107be6bca207087516304249b5de8b567143528ddcc132befdba64dd76b`, binding
`7abb2d3f53543b3dfd5c297c6760a5f6`, D81
`11f33bb6d835ed18d6d32ccb5b71db7fded253829732fcfba7e4899f2d9bb373`,
59 actual catalog assets. The default source reconstruction is checked against
the complete frozen C45/R36/R37 SEO bytes before comparison.

## Change and integration recipe

`ready.patch` contains three source changes against that input:

* `gateway.s` -> `src/cache/lexical/gateway.s`: optional
  `LX_BATCH_STEPS=4` batches at most four existing resolver or retained-role
  STEP calls per C45 public entry. A helper completion/error ends the loop
  immediately. The source verification phase still performs its original
  bounded 32-byte R14 read. `$90B4` (`CTX+30`) is ephemeral per-entry budget,
  following the existing C45 context bytes0..29; it is outside the saved FS86,
  source packet, and parent controller. No state survives as a new authority.
* `arena-open.s` -> `src/cache/arena/open.s`: optional
  `BCA_OUTER_VALIDATED=1` omits the immediately repeated `bca_guard` inside
  the read-only `bca_open_step` profile. The public OPEN still guards.
* `arena-page.s` -> `src/cache/arena/page.s`: the same optional definition
  omits immediately repeated `bca_guard` calls inside page BEGIN/STEP and
  certified arena READ. All owner, request, range, page/root/record CRC and
  checked object DMA validation remain.

In the current lexical builder, enable `LX_BATCH_STEPS=4` only for tag `edit`
(C45), and `BCA_OUTER_VALIDATED=1` only for the `open.s`/`page.s` objects of
tag `tail` (R36) and the `page.s` object of tag `lex` (R37). Retain
`BCA_READONLY_OPEN=1` for the R36 OPEN object. Do **not** enable the latter
flag globally, for R33/C35/other arena consumers, or for `ctrl`/C49. No new
catalog entry, resident flag/hook, REU object/bank, BSS or ZP is needed.

The optional guard hoist relies on the exact R36 `link_guard` and R37 `guard`
entry paths. They have just authenticated the complete FS59 source identity,
AUTH13 arena/ticket/incarnation, no pending observation, source graph/meta/
original/append capabilities, typed arena token and provider mapping, before
the inner operation. Intervening code only sets offsets/requests and checks
local metadata; it neither yields nor mutates those authorities. Every next
helper entry performs the full guard again. The keyboard IRQ queues input;
it does not mutate those foreground authorities. No across-yield memo,
PAGE32 repurposing, reserved64 flag, skipped CRC, or raw-host mutation
guarantee is introduced. Existing post-CRC lifetime behavior is unchanged.

Reassemble/reseal against the actual resident report when integrating. Do not
copy these frozen-binding SEOs into a different resident cohort. Include the
builder flag edits in the content-aware build input closure and package all
actual changed SEO bytes into D81. Parent integration should rerun its staged
stack, public presentation, cancellation and native paired cost gates before
making a native cycle claim.

## Reproduction

From the repository root, using a new output path:

```
python3 src/cache/lexical-warm-probe/build.py \
  --base build/capture-index-fixed/20261026T183928480377Z/fixture \
  --out build/your-private-lexical-batch --batch 4 --fused
python3 tests/test_cache_lexical_warm.py
```

The verifier also accepts `--fixture`, `--smoke`, `--positive-only` and
`--faults-only`. Its builder extracts the pinned source ZIP and never runs
shared Make or modifies the input fixture. With flags absent, all three
complete SEOs must equal the original bytes. Final comment-only source
annotations were independently reassembled and matched the terminal payloads
in `build/cache-lexical-warm/release-fit-{control,fused}`.

## Measured CPU result and limits

Terminal result: `build/cache-lexical-warm/20261026T192736199314Z/result.json`.
Payloads and SHA256:

| Image | Control | Fused4 | Fused4 raw SHA256 |
| --- | ---: | ---: | --- |
| C45/edit |1130|1150|`b03667c3c42e3635760ac37cc712db9896cc0a2f6f636bb599a0deeb20e87b66`|
| R36/tail |3217|3185|`cd811d24f8944509cef2dfd80e5c0a83302b57b076c95b3e597aed6159cce633`|
| R37/lex |3917|3893|`6c52f74d4d6e0acff3ac4c2159fadd59d09e10977cf0cd3a5dd739739ff1a183`|

All numbers below are actual CPU **instructions**, not PAL cycles or physical
key latency. They include the whole public preset/render operation for first,
and a forced whole public repaint for warm, with identical input per cohort.

| Source | First control -> fused4 | Warm control -> fused4 | Loads first/warm |
| --- | ---: | ---: | ---: |
| BASIC |5,098,661 ->4,765,589|4,268,957 ->3,945,597|331/286 unchanged|
| ASM |4,977,773 ->4,661,794|4,164,190 ->3,857,919|325/286 unchanged|
| BASIC + mixed inline prose |5,317,929 ->4,984,858|4,484,117 ->4,160,756|337/292 unchanged|
| ASM + mixed inline prose |5,188,958 ->4,872,977|4,371,299 ->4,065,030|331/292 unchanged|

The reduction is 6.09–6.53% first and 7.01–7.57% warm. For BASIC warm, batching
alone is4,004,763 instructions; local guard hoisting then reaches3,945,597.
C45 public calls fall592->210 for BASIC warm and554->192 for ASM warm.
This does not remove the286 overlay loads or the repeated root/page CRCs.

Cooperation tradeoff: warm C45 peak rises from6,632–6,661 to17,593–17,653
instructions; the already-existing first-build peak falls slightly from
59,585–59,586 to59,195–59,196. Each batch remains capped at four original
work units, and input/STOP is serviced on the next public root step. No
latency SLA or interrupt-cycle prediction is inferred from these counts.

Recommendation: this is a modest, bounded improvement with a larger STEP
budget. It is ready for parent source review and native paired measurement;
it does not solve the remaining whole-page performance problem.

## Exact verification scope

* 24 actual public CPU frames: BASIC/ASM with/without mixed inline prose,
  first/warm, each using byte-identical control, batch-only and fused profiles.
  The genuine producer/linker creates root1->5; no lexer span/page/result or
  semantic authority is host-seeded. Only the three tested asset images are
  substituted through the ordinary sealed catalog.
* Independent full320x200 bitmap/1000 attribute oracle; all actual type53
  arena and FE bank bytes equal control, including row maps/anchors. Whole
  16MiB REU is unchanged outside exact observed new COW page-directory/alternate
  root ranges and the real FE bank. Warm type53 arena is entirely read-only.
  Source/pending bytes, selection/history/clipboard, ticket/incarnation/ring,
  actual59 catalog and1024-byte shim remain exact. Legitimate lexical-attempt
  bit128/PAGE32 publication changes are checked explicitly.
* 22 fault/bypass groups: queued STOP in source/resolve/consume phases; foreign
  counted lease; stale epoch preserving seven foreign leases; missing C45,
  R36,R37,R14; changed ticket/incarnation/revision/generation; foreign arena
  physical owner; altered GSEM count and parent packet; actual checked owner53
  CR-page write rejected by payload CRC;54 wrong-owner opcode calls with all
  phase bytes `$8B40..$917F` immutable; competing ACTIVE BEGIN; actual Plain,
  Markdown and short-Full bypass. Fault REU checks are whole16MiB; actual
  source/pixels are verified again after recovery.
* Four distinct final PNGs directly inspected; all four warm PNGs are
  byte-identical to their first counterparts. All24 bitmap/attribute results
  equal the independent model. CPU-generated images are not native captures.

Earlier failed host assertions are retained: STOP correctly clears its owned
ACTIVE8 bit (the initial test incorrectly demanded exact flags), and the first
Markdown render legitimately creates its semantic baseline (the initial test
incorrectly called that render read-only). The final tests require precise
allowed flags, finish the actual initial baseline, and separately verify the
forced read-only repaint. No product guard or pixel oracle was relaxed.
