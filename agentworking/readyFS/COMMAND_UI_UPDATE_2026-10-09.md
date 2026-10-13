# ReadyFS command display and nested demo update — 2026-10-09

## User intent

Differentiate typed command history from results; make DIR resemble a normal
C64 directory; provide HELP for each command; replace the repetitive recording
with a coherent, human-paced nested copy/move/what-if/delete demonstration.
Delete only descendants of the current run's owned fixture folders.

## Implementation

- The live editor and submitted command echo are cyan (3); command execution
  resets output to white (1). The REU transcript already stores both screen
  and color cells, so output paging preserves the distinction. No new
  per-keystroke screen repaint was introduced.
- Input-area clearing at submission uses the existing bounded 200-byte region
  through memset; ordinary appends/overwrites still write one cell, deletions
  repaint only the changed suffix, and cursor motion writes no content cells.
- IEC DIR prints a reverse-video quoted disk title, aligned full 16-bit C64
  block counts, quoted/padded names, CBM file types, and BLOCKS FREE. It keeps
  the existing 18-line directory pager and safe resident IEC I/O.
- Ultimate host folders print quoted names and DIR/unknown file type. A `?`
  marks size unavailable: the firmware directory stream supplies attributes
  and names, not sizes. No per-entry nested UCI request or invented block
  conversion was added. DIR help explains the distinction.
- HELP COMMAND resolves the same command table as execution, including aliases
  such as CP, LS, RM and FM. Topics cover all 40 command IDs plus FORMAT's
  separate help topic (execution shares the MOUNT ID). Unknown topics get a
  safe error. HELP DIR, HELP CP and H RM appear in the new recording.
- The extended catalog and directory formatter run in new slot 14, `rfshow`,
  cached at batch-bank $7A00–$89FF. The allocation ends at $8A00. Sidecar admission
  probes ABI $5250. The linker, D81 packaging, REU map and verifier cover it.
- Shared batch-cache opening factors repeated slot 10/12/13 fetch logic; slot
  14 uses the same bounded opener. Resident callers restore the matcher and
  CPU port. The presentation sidecar performs no filesystem or overlay calls.
- CD resolves paths in resident code before entering slot 14; slot 14 performs
  only parse/absolute validation and copying to cwd. Keeping resolution outside
  the presentation overlay is essential because resolution calls the matcher.
- Resident comparisons directly reuse the existing assembly comparator. Numeric
  command IDs and matching behavior remain unchanged.

## Build and local evidence

`make readyfs` passed: complete host suites, UCI protocol contract, overlay DMA
contract, pipeline contract and memory report. Additional host checks cover
all help topics, FM/unknown, directory spacing, full 3160-block free counts,
bounded host names, CD errors, cyan echo/white execution, preserved paging
colors and draft, and the previous minimal screen-write counts.

Current resident end $B5A4, with 7 safe bytes below KERNAL scratch $B5AC. UI slot 13 uses
4048 bytes; presentation slot 14 uses 4066 bytes. Further resident growth
requires freeing memory or moving more pure work to sidecars. The UCI transport
was not changed; this update does not claim a new 1/16/64 MHz UCI acceptance run.
The monolithic binary remains a smaller diagnostic; full command-topic help
belongs to the overlay application.

## Recording and safety

The physical 1 MHz recording is driven by `run_readyfs_c64u_demo_v2.py` through
`start_readyfs_c64u_demo_v2_terminal.sh`. It captures the real VIC UDP stream,
uses natural key spacing and 3–4 second paging pauses, and preserves all logs.
The first take stopped on an overly literal decoder assertion for brackets;
the application HELP output was correct. It performed no C64 filesystem write.

