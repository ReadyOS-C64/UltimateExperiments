# Named transfer previews and optional readback

## User intent and sequencing

The user requested that recursive COPY/MOVE what-if report individual files rather than only aggregate counts, that real transfer output identify the file next to the byte count, and that verification can be skipped explicitly once trusted. They asked to finish the then-current video before changing and rerecording. The previous complete physical tour was already successful and published as Site version 7 before this implementation began. That earlier recording and its evidence remain preserved.

## Behavior

- Recursive COPY, MOVE and DELETE what-if display source root, destination root for transfers, then every selected serialized plan record as `would copy`, `would move`, or `would delete`. Directories carry `dir`; names are relative to the printed roots. Unselected entries are omitted.
- The preview reader uses existing REU plan/root storage. It never sends executor START/ACK, performs a storage mutation, or marks journal actions complete. Existing planning can still enumerate/read metadata. The final yellow line says `whatif: no files changed`.
- Long previews pause at a yellow `-- more --` before continuing. The pause is paced by the person reading; no per-keystroke screen redraw change was added.
- Each real file transfer first prints its full resolved source path. Completion prints `copied <basename>: <bytes> bytes`, accompanied by `verify: identical`, `verify: skipped`, or the tape-readback limitation. An I/O failure identifies the source basename and bytes transferred before failure.
- COPY/MOVE verify staged destination content by default. `--no-verify` and exact short alias `-nv` skip that destination readback for one command, including every file in a recursive batch. Each new COPY/MOVE recomputes the option; it cannot stick accidentally across commands. Explicit COMPARE/CM/VERIFY remains available for occasional later checks.
- Source preflight, checked writes, temporary staging, overwrite/backup/rollback handling and ordinary move-source cleanup remain. Source signature accumulation is retained to keep resident code small. Skip mode saves the extra destination read; it is not an integrity guarantee. A successful unverified MOVE commits the destination then removes its source without catching silent corruption first.
- WRITE/APPEND/RENAME and explicit comparisons keep their own checking behavior. Tape already cannot provide immediate destination readback and continues to say so.
- Full behavior belongs to normal `readyfs-overlay.prg`; the compact monolithic diagnostic retains its earlier transfer reporting/checking policy. The guide already directs users to the overlay application.

## Implementation and memory

`readyfs_io.h` adds `skip_verify` to the one-pointer call record. `cmd_copy_move` sets it before either single-file or recursive dispatch. Destination signature admission is conditional on that flag, before commit. No UCI transport source changed.

Presentation slot 14 now includes `readyfs_transfer.c`, a bounded 32-bit decimal formatter for byte counts, batch completion formatting, and factored STAT formatting. Factoring existing display code avoids expanding resident RAM. Presentation slot 15 includes `readyfs_preview.c` alongside compressed per-command help; the resident gateway routes PLAN there. No additional sidecars or REU regions were introduced. Plan header size (six bytes) is shared by writer and read-only reader.

Important aliasing constraint: native_plan occupies dest storage. Backend REPORT overwrites that workspace. Preview therefore reloads source and destination roots from REU; do not pass dest.canonical after REPORT as though it still contains a path.

Full build passes with resident end $B5A4: only seven safe bytes remain before $B5AC KERNAL scratch. Monolithic diagnostic ends $C5FB; slot 14 payload $FCD (4045 bytes), slot 15 $F46 (3910 bytes); stack top remains $D000. Do not relax memory gates. Future resident additions need more factoring or lifetime analysis.

## Verification completed before recording

- Full `make readyfs`: host tests, pipeline contract, overlay DMA contract, UCI protocol contract and memory report PASS.
- Host presentation tests: full source display; named completion/failure; verified, skipped and tape statuses; full 32-bit count 4294967295; selected nested file and directory records for copy/move/delete; omitted unselected record; REU contents unchanged; yellow paging; malformed record rejection; empty selection; moved STAT formatting.
- UI tests: exact `-nv` expansion to `--no-verify`, retaining all earlier alias/editor/minimal-drawing tests.
- Source gates: skip-readback flag refreshed on each COPY/MOVE; explicit flag guards destination signature read; preview cannot invoke storage, executor or REU writes. Existing staged-before-commit order gates remain intact.

## Updated capture and site work

