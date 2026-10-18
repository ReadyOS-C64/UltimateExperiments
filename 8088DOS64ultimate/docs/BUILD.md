# Build from source

## Tools

The native development package needs Python 3.9 or newer, Make and the cc65 toolchain: `cc65`, `ca65`, `ld65` and the toolchain's `none.lib`. The audited build used cc65/ca65/ld65 2.18. These tools must be on PATH or configured through the documented DOS64 tool variables. Package building needs no DOS images, Turbo Pascal, Zig, Peddle, device access or private working notes.

For emulator assertions install **Zig 0.16.0** with its standard libraries. Peddle's C++ sources are included under `third_party/peddle`, including their license. Python assertions use the standard library. Screenshot comparison/composition additionally needs Pillow. Optional guest fixtures need DOSBox-X and NASM; VICE/IEC and physical .NET automation are separate development lanes, not runtime dependencies.

## Native package

From the repository root:

```sh
cd 8088DOS64ultimate
make v1-candidate DOS64_V1_CANDIDATE_ARGS='--runtime-media'
```

`build/v1-candidate/RESULT.json` points to the newly created package and `DOS64-candidate.zip`. Each build gets its own directory. Copy the ZIP's twelve matched native files together; do not combine components from different builds. The package's README, BUILD.json and SHA256SUMS travel with it. This builds a preview, not V1 acceptance.

The public download is `downloads/DOS64-development.zip`. It contains no configured user disks, DOS or third-party applications. Its BUILD.json lists asset sizes and SHA-256 hashes without personal paths. The build's detailed local receipts/logs are excluded from distribution.

## Emulator and tests

```sh
make build
make test DOS64_ZIG=/path/to/zig
make v1-package-tests DOS64_V1_CANDIDATE_ARGS='--runtime-media'
```

`make build` assembles the runtime and test targets, checks linker memory budgets and writes a local tool/input manifest. `make test` runs Python tooling tests and Zig/Peddle assertions against the real linked 6510 code. Some Python integration/orchestration cases require the three user-supplied DOS images even though their devices are mocked. Supply those images before the full suite; they are not bundled. A mock test is not physical acceptance.

Place the images in the ignored `reference/` directory, retaining these filenames:

```text
MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img
MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 2 of 3.img
MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 3 of 3.img
```

Each is 368,640 bytes. Obtain them from the [specified Internet Archive item](https://archive.org/details/ms-dos-version-3.3-with-gw-basic-3.2-microsoft-1988); the tools pin the expected original hashes. Original images must remain unchanged; test tools create disposable copies. DOSBox-X and genuine DOS test lanes are opt-in. See [testing](TESTING.md) and [disk tools](DISK_TOOLS.md).

Tests create their own ignored local output folders. No prior logs, remote device session or working-record checkout is a build prerequisite. Do not use a test's synthetic image as a boot disk.

## Example disk

`python3 build_support/example_disk.py` deterministically builds and verifies `examples/EXAMPLES.IMG` from the checked-in example files. It does not use a DOS image as a template. The disk is nonbootable FAT12 data media; it includes only the explicit file allowlist.

The optional RIPPLE rebuild uses a separately supplied Turbo Pascal 7.01 compiler: copy RIPPLE.PAS into a disposable DOS directory with the compiler and standard library, then run `TPC RIPPLE.PAS`. The source's `{$G-}` selects 8088-compatible code generation. Turbo Pascal is not included or required to rebuild the emulator. The supplied RIPPLE.EXE is our compiled example, not a compiler distribution.

## Documentation

From the repository root, Node.js 20+ and Python 3:

```sh
npm ci --ignore-scripts
npm run build:docs
npm run check:docs
python3 tools/audit_public.py
```

The site contains Markdown and generated HTML under `DOCS/dos64`. GitHub Pages deploys only DOCS. Building docs does not contact the Ultimate or publish anything. [Publication audit](AUDIT.md).
