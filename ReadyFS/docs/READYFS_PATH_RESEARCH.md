# ReadyFS Path Research and Translation Notes

## Why the public syntax is not native DOS syntax

C64 OS combines device, partition, filename, and path as
`device:partition:filename:path`. Its documentation explains that filename is
placed before the path partly so a narrow status display keeps the filename
visible. That is useful for its UI, but it makes a typed hierarchical shell
path harder to read and makes an image-file boundary implicit.

ReadyFS instead keeps the hierarchy in traversal order:

- `8:/FILE` — unpartitioned/legacy IEC device
- `11.3:/games/demo.d64!/PROGRAM` — IEC device 11, native partition 3,
  host-side folders, explicit image boundary, contained file
- `u:/USB1/games/demo.d81!/PROGRAM` — UltimateDOS host path plus image
- `s3:/games/PROGRAM` — SoftwareIEC logical partition 3
- `@work:/src/file.c` — exact-place alias

The optional `.partition` numeric suffix is reserved for CMD/SD2IEC-compatible
IEC drivers. Existing `8:/` remains partition 0/default. Parsing this form does
not grant directory capability: the detected driver must explicitly support
partitioned paths before listing or mutation.

## Translation rules

The public path is always normalized and absolute. A backend may temporarily
change its own current directory, but every transaction starts by reasserting
the public absolute location; ReadyFS never treats backend current-directory
state as durable shell state.

CMD/SD2IEC use a DOS command-string grammar in which a partition and directory
path precede a colon-separated leaf. SD2IEC also treats a disk image as a
directory for `CD`, and leaving it requires a separate parent/unmount command.
ReadyFS does not leak that stateful behavior into its public path. `!` records
the transition from host file to contained filesystem, so planning can reject
an unsupported cross-image operation before changing device state.

The pure CMD/SD2IEC translator is host-harness-proven for the following
commands. The same source cc65-compiles into the cached `RFCMDPATH` sidecar
(`$B600`, `$FFD` bytes) on the overlay lab D81. Boot loads it into REU slot 5,
verifies its ABI, runs a compact `$:pattern` translation self-test, and restores
the matcher before the prompt. The larger callable VICE suite proves file-open,
rename, image-mount, two-command-unmount, and matcher restoration.
The callable `native OP PATH [DEST]` diagnostic runs from the help sidecar,
swaps into CMD path through resident scratch, restores help, prints the exact
native result, and restores the matcher. A separate `RFDRIVE` sidecar classifies
bounded status-channel replies while the resident exclusively owns KERNAL IEC
I/O. `probe iec DRIVE:` is proven in VICE, but translated mutating commands are
not issued until the detected profile explicitly grants their capabilities:

Detected IEC profiles are stored per device in session REU `$0888-$08E3` as
individually marked records. The registry is cleared at application boot and
every lookup validates both marker and device number. `profile iec 8: mount`
therefore answers from a durable, explicit capability record rather than the
last transient status buffer. The current matrix requires `P` for open and
scratch, `P+F` for directory and folder/rename operations, and `P+F+I` for
image mount/unmount.

| ReadyFS | Native operation |
|---|---|
| `8:/RF* --native-pattern` | `$:RF*` (flat read-only directory selection) |
| `11.3:/games/HELLO.PRG` | `3//games/:HELLO.PRG` |
| directory `11.3:/games/tools` | `$3//games/tools/` |
| scratch `11.3:/games/OLD.SEQ` | `S3//games/:OLD.SEQ` |
| mkdir `11.3:/games/newdir` | `MD3//games/:newdir` |
| rmdir `11.3:/games/old` | `RD3//games/:old` |
| rename old to new | `R3//archive/:NEW.SEQ=3//games/:OLD.SEQ` (`new=old`) |
| mount `11.3:/games/demo.d64` | `CD3//games/demo.d64` |
| unmount partition root | `CD//`, then `CD` plus PETSCII back-arrow `$5F` |
| `11.3:/games/demo.d64!/HELLO` | rejected as stateful until mount/open/restore transaction support exists |
| `s3:/games/HELLO` | SoftwareIEC KERNAL name `3:/games/HELLO` on discovered bus |

The harness also rejects cross-device/cross-partition rename, partitionless
legacy IEC paths, non-IEC endpoints, unsupported image extensions, components
over 16 bytes, and image-contained access that would require hidden mutable
device state. `make readyfs-host-tests` compiles and runs this contract.

## Length and capability policy

- ReadyFS canonical commands and expanded paths are at most 255 bytes.
- C64 OS documents a roughly 232–234 byte directory-path ceiling and 16-byte
  directory components for its CMD-style drivers. ReadyFS does not adopt its
  filename-before-path layout, but the limit is useful as a conservative
  compatibility profile.
- SD2IEC documents patterns/visible Commodore filenames up to 16 characters,
  partitions 1–254, CMD-compatible `CD`/`MD`/`RD`, and image mounting through
  `CD`. Native host long names and their displayed aliases must remain distinct
  metadata.
- Each driver preflights the fully translated command/open-name length, leaf
  length, partition range, supported image type, and maximum path profile.
  Unsupported or unproven operations fail before mutation.
