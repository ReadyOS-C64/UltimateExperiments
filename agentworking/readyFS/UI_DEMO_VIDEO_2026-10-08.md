# ReadyFS demo video — 2026-10-08

## Delivered recording

- Duration: 528.743 seconds (8:49 rounded).
- Actual C64 Ultimate VIC UDP capture at 1 MHz, 26,503 PAL frames, 768 × 544.
- 32 passing hardware assertions inside the selected footage; zero missing source frames.
- MP4: 5.1 MB, silent, original speed. No generated C64 screen.
- Three takes joined only at chapter boundaries; no cuts inside the selected demonstrations.
- Website source: `agentworking/readyfs-demo-site`; recording: `dist/readyfs-demo.mp4`.
- Site identity: `appgprj_6ac84b23269481919d1ea34651df6e6f`.
- Expected public URL: https://readyfs-editor-demo.klumsy.chatgpt.site/

## Coverage

- 0:00 — 01 · ReadyFS on a real C64: 1 MHz. Actual VIC display; human-paced keystrokes throughout.
- 0:34 — 02 · Insert, overwrite, Home and End: Correct a missing letter, replace a typo, and remove unwanted text.
- 1:15 — 03 · Files, aliases and relative paths: Read the same fixture using absolute, relative and @alias paths.
- 2:48 — 04 · Long lines and the moving input viewport: Type a 255-byte command. Scroll to its beginning and end; edit the tail.
- 4:18 — 05 · Recall, edit and restore a draft: Up walks older commands. Down walks newer ones and restores the unsent draft.
- 5:07 — 06 · Full and short options; quoted paths: Dry-run write and copy commands show plans without changing storage.
- 7:00 — 07 · Page Up and Page Down through output: F1 = Page Up; F3 = Page Down. Pauses let you read each page. STOP restores the draft.
- 7:59 — 08 · Join a command across entries: F7 joins input with a space. Finish the quoted message on the next entry.
- 8:39 — 09 · Demo complete: Editing, 255-byte input, history, paging, aliases and dry-run options checked on hardware.

## Safety and hardware evidence

Only the freshly built local D81 was mounted, after verifying drive A was empty,
enabled, 1581 and bus 8. Mounted fixture reads only. USB write/copy examples are
dry runs; partitioned examples translate command strings without executing I/O.
No USB/SD files were created, deleted or overwritten. Original CPU settings and
empty drive A were restored after each take, including failed capture-script checks.
Video streaming stopped. The application itself was not changed or rebuilt.

Final successful take: `ReadyFS/logs/readyfs_c64u/demo-20261008-191900/status.txt`
contains `success`; its events include exact resident CODE/RODATA verification at
1 MHz, paging draft restoration, execution of that draft, and continuation preview.

## Recording-script repairs and preserved evidence

- `demo-20261008-185958`: insertion/overwrite/deletion and all selected chapter 1–3
  cases passed. The 255-byte comparison incorrectly compared lowercase host text
  against the uppercase injected buffer. Its failed long-line section is excluded.
- The borrowed UDP decoder initially reversed adjacent pixels. Correct low-nibble-
  first decoding is now in the runner; the original incorrect encoding is retained
  as `readyfs-demo-initial-decoder.mp4`. Initial selected footage was corrected
  without timing changes. Later takes decode correctly directly.
- `demo-20261008-190748`: strict attachment refused a resident comparison at the
  restored turbo settings. No recording or filesystem command followed. Subsequent
  resident inspection at 1 MHz showed zero CODE/RODATA differences. The final
  attachment sets 1 MHz before checking and passes the original complete oracle.
- `demo-20261008-190954`: long-line, editable history, command/option and native
  translation checks passed. The capture script sent more Page Down keys than
  available older pages, returned to live input, then STOP correctly cancelled its
  draft. This failed script expectation is excluded from the final edit.
- `demo-20261008-191900`: paging adapts to actual buffered rows, walks three older
  and three newer pages at four-second pauses, and STOP restores the draft intact.
  All remaining checks pass.
- Chapter timing uses first-packet wall time for later takes. Initial chapter
  offsets were reconstructed from event times and the three-second stream warmup.

The final `video-report.json` records source frame ranges, checksum and capture
statistics; `hardware-checks.json` lists only PASS assertions in the selected clips.

## Website checks

- All local assets, nine increasing chapter timestamps, dimensions, required
  editor/history/paging assertions and final MP4 SHA-256 verified.
- Native video seeking verified through chapter buttons and browser WebMCP.
  Invalid chapter input fails without altering video state.
- Local preview supports byte ranges; standard Python static serving could not
  seek beyond the buffered video portion and was replaced.
- Actual download verified byte-for-byte against the published source MP4.
- User download saved at `/Users/karlprosserpp/Downloads/readyfs-demo.mp4`.

SHA-256: `d01364237bab757cf29964e6cd0f907711e4de06abd4b3c749f3128101e5d7b6`

## Publication confirmed

- Public Site deployment succeeded: https://readyfs-editor-demo.klumsy.chatgpt.site
- Saved version: 1.
- Source commit: `b10bf5b5b0f9be351cafb7c880fb5bfa38c3d295`.
- Deployment: `appgdep_6ac850e07a1881919341c7a936a516bf`.
- Final video and download button contain the same verified 5,149,290-byte MP4.
