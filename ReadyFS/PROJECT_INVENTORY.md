# ReadyFS Standalone Project Inventory

This directory is the complete ReadyFS filesystem proof-of-concept project.
It is deliberately independent of ReadyOS while the endpoint/path model and
hardware behavior are still being proven.

## Source and build

- `src/apps/readyfs/`: 69 C and 6502 assembly source/header files.
- `cfg/readyfs_overlay.cfg`: standalone resident/sidecar linker layout.
- `Makefile`: monolithic build, overlay plus 12 sidecars, disk fixtures, host
  tests, UCI verification, memory checks, UI reports, and VICE smoke target.
- `obj/`: current linker maps and rebuilt object trees.
- `artifacts/readyfs/`: current PRGs, D64/D71/D81/TAP fixtures, labels, maps,
  and JSON/Markdown build and UI reports.
- `artifacts/legacy/source-objects/`: 19 pre-migration object files retained as
  artifacts rather than mixed into the source directory.

## Automation

- `build_support/`: 133 support files in total.
- 35 `readyfs_vice_*.yaml` UI plans and 31 focused VICE runner scripts.
- C64 Ultimate read-only, marker-owned mutation, recursive, SoftwareIEC,
  speed-matrix, capture, and Terminal-launch wrappers.
- Host C tests for paths, matching, commands, drive classification, plans,
  tree walking, content, utility/SoftwareIEC, journal, backend, pipeline,
  recursion, tape, and the asynchronous UCI transport.
- Static verifiers for the ReadyIRC-derived UCI state machine, overlay DMA
  boundaries, and the cross-overlay execution pipeline.
- `create_readyfs_rel_fixture.py` generates a real record-length-32 REL test
  disk, removing the former dependency on a ReadyOS release image.

VICE scripts resolve the external harness from `VICE_TASKS_REPO`, or by
default from the sibling project at `../../agenticdevharness`.

## Documentation and working history

- `docs/`: six ReadyFS design, path research, requirements, safety, scope, and
  UI matrix documents.
- `AgentWorking/READYFS_PROGRESS.md`: chronological engineering and test log.
- `agent.md`: persistent discoveries and hardware safety notes.
- `AGENTS.md`: standalone working, cc65, UCI, build, and mutation rules.

## Retained evidence

- `logs/`: about 11 GB and 40,000 files, including 558 `vice_auto_*` run
  directories, 38 generated-runner plan groups, and 285 physical-evidence
  directories under `logs/readyfs_c64u/`.
- `logs/migrated-readyos-residual/`: older non-atomic ReadyFS log directories
  preserved separately during the final source-tree audit.
- Historical manifests and logs intentionally retain old absolute paths as
  provenance; active source, documentation, and automation do not depend on
  the former ReadyOS location.

## Post-migration verification

- Full forced rebuild: `make -B readyfs` passed.
- Host/self-tests, UCI contract, overlay DMA, pipeline, and build report:
  passed.
- All 35 VICE plans compile from this location.
- Fresh VICE smoke:
  `logs/vice_auto_20260820_195205/manifest.json` — passed.
- Fresh overlay native REL gate:
  `logs/vice_auto_20260820_201127/manifest.json` — passed.
- Fresh REL refusal suite:
  `logs/vice_auto_20260820_201140/manifest.json` — passed.
- Latest retained-plan report: 33/33 successful; numbered UI coverage is 58
  proven, two partial, zero missing.
- Physical C64 Ultimate read-only UI run at 64 MHz:
  `logs/readyfs_c64u/ui-readonly-migration-20260820-ui-final2/results.tsv` —
  all five probe/directory cases passed from the relocated PRG.

The physical verification was read-only. It created, replaced, moved, and
deleted no USB1, SD-card, mounted-image, or IEC filesystem object.
