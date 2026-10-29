# Integrated file coordinator ABI

Actual ca65 C12 coordinator/modal controller, C10 IEC transport and AUX popup/
independent recovery. Root routes F1 File O/S/A, F7 open/save/save as and CTRL-O/S
through commands80/81/82. CTRL modifier4 distinguishes CTRL-S from HOME ($13).
All C-slot requests return to resident before loading another C image.

## Measured placement

Current2f6d build: C10 BLOCK+transport3872/4096, C12 FILEIO3965/4096, AUX2272/4096.
FILESTATE852 shares LINEINDEX1152 at8D00–917F under explicit `se_f_owner` outside
that union. Owner plus current filename16/length/device uses19 resident BSS bytes.
Coordinator frame402 + preflight17 + provider264 + policy3 + modal166 =852.
No new ZP or ReadyOS shim memory is used. C8 refuses a nonzero owner before
accessing index/navigation. Claim/release invalidates derived index/render maps.

`state.s`, `preflight-state.s`, `dialog-state.s`, provider state and policy state
link once in resident FILESTATE. Provider uses SE_FILE_UNION; policy uses
SE_FILE_UNION+SE_FILE_STATE_ONLY. C12 policy links SE_FILE_CODE_ONLY. Exact sealed
resident imports resolve through a generated binding object. Never preserve a
code/data pointer into a C overlay across a request. Assets are cached before
opening data/raw channels; no disk overlay fetch occurs under open I/O.

## Root request protocol

C12 F_BEGIN1 begins; F_STEP2 advances; F_CANCEL3 requests bounded cleanup.
F_DIALOG6 acquires the union after pending typing/transactions finish and no
reader/writer owns the source. F_KEY4 accepts modal input; F_DIALOG_FINISH7
interprets completed directory/source work. F_DRAW5 is a legacy optional one-row
drawer omitted in production (SE_FILE_UI_KEY_ONLY); actual popup is AUX5.

Cclear/A1 means pending. The root consumes `se_f_request` exactly once, stores A
in `se_f_result`, carry as0/1 in `se_f_carry`, clears request, then reenters C12:

- C0–D2 are C10 transport operations from api.inc.
- E1/E8 are resident H_INIT/H_SAVED dispatches, never nested from C12.
- C12 retains all persistent state in the union;8000/8100 are explicit packets.

Cclear/A0 completes a slice/job, but root must inspect ui/owner: a completed
directory/error remains modal. Modal A2 means cancelled/released. Nonzero carry
is error. Provider90 argument/91 busy/92 IO/93 DOS/94 format/95 limit/96 ownership/
97 state/98 empty; coordinator99 capacity/9A changed/9B recovery/9C cancelled.
`se_f_error` plus raw/DOS copies survive cleanup. Never release the union solely
because phase0: require request0, preflight0, mode0, no leases/candidates and no
unhandled exact DOS capabilities. Existing root IRQ-head STOP/NMI polling runs
between slices; outstanding requests are consumed once before cancellation.

## Raw D81 preflight and filename identity

This adapter is read-only, ordinary unpartitioned1581/D81. Native filename and
device8/9 freeze for a transaction. Validate1–16 bytes, reject controls/DOS syntax/
all-space/A0 anywhere, preserve mixed native case/graphics/A1–FF. Prefix `0:`
before names, retaining literal@ without granting DOS replacement syntax. No
ASCII conversion or normalization is performed. Typed invalid bytes may display
until acceptance, then refuse90 before opening a channel.

FT_PREFLIGHT_BEGIN/STEP follow header/directory and the entire closed-SEQ chain,
one256-byte raw sector per STEP, computing exact24-bit length. Locked closedSEQ
is allowed. Invalid header/link/geometry/terminal00/00 refuses;3200-sector chain
budget prevents cycles. It cannot infer candidate absence across other types.

FT_EXISTS_BEGIN=$D2 uses the same bounded directory scan but regards EVERY
non-DEL type as occupied, including splat/unclosed/PRG/REL/locked/type7. It never
reads the candidate chain or opens it for write. Cclear/A2 pending, Cclear/A0
occupied; only completed exhausted directory yields Cset93/DOS62 definite absence.
Short names honor first-A0 DOS identity; exact16-byte private names compare all16.
Invalid header link0 refuses94. CANCEL closes owned rawLFN7 and resets kind/phase.

