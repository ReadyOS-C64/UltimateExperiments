# Actual-runtime floppy FORMAT checks

```sh
make test-floppy-format
```

This builds the optional FORMAT-enabled emulator, compiles the Peddle/device model and Zig assertions from public sources, then directly executes 12 Python groups and 2 Zig groups against the actual linked assembly. It needs the runtime build tools, a C++20 clang compiler and Zig. `DOS64_CLANGXX` and `DOS64_ZIG` select test tools; `DOS64_FORMAT_TEST_ARGS="--out PATH"` chooses an empty or test-builder-owned output directory. No DOS image, vendor application, private library or Ultimate connection is needed.

Tests cover full tracks, all three floppy arenas, first/last tracks and heads, reordered IDs, native flag preservation, invalid geometry/IDs/readonly media, DMA bounds and partial writes, dirty generations, cache coherency, immutable memory, nested overlay corruption and switching back to graphics. They exercise the runtime binary; they do not link the oversized FORMAT1 full UNIT profile.

`build/floppy-format-tests/RESULT.json` points to the immutable run, source/tool/SDK identities, compiled test products, exact runtime hashes and results. The builder uses fresh local Zig caches, retains compiler dependency lists and SDK copies for the C++ model, pins the installed Zig distribution, and verifies recorded inputs/products after execution. Failures retain the prior passed result and separate diagnostics. SDK paths identify the local test environment; they are not runtime dependencies.

The fixtures use synthetic disks. Genuine DOS FORMAT/SYS/boot, native floppy saving, HD persistence and actual Ultimate operation remain separate integration and release gates.

`make test-floppy-format-host` runs four fast host failure controls: existing foreign lock, failed run creation, interrupted runtime build with failed error reporting, and failure while closing a newly owned lock descriptor. The previous passed result and original failure remain intact; only this build's lock may be removed. These controls do not repeat CPU/model tests.
