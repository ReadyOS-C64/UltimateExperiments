# Local status variant: removes the caret load regression

The earlier `released/` pair is retained unchanged. The new reproducible pair
is `local-released/` and `build-local-released.py` (C33=4096,R25=3586).
There is no canonical integration or additional asset/resident/BSS/ZP.

The helper split alternated R25 and R16 merely to draw14 native status cells,
raising native warm caret movement from2 to6 loads. This variant embeds the
existing verified1024B native8 font in C33 atBC00..BFFF and draws those cells
locally. Thus caret XOR, packet/header commits and status retain the R25 slot;
no R16/17 execution is needed when no document glyph changes. Typing still uses
the actual R16/17 row renderer. New native status code is immutable, bounded,
uses the same borrowed pointers/scratch, converts the existing native screen
codes including bit7 inversion, and touches exactly the same dynamic14 tiles.

## Authority, not a blind font-lifetime assumption

C33's native font is part of its own authenticated sealed payload and survives
R25 loads. Build verifies it is byte-identical to BOTH actual R16/17 AC00 font
tables. It authenticates each frozen image's size, CRC, binding and asset hash
before generating `native-witness.inc`. R25's font capability check retains
fulllogical/physical owner2, epoch, size and catalog/header witnesses and adds
exact compiled R16/17 payload CRC plus managed backing-verified bit80.

This is the same authority used by the editor's managed overlay loader, not a
claim that RAMAC00 survives. The runtime requires compiled managed policy1.
Any checked owner2 write clears verified bits and active tags. An unverified
backend declines read-only; the ordinary full renderer must actually verify it
before fast admission resumes. Tested actual checked corruption refuses both
fast pixels/cache publication and root full rendering; repairing raw bytes
alone still declines until real loader reverification. No fresh whole-font CRC
is skipped under an unproved lifetime. No unsupported unmanaged/generic
configuration is admitted.

Original R25 helper operations and BOF<128/no-prior-colon typing restrictions
are unchanged. General arbitrary-prefix typing remains open. Source40 remains
the unchanged resident zero-load route. Shared phase8D00..917F/shim unchanged.

## Build order and integration inputs

1. Build actual bound R16/grid80 and R17/grid60, verifying their sealed payloads.
2. Generate two native CRC constants and copy trusted native8 table. All3 tables
   must be exactly1024B and byte-identical.
3. Assemble/link R25 from `local-released/helper.s` and generated
   `native-witness.inc`, then generate exact helper size/CRC include.
4. Assemble C33 `local-released/caret.s` + existing `typing/status-normal.s`;
   link using `local-released/grid.cfg` (native segmentBC00; payload4096).
5. Wrap both using current resident binding. No dependency back from R16/17 to
   these images, and no old resident/CRC constants are hard-coded by the recipe.

`build-local-released.py OUT IMMUTABLE_FIXTURE` does exactly this and reproduces
the qualified pair. The non-released generator `build-local.py` preserves the
historical transformation recipe; use the released self-contained sources for
promotion. The baseline product ZIP alone is NOT exact source for this pair;
use the explicit private override archive.

Exact same-b33 pair hashes:
- grid41bd9353a11148637b6e2a9faad2c5034c65ce4549b5a8873ce83b1d7d95ade4
- geostaildb40a9426a3e6d53f8ea9768418aaf59158d46f5fd6a646c7f7120e56db17b5c

## Qualified scope

Original typing10+27refusal/mixed-pair3; added authority8; broad actual-root
34frames/31refusals/30captures; selector/header5 and transport/STOP/missingop2
5; primitive380; exact48+7-helper stack77bytes/minSPB2. Native29 all frames
byte-identical to reviewed original gallery, with40zero-load and3 exact16MiB
caret groups. Native PAL10 and matched unmodified control pass exact same
source/position/scenario/pixel/catalog/stack/shim checks. All owned PIDs closed.

Matched warm caret remains2loads and improves about3%:60RIGHT idle134842→130694,
80RIGHT139104→135043. Scoped ordinary prose insertion idle60:3039523→374424;
80:2911078→258612. First and idle remain separately recorded. Structural
front-heading fallback worsens2.4–3.3% from factoring, remains outside this
optimization and is explicitly not waived. Details live in the local-status
checkpoint/session; no universal latency claim or ReadyOS integration claim.
