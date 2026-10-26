# Checked semantic reuse after an ordinary insertion

C41 PARSE and R34 XFORM are registered cold assets. C7 schedules the optional
job and proves the source/REKEY identity; C21 resumes its normal page renderer
when the job finishes or declines. The resident catalog contains62 assets in
four code banks, with capacity64. PARSE/XFORM reuse the FOLDPARSE/FOLDXFORM filename
suffixes. The catalog adds four cold bytes; startup ends at$0ED5, leaving42 bytes
before$0F00. No resident warm state, BSS, zero page, bank or object was added.

## Admission and authority

The current-schema path accepts BASE|LEX root flags5 and one visible literal
insertion inside a complete ordinary CR line after an unchanged retained code
BODY of at least4096 bytes. C7 also requires a committed source of at least4096
bytes before dispatch. One SPLICE, a
SPLICE followed by its real hot-window flush REKEY, or a pure representation
REKEY is supported. The dirty ordinary line is reparsed by actual SuperMark;
its exit carry must converge. Subsequent eligible insertions can reuse the
newly published graph again.

The selected closure must contain one CR page with at most42 records and one
LEX page. All INLINE references/counts must be empty; INDEX/RUN/NEXT chains are
unsupported. Deletion, Return, markup, edits before retained code, missing
observations and insufficient resources retain the ordinary parser. A valid
BASE-only root and a journal without room for the queued observations explicitly
decline to C21, preserving the selected graph and unread queue. Source,
provider, CRC and schema failures remain errors. Plain does not schedule the worker. This is a narrow semantic
reuse path; it does not implement general edit rebasing or retained layout.

R34 checks the live provider, allocation directory and complete selected
root/CR/LEX closure before choosing logical COW pairs12/13 or14/15. Those page
numbers are never treated as physical bank ownership. The old selected root
and reachable pages remain unchanged until verified publication. Old unselected
draft pages can be reused only after complete ownership/closure checks; arbitrary
historical roots are not retained. The two observer events retire only after
checked journal records and a root published VALID last in the same nonyielding
terminal call. Cancel/error releases the held source reader and preserves the
previous selected root, document/history and unread observations.

## Bounded calls and memory

C41 validates source/observer authority on each public STEP. Within that same
foreground call it executes at most four existing R34 root/page/record or
publication microsteps. Each R34 operation still performs its own typed arena
guard. The quota is reset on every call; authority never survives a foreground
yield merely because a previous batch was valid. Source-proof transitions,
parser/read32 work and final publication keep their original boundaries.

C41 is4068 bytes (28 free), R34 is4095 (one free), C7 is3930, and C21 is4096.
The batch quota uses an already borrowed byte atBC_FRAME+79, outside the live
79-byte SuperMark state. R34 and R14 complete sequentially through the existing
overlay trampoline; there is no same-slot nesting or runtime cold-code call.
The all62/staged call graph retains the measured68-byte relative stack bound.

The content-aware builder authenticates resident API bindings, source includes,
outputs and CRCs. A no-op leaves published bytes/mtimes unchanged. Compilation
failure preserves prior artifacts; publication failure restores prior content.
A restored map file can have a changed mtime. Build outputs and external font
extracts remain ignored.

## Verification and measured limits

The actual startup imports all62 packaged assets. Public repeated Q -> WRAP_OFF
flush -> scheduler repaint tests compare every classification, packet anchor,
source/history/clipboard state, independent pixels, provider ownership and
COW/journal publication. Fault tests exercise actual yielded boundaries, missing
workers, cancellation, stale source/epoch and unsupported inputs. The registered
CPU test separately checks the documented source/GTF temporary-bank regions;
no entire semantic-cache bank is exempted.

The capacity regression uses a70,002-byte source with a70,000-byte logical line
on16- and32-bank providers, across all four modes, an EOF insertion and Undo.
The journal boundary regression builds its full48 entries through24 real
insert/flush/publication transactions. Queued sums49 and50 take the normal
parser without modifying the selected graph or observations. A genuine
between-slice incarnation change still reports C1. These are correctness
fallbacks; they do not compact the journal or refresh retained analysis.
The native regression opens both documents through ROM File/Open and checks
29 actual VIC captures: EOF edit/Undo,24 real journal publications, then the
49/50 fallback cases. It retains source/history/fonts/all62 payloads and the
old analysis-bank checks. Its public-routine PC/SP measurement seam is explicit;
the CPU gates separately prove precise writes across the complete16 MiB.

The earlier native comparison on d2ea9c1 opens REBASE8K through ROM File/Open and performs four
repetitions. Its stopwatch explicitly enters public input/command routines with
a disclosed PC/SP seam, then runs the real scheduler, IRQ/VIC/REU activity.
It measures6.48–6.94 million PAL cycles versus9.84–10.04 million in committed
010fb03, with identical paired screenshots. Batching removes98 loads compared
with the first unbatched rebase candidate, but the final path still loads80/81
images versus36/37 in the control. It remains slow at1MHz; these measurements do
not establish physical-key latency or whole-editor performance.

Build with `make editor build/supereditor.d81`. Qualification commands take an
immutable fixture containing the exact packaged product, fonts and matched
raw/label/map metadata, plus its matching source project:

```sh
python3 tests/test_cache_rebase_registered.py --fixture FIXTURE --project PROJECT
python3 tests/test_cache_rebase_presentation.py --fixture FIXTURE --project PROJECT
python3 tests/test_cache_rebase_registered_stack.py --fixture FIXTURE --project PROJECT --out NEW_OUTPUT
python3 tests/test_cache_rebase_capacity.py --fixture FIXTURE --project PROJECT --banks 16
python3 tests/test_cache_rebase_capacity.py --fixture FIXTURE --project PROJECT --banks 32
python3 tests/test_cache_rebase_refusal.py --fixture FIXTURE --project PROJECT
python3 tests/test_cache_rebase_journal_refusal.py --fixture FIXTURE --project PROJECT --out NEW_OUTPUT
python3 tests/test_cache_rebase_registered_vice.py --fixture FIXTURE --variant candidate
```

The presentation gate covers55 source cases and14 retained BASIC/assembler cases,
including zero parser feeds in Plain and zero language-lexer feeds in Markdown.
The full final display/save/restart, capacity, pressure, lifecycle, media and
responsiveness acceptance remains a separate requirement.