A successful DOS W-open alone cannot prove fresh ownership: pinnedVICE3.10 may
silently replace foreign unclosed non-REL files. C12 phase41 requires the all-type
absence proof before FT_CREATE. Occupied candidates yield93/DOS63 without CREATE,
W-open, ownership grant or disk mutation. DOS62 is accepted only with matching
error/carry/phase and no cancellation; a stale status cannot authorize creation.
Media swapping identity is not established; no arbitraryIEC/UltimateDOS guarantee.

## OPEN publication

Allocate private meta1bank and original ceil(length/65536), minimum1; borrow old
append read-only. Bound SEQ reads to256 bytes, check exact EOF/length/status and
close before publication. Old source/history/caret stay canonical throughout I/O.
Failure/cancel releases only private candidates. A512KiB small-file two-object
staging profile is CPU verified; large files may refuse99 without changing source.

Save old roots256+canonical22+epoch2, validate old tokens, temporarily adopt the
candidate and schedule H_INIT. Its acknowledged success is the publication
boundary. Bind newname/device before fallible old-token retirement; never restore
old roots against new history. Failed retirement keeps its queue entry and9B;
K refuses while this cleanup obligation remains. Root reloads hot/caret/view0 and
clears selection after committed2; clipboard survives. Pending/refused H_INIT
restores the old canonical/binding and releases only fresh objects.

## SAVE and recovery

Hold a read lease across length/generation/history snapshot, stream, comparison
and savepoint. Check generated temp absence, write bounded packets, close/status,
raw-chain length check and reopen/compare exact bytes+EOF. Then optionally rename
target to exact backup, promote verifiedtemp, independently verify final target,
delete only ownedbackup and request H_SAVED if source identity still matches.
Acknowledged H_SAVED binds newname/device before cleanup. Pending/refused H_SAVED
retains old binding/savepoint/dirty state even if verified diskfile exists.

Generic provider98 empty-write refusal remains. Narrow FT_EMPTY_CLOSE requires
expectedzero/ownedtemp/mode2/no writtenbytes; mandatory raw length/readback before
and after promotion proves exactzero. Empty preflight sets EOF before CHRIN to
avoid the pinnedVICE3.10 00/01 reader bug, with no fake NUL or raw disk writes.

Definite failures use policy cleanup/rollback; uncertain acknowledgements retain
exact temp/backup capabilities and report9B. AUX2 handles missingC12 independently:
close only known LFN5/7, validate document/frameepoch, restore unpublished OPEN or
complete acknowledged history binding, release owned candidates/lease. If AUX is
also unavailable, resident closes known channels and retains the frame. Staleepoch
never mutates a new document or guesses ownership. AUX4 F6 toggles modal help;
STOP closes only when source cleanup and capabilities are clear. K explicitly
keeps exact DOS files without DOS writes, but refuses unsafe RAM cleanup. Never
scratch by prefix or lose a failed-release token. Physical power-loss recovery
and media-swap identity are not established by these standalone tests.

## Modal UI

16native bytes, DEL, F3 device8/9, F5 next8-entry page, arrows select, Return accept,
STOP cancel, F6 help. Directory work reads one entry/slice and closes the page
before returning typing control. F1/F7 stay inside the modal. One bottom status
row, ReadyOS popup/frame/title/colors. Dirty OPEN freezes requested name/device
and offers S Save/D Discard/C Cancel. Unnamed Save routes to SaveAs then resumes
only after verified save. Recovery9B preserves exact candidate names.

`se_fd_command=0` means directory completion stays modal;1 means running fileop.
`se_fd_task` routes directory jobs; `se_fd_index` is deferredcancel, not selection.
`se_fd_list_index` selects the bounded8 entries. Resume stores separate OPEN
name16/length/device. F_DIALOG_FINISH may return A1 to continue save-before-open;
root inspects ui/owner before dismissing A0. Current filename stays outside union.

## Verification scope

`tests/test_editor_file.py`: isolated actual coordinator/document/object/history,
modeled root transport, emitted raw scanner;52cases on2f6d. Main production
`test_editor_file_integration.py --frozen ... --emergency`:42cases/22complete
1000cell-color frames, actual root/C8/C10/C11/C12/AUX, only ROM/DOS modeled.
`test_file_candidates_integration.py`:12 actual-root non-DEL candidate refusals,
asserts no CREATE/W-open and stable source/savepoint/clipboard. Isolated
`test_file_occupancy.py` exhausts256 type patterns/256 grammar bytes/136 A0 positions.
Native .NET D81 suites separately verify restart, normal binary/empty/>64KiB files,
real failure resources, explicit injections and foreign SEQ/PRG/splat whole-image
preservation. Read agentsworking/STATUS for exact artifact identities; do not
relabel older normal/fault freezes as final assets or claim physical key chords.
