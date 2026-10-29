Private feasibility only. `codec.s` packs/unpacks the existing internal BSW9
full-clip, PETSCII ink output at8800 into a32-byte caller packet at8A00. It
requires owner4, allocates no BSS/ZP, and does not access REU or authenticate a
font/cache capability. A future controller must do those checks independently.

Packet: magic0, nativevalue1, style2, inverse3, screen/width/advance/height/
baseline4..8, fixed-advance class9 (PP_CODE or role4), eighteen high ink bytes
10..27, CRC16 little-endian28..29 over1..27, reservedzero30..31. VALID/magic is
published last; unpack rejects any mismatched key/geometry/CRC before publishing
CG_VALID2. Coverage and ink beyondheight remain untouched.

All256 PETSCII values ×8styles ×2inverse pass actualR23 and independentfont
oracles. Codec498B exceeds currentR23's148B free before cache plumbing. The
4160B storage budget fits the5271B unused FE tail, but no integrated cache,
all-font speed claim, or end-to-end performance result is provided.

See M8/20261025T115003299396Z-preview-glyph-codec-feasibility.
