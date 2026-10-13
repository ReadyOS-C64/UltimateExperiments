# ReadyFS RUN guide

Updated 13 October 2026 for DOS-style batch scripting. This reference is also included in the [illustrated user guide](READYFS_USER_GUIDE.md#run-scripts-parameters-previews-and-reliable-execution).

## RUN scripts: parameters, previews and reliable execution

`RUN script-path [arg1 ... arg9]` (short form `RU`) executes a text script of ReadyFS commands in the **overlay application with working REU and sidecars**. It reads and stages the whole file, closes its input stream, then dispatches commands one at a time. This is ReadyFS command scripting; it does not load and start a C64 PRG or BASIC program.

### What parameters belong where?

| Where | Example | Meaning |
|---|---|---|
| RUN invocation | `RUN @lab:/INSPECT.SEQ` | Script path, optionally followed by up to nine arguments. |
| Short invocation | `RU 8:/INSPECT` | Same command; use the actual disk directory name. IEC names do not automatically gain `.SEQ`. |
| Quoted script path | `RUN "@lab:/INSPECT NOTES.SEQ"` | One path containing spaces. |
| Inside the script | `COPY @src:/README.SEQ @dst:/README.SEQ --whatif` | COPY receives its source, destination and options. |
| Session setup | `ALIAS SRC u:/usb1/READYFS_TEST/YOUR_FRESH_RUN/source` | An alias supplies a reusable location to script commands. |

### DOS-style variables and flow control

The current overlay build supports session variables, saved variables, script arguments, branches, counted loops and label subroutines. Type `HELP BATCH` or `HELP SET` on the C64 for the compact reference.

| Command or expansion | Behavior |
|---|---|
| `SET NAME=value` | Set a session variable. A plain SET changes an existing saved variable to session-only. |
| `SET /P NAME=value` | Mark this variable for the next `CONFIG SAVE`. `/P` means persistent in ReadyFS. |
| `SET NAME=` | Delete a variable, including its persistent flag. |
| `SET` / `SET NAME` | List variables with `/P` markers, or show one value. |
| `%NAME%` / `%ERRORLEVEL%` | Expand a variable or the preceding command result. Undefined variables expand to empty text. Names are case-insensitive. ERRORLEVEL is read-only. |
| `%0`, `%1` … `%9` | Script path and up to nine RUN arguments. Missing arguments expand to empty text. |
| `%%` | Insert a literal percent sign. |
| `SET /A N=N+1` | Evaluate an unsigned 16-bit integer, or one addition/subtraction. Operands are decimal literals or variable names; undefined operands are zero. Results wrap at 65536. Use `SET /P /A` to retain the persistent flag. |
| `ECHO text` / `REM comment` | Print text or ignore the whole line. Whole-line `#` comments also work. |
| `:LABEL` / `GOTO LABEL` | Declare a label or jump to it. Labels are case-insensitive, up to 16 bytes; the first matching label wins. |
| `CALL :LABEL` | Run a label subroutine in the same staged script, sharing variables and arguments. Maximum nesting: eight. |
| `EXIT /B [code]` / `GOTO :EOF` | Return from a subroutine, or finish the top-level script. EXIT /B can set a result from 0 to 255. Reaching the physical end of a subroutine also returns. |
| `IF [NOT] ERRORLEVEL n command` | Run the command when the preceding result is **greater than or equal to** n, optionally negated. |
| `IF [NOT] DEFINED name command` | Test whether a variable exists. |
| `IF [NOT] EXIST path command` | Test the filesystem through ReadyFS's normal path and backend handling. A lookup failure stops the script with result 8. |
| `IF [NOT] "a"=="b" command` | Compare exact, case-sensitive strings. A spaced `a == b` comparison also works. |
| `IF [NOT] n EQU\|NEQ\|LSS\|LEQ\|GTR\|GEQ n command` | Compare unsigned integers from 0 to 65535. Expand variables explicitly, for example `IF %N% LSS 3 GOTO LOOP`. |

For example, save this with real line breaks and run `RUN 8:/COUNT WORLD`:

```text
REM ARGUMENTS AND A COUNTED LOOP
SET WHO=%1
SET /A N=0
:LOOP
SET /A N=N+1
ECHO HELLO "%WHO%" %N%
IF %N% LSS 3 GOTO LOOP
CALL :FINISH
EXIT /B 0
:FINISH
ECHO DONE
EXIT /B
```

Expansion happens once before tokenization on each executed line. Quote an expanded value when it must remain one argument: `COPY "%SOURCE%" "%TARGET%"`. Values are not expanded recursively. To write literal variable references into a script from the interactive prompt, double their percent signs, for example `WRITE 8:/SHOW "ECHO %%NAME%%" --line`. RUN arguments such as `--yes` are ordinary `%1`/`%2` values; they do not become global confirmation or preview options. Put those options on the intended operation inside the script.

There are 16 variable slots, with names up to 16 bytes and values up to 127 bytes. Names use letters, underscores and digits after the first character. Variables can be used interactively and inside scripts. `CONFIG SAVE` writes only variables marked `/P`, alongside the current directory and aliases, in the new RFC2 format. `CONFIG LOAD` validates the complete file before applying it, replaces the saved-variable set, and preserves unrelated session variables. A loaded saved variable takes precedence over a session variable with the same name. If the merged table would exceed 16 slots, loading fails without changing the session. Legacy RFC1 configs still load their directory and aliases and leave variables alone. Loading config is explicit after startup.

RUN remains bounded to a 16 KiB staged script and 255 bytes per expanded line, with at most 12 tokens. Tabs and spaces separate arguments; balanced double quotes can occur within an argument. Excess tokens, unmatched quotes and invalid expansion produce result 4 before command dispatch. Scripts stop after 10,000 executed lines to bound accidental loops; RUN/STOP cancels execution between interpreted lines with result 3. Filesystem operations retain their existing cancellation behavior. ONERROR STOP remains the default; use ONERROR CONTINUE before a command whose failure you intend to inspect with IF ERRORLEVEL. Comments, labels and false IF branches preserve the preceding result; SET and ECHO produce their own result.

This is a bounded DOS-style language. Loops use labels, arithmetic and conditional GOTO; CALL targets labels in the same file. Nested RUN, external-script CALL, FOR, SETLOCAL, pipes and redirection are not implemented. Scripts share aliases and the current directory, and relative paths resolve against that directory rather than the directory containing the script.


The recipes below are syntax examples reviewed against the implementation and existing batch fixtures; they are **not additional steps in the recorded 37-step video**. Set `@lab`, `@src` and `@dst` to your own intended locations before use. Mutation examples belong in a fresh disposable test folder.

### Example 1 — a small read-only script

Save this as `INSPECT.SEQ`, with real line breaks:

```text
# READ-ONLY INSPECTION
ONERROR STOP
PWD
EXPECT RC 0
MATCH "*" "ABC"
EXPECT RC 0
HEAD @src:/README.SEQ 2
EXPECT RC 0
```

Set its source location and run it:

```text
ALIAS LAB u:/usb1/READYFS_TEST/YOUR_FRESH_RUN
ALIAS SRC @lab:/source
RUN @lab:/INSPECT.SEQ
```

`HEAD` receives two parameters: a filename and the number of lines to display. `MATCH` receives a pattern and a candidate string. Successful assertions print `EXPECT RC OK`. A complete successful run ends with a `RUN DONE ... RC 0` summary. The line/command totals depend on comments, directives and line endings; ordinary commands count separately from `ONERROR` and `EXPECT`.

You can create a tiny script directly in ReadyFS, using a new filename:

```text
WRITE @lab:/CHECK.SEQ "ONERROR STOP" --line
APPEND @lab:/CHECK.SEQ "PWD" --line
APPEND @lab:/CHECK.SEQ "EXPECT RC 0" --line
HEAD @lab:/CHECK.SEQ 10
RUN @lab:/CHECK.SEQ
```

Each `--line` writes a real carriage return. Typing `\n` in a quoted string does not create a new script line. Existing-file replacement may prompt; use a fresh name unless replacement is intentional.

### Example 2 — reuse one script with different locations

Save this as `PREVIEW.SEQ`:

```text
ONERROR STOP
COPY @src:/README.SEQ @dst:/README.SEQ --whatif
EXPECT RC 0
COPY @src:/ALPHA/ONE.SEQ @dst:/ONE.SEQ --whatif
EXPECT RC 0
```

First location pair:

```text
ALIAS SRC @lab:/source
ALIAS DST @lab:/first-copy
RUN @lab:/PREVIEW.SEQ
```

Second location pair, same script:

```text
AL DST @lab:/second-copy
RU @lab:/PREVIEW.SEQ
```

The script resolves the aliases when each command runs. These previews do not create destination folders or prove that source files exist, that media is writable, or that the backend supports the eventual copy. Inspect the paths separately before executing real writes. For a single-file COPY, the destination names a **file**; a recursive COPY uses an existing destination **container**.

### Example 3 — preview a tree, then execute a separate copy script

First create `PLAN.SEQ`:

```text
ONERROR STOP
COPY @src:/ @dst:/ --recursive --whatif
EXPECT RC 0
```

Set `@src` to the source directory and `@dst` to an intended new container, then run `RUN @lab:/PLAN.SEQ`. Read the named selection. A preview performs no mutation and is not a queued job.

For the real operation, prepare `COPYTREE.SEQ` separately:

```text
ONERROR STOP
MKDIR @dst:/
EXPECT RC 0
COPY @src:/ @dst:/ --recursive
EXPECT RC 0
TREE @dst:/
EXPECT RC 0
```

Then execute it with `RUN @lab:/COPYTREE.SEQ`. The destination must be new for this recipe; MKDIR failing on an existing folder is a reason to stop and inspect it. Copy includes verification by default. `ONERROR STOP` stops after a nonzero command result; it does not roll back an earlier successful MKDIR or partially completed copy. Check the COPY reports, batch failure count and resulting tree as well as the script RC.

For a deliberately chosen copy without destination readback, change the COPY line to:

```text
CP @src:/ @dst:/ -r -nv
```

`--no-verify` / `-nv` is a COPY/MOVE option, not a RUN option. You can later run `COMPARE @src:/README.SEQ @dst:/README.SEQ` for a specific file. One comparison does not verify an entire tree.

### Example 4 — supply explicit confirmation inside the script

RUN cannot answer interactive confirmation prompts. An operation that would ask returns `BATCH NEEDS --YES` and script result 3 instead.

| Intended script operation | Parameters on that script line |
|---|---|
| Preview deletion | `DELETE @lab:/scratch --recursive --whatif` |
| Delete only approved disposable descendants | `DELETE @lab:/scratch --recursive --yes` |
| Remove the resulting empty root | `RMDIR @lab:/scratch --yes` |
| Intentionally replace one destination file | `COPY @src:/README.SEQ @dst:/README.SEQ --force` |
| Ordinary fresh copy | `COPY @src:/README.SEQ @dst:/README.SEQ` — no replacement approval is needed if it is genuinely new. |

Inspect each target before adding confirmation. `--force` authorizes supported replacement; it does not add a missing backend capability. Current confirmation lookup also accepts `--yes` where force is checked, so it can authorize replacement too. Use the option that expresses your intention rather than adding both to every line. Native-pattern mutations additionally require `--apply` on that command; formatting has separate disposable-media requirements. There is no universal “make this script succeed” switch.

### Example 5 — expect an error deliberately, then continue

```text
ONERROR CONTINUE
BOGUS
EXPECT RC 1
ONERROR STOP
PWD
EXPECT RC 0
```

This intentionally dispatches an unknown command, checks its code, then restores normal stopping. `ONERROR CONTINUE` must appear **before** a command whose nonzero result you want to examine; with STOP, execution ends before the following EXPECT can run.

A mismatched EXPECT sets result 3. Under CONTINUE, the next ordinary command may overwrite that result, so a final `RC 0` does **not** prove every earlier command/assertion passed. Read all mismatch/error lines. An EXPECT that successfully checks a nonzero code does not reset that code to zero. RUN's printed RC is its latest stored result, not an accumulated error count. That final result is also available to STATUS and `%ERRORLEVEL%` after RUN.

### Result codes and current limits

| RC | Meaning | RC | Meaning |
|---:|---|---:|---|
| 0 | OK | 6 | Destination conflict |
| 1 | Unknown command | 7 | Unsupported operation |
| 2 | Unavailable feature | 8 | I/O failure |
| 3 | Interaction denied / script assertion error | 9 | Verification failure |
| 4 | Usage error | 10 | Partial operation |
| 5 | Not found | 11 | Internal failure |

`EXPECT RC N` currently accepts **one digit, 0–9 only**, even though result codes 10 and 11 exist. It checks the most recent command result, including SET/ECHO, and needs a preceding result; blank lines, comments and policy directives do not supply a new command result. Typed-result conversion is still incomplete across legacy handlers, so code 0 alone is not proof of all filesystem postconditions.

Use plain C64/PETSCII-compatible text, uppercase command fixtures and real CR or LF line breaks. Avoid smart quotes, a UTF-8 BOM and host lowercase ASCII command files. CRLF is readable but its two terminators can increase reported line totals. The line total counts executed lines, including revisits in loops; the command total counts commands dispatched to the filesystem shell rather than interpreter builtins.

### If the script did not do what you expected

| Symptom | Check or action |
|---|---|
| `RUN FILE [ARGS]` usage text | Supply a script path and at most nine arguments; quote paths/arguments with spaces. Put operation options inside the script. |
| File not found | Use the actual directory entry: `DIR 8:/` then `RUN 8:/INSPECT` if the IEC name is INSPECT. Check aliases and the current directory. |
| `RUN NEEDS OVERLAY`, `BATCH OFF`, or REU trouble | Use the overlay application with its matching sidecars and working REU. |
| `SCRIPT TOO LARGE` or `LINE TOO LONG` | Split into separate top-level runs or shorten lines. RUN cannot call another RUN. |
| Several commands appear on one line | Create real CR/LF separators; WRITE/APPEND `--line` adds CR. |
| Unknown command from a host-created file | Check C64-compatible text encoding, uppercase command bytes, BOM, smart quotes and tabs. |
| `BATCH NEEDS --YES` / RC 3 | Identify the specific operation that needs approval; put its explicit confirmation on that line. |
| Only a plan appears | Remove `--whatif` / `--dry-run` / `-w` from the intended operation in a separately reviewed execution script. |
| `EXPECT RC MISMATCH` | Read the preceding command's output and use the expected typed code; do not hide it with CONTINUE. |
| `BATCH FLOW ERROR` / RC 4 | Check label spelling, CALL depth, IF syntax and EXIT /B result range. |
| `BATCH STEP LIMIT` / RC 3 | Inspect loop termination; execution exceeded 10,000 lines. |
| Script stops early | STOP is the default. Inspect its first failure, complete arguments, device capability and destination state. |
| Final RC 0 but earlier errors | CONTINUE may have allowed a later success to replace an earlier error; inspect the entire output and filesystem results. |

