# ReadyFS interactive editor and REU output history

The full interactive application is **readyfs-overlay.prg**, with
**readyfs-overlay-lab.d81** mounted on IEC device 8. Keep all 28 sidecars
on that disk; startup caches them in the REU. `readyfs.prg` is the smaller
monolithic diagnostic variant and retains its basic input reader. Use the
overlay application for this editor, option shorthand, scripts, and scrollback.

For a concepts-first walkthrough with screenshots and a full command reference,
see the [illustrated user guide](READYFS_USER_GUIDE.md) or its
[standalone print edition](READYFS_USER_GUIDE.html).

## Batch scripts

Use `RUN script-path [arg1 ... arg9]` or `RU`. The [RUN reference](READYFS_RUN_GUIDE.md) documents session/persistent variables, `%0`–`%9`, conditions, counter loops, same-file CALL and shared subroutine inputs, result handling and all limits. Its BACKUP.SEQ example is demonstrated in the appended physical video chapter. Separate-file CALL, nested RUN, SHIFT and FOR are not supported. TYPE streams the script; use F1/F3 output history to read earlier lines.

## Editing

The logical command can contain **255 bytes**. Four visible input rows each
hold 36 command characters, following `rf> ` or `..> `. The window follows the
cursor through longer commands. Wrapping changes presentation; it does not
insert bytes into the command. Paths and text containing spaces still need
quotes, and the existing parser has a twelve-token limit.

| Key | Action |
| --- | --- |
| Left / Right | Move within the command |
| Home / Shift+Home | Beginning / end of the command |
| Delete | Delete the character before the cursor |
| Insert | Toggle insert / overwrite (`ov>`); initially insert |
| Up / Down | Older / newer executed command; Down past newest restores the draft |
| Return | Execute the logical command |
| Trailing backslash + Return | Replace the backslash with a space and continue |
| Return with an open double quote | Continue the quoted command with a space |
| Shift+Return or F7 | Insert a joining space and continue |
| Run/Stop | Cancel the draft |

Continuation joins parts of one command. It does not execute a batch of
commands and does not add a newline to a file's contents. The same 255-byte
limit applies to the joined command. Closing a quote and pressing Return runs
it. At the limit, further printable characters are ignored; Delete frees room.

Command history uses 32 REU records of 256 bytes. Up/Down recall remains
editable. The unfinished draft, cursor position, and insert mode are preserved
in separate REU storage while walking history. History does not persist across
application restart.

## Output history

At the prompt, **F1** enters the most recent output page and then moves older.
**F3** moves newer and, at the newest page, returns to the live editor.
Commodore+Up/Down provide the same paging actions. Run/Stop or Return returns
to live output immediately. F3 at the live prompt leaves the editor alone.

The output ring stores **800 physical rows**, with both 40 screen characters
and 40 color bytes per row: 64,000 bytes in a separate REU bank. It captures
completed rows continuously, including wrapped output and command echoes.
`clear` clears the live screen while retaining scrollback. Once full, the ring
replaces its oldest row. Pages contain up to 23 output rows. The live 1,000-byte
screen and 1,000-byte color map are preserved in REU and restored exactly when
leaving history, including the current draft.

The editor and history-browser legends are excluded from the output ring.
Paging is available from the command prompt; existing `-- more --` directory
prompts still wait for a key before continuing enumeration.

## Screen work

Ordinary editing does not clear or repaint the screen:

- Append or overwrite: one character cell.
- Delete at the end: one blank cell.
- Insert/delete within text: only the changed suffix, clipped to visible rows.
- Cursor movement: no editor text writes, except when the visible window changes.
- Reaching the oldest history entry, or paging past an output boundary: no repaint.
- Legend: only when continuation state changes.
- History recall or viewport movement: redraw the four input rows; output above
  them remains untouched.
- Output paging: REU DMA restores the requested characters and colors.

The C64's ordinary input-cursor blink still operates. The host screen-write
oracle counts application drawing separately from the cursor.

## Exact short names

Names match complete tokens, case-insensitively. Prefix abbreviations are not
accepted, so adding future commands cannot silently change the meaning of an
existing short name.

| Short | Command | Short | Command |
| --- | --- | --- | --- |
| q | exit | h | help |
| pb | probe | pf | profile |
| nt | native | dv | drives |
| pw | pwd | hi | history |
| cl | clear | cd | cd |
| al | alias | ua | unalias |
| cf | config | d / ls | dir |
| tr | tree | st | stat |
| vl | volume | mt | match |
| ty / cat | type | cp | copy |
| mv | move | rn / ren | rename |
| dl / rm | delete | cm / verify | compare |
| nw | new | wr | write |
| ap | append | md | mkdir |
| rd | rmdir | mo | mount |
| um | dismount | sw | swap |
| ca | capabilities | ss | status |
| fi | find | hd | head |
| tl | tail | cr | crc32 |
| ts | test | ru | run |
| fm | format | | |

| Short option | Long option |
| --- | --- |
| -r | --recursive |
| -w | --dry-run (same preview effect as --whatif) |
| -x VALUE | --exclude VALUE |
| -f | --force |
| -i VALUE | --include VALUE |
| -l | --line |
| -n VALUE | --name VALUE |
| -np | --native-pattern |
| -t VALUE | --type VALUE |
| -y | --yes |
| -a | --apply |
| -c | --continue |
| -lb VALUE | --label VALUE |
| -id VALUE | --id VALUE |
| -ds | --disposable |

Options are expanded only after mandatory positional arguments. Values of
exclude/include/name/type/label/id remain literal, even when they look like an
option. Short names preserve the existing command's validation, confirmations,
and ownership requirements; they do not bypass them.

Examples:

```
hd 8:/rfview 2
cp u:/SOURCE u:/DEST -r -w -x "*.bak"
fi 8:/ -i "*.prg"
```

## Layout and verification

REU banks are reserved relative to the detected size:

- Last bank: 32 commands at `$0000–$1FFF`, session region based at `$2000`.
- Last minus one: existing overlay cache, tree queue, and recursive sidecar.
- Last minus two: batch/tape cache plus UI cache `$6100–$70FF`, live screen
  `$7100–$74E7`, live colors `$7500–$78E7`, draft `$7900–$79FF`.
- Last minus three: output ring `$0000–$F9FF`.

The old whole-page scrollback reservation remains unused in the session bank
so existing configuration/action regions retain their addresses.

`make readyfs` checks host behavior, UCI contracts, flat assembly DMA calls,
sidecar size limits, resident/KERNAL scratch separation, and REU disjointness.
`readyfs_ui_test.c` exercises minimal screen writes, insertion/deletion,
255-byte bounds, viewport changes, editable history with draft restoration,
continuation, and literal-valued option aliases. VICE checks the actual C64
buffer and screen. `start_readyfs_c64u_editor_terminal.sh` runs the read-only
physical suite at 1/16/64 MHz and restores the saved CPU settings and empty
Drive A. It refuses occupied or differently configured Drive A.
