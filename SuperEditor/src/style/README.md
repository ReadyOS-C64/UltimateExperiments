# Bounded source-grid color planner

C14 plans block and inline colors in bounded idle slices. C15 adds BASIC and
assembler tokens while retaining the same checked R14 merged-source lease.
The resident dispatcher checks phase owner 2 before reading lexical state and
switches command overlays between slices; no command-to-command nesting occurs.
Input cancels optional work before editing. Missing assets retain editable plain
source and release only the planner's own lease. File owner 1 remains opaque.

Current payloads are C14 4,047 bytes, C15 3,664 and R14 2,331. The shared phase
uses 566 bytes: controller 273, parser/lexer 207 and source adapter 86. The current editor has47 actual assets and64 catalog slots, using three
logical REU asset banks. Exact binding and placement are tracked in
`agentsworking/STATUS.md`; historical build numbers below retain their scope.

The 40-column plan is 880 bytes at $4400. The 60/80-column plans use 1,320/1,760
bytes at $4800, aliasing the inactive 40-column font. Returning to 40 columns
restores the real font before painting. The checkpoint stays at $4770.
Production descriptor byte 32 is `(se_mode*2)|nowrap`; four private phase bytes
retain width, plan page and cell limit. Production `SE_STYLE_GRID` leaves the
default isolated probes' original 0/1 key and state layout unchanged.

Token foregrounds are keyword/directive 7, number 13, string 5, comment 15,
label 3 and operator 1. Full-word PETSCII BASIC source is recognized; tokenized
PRG import and JSON are outside this lexer. Narrow consumers map the plan to
semantic roles, then arbitrate one foreground per physical 8×8 tile by ink count
and stable priority. Heading inversion is separate from selection/caret union.

Build 8784 passed 100 integrated CPU screens and 24 native captures, including
34,320 independent semantic cells and 1,536,000 VIC pixels. The subsequent 0659
cache/fast-renderer build also passes CPU integration, source40 regression and
the28-capture native gate; exact checkpoints are in agentsworking/STATUS.md. Neither checkpoint
claims fold UI, rendered-source mapping or editable GEOS completion.

The tests below also retain earlier isolated-service evidence. Their fixed
40-column dimensions describe that original probe profile.

`python3 tests/test_style_plan.py` assembles only `build/style-plan` and runs
actual6510 block/inline/controller code against an immutable direct-REU callback
fixture. It does not build the editor, run VICE, or prove integrated source,
input scheduling, tile pixels or colors. The pure modules are reused unchanged.

`python3 tests/test_style_plan.py --editor-source` links the actual checked
merged-view callbacks into a private CPU capsule against immutable2f6d resident
code. Its five cohorts passed: committed/hot cache,12 actual fragmented splices,
pending insertion/no flush/nonwrap pan, foreign-lease cancellation and a far
inline closer beyond64KiB. It verifies the independent880-cell plan and entire
2MiB REU unchanged per completed plan, hot/caret/roots/tokens, diagnostic prefix
and shim. Measured501 phase bytes and7971 peak STEP instructions. Capsule
addresses and direct callback calls are not production overlay placement or UI.

Current measured controller1575 + block1076 + inline911 =3562 bytes before
production entry/binding/callback routing. Phase state268 + parser contexts147
=415 bytes; the checked editor-source adapter adds86 =501 total. Published
descriptor37 and persistent checkpoint120 are separate placements. No new ZP.
The complete source adapter code2394 bytes does not fit the remaining C14 space;
the production integration therefore uses the separate R14 provider image. The fixture's
direct calls are a CPU test seam, not permission for C-to-C overlay nesting.

## Span projection

Block and inline spans seek their intersection with each visible row, including
logical-line pan. They write only cells inside the span and the row's exclusive
source boundary. `st_kind` is reused as row×3 during this private paint phase;
no later block-kind consumer depends on it. Each STEP still performs at most
one source read,32 feeds or32 plan writes; a seek skips at most22 bounded rows.
No extra persistent state or zero page is needed. Exact old/new model and root
oracles, native A/B cost reductions and current packaged identity are in STATUS.

## Inputs, calls and publication

`se_st_key[33]` is caller-refreshed before BEGIN and every STEP:

| Offset | Meaning |
| --- | --- |
|0..14|Complete meta/original/append5-byte tokens, in that order|
|15..16|Committed document generation|
|17..20|Local visible render revision, including pending edits|
|21..23|Merged visible source length|
|24..26|Viewport top canonical source anchor|
|27..29|Horizontal pan, ignored in wrapped mode|
|30..31|Provider epoch|
|32|Legacy: 0 wrapped / 1 logical lines. Production: display mode×2 plus nowrap bit 0.|

