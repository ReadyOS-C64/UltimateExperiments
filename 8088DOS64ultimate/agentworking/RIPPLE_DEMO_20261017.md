# RIPPLE physical Pascal picture

User request: a small static Turbo Pascal picture using supported C64-hosted
display modes, with actual editor and completed-picture screenshots inline.

`examples/RIPPLE.PAS` selects 40-column colour text, draws two integer-distance
ripple fields with full-block characters and eight selected RGBI colours, then
prints its completion caption and waits in BIOS keyboard input. A key restores
80-column text. No CRT unit, floating point or 80186 code generation is used.
No emulator or native memory layout changes are required.

Root alone controls hardware through detached Terminal shells and the existing
.NET native-scenario harness. The same running native C channel is retained;
there is no reset, injected guest file, or replacement DOS file implementation.
The complete source was typed through genuine DOS `COPY CON C:\RIPPLE.PAS`,
including Ctrl-Z/Enter. DOS's `1 File(s) copied` and returned prompt passed.

First lane: `agentworking/runs/c64u-physical-ripple-source-20261017`.
Its final editor predicate was too broad and matched the DOS source echo plus
the accepted TURBO command. That screenshot is rejected as editor evidence.
All original inputs/results remain intact; qualification is recorded in
`evidence/ripple-source-observer-qualification-20261017.json`.

Second lane: `agentworking/runs/c64u-physical-ripple-picture-20261017`.
It requires the actual Turbo editor footer, filename and source, and absence
of COPY CON/copied output before any compile key. Disk compilation and DOS EXE execution passed. All18 source lines and all1000
finished guest cells (960 coloured blocks) match. All6 frames pass full native
bitmap/matrix and actual VIC pixel checks. Original PNGs are exported under
`docs/screenshots/physical-ripple-20261017`; both requested images were posted
inline. The first editor frame is now independently verified, unlike the first
lane's rejected DOS echo frame. Evidence: `evidence/physical-ripple-root-20261017.json`.

Terminal1688 exited0/no watchdog; all25 frozen inputs stayed unchanged. Native
IDE exit took several minutes within the original bound. No additional exit,
recompile or reset was needed. A prepared third continuation was never frozen
or dispatched and has been removed. Executed .NET source/DLL copies are in the
second run's `executed-driver`. The final machine is RUNNING on the picture,
waiting for a key, with C backing file OPEN. Pressing a key restores80-column
text and returns to DOS. No new whole-image close/cold persistence test.

The final launch-completion wait to PNG interval was23.6 wall seconds. This
includes guest EXE loading/drawing and paused observation/video capture; it is
not pure draw time or an XT speed comparison.

Filesystem scope remains unchanged: native 2 MiB installation passed; native
20 MiB installation failed at WRITE_NEW/UCI03. The active 20 MiB runtime uses a
host-prepared development fixture. Earlier actual Turbo file save, compile,
native CLOSE, whole-image preservation and cold restart passed. Native CONFIG,
floppy swap/Save/Finish and human qualification remain open.
