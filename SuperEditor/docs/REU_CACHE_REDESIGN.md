# Configurable parsing and retained document data

Design direction recorded on 2026-10-25. The three parsing presets and the
initial GEOS block-cache path are implemented on the development branch.
Source checkpoint before implementation:
`dad569e` on the local branch `supereditor/reu-cache-redesign`. Generated media,
build outputs, logs, external font extracts and local working records are
excluded from Git.

The `fbcc8f6` checkpoint connects bounded C7 admission, the R33 REU writer,
a retained C34 semantic producer, and C35 cached block classification. A full
GEOS repaint uses the stored classifications without block parser feeds;
independent pixel, source, lease and native display checks pass. This is an
initial baseline and classification implementation. Inline/lexical reuse,
edit-chain rebasing and retained layout are still work in progress.

Performance qualification remains open. The first cached path took26.376 million
PAL cycles versus9.512 million before it. Reusing a checked CR-page proof within
a viewport reduces native Full GEOS redraw to18.448 million cycles in the first
qualified integration. Each checked cache write revokes that proof before DMA;
fresh viewports, parser fallback and the painter transition also revoke it.
The subsequent forward-query capsule retains the checked page cursor and starts
one full query per page rather than one per logical line. Its integrated native
Full redraw takes12.268 million PAL cycles; Markdown takes11.747 million. This
still exceeds the old9.512-million-cycle Full path, so performance remains open.
Initial root validation and repeated source-state exchange still cost work.

C37 also skips inline interpretation only when its checked CR certifies a
completed inline pass, zero events and a canonical null inline reference. Missing
or inconsistent metadata keeps the conservative parser path. This reduces native
Full redraw to10.977 million PAL cycles and Markdown to10.456 million, with the
same independently verified pixels. Full remains15.4% above the older path.
This is an empty-result shortcut, not reuse of nonempty inline style events.

Skipping decoded glyph scanlines with no ink and no rendering flags further
reduces Full redraw to10.608 million PAL cycles and Markdown to10.087 million.
Selection, caret and inverse flags retain the original rendering path. The
4,094-byte renderer and fixed font addresses stay unchanged in size and placement;
all11 native screenshots match. Full remains11.5% above the older path. This
raster optimization does not reduce overlay loads or close the cache redesign.

The next raster change computes the intersecting color-tile range once and
unrolls the histogram reset, retaining the same4,094-byte payload and font
addresses. Together with committed-only source admission, the verified native
Full redraw is10.443 million PAL cycles (all11 screenshots unchanged). This
remains above the older9.512-million-cycle path.

A fresh block query can now accept a changed hot-window geometry only when
both snapshots have no pending edits, their29-byte canonical source prefix and
merged lengths agree, and the real current reader and typed cache authority
pass validation. It copies the actual current59-byte identity into the local
query; every subsequent reader guard stays exact. Pending edits, REKEY and
SPLICE still use the existing safe fallback.

This admission is correctness-qualified, with a measured performance regression:
after a window move, the251-byte case takes1.958 million instructions versus
1.749 million for the previous parser fallback. The66-KiB case takes92.111
million versus76.921 million, including actual caret reveal. C35 still emits a
conservative inline hint for the first block, causing three unnecessary66-KiB
inline passes. Its compact completed-empty shortcut is being qualified
separately. Nonempty inline and retained layout probes are not yet integrated.

C35 seeds an untrusted slot after final source validation. C37 validates the
page certificate, current source/capability tuple and the selected record's CRC
and canonical START before using that slot. A bad slot, backward query or page
boundary hands off to C35 BEGIN on the next foreground slice. The resident
preserves that operation0; no C-to-C call is introduced. Actual foreground
rendering and a corrupted-slot handoff pass independent pixel/source/full16MiB
checks. The53-asset build also passes observer42, parser55, incremental15,
cleanup9, stack68 and native11 gates. Generated media and logs remain ignored.

The dirty-heading incremental regression is fixed using an explicit cached
outgoing-carry type. It consumes authenticated CR data and never fabricates a
legacy parser checkpoint. All15 incremental editor cases pass, alongside the
cached-paint, parser-bypass and stack checks. Inline/lexical and edit-rebase work
remains open. Zero parser feeds or fewer overlay loads alone are not speed
results; the native cycle measurement above remains slower than the earlier path.

The user's requirements are configurable highlighting with a real parsing
bypass, reuse of unchanged document analysis and layout, efficient REU use,
and reconsideration of overlay residency. The particular cache representation
below is a proposal, rather than a user-mandated implementation.

The repeated work is measured: a private retained-style probe still feeds the
same 857-byte BODY six times for an 863-byte test document. Its inline worker
accounts for about 16% of that run's instructions, while the raster worker
accounts for about 54%. These are CPU instruction counts from an unpromoted
probe, not native cycle timings. Both the analysis pipeline and the drawing
path need attention; retaining syntax results alone is insufficient.

## Separate the work that can be disabled

Provide session controls and host build defaults, as with the existing font
settings. Do not add disk configuration persistence in this phase.