Recorder v4 is `ReadyFS/build_support/run_readyfs_c64u_demo_v4.py`, launched through its matching Terminal wrapper. It preserves all prior chapters/editor tests, native mount checks at 1/16/64 MHz and drive-A safeguards. It adds named preview-page captures, assertions that every fixture filename is listed, a single host-to-disk COPY with `--no-verify` followed by COMPARE, and recursive MOVE with `-nv` followed by independent tree/byte checks. Pages receive six seconds of reading time before continuation. The original recording speed is retained.

The current run uses a new exact marker-owned root, preserved by default. Disk writes use only its disposable media.d81 on previously empty drive B temporarily at IEC 9. User drive A/device 8 remains occupied by its original readyos.d81 and is not mutated. REST/FTP are external test/capture automation in Terminal, never a ReadyFS runtime dependency or Mac relay.

The guide explains per-command/default semantics, actual output labels, relative plan paths and the move integrity tradeoff. Markdown remains source of truth; standalone HTML embeds all illustrations for offline printing. The Site retains chapters, subchapters, download controls and actual colored console snapshots; expandable preview-page galleries expose the whole file list rather than just the final screen.

## Completed physical evidence

The full continuous take succeeded: `ReadyFS/logs/readyfs_c64u/demo-v4-transfer-tour-20261012a`. All 62 hardware checks passed; 44,847 complete raw frames, zero missing frames. Original CPU settings and drives A/B were restored and verified. The fresh preserved marker-owned root is `/USB1/READYFS_TEST/readyfs-20261013-013111-90069`.

`verify_readyfs_demo_v4_evidence.py` passed independent saved-evidence checks: actual exported D81 contains the 38-byte HOSTSEQ as SEQ; disk-to-host 84-byte file hash matches; original and restored drives are identical. It checks the complete recorded page text for five `would <verb> <file>` and three `would <verb> dir <folder>` lines in each COPY/MOVE/DELETE preview; all three additional preview pages have yellow MORE. Single-file skip followed by explicit COMPARE, default verification returning on the next recursive COPY, and recursive MOVE skip with independent tree/byte checks all PASS.

Publishable assets: `ReadyFS/logs/readyfs_c64u/demo-v4-published-20261012`.
- MP4: 840.286977 seconds (14:00), 960×720, 42,119 complete output frames, 11.481321 MB.
- SHA-256: `8bc822287809e15329ca2c6f235db6d9c13ebf981135d9dc4191c54832a2bfa7`.
- Setup trimmed 54.424437 seconds; all demonstrations retain original speed. Nine 95%-opaque rounded chapter cards have readable timing and fades.
- Nine chapters, 37 steps, 37 actual step PNGs, one long-editor PNG and three extra preview-page PNGs. Script JSON/Markdown, captions, hardware-check list, video report and two independent evidence reports retained.

The standalone guide now has 20 embedded illustrations: sixteen preserved historical screenshots, two current transfer screenshots and two diagrams. Source provenance for the current stills is in `docs/guide-assets/transfer-screenshots-2026-10-12.json`. Site validation confirms that its guide exactly matches the repo HTML.

Browser QA confirmed 9 chapters, 37 steps, 3 expandable preview galleries, 840.286977-second video metadata, the video download attribute, complete root context on the earlier preview page, successful native video seeking into chapter 6 and pause controls. Byte-range support returns HTTP 206 in local preview. Blank leading/trailing console rows are trimmed for readability while raw snapshots remain in the JSON.

Publication provenance follows below.


## Published version 8

- Public Site: https://readyfs-editor-demo.klumsy.chatgpt.site/
- Source commit: `be098243279f3182d0b2621d606d54ecc0a4211a`.
- Saved version: `appgprj_6ac84b23269481919d1ea34651df6e6f~appgver_d290572bfaf08191905c1175c685c0eb` (version 8).
- Deployment: `appgdep_6acd8fa16d40819180319facf83ad6d8`, succeeded 2026-10-13T01:55:56.608405Z.
- Source-helper archive: `agentworking/readyfs-demo-v4-deploy.tar.gz`, 56 files, SHA-256 `68979afcb3d6650e2ac89f78aa446a2e2efb82c2bc4770632e1cbfb6371ad8b2`.
- Public browser confirmed 14:00 duration, 37 script steps, 3 expanded-preview galleries available, and 62 passed checks. Updated video remains downloadable; standalone illustrated guide remains printable and downloadable. Public audience preserved.


Subsequent video edit: see VIDEO_EDIT_2026-10-12.md. Version 9 shortens the tour to 11:59 and puts concise descriptions strictly above the C64 picture. Application behavior and physical evidence are unchanged.
