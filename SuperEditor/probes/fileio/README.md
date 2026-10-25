# Standalone IEC file provider and save policy

This is a separately linked building block for M4. The editor does not yet call
it and has no file dialog. Nothing in this directory changes the root Makefile,
resident address map, document roots, ReadyOS, or UltimateDOS.

From `SuperEditor`:

```sh
make -f probes/fileio/Makefile test
make -f probes/fileio/Makefile build/fileio/native.prg
# Only after the root grants the shared VICE window:
python3 tests/test_fileio_vice.py
```

`channel.s`, `chunk.s`, `status.s`, `directory.s`, `commands.s`, and `save.s` are
operation-sized 6502 objects. The CPU probe currently links 1,976 bytes, including
its three-byte entry. Provider/save state is 267 bytes, zero zero-page bytes.
The native probe includes its own BASIC loader, exercise code and seven observer
bytes. The configs exclude the entire `$C600–$C9FF` shim.

The current editor has insufficient resident BSS for a blind append. Put the
provider's durable frame in an explicitly allocated file-mode state area, keep
channel cleanup callable at every yield, and link transport operations into a
file overlay or move suitable existing state before integration. Never borrow
the shim, boot-only code, parser state still in use, or overlay-loader channels.

## Provider contract

All calls run in foreground and clobber A/X/Y/P. Carry clear/A=0 is success.
`se_io_init` is a once-per-idle-session initializer, not an abort: calling it
mid-transaction would discard private-name ownership. `se_io_abort` closes the
owned data channel and clears channel selection; it retains temp/backup ownership.
No routine calls LOAD or sends document bytes to the default screen channel.

- LFN5/SA2 owns a SEQ stream, LFN5/SA0 owns directory bytes, and LFN6/SA15 owns a
  short command/status operation. Existing overlay LFN2 is separate. The caller
  must still serialize all foreground IEC consumers and overlay loading.
- `se_io_device` must be8 or9, without a default. `se_io_name[16]` plus length
  contains native PETSCII. No case conversion. Controls, quotes, DOS separators,
  wildcards, paths and all-space names are rejected. `se_io_other` is the second
  exact name for rename. Filename tokens are never interpreted as commands.
- `se_io_open_read` opens an existing SEQ; `se_io_create_write` uses create-new
  `0:name,S,W` with no replace shortcut. Existing names return DOS63 and remain
  intact. Status is read after OPEN. Every attempted failed data OPEN is closed.
- Each chunk uses fixed buffer `$8000–$80FF`. `se_io_count`1..255 requests that
  count,0 requests256. `se_io_done[2]` reports transferred bytes. The final valid
  EOI byte is included; subsequent reads report zero bytes without another CHRIN.
  Read errors close the stream; write errors close it without claiming success.
  `se_io_wrote` is deliberately a boolean, avoiding a16-bit length rollover.
  The document coordinator must maintain its own24-bit length and quota checks.
- `se_io_close` closes and reads DOS status, including delayed write errors.
  Closing a write stream with no successful CHROUT returns `FIO_EMPTY=$98`.
  This is an intentional refusal, not zero-byte file support; see below.
- `se_io_status` retains raw READST, numeric DOS code, and a39-byte terminated
  display response (CR may be present). It drains up to128 bytes. Nonzero DOS
  codes are errors generally; owned scratch recognizes01 FILES SCRATCHED as its
  successful operation-specific response. Every attempted command OPEN closes.
- `se_io_directory_open` streams `$0:*=S`. It discards the two-byte load address,
  then reads BASIC link/line-number/text records. Disk link values never become
  C64 addresses. `se_io_directory_next` returns one SEQ name, two-byte block
  count and splat/lock flags. It recognizes header/free-block lines as nonfiles,
  retains up to16 name bytes inside quotes, and ignores PRG entries. Name length0
  with EOF is completion. A32-record slice yields `FIO_LIMIT=$95` with mode3 and
  the channel still open; retry then. An overlong (>82-byte) listing line returns
  the same error with mode0 after cleanup; that is malformed input, not a retry.
- `se_io_create_temp` grants an exact private-name capability only after a
  successful create-new. DOS63 never grants it. `se_io_make_backup` renames
  name→other without overwrite and grants an exact backup capability only after
  success. `se_io_rename` is exact source→destination and consumes a matching
  source capability after success. `se_io_scratch_owned` takes A0 temp/A1 backup;
  it ignores caller name fields and scratches only the stored owned bytes.
  Prefix resemblance never grants ownership. Repeated scratch is refused.

Errors90 argument,91 busy,92 KERNAL I/O,93 DOS error,94 malformed input,95 bound
or slice limit,96 missing ownership,97 invalid state,98 empty write refusal.
DOS/READST details stay available for display; the UI must not replace them with
a generic success message. Transport errors during a rename/scratch may leave
an uncertain disk state even though the exact capability remains in RAM.

## Executed save policy and coordinator work

`save.s` is an executable policy, not the document/DOS coordinator. `se_sv_begin`
takes A0 new target/A1 overwrite. `se_sv_phase` publishes the next bounded action.
Caller carries it out, closes any channel on failure, and reports an event via
`se_sv_step`: OK1, definite FAILED2, byte-exact MATCH3/MISMATCH4, UNCERTAIN5, or
CANCEL0. `se_sv_error` retains the coordinator's original diagnostic. DONE can
mean successful save or completed safe cleanup; test that diagnostic before
marking the document saved. RECOVERY freezes further destructive policy steps.

