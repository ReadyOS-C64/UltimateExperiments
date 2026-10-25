# Separate internal ink-only prototype

This variant is separate from the released3820B byte decoder. It adds one new
explicit operation, `se_geos_catalog_ink_preview`, for owner4 and context8800 only.
It executes the existing full scalar/context/selected-index and genuine FD guard.
It returns normal metrics and clipped INK rows0..HEIGHT-1. COVERAGE and INK after
HEIGHT remain untouched and are not part of this operation's output contract.
The frozen C27 preview consumer reads only those ink rows; source catalogue-glyph
public/default APIs retain their complete outputs.

No external flag was added. KIND scratch bit2 selects this operation only after
successful admission; every full measure already resets KIND. The input frame,
strict CG APIs, arbitrary-context full APIs, owner opacity, native fallback,
styles/inverse/clipping, and actual capability/epoch/loadtag/CRC checks remain.
No resident state, BSS or ZP is added. Wrong owner returnsB2; wrong context90,
before any frame or pointer-loan write.

Actual private R23:3959B versus released byte3820B (+139B;137B free).
Full proof `build/geos-catalog-byte-candidate/20261025T090827749345Z/result.json`:

-79,480 packed-face cases across all43faces/allglyphs/B/I/U/inverse/clips.
-4,096 native-only cases.
-129 exact full-output calls after ink-only calls, over three legal contexts.
-187 existing fault/boundary calls retargeted to the new private entry plus
 unchanged strict public API;14 additional opaque owner/context refusals.
-Full64KiB RAM every operation, actual16MiB REU invariance per face/fault group.
-Real-face aggregate788,456,433→596,914,385 instructions (24.29% fewer;1.321×)
 versus the already optimized byte decoder. No VICE cycles/editor integration claim.

`preview-row-entry.s` imports/calls the new entry. The candidate's full functions
remain available. Only C27's proven ink-only caller may adopt this contract;
callers that need coverage or all24rows must retain the full glyph operation.
