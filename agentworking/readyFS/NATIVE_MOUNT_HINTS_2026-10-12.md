# Native mount hints and expanded demo

## Accepted design

The user explicitly rejected a Mac relay, network or REST dependency inside ReadyFS. Firmware source checks show native UCI GET_DRVINFO (control target 4, command 0x29) exposes drive type, bus number and power, without image identity. DOS GET_PATH is the DOS instance's current working directory, not a drive's backing image. The user authorized remembering paths for mounts ReadyFS makes if no native query exists.

ReadyFS therefore stores **session-only last-mount hints** for IEC 8–30. The normal overlay build uses its existing REU batch bank at 0x9A00–0xB0FF (23 independent 256-byte strings). Existing sidecar 14 handles display and record updates; no new sidecar, file registry, relay or network component. Startup clears every hint. Successful native mount acknowledgements record the resolved absolute host path; attempts clear old hints before command construction. DISMOUNT and SWAP clear hints when the actual operation is attempted. What-if paths return before those updates. Aliases are resolved by the existing path preparation.

DRIVES lists live IEC listeners through the resident bounded handshake, along with remembered paths when available. DIR, STAT and VOLUME show the same historical context. Each known path says `last mounted by readyfs` and `may have changed elsewhere`; absent hints say `image path unknown`. Unknown does not mean no media. No capability, overwrite permission or write-back guarantee is inferred from a hint. Native mount firmware ignores some internal mount-action return codes; an accepted request is not authoritative current-media proof.

F7 join remains functional and tested; its bottom legend entry is removed. Ordinary command help still documents the shortcut. Directory first-page accounting includes the path context so its lines remain readable before the normal page size resumes.

## Build and verification

- Full `make readyfs` passes host tests, overlay DMA and pipeline contracts, and memory layout report.
- UCI transport source is unchanged; its dedicated protocol verifier passes.
- Resident end after native display integration: $B57A (49 bytes before $B5AC KERNAL scratch); monolithic diagnostic end $C5F3; stack top $D000.
- Host presentation tests cover unknown paths, successful remembered paths, stale-data warning, independent device slots, maximum 255-byte path, invalid unit limits, explicit forgetting, and startup reset.
- Source gates enforce reset at boot, slot-14 integration, resident IEC handshake, clearing before shared UCI command-buffer construction, and remembering only after target OK. No network or media mutation is allowed inside the presentation module.
- The compact monolithic diagnostic build retains its previous drive display; full editor/help/mount hints are in the normal overlay build.

## Physical safety and recorder

New recorder v3 uses only fresh marker-owned USB1 test roots and the previously empty internal drive B, temporarily on IEC 9. It preserves occupied drive A/device 8 and its existing readyos.d81. The demo PRG copy patches its initialized sidecar boot device from 8 to 9; product default stays 8. Every disk write verifies the marker-owned backing image and unchanged drive A. CPU/B configuration is restored and fixtures are preserved.

The first preflight stopped safely because REST reported a full image path in image_file with an empty image_path; the guard initially expected split fields. Recovery validated that exact owned image and marker, removed only that mount, restored original B settings and verified both original drives. The corrected guard accepts either REST representation. REST/FTP here are external test and capture automation in Terminal, never ReadyFS runtime dependencies.

Publication and physical evidence locations will be appended once the final recording passes.

## Hardware admission checks

`ReadyFS/logs/readyfs_c64u/demo-v3-native-mount-matrix-20261012b/status.txt` is success. Native MOUNT and disk-to-host COPY/COMPARE passed at 1, 16 and 64 MHz. Host-to-disk COPY/COMPARE passed at 1 MHz. DISMOUNT cleared the path hint, and the exact original A/B drive states and CPU settings were restored. This preflight preceded the final resident I/O-helper refactor and yellow pager; the final recording runs additional native MOUNT checks at all three speeds on its exact build.

The requested yellow `-- more --` prompt now emits summary yellow only for the prompt text, then immediately restores normal white before accepting the continuation key. The passive recorder recognizes both white prompts from older evidence and yellow prompts from the new build.

## Yellow pager physical check

The exact final build passed native mount checks at 1, 16 and 64 MHz and dismount invalidation in `ReadyFS/logs/readyfs_c64u/demo-v3-final-native-tour-20261012b`. The `yellow-more-prompt` hardware oracle verifies all ten prompt characters have C64 color 7. `step-02.png` records the yellow prompt on the physical VIC display. Cyan command and white help-output RAM checks also pass. The full tour is still in progress; publication is not yet claimed.

## Completed final tour

`demo-v3-final-native-tour-20261012b/status.txt` is success. One passing take contains 9 chapters, 37 recorded steps, and 55 successful checks. Raw capture has 43,358 complete frames and zero missing frames. Native mount checks at 1/16/64 MHz and dismount invalidation precede the filmed tour. Only setup is trimmed; demonstrations keep their original speed. Final MP4: 13:30.900, 960×720, 40,646 frames, 11.2 MB, SHA-256 `e711e498a8d59e69b3b09810b92fdaf9e474fc21d350cd34851fa974538e5ec5`. Rounded chapter cards use 242/255 opacity, 6–11 seconds of reading time and fades.

The offline evidence verifier reads the exported owned D81 and confirms HOSTSEQ is SEQ with the exact 38 source bytes. The disk-to-host copy is independently SHA-256 checked against the 84-byte RFVIEW fixture. Original A/B states match exactly after restoration; CPU restoration completed. The new marker-owned root remains preserved. `verify_readyfs_demo_v3_evidence.py` reproduces these checks without hardware access.

Published assets are prepared in `ReadyFS/logs/readyfs_c64u/demo-v3-published-20261012`; the Site checkout has the same MP4, 37 actual screen captures, long-editor capture, chapters, recorded steps, script Markdown, captions and evidence report. Browser QA verified chapter and MOUNT subchapter seeking, all 37 step cards, editor-image expansion, download filename and printable guide navigation. The local range-capable preview server is required for native video seeking.

The guide retains its sixteen explicitly dated 9 October stills, while the site script contains fresh 12 October screenshots. Both Markdown and self-contained HTML explain yellow paging, stale session-only mount hints and native-interface limits.

## Published

Public Site: https://readyfs-editor-demo.klumsy.chatgpt.site/

Version 7: `appgprj_6ac84b23269481919d1ea34651df6e6f~appgver_fceda1e3a9148191926c831257097b11`

Source commit: `daf9fa736fcf7a0d9537ce7ef722ec0bb68d5aa1`

Deployment: `appgdep_6acd85d711ec8191bc3441bfbaa98685`, succeeded 2026-10-13 01:14:09 UTC. Existing public audience preserved. Archive has 52 files, SHA-256 `b67882b486c34611c16c00c041c49a5ec5e8b55b2ddf9785b1baea06d056cdc8`.

Downloads: `/readyfs-demo.mp4`, `/script.md`, `/script.json`, and `/guide.html`. Local preview QA passed before publication, and the existing Site tab was returned to the live URL.
