# ReadyFS Agent Rules

ReadyFS is a standalone filesystem laboratory. It is deliberately not a
ReadyOS application yet. Build and test it only from this project root.

## Hardware-test safety

- C64 Ultimate automation may create or mutate data only below a new per-run
  `/usb1/READYFS_TEST/<run-id>` or `/sdcard/READYFS_TEST/<run-id>` directory
  carrying the matching ReadyFS ownership marker.
- Before delete, move-source cleanup, overwrite, format, partition-map
  removal, or optional cleanup, validate both the canonical test-root prefix
  and ownership marker. Never delete or replace anything else on USB1, SD
  card, an existing mounted image, or another IEC device.
- Preserve each run root and its evidence by default. Cleanup is opt-in and
  only valid for the exact marker-validated run id.
- For the user-authorized SD2IEC work, native IEC10 mutations may additionally
  use a freshly created, unique test directory with components no longer than
  16 bytes and an exact per-run ownership marker. Bootstrap must refuse an
  existing root/marker. Re-read the marker before every subsequent mutation;
  mount/write/delete only owned fixtures. Preserve all pre-existing SD2IEC
  files and retain the new test roots by default. User authorization also
  permits temporary Ultimate A8 disable/address repair and restoring its exact
  original image/settings; do not generalize that exception to other media.
- REST and FTP access from Codex must run from a separate Terminal-owned or
  long-running background bash. A one-shot foreground shell may report false
  connectivity failures.

## UCI protocol discipline

- Reuse the ReadyIRC/UCI Tester asynchronous transaction contract and verify
  physical behavior at 1, 16, and 64 MHz. Fixed delays are not UCI pacing.
- Synchronize to quiet IDLE before writing a command. Write all command bytes,
  issue PUSH once, then wait for DATA_LAST or DATA_MORE; immediate IDLE after
  PUSH is not completion.
- Drain all data and status queues before DATA_ACC. After accepting MORE,
  observe the transition away from MORE before waiting for another data block.
  After LAST, wait for fully quiet IDLE.
- ABORT is asynchronous. Respect ABORT_P and service the interface until quiet
  rather than repeatedly issuing ABORT.
- Poll bounds are failure limits only. Bound queue drains and keep limits long
  enough at the fastest CPU speed. Always drain oversized replies even when a
  caller buffer truncates them.
- Run `python3 build_support/verify_readyfs_uci_protocol_contract.py` after any
  UCI change.

## C64 and cc65

- Prefer `unsigned char` and `unsigned int`; avoid heavy stack locals in hot
  paths. Do not stomp cc65 zero-page runtime addresses `$02-$1B`.
- Keep C/assembly calling assumptions explicit and conservative.
- In linker configurations, place BSS after
  `__ONCE_RUN__ + __ONCE_SIZE__`, never directly at `__ONCE_RUN__`.
- Keep each sidecar's code, RODATA and BSS in distinct assembler segments,
  packaged into its shared load region. cc65 may emit constants inside a
  function scope before switching back to code; merging segment names can
  execute those constants as BRK. Cache sizes must cover the complete payload.
- The current overlay build keeps resident code below `$B600`, loads sidecars
  at `$B600`, and uses REU-backed state. Preserve the verifier-enforced memory
  boundaries.

## Build and automation

- Run `make readyfs` from this directory for a complete build, contract check,
  host test pass, and memory report.
- VICE launchers resolve the harness through `VICE_TASKS_REPO` or the default
  sibling-project path `../../agenticdevharness`.
- C64U UI work must use the `start_*_terminal.sh` wrappers so network calls run
  in Terminal. Never bypass ownership gates for mutation suites.
- Historical evidence under `logs/` is retained by default. Do not delete it
  as part of ordinary builds or test runs.

## Demo recording preferences

Follow `docs/DEMO_RECORDING_PREFERENCES.md` for recorded demos. The user prefers
input typing/editing presented about 40% faster (1.4×), tight waits, readable
paging pauses, and concise descriptions strictly above the C64 picture.
