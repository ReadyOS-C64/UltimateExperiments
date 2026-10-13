# ReadyFS continuation — 12 October 2026

## Delivered

- Guide now has a dedicated boundaries/possibilities section, five transfer recipes, full and short commands, aliases, explicit destination-filename rules, whole-image versus mounted-file distinction, and direct-image feature status.
- Added mounted-image discovery explanation: Ultimate REST GET /v1/drives returns internal drive image_file/image_path/bus_id/type/enabled and SoftwareIEC mappings. Match bus_id rather than assuming A=8 or B=9. Reference control target UCI 0x29 omits internal-drive image paths. Current ReadyFS DRIVES scans responding IEC units, not images. ReadyFS MOUNT does not yet save a mount-path record.
- Proposed future display distinguishes firmware-reported identity, last mount performed by ReadyFS, and unknown. Cache needs invalidation on dismount/swap/restart/external changes. Firmware unlink retains last image name, so queried identity does not prove write-back to that file.
- Summary output yellow; errors red; submitted commands cyan; ordinary data/help white. Console handles PETSCII color markers without screen cells/repaint; explicit CR restores white after yellow/red, soft wraps retain severity. REU history stores the original per-cell colors.
- Every command-help topic has 2–3 varied examples. docs/command-help.json is the readable source, build_support/build_readyfs_command_help.py creates a bounded byte-pair compressed header. 42 topics (unknown + 40 command IDs + FORMAT), 4844 source bytes -> 2565 packed bytes, depth 6.
- Fifteenth sidecar rfexamples holds examples. Cache 0x8A00–0x9A00 in existing batch REU bank; existing minimum 1 MiB REU unchanged. Presentation sidecar retains directory/free/CD formatting and now stages names and formats UCI errors/text. Device I/O and UCI transaction code remain resident.
- Reused utility decimal formatting in monolithic diagnostic to fit its existing memory gate. No removed command or weakened memory boundary.

## Verification

- Full `make readyfs` PASS (host suites, UCI source contract, pipeline contract, DMA contract, all 15 sidecars, strict memory report).
- Resident end $B569: 66 bytes below KERNAL scratch $B5AC; monolithic end $C5F7; largest help sidecar exactly 4096 bytes; cc65 stack top $D000.
- VICE run logs/vice_auto_20261012_165325 PASS. Tested boot, ALIAS, unknown-command error, ordinary PWD, output page up/down, HELP CP and H LS with new example text. Per-cell screen/color memory oracle confirms cyan echoes=3, yellow ALIAS SET=7, red UNKNOWN=2, white PWD result=1, both live and recalled history. Evidence severity-color-oracle.json.
- Existing host UI checks still verify minimal per-key screen writes, wrapping, 255-byte input, editing, recall/draft, continuation, and exact aliases.
- Guide remains 11 chapters, 18 embedded illustrations (16 authentic historical screenshots), standalone print styles, matching repo/Site bytes. Original 9 October video and SHA-256 retained unchanged, 37 physical checks. New code was checked in VICE, not newly deployed/tested on user hardware.
- No mutations to USB, SD, mounted user images, or IEC devices this turn. No new hardware mount changes.

## Remaining requested implementation

Direct `u:/usb1/image.d81/FILE` copy both directions and trailing-slash keep-name destinations are NOT implemented/verified. The guide explicitly marks these as work in progress. Do not claim them supported based only on a parsed path or firmware source. Mounted-drive COPY 8:/SHEET2 u:/usb1/SHEET2 is the existing route; 8:SHEET2 is outside absolute COPY contract. An alias cannot add a backend capability.

Reference firmware FileManager supports embedded images as folders; ReadyFS udos_change_absolute already splits / and !. Explicit ! is currently rejected by tape/core path policy. Slash form may reach native embedded FS but remains unverified. Direct writes need correct PRG/SEQ/USR staging file-type extension, careful final rename, conflict/rollback checks, and protection against concurrent mounted-image caches. Do not merely remove the parser guard and call it done. REL/special structures remain outside ordinary byte-stream copy. Folder destination resolution must occur before both preview and execution and include the same resolved name in journal/plan.

Physical work must follow ReadyFS/AGENTS.md: fresh marker-owned /usb1/READYFS_TEST/<run-id> or /sdcard/... roots; validate marker+canonical prefix before destructive steps; all REST/FTP via Terminal-owned/background wrappers. Occupied drive 8 must not be replaced for tests. Fresh unmounted owned image fixtures are needed for direct-image proof.

## Publication

Existing public Site: https://readyfs-editor-demo.klumsy.chatgpt.site/guide.html
Project: appgprj_6ac84b23269481919d1ea34651df6e6f
Markdown: ReadyFS/docs/READYFS_USER_GUIDE.md
Printable HTML: ReadyFS/docs/READYFS_USER_GUIDE.html
Site checkout: agentworking/readyfs-demo-site
Guide edits include mount-path explanation, color/build changes, and feature-status caveats. Use returned deployment records for the latest saved version and commit; keep the existing Site identity/public audience. Credentials are not stored in this note.

Latest publication: source commit da6bc7590be9c307db933a0a9a0dcaaf7d386f20; saved version 6, appgprj_6ac84b23269481919d1ea34651df6e6f~appgver_807aa765d7c48191b8972890f868d6b3.
