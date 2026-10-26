# SuperEditor

Standalone C64 editor in 6510 assembly for PETSCII Markdown-lite. The D81 now
boots working **40/60/80-column source views and a GEOS-font hires view**: mixed-case typing, Return,
backspace/insert/forward delete, horizontal/vertical cursors, preferred column, page movement, line home/end, top/bottom,
±40-character jumps, word movement, logical-line goto, native literal search,
grouped undo/redo, mark/selection, copy/cut/paste, F1 menus, F6 help and F7 typed commands.

The top row contains the menus with yellow PETSCII separators and a rounded
bottom rule. The bottom has one status line. The command prompt and errors share it; F6
opens/closes keyboard help, with 22 rows left for document text. F4 toggles soft
wrap; View/L/R or F7 `pan left`/`pan right` scrolls logical lines horizontally.
F7 `wrap on`/`wrap off` selects wrapping explicitly. F8 cycles 40/60/80/GEOS;
CTRL-F8 reverses in the normalized event lane. F7 `mode 40`, `mode 60` and
`mode 80` and `mode hires` select a view directly. Narrow body text uses the chosen pitch; menus,
help, dialogs and the status row retain their readable native 40-column grid.

It starts with an editable native tutorial. F1 → File → O/S/A opens, saves or
saves as; F7 `open`, `save`, `save as` uses the same commands. CTRL-O/CTRL-S are
also routed through the shared command system. Open stages a new document; save
verifies a temporary file before replacing the target. The final native
roundtrip, restart, filename and failure gates pass. Source40 now adds background
SuperMark colors: reversed yellow headings, cyan emphasis, yellow strong text
and light-blue code, while preserving literal source markers. A key cancels
optional styling before editing continues. BASIC and assembler code blocks now color keywords, numbers, strings, comments,
directives and labels. All three grid views now show semantic and BASIC/assembler token colors, with
one foreground/background pair per 8×8 tile in bitmap views. Source, selection,
clipboard, undo, mode cycling and native 80-column saving pass their feature
gates. Narrow views cache unchanged rows in REU; the 80-column rasterizer is specialized. Heading, code-block and explicit-region folding now works in all
four editable views and in formatted preview. Unaffected collapsed regions survive source edits and undo/redo.
The GEOS view uses proportional BSW/9 prose, actual bold/italic glyph metrics,
inverse headings and aligned native8 BASIC/assembler blocks. It supports editing,
selection, clipboard, undo, file dialogs and pixel-based horizontal pan. Literal
SuperMark markers remain visible in editable mode. A separate formatted GEOS
preview now hides confirmed controls and supports real font sizes, bold/italic/
underline, per-role appearance and aligned code. F7 `mode hires`, then `preview`;
Return returns to editing. F7 `settings` chooses body/H1–H6/code fonts, sizes,
colors and styles for the session. Host defaults live in
[config/editor-defaults.toml](config/editor-defaults.toml); see
[preview and settings controls](docs/GEOS_PREVIEW.md). Source-mapped preview editing
and formatting commands are deferred. Eligible wrapped60/80 prose edits reuse
checked pixel/row packets; GEOS layout reuses completed inline styles and incoming
parser state. Performance and final standalone hardening remain unfinished.
The full standalone goal is not complete. The ReadyOS 1024-byte reservation remains untouched.

F7 `syntax plain` skips automatic structure, inline and language parsing in all
four source views. `syntax markdown` retains formatting with uniform code colors;
`syntax full` restores BASIC/assembler token colors. Settings H cycles these
presets; the build default is `[editor] source_preset` in the TOML above. These
are session settings. Formatted preview still formats the document explicitly;
its code-token colors follow the same switch. See
[preset behavior and remaining REU redesign](docs/REU_CACHE_REDESIGN.md).
GEOS block classification now uses a checked REU baseline and forward page
lookups. Long, sparsely formatted prose can also reuse retained inline events.
Short or dense bodies and BASIC/assembler tokens use the existing parsers;
edit rebasing and retained layout remain in progress. Current Full redraw is
10.283 million PAL cycles after raster batching and the empty-inline shortcuts, so performance qualification
is still open. Committed window moves retain block classifications. A measured
66-KiB navigation case improves after eliminating unnecessary first-block inline
passes; the small navigation case still regresses. See the redesign document.

