# Faster input and tighter demo: published version 10

## User preference

The user asked to tighten the existing edited video further, present typing and similar input about 40% faster, and remember this for future recordings. Current work edits existing footage only. Durable preferences are now in ReadyFS/docs/DEMO_RECORDING_PREFERENCES.md, referenced from ReadyFS/AGENTS.md and THREAD_GROUNDING.md.

Default finished-video input rate is **1.4×**, meaning 40% faster rather than 40% less time. Keep physical filesystem execution/results and page-reading pauses at recorded speed. Tighten genuinely unchanged waits; avoid repetitive entry; keep concise descriptions strictly above the C64 picture. Preserve source evidence, exact path/option examples and remap all timestamps.

## Final video

- Version 9 length: 719.866925 seconds (11:59). New: 622.70893 seconds (10:22), another 97.157995 seconds shorter.
- Source remains original passing v4 hardware take: demo-v4-transfer-tour-20261012a. No new device mutations or recording performed.
- Relative to original 840.286977-second publication: 110.843905 seconds of stationary waits removed, 37.985384 seconds of repeated long-entry removed, and 68.731657 seconds saved by 1.4× input playback (minor frame rounding).
- All 37 steps, actual screenshots, three extra preview pages and source 62-check evidence retained. Execution/results and page-reading intervals are 1×; input editing at 1.4× includes middle insertion, long-entry cursor/overwrite actions, and command typing. History page-reading holds remain readable.
- 31,213 frames at 50.124542 fps, 960×720, 8.570658 MB. MP4 SHA-256: 347003c769228527d87a7d9855151e6b9e2bd493c8cd23951aa225037d998f07.
- Header cards remain at x52/y12, 856×104; C64 image begins y144. Navigation-only chapter track contains no description captions. Edit labels also stay above the image.

## Reproduction and checks

New files under ReadyFS/build_support: plan_readyfs_video_v6.py, edit_readyfs_demo_v6.py, verify_readyfs_video_v6.py. Planning uses the audited full-console stationary analysis from v5 and source timing records. Rate windows are restricted to input interactions; all other retained source segments use 1×. Source boundaries and output segment lengths are frame exact; chapter/step times map through that same frame-count model.

Analysis/verification: ReadyFS/logs/readyfs_c64u/demo-v6-edit-20261012. Publishable assets: demo-v6-published-20261012. Verification passed: same 37 input/output records and screenshots, all typing segments at nominal 1.4×, others at 1×, exact output frame sum, remapped timestamps, unchanged full-console pixels within idle cuts, and all descriptions above the image. Full make readyfs passed. Website validation passed its video hash, guide byte equality, 20 embedded illustrations, 9 chapters, all step assets and original evidence.

Browser QA confirmed 622.70893-second metadata, 37 step cards, the visible 1.4× note, chapter seeking and playback/pause in the editing chapter. Byte ranges return HTTP 206. Guide prose and downloadable script explain the input-only speedup. Site video download serves the revised MP4.

## Published provenance

Public URL: https://readyfs-editor-demo.klumsy.chatgpt.site/
Source commit: 3af7adf415001428ea09bdcd95514776feae4cb8.
Saved version 10: appgprj_6ac84b23269481919d1ea34651df6e6f~appgver_11777d55a4d48191b28aa26b2cf8c1d3.
Deployment: appgdep_6acdaa2961b88191831831af63a5c39b, succeeded 2026-10-13T03:49:06.529683Z.
Archive: agentworking/readyfs-demo-v6-deploy.tar.gz; 57 files; SHA-256 a67ad0ca6c9b32dce0bab01591151f547fac38542a7a67103c83bb6e4e43144d.
Public browser shows 10:22 and the 1.4× note. Proof: READYFS_FASTER_DEMO_PUBLISHED_2026-10-12.jpg.
