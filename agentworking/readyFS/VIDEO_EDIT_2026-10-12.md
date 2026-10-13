# Tighter video and descriptions above the C64

The user requested shorter waits and concise descriptions strictly at the top, preferably above the working display. This is a video/site edit; the C64 application and original passing hardware take were preserved. No hardware mutations or new network dependencies were introduced.

## Final cut

- Previous 840.286977 seconds (14:00); new 719.866925 seconds (11:59), saving 120.420053 seconds.
- Sixteen stationary waits shortened: 82.434668 seconds. Actual changing transfer output was retained after inspecting the full 25-row console, including its bottom rows. An earlier work-area-only analysis incorrectly treated output in those bottom rows as idle; that candidate was not published.
- One labelled jump removes 37.985384 seconds from the repetitive middle of typing the long quoted line. It ends before the complete 255-byte line, Home/End, overwrite and execution demonstrations. Retained footage stays at its recorded speed. Command editing, history and paging actions remain intact.
- Nine concise chapter titles with one short sentence each, shown for 4.8 seconds and faded. Card rectangle: x52/y12, 856×104, ending y116. Full C64 picture: x96/y144, 768×544, ending y688. They cannot overlap. Brief edit labels occupy y120–142, also entirely above the picture.
- The old browser track contained long full-chapter descriptions and could render over the C64 screen as captions. It is now a `kind="chapters"` navigation-only track with titles. The only descriptive overlays are burned into the separate top band.
- 37 steps, all actual screenshots and three extra preview pages preserved. All chapter/subchapter times and script Markdown were remapped through the cut list. Source evidence remains the original passing 62-check physical take, with zero missing source frames.
- Output: 36,083 frames at 50.124542 fps; 960×720; 9.48798 MB. MP4 SHA-256: `43a92aa99fb8d5af807f890a1ea39229853f33bb0e945e1aa125a8c071b73141`.

## Reproduction and checks

Sources: `ReadyFS/logs/readyfs_c64u/demo-v4-transfer-tour-20261012a` (undecorated capture) and `demo-v4-published-20261012` (earlier metadata/evidence). New analysis/evidence: `demo-v5-edit-20261012`; publishable assets: `demo-v5-published-20261012`.

Scripts: `analyze_readyfs_video_waits.py`, `plan_readyfs_video_cut.py`, `edit_readyfs_demo_v5.py`, `verify_readyfs_video_edit_v5.py` under ReadyFS/build_support. No NumPy dependency; use the existing skyleapgame C64 venv for Pillow, and Homebrew ffmpeg. The edit plan explicitly records every removed interval and protected demonstration.

Verification passed: all 37 command/screenshot records retained; typing and editing protections except the explicitly labelled repetition jump; no visible footer changes in any idle cut; header/edit labels above the image; remapped timestamps; all nine chapter frames visually inspected. Full `make readyfs` passed unchanged application gates. Site validation checked video hash, all assets, 20 guide illustrations, source hardware evidence and top-band geometry. Browser QA confirmed duration 719.866925, 9 chapters, 37 steps, `kind=chapters`, byte-range HTTP 206 and seeking to the updated editing chapter.

## Published version 9

- Public URL: https://readyfs-editor-demo.klumsy.chatgpt.site/
- Source commit: `419aeddc9eafebfc0f9dbd6bacd3a4e5d1d6f880`.
- Version: `appgprj_6ac84b23269481919d1ea34651df6e6f~appgver_ef2dd6dd52c08191a875bbbd46e081af`.
- Deployment: `appgdep_6acda68bee448191af5c92dfd387624c`, succeeded 2026-10-13T03:33:52.727093Z.
- Archive: `agentworking/readyfs-demo-v5-deploy.tar.gz`, 57 files, SHA-256 `f614bfc46e5e883edada838451bc12552855aeda017f043b18947883ca72dbf3`.
- Public browser confirms 11:59 and chapter-only track. Download points to the revised MP4. Proof: `agentworking/readyFS/READYFS_TIGHTER_VIDEO_PUBLISHED_2026-10-12.jpg`.


Subsequent request: further tighten and speed typing about 40%. Version 10 is now 10:22, with input at 1.4×. See VIDEO_PACING_2026-10-12.md and the durable recording preferences referenced by ReadyFS/AGENTS.md.
