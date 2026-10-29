# C33 true-CR capture correction

Source-only patch `capture.patch` adds TAX after R25 row_bit. Overlay calls preserve A/C and clobber X/Y; row_bit returns row/8 in A. Without TAX every CR bit was ORed into byte0. Shorten the capture loop JCC to BCC (assembler range checked) to recover3bytes; net code shrinks2bytes and the padded4096B/native-font layout stays fixed.

Build: `python3 src/render/grid/capture-fix-candidate/build.py OUT FIXTURE`. It verifies the unchanged helper SEO against actual183509 packaging through the test.

CPU gate: `python3 tests/test_grid_capture_fix.py`. PASS78 actual public frames covering all22rows in60/80, mixed softwrap/trueCR/EOF, selection at0/7/8/15/16/21, insert/backspace on7/8/15/16/21. Full forced-render reference and independent pixel/attribute oracle agree; actual canonical/history/shim preserved. Independent true-CR oracle checks all22bits everyframe. Old packaged masks were7f0000 in both mixed fixtures (first SP1 fixture wasff0000), explicitly retained as defect evidence; this does not characterize every old fast-path outcome as harmless.

Evidence: `agentsworking/evidence/M8/20261025T185008534522Z-grid-capture-fix`. No native/timing or general SP1 authority claim.
