# Isolated packed-byte decoder candidate

Released byte candidate: `catalog-preview.s` SHA256
`7b541f727fbaa0b1eeb9e3c7934f1dd738d535bfd4ec70ef582651e0cc29c16d`.
No production source, Makefile, resident state or public generic glyph module changed.

The decoder reads exactly ceil((selected start phase + raw width)/8) packed bytes
per row (zero for width0), aligns them left, then removes all bits after raw width
before bold/italic/underline/inverse/clipping. Native fallback rows after7 remain
blank. P is dead after row pointer R is formed, so its bytes store phase and final
mask index. B/SM retain final mask/source-byte count. All scratch is the original
240-byte CG frame; no BSS or ZP was added.

An explicit `context==8800` branch uses absolute scratch addressing for byte loads,
word shifts and trim. Every other legal caller frame retains the generic byte
kernel. Public strict API and actual FD capability/face/epoch/tag/CRC guards remain
unchanged. All full outputs, including coverage and ink after height, remain exact.

Private leaf:3820B versus actual frozen3581B (+239B;276B free). Complete proof:
`build/geos-catalog-byte-candidate/20261025T090256397114Z/result.json`;
archive `agentsworking/evidence/M8/20261025T090256397114Z-catalog-byte-candidate`.

-43 genuine/builtin packed faces,80,039 real-face paired cases;4,096 native cases.
-6,400 synthetic strict-public cases: every phase0..7, raw width0..24, B/I/U,
 inverse and fixed/arbitrary frames; adjacent packed bits deliberately nonzero.
-187 existing fault/boundary calls, owner opacity/full capabilities/CRC checks.
-Full64KiB RAM every call and actual16MiB REU invariance per face/fault group.
-Real-face aggregate1,077,532,410→793,986,352 instructions (26.31% fewer;1.357×).
 These are CPU instruction counts, not native cycles or whole-editor latency.

The first synthetic fixture was correctly rejected by both strict implementations
because its first index was nonzero. Final fixture begins at0 and preserves the
requested selected-glyph phase. That failed log is retained; production unchanged.

Any future ink-only prototype must be a separate copy and a separate explicit
internal contract. This released candidate preserves the entire CG output ABI.
