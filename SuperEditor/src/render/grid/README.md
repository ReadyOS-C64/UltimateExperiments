# C16 narrow source producer

Actual command overlay entry `src/overlays/grid-editor.s`, operation1 source body + logical40-column chrome, operation2 native8 UI finalization. Initial private producer image2542 bytes including16-byte binding, reusable625-byte chrome and116-byte header. Link with generated editor API and `cfg/overlay-c.cfg`; chrome/header objects require `EDITOR_OVERLAY=1`. C16 is not a resident dispatcher or mode UI. Current combined image with mode/context/color/cache3681 bytes (0659). Parent owns integration. The default40 renderer is unaffected while unused.

Caller owns foreground workspace `$8880–$8A43` (452-byte extent), excluding diagnostics `$8800–$887F`, VIEW `$8C00`, FILE/LINEINDEX `$8D00`, NAV `$9180` and HOT `$9200`. It contains NR68, three80-byte arrays, BC11, private counters/24-bit positions and22 private end anchors. No resident BSS or zero-page allocation. Existing resident text/screen pointer pairs are loaned by the R leaf. Producer never reads phase-union fields. It acquires no read lease and never calls source mutation/history/COW services.

Operation1 accepts `se_v_columns=60/80` only. It calls `se_view_init`, then checks C11 map valid, no live navigation continuation, captured width, original/append tokens10, committed generation2, visible revision4 and top3. Only after that does it read22 row anchors and bottom; it checks monotonic positions, source bounds, repeatedEOF validity and wrap spans no wider than the captured width. It resolves CR-exclusive ends and the caret's genuine row. A stale/off-caret map sets `se_l_need_wrap=1`, returns A0/Cclear and calls no leaf or pixel service. Invalid dimension returns7B/Cset. Actual read errors propagate.

No-wrap automatic pan uses24-bit column arithmetic and reveals caret with the last visible column when needed. Manual pan may hide the caret; pan beyond a line is clamped to a synthetic end+1 blank position to avoid24-bit overflow. Wrap and no-wrap do not alter source caret or shared anchors. Each source row holds at most60/80 native bytes, plain role0 and selection/caret flags. R16 is80-column, R17 is60-column. `GRID_ADMIT=2` proves the checked correct leaf exists before output; rows use op0. CR/EOF emit real blank positions; padding is plain and repeatedEOF anchors publish `se_v_seen` only once. Caret row/column are zero-based body coordinates.

After22 rows, operation1 calls the shared editor chrome to produce logical native screen codes at physical40-column rows0/1/24. The caller then lets C7/AUX paint any logical popup. Operation2 converts those three chrome rows through leaf op1 (native8 cell). It also converts the clipped box rectangle when `(se_e_ui==1 && se_e_menu!=0) || se_e_ui==3`. A popup crossing chrome is converted once. Each cell reads screen code and D800 foreground before replacing the matrix byte with a hires attribute. Background is ReadyOS blue6. Body outside the popup remains unchanged. Bitmap writes terminate at `$7F3F`; catalog tail `$7F40–$7FFF` remains intact. Shared narrow leaf fonts are fixed narrowA800/nativeAC00.

The producer requests and consumes a full exact-context narrow style plan at4800 (60×22 or80×22), never the old880-cell source40 plan. The descriptor width is encoded in byte32 as mode*2|nowrap. Emphasis/strong/combined/code flags map to existing semantic roles1/2/3/4; lexer low colors map keyword7,number8,string9,comment10,label12. Unmodified headings use strong priority and separate inversion. Tile foreground is chosen by the existing ink-count/priority policy; selection and caret invert their union once. The plan aliases the inactive40 font, restored by the real mode40 initializer. Source/history bytes are unchanged. Main8784CPU/native matrices pass; archive/fault cases and efficient dirty rows remain tracked in STATUS.

