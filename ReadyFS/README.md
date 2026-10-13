# ReadyFS

ReadyFS is a standalone C64 filesystem laboratory and DOS-like command shell.
It explores one coherent endpoint/path model across IEC floppy and tape,
UltimateDOS, SoftwareIEC, disk images, and future SD2IEC-style hierarchical
storage. It is intentionally separate from ReadyOS until the filesystem model
and hardware behavior are proven.

## Build

Requirements: cc65 (`cl65`), VICE tools (`c1541`, `x64sc`), Python 3, Clang,
and .NET for the external VICE automation harness.

```sh
make readyfs
```

The complete build produces the monolithic and overlay applications, nineteen
sidecars, boot/test disk images, host-test results, the UCI source-contract
check, and memory/REU reports below `artifacts/readyfs/`.

Useful targets:

- `make readyfs-host-tests` — host unit and pipeline tests
- `make readyfs-build-report` — linker, overlay, pipeline, and REU checks
- `make readyfs-ui-report` — summarize retained VICE evidence
- `make readyfs-vice-smoke` — rebuild and execute the VICE smoke plan

VICE scripts use `VICE_TASKS_REPO` when set; otherwise they resolve the shared
harness at `../../agenticdevharness` from this project.

## User guide

Start with the [illustrated user guide](docs/READYFS_USER_GUIDE.md) for the path
model, command syntax, options, worked examples, and full command reference.
The [standalone HTML edition](docs/READYFS_USER_GUIDE.html) embeds its screenshots
and diagrams for offline reading and printing. The guide is also available on
the [public demo site](https://readyfs-editor-demo.klumsy.chatgpt.site/guide.html).

## Interactive use

Use `readyfs-overlay.prg` with `readyfs-overlay-lab.d81` on device 8 for the
wrapped editor, command history, REU output paging, and short options. See
[Interactive UI guide](docs/READYFS_INTERACTIVE_UI.md) for keys, aliases, limits,
and drawing behavior. The monolithic build remains a basic diagnostic reader.

## Hardware automation

Use `build_support/start_readyfs_*_terminal.sh`. These wrappers deliberately
launch a separate Terminal-owned bash for C64 Ultimate REST/FTP reliability.
Read-only UI probes are safe to run directly through those wrappers. Mutation
suites require a newly created marker-owned run root below
`/usb1/READYFS_TEST/<run-id>` or `/sdcard/READYFS_TEST/<run-id>` and preserve
it by default.

See [docs/READYFS_SAFETY.md](docs/READYFS_SAFETY.md) and `AGENTS.md` before any
physical mutation test.

## Layout

- `src/apps/readyfs/` — C and 6502 assembly source
- `cfg/` — standalone overlay linker configuration
- `build_support/` — host tests, VICE plans/runners, C64U runners, and reports
- `docs/` — design, path model, safety, requirements, and UI matrix
- `AgentWorking/` and `agent.md` — implementation history and operational notes
- `artifacts/readyfs/` — PRGs, disk/tape fixtures, labels, maps, and reports
- `logs/` — retained VICE and physical-hardware evidence migrated with the app

See [PROJECT_INVENTORY.md](PROJECT_INVENTORY.md) for the migration boundary,
artifact groups, automation entry points, and current verification evidence.


SD2IEC development on `codex/sd2iec-support` adds cached sidecars 16 (stream
preparation and standalone native IEC I/O) and 17 (IEC configuration policy).
Builds now require all 19 sidecars. Slot 18 owns native configuration I/O and
mount reporting; slot 19 owns native file lookup and mutation status. See [native IEC configuration](docs/READYFS_IEC_CONFIGURATION.md)
for commands, protocol boundaries and current verification status. Full SD2IEC
filesystem/image transfer acceptance is still in progress.