| Source preset | Structure and inline formatting | BASIC/assembler token coloring | Raw-source behavior |
| --- | --- | --- | --- |
| Plain | Disabled | Disabled | Literal bytes, uniform body font/pitch and colors; normal wrapping, navigation, selection and editing |
| Markdown | Enabled | Disabled | Headers, emphasis and code-block layout; code has a single configured color |
| Full | Enabled | Enabled | Markdown presentation plus language token colors |

The implementation should keep structural formatting and code-token coloring
as separate capabilities, even if presets make them convenient to select.
Turning off only code-token coloring skips the lexical pass. Plain source
skips automatic block, inline and lexical parsing altogether: no speculative
background cache fill and no formatting-driven bold/italic metrics or code
font substitution. A low-color screen that still runs the parser is not this
bypass.

F7 accepts `syntax plain` (also `syntax off`), `syntax markdown`, and `syntax
full` (also `syntax on`). Settings H cycles Plain → Markdown → Full. R restores
both the font settings and the configured preset. Host defaults use a separate
`[editor] source_preset = "full"` field in `config/editor-defaults.toml`; the
existing 64-byte font settings format is unchanged. Configurations that omit
the editor section retain Full. Nothing is saved to disk by these controls.

Plain keeps literal markers visible, uses the ordinary fixed grid font in
40/60/80 views and unstyled BSW/9 throughout editable GEOS source. Code fences
therefore do not select native8 pitch in Plain. The separate body/heading/code
font choices remain formatted-preview settings, as before. Switching presets
invalidates the derived viewport/style caches before publishing the new preset.

Preview is an explicit consumer of document structure and inline formatting.
Code-token coloring can still be disabled in preview. Plain source does not
promise active semantic folding without structural analysis: it presents the
expanded literal document and rejects explicit fold operations. Stored fold
choices are retained for returning to Markdown or Full. Formatted preview is
an explicit formatting operation even when the source preset is Plain; it
retains its selected fonts and bold/italic/underline. Preview code is uniform
in Plain/Markdown and token-colored in Full. Its retained bitmap key includes
the preset, preventing reuse of colors from a previous setting.

## Cache semantic blocks independently of the viewport

Use CR-delimited logical lines as the basic semantic records. A fenced code
section or explicit region is a dependency across these records, not a single
large unit whose tokens must all be regenerated after every interior edit.
Current BASIC/assembler lexical state resets at CR, so an ordinary code edit
usually needs one line's lexical runs once its language is known.

A completed record contains:

- Source identity, canonical START/BODY/END/NEXT and CR-versus-EOF reason.
- Incoming and outgoing block-parser state, including fence, language, region
  depth and region-overflow state. The current CR-boundary carry is six bytes;
  mid-line parsing uses the existing larger continuation state.
- Block kind, heading level and control-marker information.
- Completed inline events or spans, plus language-token runs when requested.
- Its own version and a final publication marker.

Store event/token positions relative to the logical block. An insertion before
an unchanged block should rebase an anchor through a complete edit history,
rather than rewrite every token's absolute position. An indexed anchor or piece
reference must also prove that the unchanged text is still the same text.

Keep layout records separate: wrap boundaries, glyph advances, source/glyph
mapping, height/baseline and resolved font/style runs. Keep color and bitmap
projection separate again. Scrolling, a palette change or a caret move should
not invalidate the document's parsed meaning.

## Invalidate from edits, and stop at proven convergence

Record every visible mutation, including unflushed hot-gap typing. Document
generation alone is insufficient: many pending edits share that generation.
The cache root must identify the visible revision, source graph, provider epoch
and parser ABI. Migration to a newer revision requires a complete ordered edit
history. The existing bounded fold journal is conditional on a valid fold
object; it is not a universal edit journal.

For an edit, restart at the affected certified logical boundary. Include the
preceding line when removing a CR joins two lines. Invalidate the entire
affected inline BODY: a newly matched closing marker can change styling before
the insertion point. Inserted/deleted CRs split or merge records.

Propagate structural parsing forward until an unchanged suffix has both an
exact unchanged-source proof and matching incoming parser state. A fence or
language change can propagate to EOF. Equal offsets, similar visible colors or
a checksum alone do not prove convergence. Ordinary prose edits should usually
converge after the affected logical line; the stopping rule must establish it.

Cache complete inline analysis once per logical BODY, then supply windows from
that result. The present repeated whole-BODY scans for successive 160-character
requests are a replacement target. A long line must use chained chunks or a
retained continuation; a small result-buffer limit must not cause repeated
complete parsing or silently truncate the result.

| Change | Recompute |
| --- | --- |
| Text edit | Affected inline/lexical records; structural suffix until convergence; dependent layouts and damaged paint |
| Parser/dialect change | Semantic records and dependents |
| Enable code coloring | Missing lexical runs for needed blocks |
| Palette/foreground/background change | Color projection and paint; retain parsing and applicable metrics |
| Font, size or metric-affecting style change | Dependent layout and paint; retain parsing |
| Column width or wrapping change | Layout and paint; retain parsing |
| Top, pan, selection, caret or fold visibility | View projection and damage; retain parsing |

