# Clean tracked-source native-media inventory: PASS

Only two public files are proposed; none was changed publicly. PUBLIC_COPY_MAP and PRODUCTION.patch contain the exact reviewable deltas. Remove the two untracked, unused text probe sources from native_media_sources.json; add tracked src/trap.s, which the current Makefile links even when DOS64_TRAP1=0. The tracked file is an existing dependency, not a new native source delta. All163 fixed inventory inputs reproduce exact tracked afa2908d bytes. No untracked probe file was read or changed.

First missing-private-probe staging failure is preserved in FIRST_FAILURE; Root's subsequent actual ld65 missing build/trap.o failure is retained in first-missing-trap-build. Make's profile-stamp prerequisite gives an empty rule for the absent trap target, so the otherwise missing-source failure appeared only at link. No profile workaround or copied opaque object was used.

Two fresh native-only builds both pass compiler/linker/package/memory checks with DOS64_ZIG and DOS64_CLANGXX set to nonexistent paths: selected runtime46fa2e54/unit63f131a7 (the existing test baseline), defaults exact666089b5/b9e9cc9e. Four memory checks pass. No emulator CPU suite or DOS replay was necessary for an inventory-only fix.

Three focused host groups pass; added test15 parses the actual staged Make ASM_SOURCES and requires every linked source to exist, while explicitly excluding the temporary text probes. The same test detects the prior trap-omitting inventory (EXPECTED_MISSING_TRAP). Existing no-private/vendor-path and Make-include guards also pass. Pure native/test stages verify239/325 source+copy records, including canonical model pins and Peddle source admission for the optional branch, with no optional VM execution.

closed/ checks446 unique source/tool/evidence input records plus244 actual native products before/after; all immutable copies are retained. Builder per-run before/after and RESULT/products are complete. The copied failed build is historical evidence only. No source flags/algorithms/ABI/model implementation changed.

Reproduce native-only from this tracked public-layout source tree:

    python3 -B source/build_support/native_media_tests.py --native-only --out /fresh/owned/output
    python3 -B source/build_support/native_media_tests.py --native-only --default-profile --out /another/fresh/output

Or after Root applies the two exact public files, use existing make native-media and make test-native-media (the latter retains its existing27 native groups but was not redundantly rerun in this inventory slice). No hardware/publication/V1 claim.
