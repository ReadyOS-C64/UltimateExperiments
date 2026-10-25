# SuperEditor standalone keys

Attach the D81 as drive 8, enable a REU, then enter:

```text
LOAD"SUPEREDITOR",8,1
RUN
```

Use a 16 MiB REU for the full development configuration. Reduced-capacity and
64KiB document checks are recorded separately in the acceptance evidence;
the full font image does not start with 512 KiB. Files contain raw PETSCII source.
VICE's PC-key mappings depend on its keyboard configuration; these labels refer
to C64 keys.

| Key | Action |
| --- | --- |
| F1 | Menus; type a menu letter, then an item letter |
| F6 | Keyboard help; F6 again closes it |
| F7 | Typed command; Return runs it, RUN/STOP cancels |
| F8 / CTRL-F8 | Next / previous display mode: 40, 60, 80, GEOS |
| F4 | Toggle soft wrapping |
| Cursors | Move the source caret; up/down retain the preferred horizontal position |
| F3 / F5 | Page up / down |
| HOME / CTRL-E | Start / end of source line |
| SHIFT-HOME | Top of document |
| CTRL-J / CTRL-L | Jump backward / forward 40 source characters |
| CTRL-A / CTRL-W | Previous / next word |
| Return / DEL | Insert newline / erase previous character |
| SHIFT-DEL | Insert a space; forward deletion is Edit→D or F7 `delete` |
| F2 | Mark/unmark a selection; move the caret to extend it |
| RUN/STOP | Clear a source selection; close a menu or prompt |
| CTRL-C or CTRL-K | Copy selected canonical source |
| CTRL-X / CTRL-V | Cut / paste |
| CTRL-Z / CTRL-Y | Undo / redo |
| CTRL-O / CTRL-S | Open / save |
| CTRL-G / CTRL-F / CTRL-N | Go to line / find / next match |

For example, F1,F,O opens a file and F1,F,A opens Save As. In a file dialog,
type a name and press Return; DEL erases, up/down choose a listed name,
F3 selects drive 8/9, F5 changes directory page, F6 shows dialog help, and
RUN/STOP cancels. A dirty Open asks S to save, D to discard, or C to cancel.
Opening a different file begins a fresh Undo history.

Useful F7 commands:

```text
mode 40          mode 60          mode 80          mode hires
top              bottom           home             end
goto 25          jump -40         jump +40
find text        findi text       next match
wrap on          wrap off         pan left         pan right
mark             copy             cut              paste
undo             redo             delete           clear undo
open             save             save as
fold             fold all         unfold all
preview          source           settings         diag
```

`findi` ignores case. `pan left/right` enables the unwrapped view and moves 20
columns in the text views or 20 pixels in GEOS. Manual panning may hide the caret;
ordinary source navigation reveals it again. A capacity error refuses the new
edit before changing the source or existing pending edit; Undo remains usable.

Editable GEOS keeps source markers visible. F7 `preview` opens a separate,
read-only formatted view: F3/F5 or up/down change pages, Return or RUN/STOP returns
to source. F7 `source` also returns. Menus/help remain available. Formatting
controls are hidden only in preview; saved files retain the original source.

F7 `fold` toggles the region at the caret. Fold summaries show an inverse `+`;
selection, copy/cut and saved files still refer to the complete source. Direct
GOTO/find into hidden text opens its ancestors. Arrow/page navigation skips
collapsed bodies.

F7 `settings` changes preview profiles: 1–8 choose Body, H1–H6, Code; F changes font,
S size, C/G ink/paper, B/I/U bold/italic/underline, R restores defaults, Return
closes. These settings last only for the session. See [GEOS preview and
appearance](GEOS_PREVIEW.md) for the actual font catalog and C64 color constraints.
