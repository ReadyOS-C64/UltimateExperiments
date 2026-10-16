# Independent A/B floppy core

The emulator now provides two installed 360 KiB XT floppy drives with independent mounted images. BIOS DL=0 selects A and DL=1 selects B; an empty installed drive reports not-ready. Reset and last-status services are shared, and BIOS publishes the shared diskette status at guest BDA 0441. Equipment and the supported late-XT geometry query report two drives. This does not add an AT media-change line or implement unsupported format commands.

Actual linked-code tests cover independent reads/writes/verify, readonly failures, full preservation of the other disk, partial-write errors, BIOS interrupt-frame return/status, repeated swaps and stale save acknowledgements. The current combined build passes genuine DOS boot, VER and DIR in Peddle. Physical A/B use, startup configuration, native Save/Discard controls and the disk browser are separate integration work.

Three complete images rotate through REU bases 100000, 180000 and 380000. PREPARE chooses the unmounted arena; the loader must use that returned base. COMMIT publishes the validated incoming image and releases the old arena. The next swap must choose the newly free arena, rather than always loading 380000. The spare ends at 3DA000 exclusive, below the reserved installer bank 3E0000–3EFFFF and anchor 3FF000–3FFFFF. All three images fit the 4 MiB minimum. Larger configured capacity does not change these baseline addresses.

The disk code uses an additional C900 overlay, loaded from immutable REU 343800–343FFF. It is the eighth physical startup slot, following the separate SAVER slot at 343000. The managed DISK and special SAVER headers both use numeric identity 7, but have distinct exact tags, entry addresses and locations; they are never interchangeable. All eight startup headers are validated before copying. Runtime PRG size is now 47,105 bytes, including its two-byte load header; payload size is 47,103 and destination is 0801–BFFF. Loader code must use the checked size, not the earlier 45 KiB package assumption.

The paused/cold native API is `dos64_floppy_control`, with resident `dos64_floppy_request` and `dos64_floppy_status`. It is not a guest DOS service. The caller owns exclusive cache/REU/UCI activity and must be cold-open or coherently paused at stage 5. Native P is preserved except returned carry; A/X/Y and documented scratch are clobbered. The request layout and constants are authoritative in `include/disk.inc`:

| Offset | Bytes | Field |
| --- | --- | --- |
| 0 | 1 | Operation: PREPARE=1, COMMIT=2, CANCEL=3, EJECT=4, CLEAN=5 |
| 1 | 1 | Drive, A=0 or B=1 |
| 2 | 1 | Incoming readonly bit 0; explicit discard bit 1 |
| 3 | 1 | Caller completion proof, A5 |
| 4 | 1 | Configured REU MiB for PREPARE, 4–16 |
| 5 | 3 | Returned candidate REU base |
| 8 | 3 | Exact image length, 05A000 |
| 11 | 4 | Session-local staging token |
| 15 | 4 | Mount-generation snapshot |
| 19 | 4 | Content-generation snapshot |
| 23 | 4 | Caller binding cookie |

PREPARE captures drive, policy, binding and old generations. COMMIT requires the matching token/drive, complete whole-image load/CRC/known-close proof from its caller, exact length/base, unchanged generations and a valid supported BPB. It performs no fallible operation after publication starts. Cancellation and incoming errors preserve the old mounted image. Dirty replacement requires the captured explicit-discard policy.

Writes conservatively mark the selected disk dirty and advance its content generation before any potentially partial export. Invalid and readonly requests cannot clear dirty state. CLEAN is only an acknowledgement after the coordinator has completed full save, close/reopen and verification; it requires exact current mount/content generations and a new backing binding. An old acknowledgement cannot clear a newer write. Generation exhaustion refuses capability reuse. Tokens and generations are session-local: cold initialization resets metadata and invalidates outstanding clients.

The legacy startup importer still loads A at its historical fixed arena. Legacy native SAVE is guarded by its configured export bank and remains A-only; it does not yet acknowledge the new generation pair or support saving while C is online. The frontend must integrate current descriptor bases, filename/CRC bindings, dirty prompts and disk-file verification before advertising swap/save as an end-user feature. A native save only exports data that guest DOS has already submitted to BIOS; it cannot close application files or flush data still buffered inside DOS.

Evidence: `agentworking/evidence/dual-floppy-root-20261016.json`. The accepted keyboard, cursor, address/memory optimizations and IRQ/REP/clock sampling policy remain composed with this core. No physical speed or 8088-equivalence claim follows from these tests.
