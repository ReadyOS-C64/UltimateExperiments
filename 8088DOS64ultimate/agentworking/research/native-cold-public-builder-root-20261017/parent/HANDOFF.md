# Source-only production cold builder

READY for independent public-layout builder review; no public edits or hardware actions.

`project/` is the portable public-layout source derivative. `PUBLIC_COPY_MAP.json` lists18 owned writes and required exact shared dependencies. The existing27-file installer map owns the identical `start_ini_bundle.py` and `start_template_descriptor.py` prerequisites; coordinate these two rather than replace a competing version. Other shared native sources are reused unchanged. Only the extra Make include is intended for the public Makefile.

```
make cold-start RUNTIME_MEDIA_RESULT=/absolute/immutable/runtime/RESULT.json
make cold-start-tests RUNTIME_MEDIA_RESULT=/absolute/immutable/runtime/RESULT.json
```

Or `python3 -B build_support/cold_start.py --runtime-result PATH --out OWNED_OUTPUT`. Native build needs Python, make, cc65, ca65, ld65, none.lib and compiler include/asminc resources. DOS64 tool/library overrides are resolved explicitly; compiler environment injection is scrubbed. No DOS images, Zig, clang, Peddle, private paths, prebuilt models or previous compiled START are ordinary build inputs.

The builder verifies every declared runtime source, generated product and published product before and after use; validates role/header/main/menu/asset agreement; independently regenerates the main D64L2; stages42 compiler source inputs through the inventory; regenerates exact linked prefix/import aliases, gate and recovery worker and patches only initialized gate/worker DATA capsules. It rebuilds the gate after DATA patching and requires identical gate/prefix. It runs the existing strict eight-asset validator. Results publish only after immutable run products and source checks. Failure preserves the previous pointer and the exact first exception despite failed reporting/cleanup. No mutable top-level product aliases.

`result['bundle']` contains exactly eight files: DOS64.PRG/REL/MNU and START.TPL/REL/INO/RCV/RFW. `result['products']` additionally supplies immutable START.labels/map and DOS64.labels/map for the installer/config consumers. `source_inputs` and `native_products` carry complete recorded closures. `run/RESULT.json` precedes atomic output RESULT publication.

## Actual observed runtime binding

`closed-native/RESULT.json` is the final source-built result. Its provider is Root's observed `native-format-runtime-integration-root-20261017/combined-build/RESULT.json`, not a claimed final parent seal. `RUNTIME_RESULT_OBSERVED.json` retains that precise metadata. No earlier edce/0b52 full hash is relabeled.

- DOS64.PRG806eaab6 / DOS64.MNU1b7086ec / DOS64.RELb2c4a605
- START.TPLf17bdce7,20480B; START.RELa198644d,64B
- START.INO44dd9461,7692B; START.RCV08715a79,7902B; START.RFWf11b0c1d,5578B
- START loads0801..57FE; INO6000..7E0B, shared prefix1350B.
- RCV private state9000,1226B; RFW private state9800,871B. Worker codeA000. Existing stack/runtime and split56KiB menu policy unchanged.

`closed-builder/RESULT.json`:11 focused host groups,61 local source inputs/copies exact;1140 consumed runtime/compiler/source records and99 generated records exact. Native rebuild equals all executed consumer asset bytes. Actual public-layout Make invocation also passed. `default-comparison/RESULT.json`:four fresh native links prove default and options18KiB START PRG/labels/map/INO byte-exact against the original helper. Default cold=False and descriptor start20k=False behavior remains unchanged.

`consumer-closed/RESULT.json`:two genuine actual SYS/INI/RCV/main DOS consumers40/80 passed24.00/26.52s,1098 source/SDK/model/media/product records plus retained copies exact. They observed593993/594002 guest instructions, genuine VER/full36-entry paged DIR and8192 free bytes, correct BIOS columns and all three full floppy arenas unchanged. These are prior actual CONFIG-produced settings/media rebound to the new matched release and properly configured START; no new SETUP/CONFIG execution or guest-loader shortcut. Source-built Peddle/device model is independently rebuilt byte-exact in `consumer-model-rebuild/RESULT.json`. Firmware devices are mocked; genuine DOS runs in actual assembled emulator. No physical throughput, keyboard, video, Turbo or whole V1 acceptance claim.

Capture qualification: `native-screen.bin` is the literal0400 startup buffer, not the4000 runtime text screen; captures are raw model RAM, not rendered hardware video. The40/80 result is established by actual INI parsing and guest BIOS/text assertions, not by that startup buffer.

## Preserved failures and remaining gates

See FIRST_FAILURES.md. The first descriptor18KiB refusal, partial graph Make parse failure, wrong Make variable and host Make-oracle failure remain retained. No native source repair was required. CIA's source graph omitted overlay_capsule.s; the exact sealed native source plus files.inc/uci.inc are now explicit inventory entries.

Root must independently review/copy this builder, supply its final immutable runtime result, coordinate the accepted27 installer dependencies, and rerun the public optional builder/host tests. Current source-produced assets are suitable inputs to that review; no new producer/model or physical acceptance is inferred. Full native SETUP/CONFIG→media actions and device/human V1 remain separately owned. No binaries or DOS media belong in the promotion map.
