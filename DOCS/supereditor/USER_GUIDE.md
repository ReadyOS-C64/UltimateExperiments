# SuperEditor user guide

SuperEditor edits raw PETSCII source on a C64 with a REU. Its four editable views
share one document, selection, clipboard and Undo history. Formatted GEOS preview
is a separate, read-only view of that same source.

This guide describes the current standalone working release, including the
qualified three-page F6 guide.

## Start and open a file

Attach the complete SuperEditor D81 as drive 8 and enable a REU. The complete
font package works with 2 MiB for the tested small-document workflow; larger
tests use 16 MiB. It does not start with 512 KiB. See [capacity](CAPACITY.md).

```text
LOAD"SUPEREDITOR",8,1
RUN
```

Keep the overlay and font files on the disk. Startup and some operations at 1 MHz
can take a substantial time; see [performance and remaining latency](PERFORMANCE.md).
The editor uses C64 key names below. A host emulator's PC keyboard mapping may
differ; these instructions are not a claim about every physical key chord.

Press **CTRL-O**, or **F1, F, O**, to open a file. Type a PETSCII filename or select
one with up/down, then press Return. Files are raw PETSCII SEQ text with CR line
endings, not tokenized BASIC PRGs or UTF-8 Markdown.

## Menus, commands and display modes

**F1** opens the menu bar. Choose a heading and item by its cyan/yellow displayed
letter, or use left/right, up/down and Return. The attached yellow child menu
meets the menu bar at PETSCII T junctions; its lower corners are the PETSCII
rounded corner cells. RUN/STOP closes the current menu or prompt.
For example, **F1, V, H** selects GEOS and **F1, V, S** opens Settings.

| Menu | Available actions |
| --- | --- |
| File | Open, Save, Save As |
| Edit | Undo, Redo, Delete next character, Clear Undo/recover |
| View | 40/60/80 columns, GEOS, wrap, pan, preview/source, settings |
| Navigate | Up/down, pages, line/document ends,40-character jumps, words, GOTO, Find/next |
| Block | Mark, copy, cut, paste, fold toggle, collapse all, expand all |
| Help | Keyboard/SuperMark guide, document diagnostics |

**F7** opens a typed command line. Return executes; RUN/STOP cancels. Commands are
case-insensitive. Representative commands, including aliases without dedicated
menu items, are:

```text
mode 40          mode 60          mode 80          mode hires
home             end              top              bottom
up               down             page up          page down
jump -40         jump +40         word left        word right
goto 25          find text        findi text       next match
mark             copy             cut              paste
undo             redo             delete           clear undo
wrap             wrap on          wrap off
pan left         pan right
open             save             save as
fold             fold all         unfold all
preview          source           settings         diag
syntax plain     syntax markdown  syntax full
```

**F8** cycles 40→60→80→GEOS; **CTRL-F8** cycles in reverse. The 40-column view uses
native cells;60/80 use narrower bitmap text; editable GEOS uses proportional
BSW text and fixed-width code. All keep source markers visible and editable.
There is no source formatting command on CTRL-B or CTRL-I, and no `quit` command.

## Edit, navigate and select

| C64 key | Action |
| --- | --- |
| Printable keys / Return | Insert source text / CR newline |
| DEL / SHIFT-DEL | Delete previous character / insert a space |
| Cursors | Move caret; up/down preserve the preferred horizontal position |
| HOME / CTRL-E | Beginning / end of the logical CR-delimited source line |
| SHIFT-HOME | Top of document |
| F3 / F5 or CBM-Up / CBM-Down | Previous / next page |
| CBM-Left / CBM-Right | Move backward / forward 40 characters within the source line |
| CTRL-A / CTRL-W | Previous / next word |
| CTRL-G | GOTO prompt; line numbers start at 1 |
| CTRL-F / CTRL-N | Find prompt / next match |
| F2 | Mark/unmark; move the caret to extend a selection |
| CTRL-C or CTRL-K | Copy selection |
| CTRL-X / CTRL-V | Cut / paste |
| CTRL-Z / CTRL-Y | Undo / redo |
| CBM-F | Toggle the region containing the caret between folded and expanded |
| CBM-D / CBM-E | Collapse / expand the region containing the caret |
| CBM-S | Open session Settings directly |
| RUN/STOP | Clear selection or close the current popup/prompt |