`se_st_rows[69]` contains22 actual source row starts plus the exclusive bottom
anchor. Caller supplies a validated monotonic row map for this exact key, and
does not mutate it during a job. Nonwrap starts are logical-line starts; pan is
added only while mapping cells. The source callback binds its own authoritative
full source/hot identity; root obtains key and row inputs at the same foreground
safepoint. Unknown/stale layout must be prepared before BEGIN.

BEGIN refuses an active job unchanged, invalidates the old plan, obtains the
callback's own counted lease and validates merged length. STEP guards full source
and key each time, reads at most one128-byte packet, feeds at most32 bytes, or
updates at most32 plan cells, then yields. Carry clear/A2 is pending; carry
clear/A0 is complete; carry set/A nonzero is failure. A failed/aborted candidate
never publishes. CANCEL is idempotent and releases only the callback ownership
acquired by this job. Root also needs independent missing-overlay cleanup.

`se_st_descriptor` is the published key33 followed by generation16, valid1 and
reserved1. Completion performs a final source GUARD, releases its own lease,
increments generation and sets valid. R1 must compare the complete descriptor
with current context, and treat generation changes as a cache miss before
restoring cached caret colors. Existing source rendering is the fallback while
valid0. Source/history dirty state never changes because of this plan.

The source callback ABI is `se_fs_begin/guard/read/end` from `fold/source.inc`.
READ gets absolute offset24, count1..128 and caller buffer pointer; returns
done1..128, possibly short, or0 only at EOF. Errors are carry set/nonzero A.
The output buffer here lies in the owned8D00 phase union. No VIEW source-reader
state, overlay pointer, or doc-cache pointer persists between calls.

## Plan bytes, nesting and renderer precedence

For source40, the plan is exactly 880 bytes at $4400–$476F; narrow plans use the separate $4800 extent described above. Low nibble is C64 foreground; bits4/5/6
retain emphasis/strong/inline-code masks for matched nested spans; bit7 means
reverse heading. These flags are derived display state, never source bytes.
All delimiters/escapes remain visible. Plain1; emphasis3; strong7; combined10;
inline/fenced-code14; fence/region structural line15; headings87 before inline
style overrides. This palette is provisional until actual native PNG review.

R1 first applies heading reversal to the base glyph, then one inversion for the
union of selection/caret, not two inversions at a selected caret. It masks low4
for semantic foreground; selection/caret colors retain the existing higher
priority. Underlying-caret cache must include the resulting base/selection
glyph/color. A full styled-plan publication invalidates the previous cache.

Block classification waits through CR/EOF. Inline matching then scans that
complete line's body separately; a closer far beyond the viewport is still
required. Unmatched markup remains ordinary source. No complete line is buffered,
and neither a source read nor a paint-span sweep runs unbounded in one STEP.
Code and fence lines skip inline matching. Span application clips canonical
source ranges to row anchors; CR/EOF/filler cells remain normal.

## Checkpoint and input contract

4770–47E7 holds the full block79-byte context, canonical anchor3, key33, valid1,
earliest damage3 and damage-known1. It fits the144-byte remainder after the plan.
The service saves CR-complete block boundaries up to viewport top. A checkpoint
can be reused only with identical capabilities/generation/provider and either
identical revision/length or an explicit mutation proof entirely at/after its
anchor. Revision/length changes without that proof discard it.

Root must record the earliest canonical edit position across all pending edits
in `se_st_cp_damage`, set `se_st_cp_dirty=1`, and invalidate `se_st_valid` before
R1 consumes/clears its own damage range. If an operation's range is unknown,
clear `se_st_cp_valid` instead. Never reconstruct this proof from an already
cleared renderer flag. Provider reset, OPEN/undo source capability changes or
unknown publications clear the checkpoint. The first integration can clear it
conservatively until the mutation hooks have their own proof.

Parser jobs use a distinct phase-union owner, not file owner1. Root checks queued
input/NMI before every optional STEP. It cancels/releases the style lease before
executing the event exactly once, and gives urgent source render priority. The
production idle loop checks input before optional planning; calling this
bounded service repeatedly without checking input does not make typing responsive.
No pending gap flush is required for colors. EOF/very long lookahead may delay
styles while ordinary source editing continues.