| Phase | Required coordinator action and successful successor |
| --- | --- |
| CREATE | Collision-safe create temp → WRITE |
| WRITE | Stream a leased source snapshot, length24/quota checked → CLOSE |
| CLOSE | Close and check DOS; empty98 is a failure → OPEN_VERIFY |
| OPEN_VERIFY | Open exact owned temp → COMPARE |
| COMPARE | Byte-for-byte source readback, including exact EOF → CLOSE_VERIFY |
| CLOSE_VERIFY | Close read channel → BACKUP if old target exists, else PROMOTE |
| BACKUP | Rename old target→free backup candidate → PROMOTE |
| PROMOTE | Rename verified temp→target → CHECK_TARGET |
| CHECK_TARGET | Reopen, exact readback, close and check target → DELETE_BACKUP or DONE |
| DELETE_BACKUP | Scratch exact owned backup only after confirmed new target → DONE |
| ABORT_CLOSE | Close owned channel without losing capabilities → DELETE_TEMP |
| DELETE_TEMP | Scratch exact owned rejected temp → DONE |
| ROLLBACK | After definite refused promotion, rename backup→target → DELETE_TEMP |
| RECOVERY | Preserve all candidate files and explain/reconcile explicit recovery |

No backup is deleted on failed verification, failed promotion or uncertain
acknowledgement. A definite backup refusal leaves the old target unchanged and
removes only this save's temp. A definite refused promotion with a known backup
requests rollback. An I/O acknowledgement can be lost after the drive applied a
rename: report UNCERTAIN, never FAILED in that case. Every UNCERTAIN action enters
RECOVERY, including cleanup failures. Caller can close its channel safely there.
Cancellation before BACKUP cleans only temp; after target-changing work begins,
it enters RECOVERY and leaves both copies. The host coordinator in
`test_fileio_save.py` executes these actual emitted modules across43 success,
mismatch, cancel, rollback and interruption scenarios. It is not editor code.

Opening a file must likewise build a fresh document object with bounded chunks,
capacity checks and clean EOF, then swap document roots and saved node only on
success. Current source/selection/history stay live until publication. Save must
lease/freeze its source snapshot and retain current dirty state if that snapshot
is no longer current. These document coordinators are not yet integrated.

## Restart recovery design still to implement

Current capabilities are RAM-only; after process restart they cannot authorize
scratching a matching-prefix file. Leave unknown candidates untouched. Use names
such as `SE` + eight hex digits + `T/B/M` (11 native bytes), generate fresh nonce
and retry exact create-new/rename collisions. The generator is coordinator work;
the provider currently accepts caller-supplied candidates and enforces collision
and ownership behavior.

Before renaming an old target, persist a separately created transaction record
containing schema, native device/disk identity, exact target/temp/backup names,
24-bit old/new lengths, old/new content fingerprints and a record checksum.
Only write a record describing an owned temp after its create/readback succeeds.
Use closed/readback-verified immutable record revisions rather than overwriting
the sole recovery record. Record intent before each destructive name operation
and publish a completed revision only after status/verification succeeds.

At restart enumerate records without deleting anything, validate schema/checksum,
check disk identity, then reopen candidates and compare their entire content to
the recorded fingerprints. A verified old backup with missing target can be
offered for restore; a verified new target plus old backup can be offered for
completion; a verified temp with intact old target can be offered for retry or
discard. Missing/corrupt records, unknown candidate content, disk swaps, or
ambiguous duplicate contents require explicit recovery selection, with no
automatic scratch. A crash between temp creation and record publication can
leave an orphan which must remain untouched without renewed authorization.
Implement and native-test this journal/reconciler before claiming restart-safe
saving. DOS rename/scratch is not atomic.

## Exact verification and remaining gaps

CPU provider tests exercise emitted code with an independent modeled ROM/DOS
boundary: all256 filename bytes, devices, binary1..65,537-byte streams, final EOI,
failed OPEN/CHKIN/CHKOUT/CHRIN/CHROUT cleanup, malformed status, listing slices,
empty/header/footer/padded16-byte native directory names, and private ownership.
Every call checks all1024 shim bytes. CPU modeling cannot prove drive behavior.

Native run `20261024T183132429401Z-fileio-native` uses a newly formatted writable
D81, actual KERNAL/.NET VICE warp/traps1581 path.273 binary bytes survive write,
readback, backup, promotion and process exit; host c1541 extraction confirms all
273 bytes. Directory enumeration, missing-file status62, exact owned scratch,
all-channel cleanup and shim preservation pass. The384×272 screenshot was
inspected and shows FILEIO NATIVE PASSED. No UI, timing or physical-drive claim.

The prior run `20261024T182931526521Z-fileio-native` deliberately measured a
zero-CHROUT OPEN-W/CLOSE. It produced a254-byte SEQ rather than an empty file.
The disk initially contained only the probe PRG and ORIGINAL fixture; the exact
directory/data chains and extracted bytes are retained in `empty-corruption.json`
and `empty.seq`. Their origin is not assumed random/uninitialized. This is
observed on the trapped path only; true-drive/physical behavior is unknown.
The new close guard returns98 and retains the owned temp for precise cleanup;
native rerun confirms the rejected EMPTY artifact is removed. Do not write a NUL
to simulate an empty document. Correct zero-byte save and imported-empty read
semantics remain unresolved M4 work, along with disk-full/write-protect, capacity,
device9 native, dirty dialogs, REU staging and restart recovery tests.
