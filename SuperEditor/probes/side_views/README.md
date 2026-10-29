# Actual 80-column and GEOS side previews

Run `python3 probes/side_views/run.py`. It builds only `build/side-views`, creates
an owned disposable D81, and uses the existing .NET VICE path with warp/traps and
`headless=true` (`-console +sound`). Reserve binary6800 plus text6900..6939;
the text-monitor port finder uses a separate40-port range. No stale/global
process is killed, and the harness closes its owned emulator after capture.

The probe reuses the actual M1 `src/probe_display.s` drawing routines and
unchanged generated narrow4/English GEOS BSW9 fonts. It adds a small full8px
adapter for physical40-tile chrome and aligned GEOS code. 1 selects80 columns,
2 selectsGEOS, F6 toggles help. One400-byte native source fixture backs both
scripted visual plans. This is not an editor or a parser/folding implementation.

Chrome matches the root's frozen titlecase40-tile ABI: row0 menu, yellow native
verticals at0/6/12/18/27/34/39; row1 rule with bottom corners and upward junctions.
Body begins y16; exactly one status row begins y192. It has no top title/status
line. The80-cell ruler spans all320 pixels; GEOS body uses actual proportional
BSW metrics with actual bold/italic transforms and8px native fixed code.

The latest corrected capture is
`agentsworking/evidence/M6/20261024T220623369509Z-side-previews`.
All three native PNGs were visually reviewed; integer3x copies are retained.
Independent checks pass192000 captured VIC shape/color pixels,15360 exact header
pixels, and10293 narrow/GEOS style/ruler pixels. The full native source agrees
between all captures and the1024-byte ReadyOS shim remains untouched.

The original220313 capture with lowercase menu initials is preserved. The
corrected220623 source ZIP also preserves the initial oracle assumptions;
`verification-sources.zip` contains the corrected trueRGB/native-pipe oracle.
Neither old source archive was silently replaced or relabeled.

The M1 pixel backend retains its rank-only tile conflict shortcut. The new
ink-majority narrow-row service is separate and CPU-verified; these previews do
not imply it is integrated. Readability, especially at four-pixel pitch, remains
something to judge from native and integer-scaled screenshots.
