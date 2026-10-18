# ReadyFS C64 Ultimate Test Safety

## Non-negotiable boundary

Each automation run receives a unique run id and two optional owned roots:

- `/usb1/READYFS_TEST/<run-id>`
- `/sdcard/READYFS_TEST/<run-id>`

The host setup creates the root and a marker containing that exact run id.
Before a destructive command, both the normalized path prefix and marker must
match. Prefix-only checks are insufficient. Symlink-like escapes, parent
components, aliases that expand outside the root, and image boundaries whose
host image is outside the root are rejected in automated destructive suites.

Tests may create and remove leaves inside their own root. Run roots and logs
remain after the suite unless an explicit cleanup request names the exact run
id and its marker validates. Existing USB1, SD-card, disk-image, and IEC-device
content is never a cleanup target.

## Ultimate access

C64 Ultimate REST/FTP commands run only from a Terminal-owned/background bash.
The suite records the original Ultimate configuration before enabling Command
Interface or Software IEC and restores it on every exit path.

## UCI transport

ReadyFS follows the transport proven by ReadyIRC and UCI Tester. Commands start
from fully quiescent IDLE, PUSH is asynchronous, both queues are completely
drained, DATA_ACC must visibly advance state, ABORT is requested once and then
serviced, and completion includes the final quiet-idle wait. Poll counts bound
failure; they never pace commands. Physical acceptance runs at 1, 16, and
64 MHz.

## Current owned scope and recursive fixtures

The only active mutation roots are the USB1/SD pair for
`readyfs-20260815-190355-79014`, with marker
`.readyfs-owner-readyfs-20260815-190355-79014`. The recursive fixture suite may
create a uniquely timestamped subtree only below the USB1 root, revalidates the
marker before every mkdir/write, performs no deletes, and preserves the tree.
Runs ending `230322` and `231705` stopped after a successful marker comparison
because REST launch reset; no filesystem command ran in either attempt.
Run `recursive-owned-20260816-011419` stopped even earlier: all ten FTP marker
fetches reset, so it did not validate ownership, launch ReadyFS, or issue any
filesystem command. Preserve it and do not retry the C64U in a tight loop.

The later true Terminal-owned SoftIEC attempt
`softiec-owned-20260816-100658` also stopped at the first exact marker gate:
ten FTP connection resets, an empty results table, and no ReadyFS launch,
mapping, filesystem I/O, configuration change, or mutation. Preserve its logs
and never bypass the marker because connectivity is intermittent.

Audit invalidated `preflight-20260816-112357` as FTP evidence: its old script
did not exit on curl failure, so three reset/empty FTP outputs were followed by
a successful manifest write and a false `success` status. The preflight now
uses `set -euo pipefail`, ten bounded attempts, FTP `--list-only`, and rejects
empty outputs. Corrected independent run `preflight-20260816-113019` proves
nonempty REST version/info/drive/config access but fails honestly at FTP root
listing after ten resets. `softiec-owned-20260816-112412` likewise failed at
the exact marker fetch with zero cases and no launch/map/I/O/mutation. Do not
use the invalid earlier status to weaken the ownership gate.

Local VICE run `vice_auto_20260816_121327` exercises direct and alias-resolved partition
mutation gate only against a detected legacy profile. It stops at `PROFILE
DENIED` before action BEGIN and before command-channel I/O. It is not physical
storage evidence. No C64U retry, REST configuration change, FTP write, USB1
mutation, or SD mutation accompanied this milestone; the owned roots and
marker rule above remain unchanged.

The latest local authority is `vice_auto_20260816_122410`; it additionally
denies alias-resolved partition directory listing on the legacy VICE profile.
No physical command or storage request is implied. Boot failures `121620` and
`121741` were local memory-boundary diagnostics, and `122154` captured the
KERNAL scratch collision. They did not contact the C64U or mutate storage.

True Terminal-owned read-only preflight
`preflight-20260816-1228-final-local` again obtained all seven nonempty REST
documents, then failed strictly after ten FTP root-list resets. It did not
reach SD/USB listing, marker retrieval, ReadyFS launch, configuration writes,
or any filesystem mutation. Do not start a mutation run from its REST-only
success; fresh exact marker access is still mandatory.

## Preserved SoftwareIEC diagnostics — 2026-08-17

All later SoftwareIEC automation remained inside the exact marker-owned USB1
root and re-read the exact USB1 and SD markers before mutations. No suite is a
cleanup authority. Preserve every created folder and file, including
`rf065128/ap0840.seq`, `rf065128/ap1000.rel`, `rf065128/ap1030.seq`,
`rf065128/ap1100.seq`, `rf065128/ap1115.seq`, folders `rf080727`, `rf081054`,
`rf082251`, and `rf083856`, their `sfa.seq`/`fromu.seq` leaves, root
`fs081054.seq`, `us081054.seq`, `fs082251.seq`, `us082251.seq`, and
`rf083856/ap0853.seq`. The REL leaf was created only by an unsafe diagnostic
existence probe; REL probing is now forbidden in production.