The next take attaches only after comparing immutable CODE and RODATA to the
fresh build at 1 MHz. It owns `/USB1/READYFS_TEST/readyfs-20261009-065124-42760`.
The five source files span `alpha`, `beta` and `beta/deep`. Exact markers and
canonical prefixes gate all mutation commands. Source bytes, directory shape,
move-source absence, deleted descendants and preview non-mutation are verified
independently by FTP. The source, root and marker are preserved. The local D81
is mounted read-only in previously empty drive A; CPU and drive settings are
restored on exit. Failed takes are evidence, not cleanup targets.

Final recording and publication results will be appended after completion.

## Alias admission defect found by the demo

The second take completed editor/history/paging but stopped at `MD @LAB:/COPY`
before creating the directory. Existing single-path mutation admission passed
raw alias arguments into a backend that deliberately accepts canonical paths
only. The path had been resolved for I/O, but the admission call discarded that
canonical identity, returning silently.

MKDIR, RMDIR and single-file DELETE now admit `command_stream.canonical`.
Single-file COPY/MOVE prepare both paths before admitting their canonical
source/destination. The source and destination remain persistent resident
stream storage through completion. The verifier requires these canonical
identities. No backend capability or safety check was relaxed. The IEC DIR
formatter now receives the existing complete cbm_dirent ABI and reads metadata
in slot 14, freeing resident bytes for this fix.

New physical take `demo-v2-20261009-000005` owns
`/USB1/READYFS_TEST/readyfs-20261009-070006-46712`, with the same five-file
source fixture. Before filming, a focused alias regression creates `smoke`,
copies a source file into it, moves the copy, deletes it, and removes that empty
folder; byte/absence oracles and marker gates cover each step. The filmed
workflow then uses only `copy` and `moved`. The original failed fixture remains
untouched. Final footage combines only passing chapters 1–3 of the previous
take and chapters 4–7 of this fresh take, at original speed.

### Follow-up canonical lifetime fix

The 070006 take passed alias MKDIR and copied the expected 38 bytes, but MOVE
reported `COPY OK; DELETE FAIL`. Its partial smoke files and source remain
preserved. A 7-second automation pause also inspected the operation before it
had finished; a later read-only capture confirmed the actual cleanup failure.
Alias lookup scratch overlaps the resident action checkpoint storage. Copy
I/O and move cleanup now retain the already-resolved canonical paths after
BEGIN, avoiding another alias lookup in that lifetime. `path_prepare` resets
its open flag rather than erasing an in-place canonical input; parsing and
opening initialize the descriptor fields they own. The pipeline verifier
checks these canonical call boundaries. No backend safety check was relaxed.

A complete `make readyfs` passes for this build. The new take is
`demo-v2-20261009-001350`, owned root
`/USB1/READYFS_TEST/readyfs-20261009-071351-52789`. The recorder now waits for the
live-input footer through the passive VIC video stream, avoiding REST RAM reads
while filesystem operations run. The focused regression is excluded from the
final chapter edit. Physical result remains pending at this point.

### Literal host filename lookup regression

The 071351 retake again reported COPY OK / DELETE FAIL, despite retaining
canonical paths. The remaining concrete defect was in pure matcher lookup:
`RF_MATCH_ULTIMATE_FIND` always decoded a host name and stripped `.SEQ` before
comparison. Thus a literal `WORK.SEQ` could be opened directly and copied, but
could not be found for deletion (nor reliably for replacement existence).
Lookup now accepts the actual case-folded host spelling first, then the
existing decoded logical spelling. It returns the original access identity.
Host regressions cover `WORK.SEQ`, logical `WORK`, unrelated names and the
existing escaped disk-name identity. UCI transport and transaction pacing
remain unchanged. Preserve the 071351 source and partial smoke evidence.
The latest full build passes; resident end is $B5A4 with 7 safe bytes, matcher
is 4040 bytes. Tree/find help no longer advertises mutation flags, and write /
append help mentions the line-ending option. The overlay and smaller
monolithic copy argument setup retain their respective initialized sources.


## Current recording authority