- `--native-pattern` is the only mode allowed to forward a C64-DOS pattern.
  Shell `*`, `?`, and `**` otherwise operate on complete ReadyFS relative stems.

## Native-pattern action contract

Native patterns may eventually select copy, move, and delete inputs, but they
must never be forwarded as a wildcard mutation such as `S:RF*`. The accepted
execution model is:

1. Translate and open the backend pattern only as a read-only directory query.
2. Ignore the directory header and serialize every exact returned filename,
   type, and block estimate into the existing bounded REU action plan. Hitting
   the entry limit invalidates the whole plan; it never means “apply the first
   N”.
3. Apply `--include`/`--exclude`, if present, only after native enumeration and
   against each complete ReadyFS relative stem. This keeps backend selection
   and shell filtering distinct and inspectable.
4. `--whatif` prints every exact selected target plus totals and performs no
   write, scratch, rename, mount, or directory-changing command.
5. A real run requires `--apply`, displays the complete selection, and freezes
   those exact names before execution. Bare `--native-pattern` remains denied
   even with `--force`/`--yes`. Each frozen target then uses the normal staged
   copy/move or exact-name delete path with RFJ1-before-ACK and stop/continue
   policy; the wildcard is never reissued as a mutation command.
6. Copy/move require a directory destination when more than one source is
   selected. Directories and unsupported REL transfers reject the entire
   first-generation plan before mutation; per-type expansion comes only with
   dedicated evidence.

Preview syntax is `copy 8:/RF* 9:/ --native-pattern --whatif`, `move ...`, and
`delete 8:/RF* --native-pattern --whatif`; execution replaces `--whatif` with
the explicit `--apply` opt-in (plus normal conflict/confirmation options).
Users do not add `--recursive` merely because the implementation reuses the
batch controller. In `171906`, resident IEC enumeration feeds exact names and
types through the backend/matcher/recursive sidecars; filtered planning stays
zero-write, singleton native delete succeeds, and native copy/move cross from
IEC8 to IEC9 with exact byte/postcondition checks. Parsed RFJ1 dumps contain
only `RFNC1`, `RFNC2`, and `RFNM1` exact-name actions. Wildcard scratch, write,
and rename commands remain forbidden. Regular IEC collection destinations must
be the flat root; `171852` additionally proves that a matched REL `$13` entry
rejects the entire native plan with the destination still absent.

## Sources

- C64 OS file-reference design and path limits:
  https://c64os.com/c64os/usersguide/filesystem
- C64 OS File Manager device/partition and recursive-operation behavior:
  https://www.c64os.com/c64os/usersguide/filemanager
- C64 OS discussion of absolute file references rather than shared mutable
  drive-directory pointers:
  https://c64os.com/post/cmdhdcurrentdirpointers
- SD2IEC command manual derived from the firmware README, including partition,
  directory, and image `CD` semantics:
  https://c64os.com/post/sd2iecdocumentation
- UltimateDOS reference:
  https://1541ultimate.net/content/download/ultimate_dos_v1.0.pdf

## SoftwareIEC host-file/type findings on firmware 3.14

- The BASIC directory stream is not an exhaustive FAT enumeration authority.
  Physical traces can show the host-path header and one earlier file, then end
  before the requested later leaf. ReadyFS must not infer absence from that
  stream.
- Ordinary SoftwareIEC OPEN without an explicit type maps through `.???`;
  explicit SEQ/PRG/USR opens map to `.seq`, `.prg`, and `.usr`. ReadyFS probes
  only those three explicit types and consumes the DOS status reply.
- Never probe REL for existence. Firmware source opens REL with
  `FA_OPEN_ALWAYS`, so a read-style existence check can create a missing host
  `.rel` file. `rf065128/ap1000.rel` is the preserved proof artifact.
- UCI SoftwareIEC target command `$14` closes the data channel selected by its
  secondary-address byte. Firmware implements it synchronously through
  `get_data_channel(sa)->ext_close_file()->push_command($E0)`. ReadyFS uses it
  for read SA 2 and probe SA 6 via the complete ReadyIRC-derived UCI transport.
- UCI status and resident IEC DOS status intentionally share scratch storage.
  Therefore the exact order is KERNAL close, target-5 close, then DOS-status
  read. Checking DOS status before the UCI command lets the UCI reply overwrite
  the evidence and can misclassify an absent host leaf.

## SoftwareIEC directory-breadth boundary

The marker-owned run root eventually accumulated many deliberately preserved
diagnostic folders. Firmware 3.14 then stopped entering newly appended root
folders through direct `CD:` even though UltimateDOS listed them. Seeding
`rf094315/rfseed.seq` and rebooting with exact SoftIEC config equality did not
change the result. Creating a fresh child under already visible, uncrowded
`rf091800` worked immediately, including a nested directory below it. This
aligns with the truncated FAT/BASIC-directory behavior: path design cannot
assume every raw host entry is reachable through SoftwareIEC at arbitrary
parent breadth. Future integration should expose a capability/refresh boundary
and prefer dedicated shallow SoftIEC-visible roots.