Read-only authorities `softwrite-noftp-20260817-uci-close-trace`,
`softwrite-noftp-20260817-uci-close-prod`, and
`softwrite-noftp-20260817-ap0846-read2` pass exact owner checks before and
after. Trace mutation authority `softwrite-noftp-20260817-uci-close6-trace2`
created only `rf083856/ap0853.seq` after both pre-owner checks and passed both
post-owner checks. Failed full run `softiec-owned-20260817-uci-close-full`
created only `rf083856` before stopping; do not remove it. The follow-up full
run `softiec-owned-20260817-close26-full2` uses another fresh exact-owned
folder, performs no deletes, and must retain all artifacts regardless of its
result.

Later exact-owned artifacts are permanent: top-level `rf085532`, `rf090410`,
`rf091228`, `rf091800`, and `rf094315`; nested `rf091800/rf100154`; raw roots
`fs091800.seq`, `us091800.seq`, `fs100154.seq`, and `us100154.seq`; successful
focused leaves including `ap0902.seq`, `ap0904.seq`, `ap0917.seq`,
`fx0930.seq`, `fx0938.seq`, and `fx0940.seq`; `rf094315/rfseed.seq`; and the
final case's `sfa.seq`, `fromu.seq`, and `nested/inside.seq`. Failed
diagnostics may have additional partial artifacts, so these names are a
minimum preserve set, never a cleanup allowlist.

Corrected recursive destination `rf091800/rr111505` is now permanent too. It
contains normal lowercase host files `sfa.seq`, `fromu.seq`, and
`nested/inside.seq`, created by successful marker-gated `rr5-final3` and
independently read by `rr5-verify`. Preserve earlier `rr111504` with its
encoded-name diagnostics, failed/partial `rr5-final` and `rr5-final2`, every
runner diagnostic log, and any partial runner-diagnostic folder if firmware
accepted one before FTP reset. Neither successful suite nor any diagnostic is
cleanup authority. Both successful suites restored Drive A to the exact
captured empty-enabled-1581 baseline.

`softiec-owned-20260817-nested-parent-prod-full` issued no delete and gated
every mutation with both exact 116-byte owner files. Its stale final uppercase
directory oracle did not invalidate completed mutations. Read-only
`softwrite-noftp-20260817-treeverify-final` subsequently verified the raw tree
and both owner markers after all mutations. No run authorizes cleanup.

## 2026-10-08/09 — explicitly requested nested demo deletion

The user's new request authorizes copying, moving and deleting demo descendants
only inside a fresh owned run root. It does not authorize cleanup of historical
roots, source fixtures, or ownership markers.

- `readyfs-20261009-064723-40789`: fresh USB1 source fixture; first recording
  stopped on a screen-decoder bracket assertion before any C64 mutation.
  Preserve the root, marker, source, and failed-take evidence.
- `readyfs-20261009-065124-42760`: fresh USB1 source fixture for the revised
  recording. Allowed mutation descendants are `copy`, `moved`, and the
  what-if-only `field notes.seq`. Preserve `source`, the root, and its marker.
  The runner verifies an exact marker before each mutation command and takes
  independent recursive FTP snapshots before and after previews and actions.

These are new per-run roots; they do not widen the historical August preserve
set. Terminal-owned read-only preflight `preflight-20261008-233820` passed all
REST and nonempty FTP checks before creation. No SD, user disk image, Software
IEC mapping, or unrelated USB content is a mutation target.

The alias-admission repair uses another fresh root,
`readyfs-20261009-070006-46712`, for `demo-v2-20261009-000005`. Its permitted
mutation descendants are `smoke`, `copy`, and `moved`; preserve its root, marker
and `source`. `smoke` is the focused regression before filming. The previous
root `readyfs-20261009-065124-42760` stopped before creating `copy` and remains
preserved. No historical fixture is cleanup authority.

### 2026-10-09 canonical-lifetime retake

Preserve the earlier 070006 root, including partial `smoke/work.seq` and
`smoke/moved.seq` evidence after COPY OK / DELETE FAIL. Do not clean it up.
The new run owns only `/USB1/READYFS_TEST/readyfs-20261009-071351-52789`.
Marker and canonical prefix gates cover smoke regression and recorded copy,
moved, and source descendants. The user authorized deleting only the newly
created demonstration copies/moved descendants; preserve this run's source,
root and ownership marker. No other run or original data is a cleanup target.

### 2026-10-09 literal-host-name retake

Latest owned run: `/USB1/READYFS_TEST/readyfs-20261009-072020-56555`.
The 071351 run is retained after a literal `.SEQ` lookup failure, with no
cleanup permission for that earlier root. This fresh run alone may perform the
smoke regression and delete its newly created copy/moved fixtures. Preserve
its five original source files, source folders, root, and marker. Recorder
snapshots the exact build before boot and checks completion passively from VIC
before any REST RAM evidence reads.
