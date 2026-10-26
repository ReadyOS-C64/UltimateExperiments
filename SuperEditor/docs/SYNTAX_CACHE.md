# Retained BASIC and assembler colors

Full source mode can now retain lexical spans for a long code line in the
checked REU analysis object. Markdown skips the language lexer; Plain skips
automatic structure, inline and language parsing. F7 `syntax full`,
`syntax markdown` and `syntax plain` select these session settings.

Automatic construction currently applies to the first eligible CR-delimited
code BODY of at least 768 bytes in a baseline. It runs through the actual
foreground dispatcher and five registered operation modules: C45 gateway,
R36 resolver, R37 transport, C47 producer and C49 publisher. They reuse existing
filename strings and fit their ordinary 4 KiB overlay slots. The complete disk
has62 editor overlays in four REU code banks; the catalogue still holds 64.

The producer lexes the BODY once, storing bounded spans. The publisher writes
unused pages and a new root, validates the completed record, then publishes
VALID last. The old reachable root stays unchanged. Consumers authenticate the
actual source identity, record, page and allocation before using stored roles.
This does not replace source bytes or manufacture a parser checkpoint.

One attempt is permitted per baseline, including refusals and cancellation.
Observer flag128 remembers it; successful baseline replacement or a genuine
new document resets that flag. Cleanup releases owned ACTIVE state and source
leases while preserving the attempt flag. This prevents repeated construction
when resources or the span budget are unavailable. Missing workers, malformed
records, stale capabilities, pending changes and unsupported root formats keep
the existing parser fallback.

## Reusing a retained BODY after an insertion

C41/R34 can preserve the checked flags5 code BODY when one ordinary character
is inserted in a complete ordinary line after a retained BODY of at least4096
bytes, optionally followed by the
actual hot-window flush REKEY. The source threshold is4096 bytes; the dirty whole
line is reparsed and its carry must converge. Repeated eligible edits alternate
checked logical COW page pairs and publish VALID last. Empty INLINE references,
one CR page/one LEX page and complete source/observer identity are required.
Deletion, Return, markup, edits before code and unsupported graphs retain the
existing parser. Plain never schedules this worker; Markdown still performs no
language-lexer feeds. This does not add general edit or layout retention.
See the [registered rebase contract](../src/cache/edit-rebase-integration/README.md).

## What the measurements prove

On the paired approximately 1 KiB BASIC and assembler documents, the previous
54-overlay build repeatedly feeds 18,962/18,924 source bytes during a full page
repaint. The retained path constructs each BODY with 998/996 feeds once; a warm
repaint performs zero lexer init/feed/finish calls and consumes retained roles.
C25 still runs as a gateway: module-entry counts are not parser-feed counts.

| Complete warm repaint | Previous CPU instructions | Retained CPU instructions |
|---|---:|---:|
| BASIC | 5,895,637 | 4,268,957 |
| Assembler | 5,791,898 | 4,164,189 |

These are measured instruction counts. The paired native test also measures
whole foreground work with IRQ/VIC/REU stalls included:

| Warm repaint | Previous PAL cycles | Retained PAL cycles |
|---|---:|---:|
| BASIC | 23,909,858 | 17,277,646 |
| Assembler | 23,502,441 | 16,874,426 |

Setup uses real D81 File/Open and typed commands; the stopwatch uses an explicit
PC/SP/public-input seam. Warp and drive traps are enabled. These are not physical
keyboard-latency measurements. This compares complete54/59-overlay build
cohorts, rather than attributing every cycle to one assembly change. Warm overlay loads rise
from 211 to 286; the remaining source checks, role dispatch and rasterization
still cost substantial work. Zero lexer feeds do not establish general editor
performance, and full-page responsiveness remains unfinished.

The native gate checks real D81 startup/imports, source/history, the ReadyOS
reservation, independent VIC pixels, exact allocation changes during publication
and an immutable analysis arena on warm reuse. The controlled standalone
prepare/resume proof preserves the observer and unchanged lexical object, then
continues editing and modeled SaveAs/Open. It is not ReadyOS integration.

## Remaining limits

This is a first long-line cache policy, not complete retention for every code
block. Other code lines and short bodies use the existing lexer. Editing and
some content-preserving hot-window movements conservatively miss; cached
colors are not rebased onto changed source. Preview has its own pipeline.
Mapped edit roots and retained layout remain separate unfinished work.

Reserved observer bit64 is not part of this lexical protocol. A future live
reader-revocation protocol must explicitly couple all participating readers
and writers before those implementations can be combined.

## Same-call lexical work batching

C45 services up to four existing resolver/retained-role work units per public
STEP. Every helper entry still validates the full source identity and arena
capability. R36/R37 alone omit immediately repeated inner guards after that
same-call validation; no proof is retained across yields. Source verification
remains bounded to32bytes per original step. Other arena profiles retain their
original guards. No new flags, allocations, BSS or ZP are introduced.

Paired native59 control/candidate measurements save6.25% BASIC and6.06% assembler
warm PAL cycles, with identical pixels and unchanged286 overlay loads. C45 warm
inclusive call peaks grow from about29k to64kcycles; whole scheduler-service
peaks remain about80.5k/68.1k. This is a throughput improvement with a larger
service-call budget; long-page responsiveness remains open. See the
[exact paired qualification](../src/cache/lexical-batch-native-probe/README.md) and
[same-call lifetime proof](../src/cache/lexical-warm-probe/README.md).
