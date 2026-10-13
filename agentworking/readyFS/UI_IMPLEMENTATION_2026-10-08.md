# ReadyFS UI implementation — 2026-10-08

This continues the historical grounding in `THREAD_GROUNDING.md`. It describes
new work in this chat, rather than the August thread's baseline.

Status: **complete**. The complete build, host/VICE checks, and all 55 physical
checks pass, including 1/16/64 MHz interaction and the 800-row ring wrap.

## Intent and scope

The user requested responsive long command entry, continuation, Up/Down command
history, independent REU output history with paging, exact short command and
option aliases, and physical C64U testing. They additionally emphasized that
redrawing on every key produces a bad experience on slow 8-bit machines.

The full interactive target is `readyfs-overlay.prg` with its generated D81
fixture. The monolithic PRG remains a smaller diagnostic application with its
basic reader. It already lacked several full-overlay facilities; fitting the
new editor into that diagnostic's resident memory was not silently assumed.
README and the interactive guide identify the correct user-facing target.

## Editor behavior and performance

- Logical command length remains 255 bytes, in the resident 256-byte line buffer.
- Four input rows hold 36 characters each, following a four-character prompt.
  Up to eight logical rows can be navigated through a four-row viewport.
- The window follows the cursor. Screen wrapping adds no bytes to the command.
- Normal append and overwrite paint one character. Backspace at the end paints
  one blank. Editing inside the command paints only the affected visible suffix.
- Cursor movement paints no command text unless it changes the viewport.
- A history recall or viewport change redraws the input rows; output above them
  is untouched. Input legends change only when their state changes.
- Cursor-row calculation is reused across viewport decisions and cursor placement,
  reducing repeated division in the hot path.
- Unsupported function/control keys do not become command characters. F3 at the
  live prompt is a no-op; paging controls remain independent from command history.
- The host test measures conio text writes on ordinary editing and exercises the
  255-byte boundary and each viewport crossing. The ordinary cursor blink is
  separate from those application writes.

Continuation accepts F7, Shift+Return, an open quote on Return, or a trailing
backslash on Return. It inserts a joining space and continues the same command;
it does not create separate commands or file-data line endings. Both ASCII-host
and cc65/C64 representations are tested in their respective environments. The
physical driver must convert a textual backslash into cc65's PETSCII $BF; writing
ASCII $5C directly injects the C64 pound character instead.

Up walks 32 executed-command records in REU. The first Up saves the current
256-byte draft plus cursor, overwrite, and continuation state. Down past newest
restores them. Oldest-history bounds do not redraw. The existing twelve-token
parser limit remains distinct from the 255-byte editing limit.

## Output capture and paging

A resident assembly console replaces the relevant conio output entry points.
Every completed physical output row is captured before cursor advance or bottom
scroll. It captures command echoes, wrapped output, and ordinary command output;
editor and browser drawing disable capture to avoid polluting the transcript.
The initial banner is printed before REU initialization; subsequent startup rows
and command output are captured.

The ring contains 800 rows, each 40 screen codes plus 40 colors: 64,000 bytes in
a dedicated REU bank. Oldest rows are replaced when full. Clear affects only the
live screen. F1 enters the latest 23-row page, then moves older; F3 moves newer
and then returns live. Commodore+Up/Down supply corresponding paging controls.
Stop or Return also exits browsing. Existing directory `-- more --` handling
continues to acknowledge a key; browsing is entered from the command prompt.

The browser stashes the live 1,000-byte screen and 1,000-byte color map, preserving
the current draft. Pages use REU DMA, avoid clearing the entire screen before
fetching, and draw the legend once per entry. Unchanged page boundaries do not
fetch/redraw. The hardware screen comparison normalizes only the draft cursor's
reverse-video blink bit; color comparisons mask the electrically irrelevant
upper nibble of color RAM.

A scrolling bug found during this work was corrected: copying three overlapping
screen pages interleaved by X would overwrite source bytes before later reads.
The replacement moves complete pages in ascending address order, followed by the
192-byte tail, for both screen and color RAM.