F7 `fold` toggles the innermost visible region; `fold all` and `unfold all`
operate on the document. Block/F, Block/L and Block/E reach the same commands.
A collapsed opener keeps its text and shows an inverse `+` in its newline cell.
GEOS preview formats heading and region titles, keeps a collapsed code fence's
literal label in the selected code font, and shows the same inverse summary mark.
Expanding restores a saved inner caret if no ordinary movement has intervened.
Navigation into hidden source opens its ancestors, and selections crossing a
fold still copy/cut the original hidden bytes. Hidden-only selections highlight
the collapsed summary marker. A checked edit journal transforms
fold positions and a fresh parse retains only matching collapsed regions.
Changing an opener drops its old fold; a failed or overfull journal falls back
to ordinary expanded source without failing the source edit.

In file dialogs, type a native filename of up to16 bytes, use arrows to select
an entry, F3 to change device8/9, F5 for the next page, Return to accept and
RUN/STOP to cancel. F6 opens dialog help. Dirty OPEN offers S Save/D Discard/
C Cancel. A recovery popup retains exact temporary/backup filenames; K keeps
those files on disk and closes only after source cleanup is safe. It does not
automatically delete recovery files. File transport currently targets
unpartitioned1581/D81 disks; filename syntax characters and PETSCII shifted-space
are refused. Native uppercase/lowercase and graphics are preserved.

Build from this directory:

The build needs Python 3.11+, the cc65 assembler/linker and VICE's `c1541`.
Font extraction uses the local sibling `GEOS20/reference/geos` sources and
`GEOS20/media` collection, plus a C64 character ROM (`C64_CHARGEN` can override
its local path). Generated font binaries and external media are intentionally
not committed. Native tests additionally use .NET 8 and the existing harness
selected by `VICE_TASKS_ROOT`; CPU tests use the Peddle source selected by
`PEDDLE_ROOT`. Historical private probes may reference local frozen fixtures;
those execution artifacts are also intentionally excluded from the source
checkpoint.

```sh
make
```

Mount `build/supereditor.d81` in VICE drive8 as1581, then:

```basic
LOAD"SUPEREDITOR",8,1
RUN
```

Use F1 → Edit → U/R for undo/redo, or CTRL-Z/CTRL-Y. F7 accepts `undo`, `redo`,
`home`, `end`, `top`, `bottom`, `up`, `down`, `page up`, `page down`,
`jump -40`, `jump +40`, `delete`, `wrap`, `wrap on`, `wrap off`,
`pan left`, `pan right`, `mode 40`, `mode 60`, `mode 80`, `mode hires`,
and `help`; Return executes, RUN/STOP cancels. Menus support arrows/Return and
case-insensitive letters. Unfinished menu choices explicitly say not ready.
F3/F5 move a page up/down. Physical modifier chords remain a separate verification lane; all implemented
commands have menu/typed access. CTRL-A/W move by word; CTRL-G/F open goto/find
prompts; CTRL-N repeats search. F7 `goto 12`, `find text` and `findi text` use
logical CR lines, exact native bytes and explicitly case-insensitive search.
Queries wrap once and preserve source; `next match` starts after the caret.
Current status7C means invalid argument,7D absent line and7E no match.

F2 starts/clears mark; navigation extends the source selection. CTRL-C/K copies,
CTRL-X cuts and CTRL-V pastes; Block menu and F7 `mark`, `copy`, `cut`, `paste`
reach the same commands. RUN/STOP clears mark; copy retains it. Typing or deleting
a selected range replaces/deletes it as one undoable edit. Empty clipboard paste
preserves selection. CTRL-C requires the native CTRL modifier to distinguish it
from RUN/STOP; CTRL-K is the byte-only copy alias. Edit/C or `clear undo` explicitly
recovers a latched undo-storage fault while keeping dirty source.

`python3 tests/test_geos_nowrap_editor.py --accept` checks actual GEOS no-wrap
pixels, tile colors, signed clipping, source maps, selection and pending input.
`python3 tests/test_geos_rendered_editor.py --capacity-accept` checks the
161-glyph partial-viewport edge case against the frozen packet ABI, exact arrays
and pixels (including ABI3 implicit canonical affinities);
this capacity gate does not claim hidden-marker editing.
`python3 tests/test_geos_pan_dispatch.py` checks the public pan/reveal route,
including success flags, pending preservation and failure cleanup.
`python3 tests/test_geos_nowrap_vice.py --run --source-freeze <cpu-fixture>`
captures all four actual VICE modes
through the .NET automation harness and checks native pixels and REU ownership.

