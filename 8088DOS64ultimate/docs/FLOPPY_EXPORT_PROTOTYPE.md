# Source-complete standalone package integration

Copy only the additive files named in PACKAGE_MANIFEST.json into the project. In root `build.zig`, immediately after its single `const target = b.standardTargetOptions(.{});`, add:

```zig
@import("tests/floppy_export/build.zig").add(b,target);
```

Optionally add `include build_support/floppy_export.mk` to the root Makefile. `make test-floppy-export` then builds the disabled fixture and executes the opt-in Peddle lane. It is intentionally not a dependency of the existing normal runtime target or default tests. The package's test module reuses the already resolved Zig target and normal host-model/Peddle include paths.

No existing source change is part of the promotion package. The private work/build.zig registration is just this one-line change and is separately pinned. Before integration, check every dependency against the manifest; root source changes after this private baseline need review, not an assumed hash waiver.

## Production integration remains open

The final standalone exporter is1265 code bytes and164 state bytes, measured by ca65/ld65. It adds no ZP; standalone REU uses4bytes. Its dependencies are the existing182-byte REU primitive,1265-byte UCI and1088-byte FILE payload. Full disabled PRG is3817bytes. State is allocated below KERNAL in the standalone linker control area, command/response buffers remainC100–C8FF and compare staging8000–81FF. This does not fit the proposed performance target's1223-byte free shadow tail: code alone is42bytes too large, before production entry/leases. MAIN115/DEVICE22 cannot absorb it silently. A new runtime overlay or proven code rearrangement is required.

A seventh2KiB source at hostB000–B7FF / REU343000–3437FF is only a possible budget: that host range currently belongs to guest cache; it would require four additional startup-protected cache frames, a longer PRG, asset-copy verification, new overlay descriptors/deadlines, source-collision accounting, resident state and a safe continuation strategy while FILE occupiesC900–CFFF. Directly switching FILE underneath an exporter executing fromC900 is invalid. No such layout is implemented or accepted here. A retained shadow controller or resident bank-safe continuation is necessary, and all bytes must be charged by actual link maps.

Before production use: flush/finish guest disk and BIOS operations; acquire exclusive FILE/HD/UCI/REU leases; pause guest mutations with a generation check; protect source image from eject/swap; account staging against page cache; preserve active emulator host cache and complete native IRQ/NMI/banking contract; establish caller time and total bound; retain uncertain authority/output diagnostics before external restoration; wire save/discard/cancel and dirty state only after successful verification. The two attestation bytes do not implement those requirements.

Next acceptance: independent package/source/test review, a separate owned physical fixture with fresh backup and installed-firmware CREATE_NEW adversaries, full image byte/FAT checks after native CLOSE/reopen, retained failed file/REU authority, then production UI/lease integration. A successful modeled save is not physical persistence, and no power-fail atomic replacement is claimed.

## Measured evidence and primary contract

The private final suite passes12Zig/Peddle tests covering39executed assembly scenarios, including whole360KiB success for both A/B REU slots, target1/2 and128-byte path boundary; all8native banking modes; every file phase; binary byte preservation; silent partial WRITE with accepted status; corrupt, short and excess readback; partial DMA before/during verification; existing-file protection; denied ownership/pause/configuration; cancellation; elapsed wrapping/overflow/hard bound; stuck firmware and failed cleanup. Full4MiB remains unchanged for every guarded scenario. Strict native executable/memory write guards pass. Maximum observed poll is6452Peddle CPU cycles; no DMA stalls or physical elapsed-speed result is included. Fivehost packaging tests rebuild the disabled3817-byte PRG from a clean minimal temporary source tree and verify source/artifact hashes, exact map budgets, missing-output rebuilding and normal-path registration. The measured disabled PRG SHA256 is `556e61c4a25264d9762446c23cd5dd29ad0300566ab8e6641b986e14a11eeb1f`.

Primary inspected firmware: [access flags](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/filesystem/fs_errors_flags.h), [Ultimate DOS commands](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/filemanager/dos.cc), [FileManager create-new handling](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/filemanager/filemanager.cc). Mode6 combinesWRITE2withCREATE_NEW4. FileManager rejects existing paths under its lock; exported output is never opened with truncate/create-always. Target WRITE/CLOSE omit useful completion guarantees, so the native reopen/full-content/EOF checks are required. These primary-source contracts require installed-firmware validation before a physical persistence claim.