## Alias semantics

The complete lookup table uses exact case-insensitive tokens, not prefixes.
All normal command families have one- or two-character forms, including `fm` for
format. Existing cp/mv/md/rd/ls/rm aliases remain. The guide contains the full map.
Fifteen short option tokens cover all existing long-option behaviors; `-w`
expands to --dry-run, which has the same preview effect as --whatif.

Expansion begins after mandatory positional arguments, preserving paths/text
that resemble flags. Values of exclude/include/name/type/label/id remain literal,
including a value such as `-f`. Expanded pointers refer to resident strings,
never strings inside the soon-to-be-replaced overlay window. High-bit lookup-only
file-type IDs bypass argument expansion.

Two existing literal-name consumers required attention:

1. Preview previously classified writes/deletes/mounts by long command spelling.
   Resident now passes the decoded numeric command ID through utility.value_low,
   so every short form reports the same proposed operation counts. Preview still
   reports zero completed writes/deletes/mounts, even when --apply is present.
2. Cooperative batch parsing rejects both run and ru as nested-script commands,
   maintaining the same typed error and stop policy.

Alias table set/list/remove logic moved from resident into the batch sidecar to
make resident space for continuous capture. Path resolution and all device I/O
remain resident-owned. The alias record layout and existing configuration format
retain their addresses and sizes.

## Memory and architecture

There are now thirteen sidecars. UI/command lookup occupies slot 13; tree traversal
stays in slot 8, while batch/alias handling is slot 10. Resident numeric dispatch
remains the interface, and all physical I/O remains outside sidecars.

REU reservations relative to detected bank count:

- Last: 32 history records at $0000–$1FFF; session storage based at $2000.
- Last minus one: original overlay caches, tree queue, recursive cache.
- Last minus two: batch cache $0000–$0FFF; script $1000–$4FFF; checkpoint
  $5000–$50FF; tape cache $5100–$60FF; UI cache $6100–$70FF; live screen
  $7100–$74E7; live colors $7500–$78E7; draft $7900–$79FF.
- Last minus three: continuous output ring $0000–$F9FF.

Retired whole-page scrollback regions remain reserved so configuration, action,
and recursive session offsets stay stable. Public overlay/session/batch/console
DMA uses the flat six-byte assembly boundary in both variants. Its implementation
avoids cc65 runtime zero-page temporaries. The console capture also uses assembly.

Final build report currently shows resident end $B587, 36 safe bytes before
KERNAL scratch $B5AC; monolithic end $C2A0; UI sidecar exactly $1000; cc65 stack
top $D000. The UI slot is full, so future additions require moving/simplifying
code rather than increasing that window. Other established sidecar boundaries
and REU-region disjointness continue to be checked by the complete build.

## Verification and evidence

Complete `make readyfs` passes compilation, all host tests, UCI contract,
overlay/DMA and pipeline contracts, and the expanded memory/REU report.

New/expanded host checks include:

- Ordinary screen-write counts, insertion/deletion/overwrite, controls ignored,
  255-byte bounds, viewport crossings, editable history and draft restoration,
  continuation, exact flag expansion, and literal-valued options.
- Exact lookup for every short command and rejection of ambiguous prefixes.
- Proposed operation counts for short mutation commands, including format,
  and zero completed operations in preview.

VICE evidence:

- `ReadyFS/logs/vice_auto_20261008_151449`: editor/history success, including exact
  256-byte RAM oracle for 255 characters plus NUL.
- `ReadyFS/logs/vice_auto_20261008_150847`: continuous scrollback, newer/older
  pages, and return to the live prompt.
- `ReadyFS/logs/vice_auto_20261008_151654`: complete existing batch-policy suite.
- `ReadyFS/logs/vice_auto_20261008_152058`: batch-policy success after changing
  the nested-script fixture to use the ru alias.

