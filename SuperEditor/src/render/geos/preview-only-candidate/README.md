# Preview-only R23 specialization

NEW private candidate; canonical catalogue glyph/default sources are unchanged.
Released proof: `build/geos-preview-only/20261025T120244281023Z` against exact
immutable47 fixture115028. Control reassembly must byte-match packaged R23.

Measured linked image3948→3319B:629B reclaimed,777B free; no BSS/ZP added.
Actual real-face aggregate596372463→577062974 CPUinstructions (3.2378% fewer).
This is component CPU work, not native cycles or wholepreview speedup.

## Reachable API and retained checks

The actual product `preview-row-entry.s` imports only
`se_geos_catalog_ink_preview`. C27 `preview.s` consumes metrics plus CG_INK rows
0..HEIGHT-1; it does not consume coverage or ink afterheight. The copied wrapper
is byte-identical to the frozen control. The explicit ink entry verifies owner4
before frame/loan access and requires X/Y=8800. It alone establishes the two
borrowed foreground pointers. Wrongowner B2 and wrongcontext90 remain opaque.

This candidate removes only code unreachable under that API: strict full measure/
glyph exports and globalindexscan, arbitrary-context byte decoder, full192B clear,
coverage/full output, duplicated owner/generalcontext admission, and branches
selecting those paths. The new object exports no genericmeasure/glyph symbols.
The general `catalog-glyph.s` and current default `catalog-preview.s` remain
untouched. Public strict operations must keep their normal module, not thisone.

Retained code includes every scalar encoding/style/inverse/clip check; legalRAM/
full nativefont span and disjointframe checks; packedfont length/extent/header
checks; actual FD/window capability verification before fontread; selectedindex
ordering/width/end<=stride*8; PETSCII converter, GEOSASCII and native fallback;
byte-phase masking; genuine bold/italic/underline; inverse; horizontal/vertical
clipping; and the promise that coverage and ink afterheight stay unchanged.
Fonts remain in the actual verified5000 workingwindow; no newfont is generated.

R23's existing font-store preview authority is unchanged. With managed overlay
loads, a loadcounter change alone does not revoke an intact authorized window.
Every actual window writer clears the sticky validtag. The test checks cleared
borrowtag+poisonedwindow→verified refill and counter-only change→same exact
intact window. An earlier inherited test incorrectly combined unnotified RAM
corruption with only a loadcounter change; that failed verifier run is retained
at120026, and was corrected to the accepted managed-memory contract. The generic
strict FETCH still retains CRC-on-every-hit in the unchanged font-store module.

## Reproduction and evidence

```sh
python3 tests/test_geos_preview_only.py --smoke --fixture IMMUTABLE_FIXTURE
python3 tests/test_geos_preview_only.py --fixture IMMUTABLE_FIXTURE
```

Actual unpackedfontbits/nativefont independent oracle plus exact packagedR23
A/B passes79480 packed cases/all43faces,4096native cases and70 fault/boundary
groups. Every glyph/directAPI call guards full64KiBRAM; every face/faultgroup
checks the actual whole16MiBREU unchanged. Faults cover all scalar/clip/native/
fontpointer spans, owner/context opacity, FD READY/busy/handles/epoch/logicaland
physical owners, stickywindow refill, counter-only preservation, selectedindex
edges up to16bitmaximum. Fonts/header/source/shim preservation are included.
The test consciously does not call removed full APIs. It asserts they are absent
from the candidate and preserves the separately bound control's actual APIs.

Parent may replace only R23's catalogue-preview object with this candidate;
wrapper/font-store/metadata/build bindings stay current. No new entry/diskasset,
mode behavior, source writes, parser or general API change is required. The
independent498B BSWglyphcodec would yield3817B before integration helpers; that
future controller and cache authority are not part of this proof.