| Take | Result / role | Owned root suffix |
|---|---|---|
| 234723 | HELP decoder assertion only; no C64 writes | 064723-40789 |
| 235123 | Valid filmed chapters 1–3; alias MKDIR stopped chapter 4 | 065124-42760 |
| 000005 | Alias admission fixed; literal filename cleanup failure | 070006-46712 |
| 001350 | Canonical lifetime retained; literal filename lookup failure confirmed | 071351-52789 |
| 002019 | Latest build, raw/logical lookup regression fix; physical checks pending | 072020-56555 |

All roots above are under `/USB1/READYFS_TEST/readyfs-20261009-`. Earlier
failed roots remain evidence. The final video selects passing chapters only,
with chapter boundaries documented in the assembly report.

The 002019 take passed the entire focused physical alias regression: MKDIR,
COPY with byte identity, MOVE with source absence and destination identity,
DELETE, RMDIR, and an exact return to the original seed snapshot. The literal
host-name fix is physically confirmed. Filming chapter 4 began after that
regression; final nesting checks are still pending at this point.

Latest physical results: recursive COPY byte/shape oracle PASS; MOVE destination
byte/shape and source-descendant absence PASS; recursive DELETE plus explicit
empty-root removal PASS. CP, MOVE and DELETE what-if snapshots each match
before/after exactly. The original source subtree remains identical through
all phases. Canonical marker gates covered every mutation. The finale shows
CD into the surviving source, its DIR, and relative `TREE .`.

## Completed recording and public publication

- Latest physical take `demo-v2-20261009-002019`: SUCCESS; CPU settings and
  previously empty drive A restored, with recorded restoration evidence.
- All focused alias operations pass. All nested byte/shape/absence checks pass;
  three what-if before/after snapshots are identical. Deleted snapshot contains
  only the original source subtree; the marker is separately verified by RETR.
- Final edit: `ReadyFS/logs/readyfs_c64u/demo-v2-final-20261009`.
  Frames `[0,11224)` from the passing first three chapters of 235123, then
  `[3394,23270)` from 002019. The off-camera regression and failed material are
  excluded. No cuts inside selected demonstrations and no speed changes.
- 31,100 frames, 620.454545 seconds (10:20), 768×544, 50.124542 fps,
  silent H.264 MP4, 7.452699 MB, seven chapters. Both source takes have zero
  missing frames. 37 PASS assertions belong to the selected chapter windows.
  Event windows use exact chapter timestamps; frame boundaries round down
  less than one frame, avoiding misclassification of adjacent assertions.
- Final video SHA256:
  `fccaa313df863e5119d8c3ca79c8fc1a9d50c793571c035c974e6e2cf83ecc1a`.
- Site asset validator passes all required editor/history/paging and nested
  operation checks, chapter order, video hash, poster size and asset presence.
  Local HTTP page and byte-range video seeking pass. Existing player behavior
  is preserved; the native preview handoff was queued because the chat was not
  foreground. The public link handoff is likewise available in the chat panel.
- Existing public site updated successfully to version 2:
  https://readyfs-editor-demo.klumsy.chatgpt.site
- Site source commit `f28b3d0bcf2eb160589a1f4d7b63ff57f4b50e1a`, saved version
  `appgprj_6ac84b23269481919d1ea34651df6e6f~appgver_796f82b49a108191b16b6a7cab8c1bd4`,
  deployment `appgdep_6ac899334fe08191b84bb3bd86560286` SUCCEEDED.
- The final C64 build is `ReadyFS/artifacts/readyfs/readyfs-overlay.prg` with
  `readyfs-overlay-lab.d81`; the exact physical build is frozen in the latest
  take's build-snapshot with hashes. Complete `make readyfs` passed. No UCI
  transport edits and no claim of a new 1/16/64 MHz transport matrix.
- All earlier failed run roots remain evidence. No original data or unrelated
  folder was deleted, and no broad cleanup is authorized.