`python3 tests/test_grid_editor.py` compiles only private output under `build/grid-editor`. Its immutable frozen46c8 resident/report/assets must be preserved there (or restored from the evidence below). Actual C11 builds maps; actual view services read merged pending source; newly built C16 and both R leaves use the same resident binding and checked cache.36 full screens,2,304,000 pixels,828 anchors, full2MiB REU profiles, source/history/hot/selection, opaque owner1 FILE851, NAV, diagnostics prefix, style/checkpoint and1024-byte shim guards pass. Coverage includes60/80 wrap/no-wrap, auto/manual pan,66KiB logical lines/24-bit columns, mixed native glyphs, selection/caret union, exact width/CR/EOF, pending insertion, fullpopup/chrome overlap, missing leaf and stale/malformed maps. Evidence: `agentsworking/evidence/M6/20261024T230737136174Z-grid-source-producer`.

Peak whole-operation1,432,796 CPU instructions includes real checked overlays and synchronous full rows. This is not a timing or responsiveness bound; parent must assess/measure scheduling and native behavior. No VICE/native screenshots, actual mode commands or integrated editable-mode claim are made by this private gate.

## Warm mode operation3

`src/render/grid/mode.s` is a separately linked object exporting `grid_mode`; it includes generated numeric resident aliases only, no additive field/global imports. CODE218 +RODATA6, entry dispatch+7 bytes. C16 now2773/free1323. Op3 reads `se_e_command`:96/97/98 select40/60/80,100 cycles forward (modifier4 reverses),101 cycles backward;99/unknown or invalid old mode return77. Owner!=0, active navigation or owned nav lease returns7A before leaf admission.

Requested60/80 first calls checked renderer `GRID_ADMIT=2` through the resident cache. Admission failure preserves old mode, width, VIC registers, layout/cache flags, viewport/pan, screen and font. Success publishes mode0/1/2, width0/60/80 and bitmap D01808/D0113B/D01608/sprites0. Leaving bitmap for40 invokes warm resident `se_display_init` under PHP/SEI/PLP; same40 does not recopy/clear. CIA unrelated bits and CPU port follow the resident initializer contract. Both entry IRQ states remain unchanged.

After success op3 clears render/layout/style validity, request/checkpoint validity, preferred column validity, manual pan/pan3 and top3; it sets need_wrap/redraw1. Source, pending gap, hot context, caret, selection, clipboard/history, file owner/frame and current UI are untouched. Root must cancel its optional owner2 work before entering and must schedule C11/redraw; this module does not flush pending source or request a cold service.

`python3 tests/test_grid_mode.py` passes42 transitions,9 unavailable/admission cases and5 busy refusals, both IRQ states, real same-seal leaves, warm resident initializer execution, exact pending source/history/clipboard/selection/hot/phase/diag/shim/catalog and whole2MiB REU guards. Producer36-screen gate rerun on this same2773-byte image also passes. Evidence: `agentsworking/evidence/M6/20261024T231102584165Z-grid-mode`. The CPU fixture does not model native character-ROM banking pixels; parent native mode/render/key evidence remains required.

## Exact row cache and specialized80 leaf

The current C16 links the387-byte cache micromodule. Nine resident bytes at
C574–C57C retain a logical FE-owned bank handle/epoch, width,22 valid bits and
UI flags. Full240-byte character/role/flag packets are compared exactly through
8A44–8B33; only successful leaf paint can commit a row. Mode/font/output resets
invalidate all rows; popup close conservatively repairs opaque coverage. Cache
faults leave the editor functional. Only5280 owned REU bytes contain packets.

R16 now uses row80.s:1477 bytes including tables, no BSS/ZP, strict80-column
NR68 contract. Native8 UI and fixed fonts A800/AC00 remain unchanged. R17 keeps
the general60 renderer. ActualCPU/native0659 gates and instruction comparisons
are in agentsworking/evidence/M6/grid-fast-editor-checkpoint.json.
