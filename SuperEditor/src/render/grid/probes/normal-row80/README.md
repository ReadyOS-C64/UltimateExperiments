# Normal-role 80-column rows

R16 checks the effective roles of the clipped row once. If every role is normal
(including unknown IDs, which the public ABI maps to normal), palette0 already
fills all forty attributes. It can omit ink counting and color arbitration.
Glyph conversion, raw/explicit inverse union, selection/caret union, odd counts,
blank tails and all scalar argument validation retain their existing behavior.
Any known nonzero role uses the original arbitration path. Only existing caller
scratch NR_TILE is borrowed; no resident state, new ABI, allocation or font moves.

The normal pixel loops are unrolled over eight scanlines. R16 CODE/RODATA ends
at A7DB:36bytes remain before its unchanged A800 font. The native font remains
AC00. Both fonts and resident bytes are exact. The complete59 foreground graph
retains its relative68-byte bound including one IRQ/NMI.

`build.py` first reassembles the immutable946e7d3 control exactly, then builds
the candidate. Its `--packaged` path also rebuilds the actual R25 and C33 native
CRC witnesses. Changing R16 without those authentic witnesses must refuse;
there is no CRC or verified-bit waiver. All84 D81 files are independently read;
only GRID80, GEOSTAIL and GRID data change, with directory/sector links exact.

```sh
python3 src/render/grid/probes/normal-row80/build.py build/my-normal-row80 --packaged
python3 tests/test_normal_row80.py
python3 tests/test_normal_row80.py --public --fixture build/my-normal-row80/fixture
python3 tests/test_normal_row80_vice.py
python3 tests/test_normal_row80_vice.py --source build/my-normal-row80/fixture
```

The component verifier obtains its control row source from the immutable ZIP,
so promoting the production source cannot silently turn the comparison into
candidate-versus-candidate.934rows plus17invalid inputs per variant pass the
independent pixel/tile oracle, immutable19-byte input frame,52KiB RAM guards,
ReadyOS reserve and512KiB unchanged REU. Every256 input values occur in every
column in both encodings; all flag combinations,25rows, counts0..81/255 and
known/nonzero/unknown roles are covered. Normal rows use30.77% fewer instructions;
the mixed-role fallback costs1.36% more at the component level.

Actual packaged CPU public20 control/candidate frames show Plain80 insert/delete
about12.8% fewer instructions, Full80 about5.78%;60-column costs are unchanged.
Twenty wrapped-edit frames and24 prewrite refusals retain independent pixels,
source/history, packet/header CRCs, source positions above64KiB and exact whole
16MiB checked-DMA masks. Wrapped edits use their existing glyph-shift route.

Native PAL uses actual Full-default products, public IRQ `syntax plain`, ROM
File/Open and the disclosed instruction-entry PC/SP stopwatch seam. Short80
insert255925→226807cycles (-11.38%); BACK255319→226366 (-11.34%), four overlay
loads unchanged. Wrapped quote insert365234→365145 and BACK368412→368335 are
essentially unchanged. Control, initial loop candidate and final unrolled
candidate each have four independent VIC captures,12directly inspected frames
total. All corresponding PNG bytes match. No physical key-latency, cold-Plain
unverified-dependency, general performance or worst-case claim is inferred.

The physical Ultimate play session is a separate older build and is untouched.
