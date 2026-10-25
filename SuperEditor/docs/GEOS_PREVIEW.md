# GEOS preview and appearance

The editable GEOS source view and formatted preview are separate presentations.
Both use the same PETSCII document. Preview never rewrites markup or saves a
formatted copy over the source.

From F7, enter `mode hires`, then `preview`. Return or RUN/STOP returns to editable
GEOS source. F3/F5 or up/down page through preview; F1 menus, F6 help and F7 typed
commands remain available. F8 changes display mode and returns to source editing.
Typing, deletion and text mutation commands are ignored while preview is active.
The page-back stack currently retains32 page starts. Word-aware preview wrapping
and source-mapped formatted editing remain future work.

Preview hides confirmed emphasis/code delimiters, heading prefixes, confirmed
escape introducers and fence/region control lines. Unmatched delimiters remain
literal. Native hyphen and numbered list prefixes remain visible. Region titles
can contain inline emphasis; the explicit close is `:::end`. BASIC and assembler
code keep their own fixed-width font and syntax colors. JSON highlighting is not
part of the dialect.

## Collapsed regions

F7 `fold`, `fold all` and `unfold all` share the document's fold state with the
40/60/80-column views. Editable GEOS source retains the opener and displays an
inverse yellow `+` at its newline. A selection crossing hidden bytes highlights
that marker; copy/cut still operate on the original source bytes.

Formatted preview keeps styled heading/region titles and their selected fonts.
A collapsed BASIC or assembler fence keeps its literal `:::basic` or `:::asm`
label in the selected fixed-width code font. Its inverse `+` uses that font
without bold/italic/underline, yellow ink and the containing band's background.
The marker wraps normally, including onto the next preview page when necessary.
Changing fold state resets the preview page-back history.

Up/down and page navigation skip collapsed bodies in the editable view. A direct
GOTO or search target inside hidden source opens its containing ancestors.
Folding never removes source bytes or changes the saved file format.

## Session settings

F7 `settings` opens the dialog in any display mode. Changes affect formatted
preview; editable GEOS source continues to use its established BSW/9 and native8
presentation. Source text, selection, undo and saved files do not contain settings.

| Key | Action |
| --- | --- |
| 1–8 or arrows | Body, H1–H6, Code profile |
| F | Next font family |
| S | Next genuine size in that family |
| C / G | Foreground ink / background paper |
| B / I / U | Bold / italic / underline |
| R | Restore compiled defaults for all profiles |
| Return / RUN/STOP | Close |

Size and color fields use explicit C64 `$` hexadecimal notation. `$18` is24,
`$12` is18 and `$0A` is10. Font names are shown in the dialog. Only sizes present
in the original GEOS font files are offered; there is no bitmap scaling.

The44 choices consist of BSW/9, native/8 and42 genuine GEOS file faces:

| Family | Genuine sizes (decimal) |
| --- | --- |
| University | 6,10,12,14,18,24 |
| California | 10,12,14,18 |
| Roma | 9,12,18,24 |
| Dwinelle | 18 |
| Cory | 12,24 |
| Commodore | 10 |
| LW Roma, LW Cal, LW Greek, LW Barrows | 9,10,12,14,18,24 each |

Code admits native/8 or Commodore/10, the measured fixed-width faces. Both use
8-pixel advances. Bold/italic code ink is clipped within that advance so columns
stay aligned. Graphics absent from a GEOS face use the native PETSCII fallback.
LW Greek deliberately retains its original glyph repertoire.

Profiles share the C64's real two-color-per8×8-cell limit. Preview aligns each
text band to an8-pixel boundary, aligns mixed fonts by baseline and uses the block
profile's background for the band. The first glyph depositing ink in a cell
chooses its foreground. Fixed8-pixel code columns align with color cells; lexer
colors override the code profile's base ink for recognized tokens. Inline code
uses the code font while retaining the containing paragraph's background.

Settings are session-only. Restart restores compiled defaults. For repeatable
testing, edit `config/editor-defaults.toml` and rebuild `make editor
build/supereditor.d81`. For example:

```toml
[heading1]
font = "roma"
size = 18
foreground = 6
background = 7
bold = true
italic = false
underline = true
```

The compiler validates the complete table before publishing it. A proportional
code face, nonexistent size or invalid color is refused. Reset reads the table
embedded in its overlay, not startup code that may have been reclaimed.

## Implementation and verification

C27 coordinates bounded source/parser jobs; R23 fetches/rasterizes genuine fonts.
C7 controls settings and R22 draws the shared popup. There is no same-slot overlay
nesting. The GFC1 pack contains43 native records, including the system BSW font,
in74,432 bytes across two typed logical REU allocations. Pack/face CRCs and actual
logical/physical ownership are checked before use.

The maximum4210-byte font temporarily occupies `$5000-$6071`, sharing the overlay
stage and114 bytes of top chrome. Document pixels start atY16/`$6280`; chrome is
repainted after the final glyph. A new page or overlay stage write forces validation and
refill before a font pointer is used. Glyphs within the same verified font window
reuse its capability and face witness; the public strict fetch API still checks CRCs. The ReadyOS `$C600-$C9FF` reservation remains
untouched. `$CA00-$CFFF` is now a second CPU-only warm extent; future suspend/resume
must include it explicitly in addition to `$1000-$C5FF`.

Verification commands:

```sh
python3 tests/test_geos_preview_editor.py --run
python3 tests/test_geos_preview_settings.py --run
python3 tests/test_geos_preview_vice.py --run
```

CPU tests use explicit ROM file-transport seams. Native tests perform real D81
startup/font import and File/Open through the .NET VICE harness with warp/traps,
compare actual VIC pixels to a canonical-source/raw-font reference, and retain
source/history/REU/reserved-memory evidence. Physical key chords, PAL/NTSC speed,
full lifecycle integration and the wider standalone completion gates remain open.