`python3 tests/test_style_editor.py --run` freezes and checks actual idle/input,
style overlays, source colors, pending edits and cancellation.
`python3 tests/test_style_vice.py` captures native source styling, menu/help and
checks the880-cell semantic plan plus complete VIC pixels.

`make editor-test` checks the real command pipeline with independent byte models,
including 70002-byte source, 69200-byte line, cache boundaries and full-gap typing.
`make smoke` / `make editor-vice-test` cold-boot the actual editor through the
.NET VICE harness, type/edit/replay via the KERNAL byte queue, verify source,
journal, unowned REU and shim, and check native VIC pixels/screenshots for both
16 MiB and512 KiB profiles. `make editor-failure-test` checks missing REU and
missing/corrupt disk assets. No physical-key or end-to-end key latency claim.

`make navigation-test` checks preferred columns, page/line/jump commands,
24-bit line numbers, sparse indexing through a1MiB source and edit/cancel/failure
cleanup. `make navigation-vice-test` exercises the shared shortcut/menu/typed
paths, caret visibility and history invalidation on both REU profiles.

`make search-test` checks word/search/goto against independent byte models,
native cases, overlapping/wrapped matches, pending edits/undo, >64KiB positions,
invalid arguments and cancel/reload/epoch cleanup. `make search-vice-test` checks
those command routes and VIC screenshots on both REU profiles.

`make selection-test` covers independent selection/clipboard transactions,
>64KiB replacement/replay, cancellation, allocation/reload/epoch faults and
postcommit recovery. `make selection-vice-test` captures actual selected rows,
copy/cut/paste/replacement and undo/redo on both REU profiles, with exact storage
and whole-REU checks. See the local [selection contract](agentsworking/SELECTION_ABI.md).

Logical-line up/down/page movement keeps24-bit preferred columns through short
and blank lines. Manual pan can hide the caret; ordinary movement/typing reveals
it again. Source bytes/indentation stay intact. GEOS pan moves by20 pixels and
clamps to the current logical line width; it preserves pending typing without
committing it. Source-grid view commands first commit an existing pending group. Off-bottom typing itself uses bounded row discovery
and preserves pending source. See the [layout contract](agentsworking/LAYOUT_ABI.md).

The hot 2 KiB RAM gap batches typing before a minimal delta is journalled in REU.
Render/menu/navigation/mutation/edit/replay are separately assembled overlays with complete resident
build binding and CRC admission. Startup-only code lives in BOOT; operation-sized
TUI services use the ReadyOS palette/window roles. Current measured GEOS caret
and redraw costs are documented in [Performance](docs/PERFORMANCE.md). Future ReadyOS application,
OS suspend/resume integration and UltimateDOS remain separate work. The controlled
standalone capture/resume adapter is tested independently.

Foundation probes remain on the disk: BOOTPROBE (old diagnostic), DISPLAYPROBE
(four-view/font prototype), MEMORYPROBE, OVERLAYPROBE, OBJECTPROBE,
DOCUMENTPROBE, SPLICEPROBE, CLIPBOARDPROBE, LOCALPROBE, RANGEPROBE and
HISTORYPROBE. `make boot-smoke` exercises the legacy M0 diagnostic; `make cpu`,
`reu-test`, `overlay-test`, `object-test`, `document-test`, `splice-test`,
`clipboard-test`, `replay-test`, `refs-test`, `local-test`, `read-some-test`,
`range-test`, `history-test`, `hot-test`, `bindings-test`, and `crc-test` retain
their narrower CPU checks. Existing `*-vice-test` targets provide native evidence.
`make display-test` covers the original four display probes. The editor now
uses all four views through its own integrated rendering path. Generated GEOS
assets and development disks remain local.

Read the local [status](agentsworking/STATUS.md),
[editor contract](agentsworking/EDITOR40_ABI.md) and
[implementation milestones](agentsworking/IMPLEMENTATION_PLAN.md). The
`agentsworking` folder follows the repository's ignored local-record convention.