Physical runner: `start_readyfs_c64u_editor_terminal.sh` opens an independent
Terminal process; no foreground Codex networking is used. It refuses occupied
Drive A, mounts only the local build fixture in RAM on an already-enabled 1581
bus 8, uses read-only commands and session-only aliases, and restores exact saved
CPU settings and empty Drive A even on failure. The fixture includes a 900-command
read-only script to force output-ring wrap.

Earlier hardware attempts are retained. They exposed runner issues (CPU value
padding, missing @/reverse-video support in screen decoding, polling before screen
drawing finished, ASCII-versus-PETSCII backslash encoding, and an oracle that
incorrectly expected `PW D` to be unknown although PW is now the pwd alias). Restoration was
verified in each failed/interrupted attempt. Intermediate runs remain archived
with their actual statuses. Attach-live mode compares resident CODE and RODATA
against the current PRG before reusing an initialized application. The final
passing run and matching build hashes are recorded below.

### PETSCII comparison detail discovered in the wrap test

The C64-target assembler translates character literals such as `'A'` to PETSCII.
The resident word comparer first masks bit 7. Its old comparisons against
`#'A'` / `#'Z'+1` therefore could not perform the intended ASCII case fold.
Explicit numeric bounds `$41` / `$5B` fix this without growing resident code.
The lowercase `pw` commands in the ring fixture exposed the issue on hardware.
Utility and batch code now use the same resident comparer under cc65, while
host builds retain their normal ASCII implementation. This also makes
script keywords and native/ASCII option spellings consistent. Resident option
strings are PETSCII-encoded by the assembler; returned pointers remain valid
after the UI overlay is replaced.

Physical interaction evidence before that final comparer fix:
`ReadyFS/logs/readyfs_c64u/editor-20261008-152702` contains all 1/16/64 MHz
interaction passes and verified restoration, but its overall status is failed
because the lowercase ring script stopped at the first command. Do not call
that run an overall pass. The final build was freshly booted in
`ReadyFS/logs/readyfs_c64u/editor-20261008-153305`; that attempt stopped at
the directory-transfer polling issue. The verified reattachment run below passes.

The final comparer build also passes the focused emulator plan in
`ReadyFS/logs/vice_auto_20261008_153922`: `fi 8:/ -i RFVIEW` completes, and
the lowercase 900-command ring fixture completes with RC 0. Physical screen
polling during IEC enumeration was observed to interrupt a directory transfer
(FIND FAILED after 13 files), so the runner now leaves a five-second quiet
interval before capturing that command's screen. This is transport-test pacing,
not UCI transaction pacing. The physical adjustment is proven by the final passing run.

## Final physical result

`ReadyFS/logs/readyfs_c64u/editor-20261008-154022/status.txt` is **success**.
Its `verification-summary.json` records 55 passing cases and SHA-256 hashes of
the tested resident, UI sidecar, and D81 image. This run verified every immutable
resident CODE/RODATA byte against the current build before reusing the initialized
application from the fresh 153305 boot.

At **1, 16, and 64 MHz**, the final run proved exact 255-character RAM contents,
wrapped display, editable command history with draft restoration, continuation
and execution, command and include-option aliases, preview alias operation counts
with zero completed mutations, UCI detection, independent output paging, and
restoration of the live draft and color map. Session alias set/list/resolve/remove
also passed.

The lowercase **900-command** script completed with **RC 0**. The resident output
count reached **800**, and the newest/oldest ring pages plus return-live and
ignored function keys passed. Original CPU settings were compared field for
field after restoration, and Drive A returned to its original empty state. No
USB/SD filesystem data was created or modified.

Final operational entry points: `docs/READYFS_INTERACTIVE_UI.md`, the complete
`make readyfs` gate, `run_readyfs_vice_editor.sh`, `run_readyfs_vice_scrollback.sh`,
`run_readyfs_vice_batch.sh`, the focused `readyfs_vice_ui_find_ring.yaml` plan,
and `start_readyfs_c64u_editor_terminal.sh`. The optional attach-live mode refuses
a resident program whose immutable bytes differ from the current build.