Use Edit→D or F7 `delete` for forward deletion. A selection refers to canonical
source bytes, including markup and collapsed text. Copy preserves it; cut and
replacement operate on those bytes. Paste replaces an active selection.

`find text` searches literally; `findi text` ignores case. `next match` repeats
the search. GOTO uses logical line numbers, so soft wrapping does not add lines.
A GOTO or match inside a collapsed block opens its containing folds.

Undo/Redo history is finite. A new edit after Undo discards the redo branch;
opening another document starts a fresh history. `clear undo` deliberately clears
history and should not be used when you still need those edits.

**F4** toggles soft wrapping without inserting CRs. `pan left/right` enables the
unwrapped view and moves 20 columns in text modes or 20 pixels in GEOS. Manual
panning can hide the caret; ordinary source navigation reveals it again.

## Choose source processing and preview appearance

The presets change display processing, not document bytes:

| F7 command | Source behavior |
| --- | --- |
| `syntax plain` or `syntax off` | Literal source, no syntax parser or code-token coloring; folds shown expanded |
| `syntax markdown` | SuperMark structure and inline styles, uniform code color |
| `syntax full` or `syntax on` | SuperMark plus BASIC/assembler token colors |

Plain preserves stored collapse choices for the other presets. Formatted preview
remains an explicit formatting view even with Plain selected; its code-token
colors are enabled only in Full.

Open **CBM-S**, **F1, V, S**, or F7 `settings` in any mode. Settings affect
formatted preview; editable GEOS keeps its established source fonts.

| Settings key | Action |
| --- | --- |
| 1–8 or up/down| Select Body, H1–H6 or Code profile |
| F / S | Next font family / next supported size within that family |
| C / G | Cycle ink / paper color |
| B / I / U | Toggle bold / italic / underline for that profile |
| H | Cycle Plain→Markdown→Full source processing |
| R | Reset all appearance and source-processing settings to compiled defaults |
| Return / RUN/STOP | Close; already applied choices remain applied |

