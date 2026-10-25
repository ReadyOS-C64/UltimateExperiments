# Corrective Backspace restoring a heading

Private R28 candidate: **4051 bytes**, +39 over the released 4012-byte heading-to-prose implementation; **45 bytes free**. No new BSS, zero page, phase fields or overlay/controller hooks. `edit-cache.s` SHA256: `63751bf14219abf21d628b9a08418f6f089c1566197efa90c51a1a7bb7baa763`.

This is a separate namespace; the earlier heading-transition candidate and its verifier remain unchanged. The private builder uses immutable `build/geos-incremental-editor/20261025T133435860867Z/fixture` and proves byte-identical original 4012-byte R28 reassembly before substitution. It never changes shared product/build outputs.

## Exact added admission

New `GEX_CLASS=3` accepts only a single **BACK** (`se_hot_command=4`, `GEC_OP=1`) which deletes one alphabetic first byte from a complete old prose row, exposing one through six `#` followed by space. For example, `Q# Heading` becomes `# Heading`. Forward Delete is deliberately excluded.

The old row must have BSW kind 0, exact flags 0, INLINE 0, all styles 0 and roles 0. Its TOP/HEIGHT must equal the resident saved painted-caret-row `GCC_Y/GCC_HEIGHT`; height must be 9. All existing full source graph/provider/epoch/revision/length/caret/sequence, no-selection/no-fold/no-pan/no-preview/no-modal, START/FIRST/count, CR/EOF/END/NEXT and preceding-CR guards remain intact. The old cached deleted byte must equal the authoritative certificate's alphabetic `GEC_OLD`. No row is accepted from the prefix alone.

The implementation shares the existing START admission, geometry and bounded prefix reader. START loads operation into X, chooses authoritative NEW/OLD alphabetic byte, verifies old flags as `operation XOR 1`, then stores class `operation+2`. The prefix reader starts at X=`GEX_OP` (0 for the old heading INSERT, 1 for inverse BACK) and counts one through six hashes separately in Y. Its checked read still covers at most eight old source bytes. Class 3 follows the existing zero-style/role checks before this prefix proof. Class 2 retains its heading-role2 proof. The first-letter guard is skipped for both explicitly certified START transitions.

C21 already rebuilds nonzero classes through actual C24/C20/C26. VERIFY expects flags 1 only for class 3 (CMP3 carry becomes 0/1 with `LDA #0; ROL`, then XORs actual flags); all other classes still require 0. It also requires exact kind/height/TOP/START/FIRST, unchanged CR/EOF reason and END/NEXT minus one. Geometry or parser mismatch abandons staging before dirty painting. Existing suffix rebase and majority color arbitration are unchanged.

## Why parser carry is safe

A recognized heading only changes its event metadata/body marker; it does not change fence/language/region carry after CR. The prior alpha-prefixed prose also changes none of that carry. Both the bounded old-prefix proof and actual new C24 classification are required. Fence/region opener transitions are not generalized. Fenced code has a different kind/height and refuses admission. A heading within an existing region is safe because the surrounding region stack remains unchanged. Old inline markup or styles deliberately refuse this extension.

## Proof

Candidate and byte-identical original control each pass 35 actual public frames. All 35 PNG files are byte-identical. The gate compares independent canonical SuperMark/expanded-font pixels, forced actual full-renderer output, attributes, every START/END/NEXT/FIRST/count/TOP/HEIGHT and canonical bottom, source/history/catalog, leases and the 1 KiB ReadyOS shim. Whole 16 MiB guards permit only declared active FE cache ranges. Twelve malformed-cache cases use actual checked FE DMA; they are not host-forged positive certificates.

Coverage includes levels 1–6, EOF, after CR, inside a region, real typed GOTO flushing a preceding insertion and then BACK, old wrap, ordinary text, space/nonalphabetic deletion, seven hashes, missing marker space, bullet, inline markup, fenced code, interior edits, forward Delete and two unpainted edits. Existing forward 37-frame gate also passes, including all metadata/fold fallback cases and six opaque owner/operation entry groups; its only changed expected path is the now-optimized inverse BACK. That wrapper records the original verifier hash and exact predicate replacement without editing it.

Additional actual diverse422 correction: **670,972 instructions / 17 loads**, versus forced full **3,156,767 instructions**, with exact 19-row output. The simple corrective case measures original **891,281 → 449,130 instructions**, loads **24 → 17**. EOF can add a load (16 → 17), so no universal latency claim is made. These count executed instructions inside render after key input has already settled; they exclude the key-input call. Native whole-interaction cycles and integrated stack bounds belong to the parent gate.

## Commands

```
python3 tests/test_geos_heading_back.py --fixture IMMUTABLE
python3 tests/test_geos_heading_back.py --fixture IMMUTABLE --variant control
python3 tests/test_geos_heading_back.py --fixture IMMUTABLE --forward-regression
python3 tests/test_geos_heading_back.py --fixture IMMUTABLE --smoke --diverse
python3 tests/test_geos_heading_back.py --fixture PROMOTED --packaged
```

`--packaged` uses the actual frozen R28 image, with no private reassembly/replacement. The forward wrapper alters only its historical corrective-BACK expected-path predicate, retaining its independent source/pixel/REU assertions. It intentionally refuses a changed original verifier until reviewed.
