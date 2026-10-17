# Matched cold START builder

Build the runtime first, then give its immutable result to the cold builder:

```sh
make runtime-media DOS64_RUNTIME_MEDIA_ARGS="--floppy-format"
make cold-start RUNTIME_MEDIA_RESULT="$PWD/build/runtime-media/RESULT.json"
make cold-start-tests RUNTIME_MEDIA_RESULT="$PWD/build/runtime-media/RESULT.json"
```

The native build needs Python, make, cc65, ca65, ld65, cc65's `none.lib`, and its include/asminc resources. The existing `DOS64_*` tool overrides apply. DOS images, Turbo Pascal, Zig, Peddle, a development computer connection to the Ultimate, and prebuilt private assets are not build inputs. The tests above are host checks of building, binding and failure handling; they do not boot DOS or qualify hardware.

`build/cold-start/RESULT.json` publishes an immutable run. Its `bundle` contains exactly eight files: DOS64.PRG, DOS64.REL, DOS64.MNU, START.TPL, START.REL, START.INO, START.RCV and START.RFW. START labels/map and main labels/map are separate products for the installer and validation tools. Keep the bundle together. START.TPL is a template for the folder-aware launcher, not a configured end-user START.PRG.

The builder verifies the runtime's declared source and products, rebuilds START and its recovery code from the source inventory, independently regenerates the main descriptor, and validates the complete bundle. Gate and worker capsules are patched only in initialized DATA. It rebuilds the gate and requires the linked prefix and gate to remain exact. Product publication happens after verification; a failed build keeps the prior passed result. Changes to a consumed source require a fresh runtime result.

The cold profile uses a 20 KiB template and the runtime's split 56 KiB menu. Its explicit descriptor and inventory options leave the default 18 KiB launcher and five-file bundle behavior unchanged. This adds no REU allocation and preserves all three complete floppy arenas and the 4 MiB minimum.

This is a development build checkpoint. Final SETUP/CONFIG composition, source-closed DOS consumers, floppy/HD persistence, original Turbo Pascal and actual Ultimate/human acceptance retain their separate evidence and [V1 gates](../../docs/V1_ENDPOINT.md). Successful compilation is not a V1 release.
