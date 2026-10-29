# Build SuperEditor

The downloadable preview is a standalone D81 assembled from the same production
editor, overlay capsules and data-only bitmap-font pack used by development.
Probe programs, malformed test images, logs and agent working records are not
part of the runtime disk or release ZIP.

## Prerequisites

- Python 3.11 or newer
- cc65 (`ca65` and `ld65`)
- VICE's `c1541`
- local GEOS font source media used by `tools/geos_font_catalog.py`
- a C64 character ROM, selectable with `C64_CHARGEN`

Native integration tests additionally use .NET 8 and the repository's VICE UI
automation harness. CPU-level tests use the configured Peddle source tree.

## Build the runtime disk

From `SuperEditor/`:

```sh
make runtime-disk
```

The result is `build/supereditor-runtime.d81`. It contains `SUPEREDITOR`, the
registered runtime capsules, and `GEOSFONTS`. The font member contains only
bounded metrics, glyph indexes/advances and bitmap rows in the project's `GFC1`
container. It does not contain a GEOS system disk, filesystem or executable
font-rendering code.

The development command `make disk` creates `build/supereditor.d81`; that image
may include diagnostic programs and is not the published download.

## Verify and package

The runtime-package test rebuilds the exact member allowlist, checks every D81
member against its source, proves no-op behavior and exercises rollback:

```sh
python3 tests/test_runtime_package.py --fixture path/to/frozen/editor/fixture
python3 tools/package_release.py
```

`package_release.py` requires a qualified runtime disk and its content proof. It
creates `releases/SuperEditor-preview.zip` with exactly:

- `SUPEREDITOR.D81`
- `README.txt`
- `BUILD.json`
- `SHA256SUMS`

The ZIP is deterministic for identical input bytes and verifies every member
after writing. The repository documentation build copies this exact archive to
the GitHub Pages download directory and checks byte equality.

## Start the build

Mount the runtime D81 as an unpartitioned 1581 disk on device 8, enable the REU,
and enter:

```basic
LOAD"SUPEREDITOR",8,1
RUN
```

Keep the D81 mounted while editing because overlays and fonts are loaded from
it. Two MiB supports the tested small-document workflow; 16 MiB is recommended
for large documents and the full feature set. A 512 KiB REU is rejected.

## Documentation site

From the repository root:

```sh
npm ci
npm run build:docs
npm run check:docs
python3 tools/audit_public.py
```

The Pages workflow performs the same build and validation before publishing
`DOCS/`.
