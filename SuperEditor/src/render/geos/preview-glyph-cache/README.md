# Preview-only R23 glyph cache

Production R23 is4095 bytes, no new BSS/ZP/bank. Generic catalogue APIs remain
unchanged. This specializes exact BSW9 (origin2/familyFFFF/point9,744 raw bytes),
PETSCII/native4800 and full clip. Other faces/native use the real decoder.

The internal fetched entry consumes the wrapper's immediately preceding actual
font fetch. Only frame pointer/length stores intervene; no yield, window writer,
capability writer or overlay call. Public guarded entry still performs its own
fetch and clears stale immediate markers. Common scalar/native/span checks run.

Header64 and128×32 records occupy exactlyFE[EB69,FBA9). Actual typed FE map and
epoch, resident16-byte seal, full9-byte FDgraph/face witness and generated exact
GF_BSW9_CRC bind the header. Clear all128 records before new header publication.
Each record checks full value/style/inverse/fixed-role key, reserved zeros,
screen identity, metric bounds/relations and CRC before output. Optional cache
failure falls back; successful genuine decoding cannot fail because of caching.

Scratch8800..88EF and8A00..8AAF belongs to owner4 during this uninterrupted call;
C27 transport uses8A00 outside glyph calls. Every checked cache write also
revokes the managed preview-body memo. Body publication later re-arms it.

Current first source40→preview has noFE during glyph calls; optional capture
allocatesFE at completion. An early-allocation candidate remains private.
No automatic extra allocation or physical-bank assumption is introduced here.

Qualification: all43faces/79480 packed+4096native and70 direct fault groups;
4096BSW keys+328cache faults;6 recomputed-invalid-metric CRC cases; direct fetch
1/native0/wrapper1 trace and all4210font+64FD bytes unchanged at internal seam;
public68 fullsource/rawfont/full16MiB guards. Root production payload is byte
identical to the released private variant. PAL native7: first8,008,125cycles,
pageback6,995,993, unchanged378,231, all pixels unchanged. Stack remains77bytes.
