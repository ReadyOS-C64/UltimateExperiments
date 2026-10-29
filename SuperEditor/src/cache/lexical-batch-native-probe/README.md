# Paired native qualification of same-call lexical batching

Released private candidate; no canonical/shared build, Git or hardware changes.
The CPU source release remains immutable in `src/cache/lexical-warm-probe`.

`build.py` prepares a genuine private59 fixture from the exact946 control:
`build/capture-index-fixed/20261026T183928480377Z/fixture`. It rebuilds the
released C45/R36/R37, replaces exactly `edit`/`tail`/`lex` in a copied D81,
checks all59 packaged assets and every other disk member, and preserves the
resident. Its source ZIP contains the actual optional flags. Rebuilding all
five lexical jobs from that ZIP produced byte-identical packaged SEOs.

```
python3 tests/test_lexical_batch_cost_vice.py
```

This runs the cohorts sequentially on binary8300/text8400..8439, with unique
disks/logs/REU/PIDs. `--control`/`--candidate` accept explicit fixtures;
`--verify CONTROL_EVIDENCE CANDIDATE_EVIDENCE` repeats offline evaluation.
The unchanged released `test_lexical_cost_vice.evaluate(...,'candidate59')`
is used for both59 cohorts. Only cohort metadata is renamed; the old54 parser
branch is not used for control. No actual product/oracle assertion was relaxed.

Native result:

| Actual PAL completion cycles | Control59 | Fused4 | Saved |
| --- | ---: | ---: | ---: |
| BASIC first |20,624,697|19,512,743|5.39%|
| BASIC warm |17,277,610|16,198,193|6.25%|
| ASM first |19,172,728|18,119,873|5.49%|
| ASM warm |16,874,703|15,852,611|6.06%|

Loads remain331/286 for BASIC first/warm,325/286 for ASM. Warm C45 calls fall
592->210 and554->192; whole overlay calls fall2647->2265 and2574->2212.
All four paired bitmap/attribute and PNG hashes are identical. Eight measured
frames cover512,000 actual VIC pixels, plus four prompt-baseline captures.

The STEP tradeoff remains explicit: warm inclusive C45 call maxima rise from
28,993->64,181 PAL cycles for BASIC and28,998->64,142 for ASM. Whole scheduler
service peaks remain approximately80.5k/68.1k because other steps dominate.
These are actual PC/SP/public-input-to-quiescent-idle stopwatch measurements
with warp enabled, IRQs running and a cold probe beyond the actual cold end.
They do not measure physical keyboard latency or remove the seconds-long
whole-page cost. The optimized candidate performs fewer repeated admissions
and same-call validations, not fewer overlay loads or a new cache proof.

Both runs require actual initial nonlexical root1, genuine producer/linker
publication to root5, zero source-matched C25 lexer init/feed/finish, and
warm-zero producer/linker work. They retain independent native pixel/source,
history/observer ring, all59 catalog,1024-byte shim, stack/probe and whole16MiB
REU oracles with only exact new COW pages/directory/alternate root and actual
FE ownership spans allowed. Warm arena is completely immutable. Setup uses
real File/Open and IRQ typed presets, including Markdown before ASM Open.

Evidence:

* Control: `agentsworking/evidence/M8/20261026T193448786288Z-lexical-batch-control59`
* Candidate: `agentsworking/evidence/M8/20261026T193524059569Z-lexical-batch-fused4`
* Comparison: candidate `comparison.json`; final hashes/closure are in each
  `manifest.json` and `receipt.json`.
* Private preparation: `build/lexical-batch-native/20261026T193448027555Z`;
  D81 `fbfd9820471e32e5bec863f1b0313f2b5f69c9d81cdd796f2053921dc9ab3f34`.

Four distinct candidate PNGs (BASIC/ASM prompt and full frame) were directly
reviewed; all12 output PNGs match those reviewed pairs byte-for-byte. Owned
PIDs15218/15300 are closed and the entire8300/8400..8439 block is released.
Runtime artifacts were hardlinked into evidence only after each owned run
returned successfully with `--close-vice`. No other PID was stopped.

Recommendation: source review/promotion can use the original optional recipe
and parent combined gates. This is a measured6% warm improvement on this
isolated immutable control, not a completed general rendering-performance goal.