Old records remain available until their replacements are complete. Publish
validity last. A missing/overflowed edit history, stale provider or unverifiable
record must cause explicit invalidation and bounded rebuilding, never a guessed
hit. Stop/error recovery must preserve the pending document edit.

## Reorganize residency around jobs

The current root loop draws on damage requests; it does not repaint continuously
on every idle VIC frame. However, content/layout jobs do make many overlay calls
and transfers. The redesign should reduce those transitions architecturally.

1. Consume or build semantic records for a batch of logical blocks while that
   worker remains loaded. Retain continuation state across bounded yields.
2. Derive layout from those completed records while the layout worker remains
   loaded. Styled advances are required before wrapping can be finalized.
3. Paint damage in consecutive font/style runs, preserving draw order and the
   C64 8x8 color-cell rules. Retain the compositor and active expanded glyphs
   for the paint job, rather than swapping helpers for each glyph or packet.

Cold file dialogs, settings, import/export and recovery are suitable overlay
work. Frequently used source access, cache lookup, caret and drawing primitives
need a measured residency budget. Preserve the assembler micromodule approach;
link and schedule modules according to task lifetime instead of making every
micro-operation a runtime overlay boundary.

Do not append another supervisor layer to the current graph without measuring
the result. Budget a replacement hot path and compare overlay loads, DMA bytes,
parsing feeds and total cycles on the same documents. After adding the presets,
resident code/constants end at `$3EFD`, with two bytes before the CRC table;
resident BSS uses 1,534 bytes, with two before the ReadyOS reservation. A new
resident/phase map is required; additional hot storage cannot be assumed.

The [implemented observer foundation](REU_CACHE_OBSERVER.md) appends a 17-byte
descriptor and three 32-byte records to existing work segments. OBJECTS now
occupies 454 of 512 bytes and DOCSTATE 997 of 1,024 bytes. Existing data fields
retain their addresses; ordinary BSS and zero page do not grow. The existing
clear routine covers `$9A00–$9FFF`, and the lifecycle adapter copies that range.
Cache query revocation on restoration remains an integration requirement.

The chosen producer records edits in RAM inside the already loaded mutation
images; it performs no REU DMA on warm local edits. A separate edit ticket
observes hot edits and R2 byte/reference publication, with REKEY for already
visible flushes and incarnation revocation on successful new H_INIT. It does
not redefine `se_r_revision`. Typed arena transport and sequential semantic
production are separately tested components; renderer reuse and lifecycle
integration remain open. Allocation failure must only invalidate disposable
cache data.

Checks belong at ownership/transaction entry, actual yield/resume boundaries,
resource changes and publication. Work under a still-valid, non-yielding lease
should not repeat the complete source-graph or font-header validation for every
glyph. Establish those lifetime guarantees before removing redundant checks.

## REU capacity and RAM contracts

Allocate optional cache pages through typed logical handles. Do not hard-code
physical bank numbers. Make semantic, lexical, layout and decoded-glyph pages
independently evictable; document, clipboard and undo correctness takes priority.
Cache pressure may evict or stream derived data, never reject a document edit.

Measure both the normal large REU profile and the existing small profile. The
1MiB profile already reaches 15 allocated banks in an earlier acceptance run;
an always-reserved extra cache bank is not a safe assumption. Use an explicit
quota and graceful pressure behavior rather than claiming unlimited cache space.

Existing FE row, checkpoint, font and preview extents are occupied and have
published contracts. Likewise, $5000 is an armed staging/font/code window and
$8D00 is a shared ownership phase. Neither is general spare memory. A new map
must prove every persistent and temporary lifetime, including IRQ behavior.
Preserve $C600-$C9FF, define cache revocation on suspend/resume/provider changes,
and keep the REU provider boundary suitable for a later ReadyOS adapter.

## Implementation gates

1. Inventory hot-path residency and produce a replacement memory/call budget.
   Specify the independent source-presentation controls and session ABI.
2. Implement Plain bypass first. Instrument actual emitted-code parser/lexer
   entries: off-mode source editing must make zero such calls, including after
   warm/cold mode changes and foreground idle. Verify pixels, text, history,
   selection and file operations in all four source views.
3. Implement typed cache pages, complete edit tracking and semantic records.
   Prove edits, pending input, CR splits/joins, distant delimiter closure, fence
   propagation, eviction, cancellation and resume. A viewport change over valid
   cached text should add no semantic parser feeds.
4. Add layout reuse and the batched paint path. Prove independent pixel/source
   maps, fonts and color-cell results; test settings/palette invalidation.
5. Compare cold open, ordinary/repeated edits, scrolling and full redraw under
   normal PAL/NTSC timing. Record parsing feeds, cache hits/misses, overlay loads
   and DMA bytes alongside total cycles. A cache hit must eliminate the work,
   not merely skip showing its result. Keep the original usability targets.

Existing private style, producer and wrapped-line experiments remain evidence
and possible reusable components. They are not prerequisites that must all be
promoted before this architecture can replace the expensive path. Rendering is
also a separate measured bottleneck; semantic caching alone cannot promise to
solve full-page latency.
