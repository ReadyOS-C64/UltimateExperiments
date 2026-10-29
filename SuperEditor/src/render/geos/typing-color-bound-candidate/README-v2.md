# Promotable V2 certificate discriminator

Use `build-runtime-v2.py` and `runtime-v2/*` with the released
`two-color.s/.inc`. Do not promote the historical VALID1 producer variant.
The V1 native17 remains an unchanged performance/pixel ancestor; its certificate
semantics were unsafe when mixed with the older production R30.

V2 differs from V1 by three immediate payload bytes only, at unchanged sizes:
C6 payload offset3482 changes1→2; R30 offsets76 and608 change1→2. C32 is byte
identical. C6 now publishes GTC_VALID2 after its CRC; both the new R30
supervisor and independent guard require exactly2. Old R30 requires1 and
therefore refuses the new producer before claiming phase/reading the stage.
New R30 refuses old C6 VALID1 likewise. The marker is distinct from the
CRC-covered byte44 mode0/1, whose interpretation still belongs to V2.

Audit of executable consumers found the two R30 checks above. The generic
`typing/guard.s` has a historical VALID1 path and is not linked into the new
R30. R31 only retires9149; R28 initializes its overlapping phase independently.
No other canonical code executes a GTC certificate.

`tests/test_geos_typing_color_bound_candidate_generation.py` executes six
actual combinations and guards source/pixels/FE/GCC/leases. It retains the
historical V1+oldR30 LSN190 counterexample (actual16 versus expected36 at cell160,
with RAM capture). Both V2 mixed producer/worker directions now return2 before
publication, then actual root fallback paints the exact expanded reference.
Matched V2 admits. New worker plus incompatible old C32 returns94 before
execution; the V1 C32 is compatible because its bytes are identical.

Final V2 private public25+recovery4 and transaction10+fault21 gates pass.
Actual V2 PAL17 also passes exact source/catalog/shim/stack/all1,088,000 native
pixels and seven paired whole16MiB/canonical-history intervals. Captured local
certificate generation2 is asserted. Every active crop is byte-exact to the
visually reviewed V1 counterpart. Native17 used the requested7900 range but
allocator selected actual7901/text8001, recorded in manifest/VICEargv. The
fixed-port PID observer missed this; closure is proved by normal --close-vice,
absence of the exact private workingD81 process, and free actual ports. No PID
is invented. The later compact-media wrapper observes the exact D81 regardless
of selected port and records every owned PID explicitly.

Relevant checkpoints:

- V1 private `M8/20261025T164809216737Z-typing-two-color-private` (historical).
- V1 native `M8/20261025T170707238882Z-typing-two-color-native` (historical).
- V2 private `M8/20261025T171454792211Z-typing-two-color-v2-private`.
- V2 native `M8/20261025T171529016248Z-typing-two-color-v2-native`.

Parent owns canonical promotion, binding reseal, seventh-vector stack proof and
combined product acceptance. No canonical/sharedbuild edits were made here.