Settings are session-only. Restart restores the compiled defaults; Save does not
write appearance into the source file. Numeric sizes/colors use C64 hexadecimal
notation: `$18` means 24, `$0A` means 10. Fonts have genuine supplied sizes, not
arbitrary scaling. Code offers only the supported fixed-width faces. See the
[font catalog and C64 color-cell rules](GEOS_PREVIEW.md#session-settings).
Settings/H changes processing; **View/H** selects the GEOS view.

## Formatted preview

Select GEOS, then **F1, V, P** or F7 `preview`. Preview hides confirmed formatting
controls and uses the heading/body/code profiles. Unmatched inline delimiters
stay literal. It does not edit or replace the saved source.

In preview, **F3/F5** or up/down change pages; HOME returns to the top. **Return**
or **RUN/STOP** returns to editable source. F7 `source` and View/P toggle between
source and preview in GEOS. F8 switches mode and returns to source. Preview is
not available in the 40/60/80-column modes.

Menus, Help and Settings remain available. Closing Settings opened from preview
returns to preview. Typing, deletion, cut/paste and Undo cannot mutate source
while preview is active. Preview currently retains 32 page-back starts; it does
not yet provide word-aware wrapping or editing inside formatted text.

## Write SuperMark

SuperMark is PETSCII Markdown-lite. The examples below are readable host
transcriptions; use the C64's native characters in the document.

| Form | Meaning |
| --- | --- |
| `# Title` … `###### Title` | Heading levels 1–6, starting in column zero with a following space |
| `**bold**`, `*italic*`, `***both***` | Matched emphasis; may be nested within supported parser limits |
| `@@code@@` | Inline code; no emphasis or pound escapes inside it |
| `- item`, `* item` | Bullet list item |
| `1. item`, `27. item` | Numbered item; supplied numbers are preserved, not renumbered |
| `:::basic`, `:::asm`, `:::text` | Fenced BASIC V2, 6502/6510 assembler, or plain code |
| `:::region Title` … `:::end` | Explicit nested region |
| `£*`, `£#`, `£@`, `££` | Contextual literal syntax escapes using the native pound key |

Indent with spaces; typed Tab does not expand into four-column stops. Lists
recognize two-space indentation through three nested levels. Block markers
start in column zero; indented colon strings do not open fences. A leading `* `
is a bullet marker, not italic markup. Inline styles end at CR; unmatched markers
remain literal while typing. BASIC/assembler colors are lexical assistance,
not compilation or validation. Unknown code-language labels use plain code.

A fence opens with 3–15 colons and closes on a line containing **exactly the same
number of colons**, without a label or trailing text. To include a literal
three-colon line, use a longer fence:

```text
::::text
A literal closing-looking line:
:::
::::
```

A region uses exactly `:::region` and `:::end`; regions can nest. For example:

```text
# Notes
A **strong** idea and @@lda #0@@.
:::region Example
:::basic
10 PRINT "HELLO"
20 GOTO 10
:::
:::end
```

The native pound character (`£`, PETSCII `$5C`) replaces Markdown's backslash.
It escapes `# * - . : @ £` only where the following character would be syntax;
for example, `£# Title` at line start is literal. Currency such as `£5` stays
literal. Escapes are disabled inside fenced/inline code.

There is no underscore emphasis, backtick/tilde fence or backslash escape syntax.
Links, images, HTML, tables and block quotes are unsupported and stay literal.
There is no JSON highlighting. Return inserts CR, not a host LF; source views
preserve imported unsupported control bytes as data with visible markers.
Changing views never renumbers lists or rewrites the source.

## Fold without losing source

Heading sections (through the next equal or higher heading), fenced code and
explicit regions can collapse. Place the
caret in the desired unit and use **Block/F** or F7 `fold`; repeat to expand it.
Use `fold all` or `unfold all` for the document. There is no standalone `unfold`
command.

A collapsed unit keeps its summary/opener with an inverse `+`. Arrow/page
navigation skips the hidden body; direct GOTO/find reveals it. Selection and
copy/cut still include the hidden source. No hidden-line count or delete
confirmation is shown, so check the selection before a destructive edit.

Incomplete fence/region syntax during editing makes automatic fold retention
fall back to expanded source. You can keep typing and use Undo. Explicit
`fold all` still reports malformed fold syntax; it does not silently accept it.

## Save and handle a file dialog

**CTRL-S** or **F1, F, S** saves. An unnamed document opens Save As; **F1, F, A**
always asks for a new name. Filenames allow up to 16 native bytes. In the dialog:

- Type a name, DEL to erase, or up/down to select a listed file.
- F3 switches drive 8/9; F5 advances the directory page.
- F6 shows the dialog's own help; Return accepts; RUN/STOP cancels.

Opening over a dirty document asks **S** to save, **D** to discard or **C** to
cancel. Saving an unnamed document first asks for a name, then resumes the Open.
The clipboard survives opening another file; the document's Undo history does not.

Save writes and verifies a staged file before replacing the target, retaining
recovery candidates when DOS status is uncertain. It needs temporary free disk
space as well as room for the final file. On an error, read the dialog and keep
the disk attached until cleanup finishes; cancelling does not imply a save
completed. If a recovery dialog offers **K**, that explicitly keeps the precise
candidate files on disk. It is not a generic success acknowledgement.

A capacity error refuses an edit before changing source or pending text; existing
Undo remains usable. Source quota, append/history storage, object slots and disk
space are separate finite resources. See [capacity and tested limits](CAPACITY.md).
A D81 is 819,200 bytes including its filesystem and cannot store a 1 MiB document.

## Help and current limits

**F6** opens a three-page guide: keyboard/routes, inline/list syntax and
blocks/fences. **F3/F5** wrap between guide pages; **F6** or **RUN/STOP** closes
it and restores the source or preview. **Help/D** or F7 `diag` opens document
diagnostics. The normal source F3/F5 page keys are unchanged when Help is closed.

General reflow, cold startup and some far navigation/editing are still slow.
The 1 MiB capacity result is a bounded CPU/source-engine test, not a 1 MiB native
D81 save claim. See [current performance](PERFORMANCE.md), [capacity](CAPACITY.md),
[preview limitations](GEOS_PREVIEW.md) and [memory/standalone adapter scope](MEMORY_AND_ADAPTERS.md).
ReadyOS integration and UltimateDOS file access are future adapters; the current
standalone file workflow is drive 8/9 D81. This guide does not claim those adapters
or general performance work complete.
