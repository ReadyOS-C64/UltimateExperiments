# Pinned VICE3.10 native filename identity audit

This disposable offline checker executes the **unmodified** matching VICE CBMDOS
parser, directory-slot encoder and filename comparator. It does not run VICE,
modify a D81 or build production code. Its minimal headers substitute only
standard integer types, disabled debug logging and libc allocation aliases.

Download the five source files from the official release tag into an isolated
directory such as `build/filename-audit/`; preserve their GPL headers. Then run:

```sh
python3 probes/filename_identity/check.py --source-dir build/filename-audit
```

The script requires exact SHA256 identities, writes only under that directory,
compiles `cbmdos.c` as a tiny host library and writes `result.json`. Source URLs:

- [cbmdos.c](https://raw.githubusercontent.com/VICE-Team/svn-mirror/3.10.0/vice/src/cbmdos.c)
- [cbmdos.h](https://raw.githubusercontent.com/VICE-Team/svn-mirror/3.10.0/vice/src/cbmdos.h)
- [vdrive-iec.c](https://raw.githubusercontent.com/VICE-Team/svn-mirror/3.10.0/vice/src/vdrive/vdrive-iec.c)
- [vdrive-dir.c](https://raw.githubusercontent.com/VICE-Team/svn-mirror/3.10.0/vice/src/vdrive/vdrive-dir.c)
- [vdrive-command.c](https://raw.githubusercontent.com/VICE-Team/svn-mirror/3.10.0/vice/src/vdrive/vdrive-command.c)

The fetched `vdrive-iec.c` SHA256 is
`5a13de2d32da96d09d5c499965a796cf9dd8e51648d7531af74cb3bc324d41ba`, identical
to the retained official3.10 release reference in `probes/empty_seq/`. No whole
release-tarball checksum is claimed by this audit.

## Confirmed identity defect: PETSCII $A0

The comparator stops at the **first** `$A0` and accepts when the corresponding
directory byte is also `$A0` (`cbmdos.c:143–144`). Slot creation pads with `$A0`
and copies input bytes unchanged (`155–166`); directory lookup calls this same
comparator (`vdrive-dir.c:111`). Executed examples match in both directions:

| Input A | Input B | Raw16-byte slots equal? |
| --- | --- | --- |
| `NAME` | `NAME A0` | Yes |
| `NAME` | `NAME A0 SUFFIX` | No; comparator still aliases |
| `NAME A0 ONE` | `NAME A0 TWO` | No; comparator still aliases |
| `A0` | `A0 HIDDEN` | No; comparator still aliases |

Here `A0` denotes the actual byte, not ASCII text. The BASIC listing also quotes
the name at its first `$A0` (`vdrive-dir.c:738–744`). The editor's exact raw
preflight comparison and the isolated host filesystem model therefore disagree
with real DOS lookup when any input `$A0` is accepted.

Minimal safe grammar: retain the current1..16-byte/native/device rules and reject
`$A0` **anywhere**, using existing argument90. Preserve `$A1..$FF`, ordinary
internal spaces, and mixed-case bytes. Do not trim, translate or silently rewrite
the name. Rejecting only lone or trailing `$A0` leaves the internal alias intact.
The current validator can implement this with the immediate-byte change
`cmp #$A0`→`cmp #$A1` after its `$7F` check; the existing branch then rejects
`$7F..$A0`. This adds no code, state or ZP bytes. Typing may still show an invalid
name until acceptance, as it already does for other rejected DOS syntax.

## Literal @ is safe under the fixed prefix

The file parser recognizes replacement only when the full input begins `@`
before its colon (`cbmdos.c:400–402`). The editor emits `0:<name>,S,W` with
secondary2. Its first byte is `0`, so `@` inside `<name>` remains literal and the
command field is empty. The checker executes2912 combinations of @ at all16
positions and every safe companion byte, plus364 ordinary native read/write
parses. All preserve the exact filename. An unprefixed `@0:NAME,S,W` control
does produce the replacement command. Rename/scratch prefixes likewise retain
literal @ in their filename fields. There is no reason to reject @ for this
pinned adapter while its emitted prefixes stay fixed.

## Separate confirmed create-new ownership defect

`vdrive-iec.c:246–250` enables replacement for an existing **unclosed non-REL**
file even when the parsed command is not @. Plain `0:<candidate>,S,W` is thus
not sufficient proof of create-new behavior on this backend. The editor currently
grants temporary ownership after successful OPEN, so a foreign splat with the
generated candidate name can be treated as a fresh owned file. This conclusion
comes from the pinned backend branch and the actual provider caller; this audit
has not run that destructive branch in VICE.

Before W-opening a generated temporary, prove exact candidate absence in a
read-only raw directory scan across **all non-DEL file types**, regardless of
closed/splat state. The current closed-SEQ `$81` preflight is insufficient for
that question. Refuse an occupied candidate without OPEN-W, writes, rename,
scratch or ownership grant. Keep source/caret/history/savepoint unchanged. A
fixed-prefix @ test does not solve this independent splat behavior.

## Required production and later native checks

- AddA0 to the exhaustive validator rejection set. Reject lone, repeated,
  leading, internal and trailingA0 at every permitted position without ROM calls.
- Replace the old A0-acceptance filename fixtures with A1 where a valid native
  name is intended. Keep a typedA0 popup fixture if it is testing rendering only;
  accepting that field must yield90 before disk activity.
- Against an existing `NAME`, attempt `NAME A0`, `NAME A0 X` and `A0`. Verify
  source/history/caret/binding, existing disk entry and capability flags unchanged.
- Save/open/overwrite a valid mixed-native16-byte name containing literal@,
  lower/upper native glyphs and A1/FF; verify exact raw directory bytes and source.
- In a disposable D81, seed the exact generated candidate as a foreign closed
  SEQ and as a foreign splat SEQ. Preserve original raw sectors/links. Both must
  refuse before OPEN-W, acquire no capability and preserve the foreign file.
  Repeat with another non-DEL type. A native window is still required for these
  runtime claims; no physical drive/UltimateDOS inference is made.
