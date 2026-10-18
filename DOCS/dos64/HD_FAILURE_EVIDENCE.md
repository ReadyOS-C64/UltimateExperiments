# Retaining HD failure evidence

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The optional host collector retains newly authoritative HD data before the outer workflow restores its pre-run REU backup. Restoring that old backup alone would destroy evidence of an uncertain new write. This is a development foundation; the physical HD runner and complete guest-write trace are still unfinished.

`HdEvidenceCollector` is passed explicitly as `pre_restore_evidence` to `run_with_recovery`. With no hook, the existing recovery path is unchanged. The native-file runner still allows two fresh restoration attempts, with a separate600-second phase per attempt.

The collector requires an exact configured native PRG, labels,140-byte D64H configuration, source image and freshly verified owned-directory marker. It accepts only the2/20MiB profiles and exact owned image path. It first captures RAM, then uses the original independent REU service to retain512 bytes at350000 and512 bytes at352000. It also reads the complete owned remote HD image through a fresh bounded FTP connection. Complete artifacts are independently rehashed by the parent. Accepted partial FTP chunks are flushed and retained even when collection fails or times out.

Collection runs in an isolated POSIX child, with an explicit1–120second evidence bound, default90. Interrupted waits, malformed reports and collector failures terminate/reap the child and cannot bypass the authorized full REU/configuration/reset recovery. Collection failure stays separate from the primary application failure. Cleanup errors remain visible. A process bound cannot undo an already submitted remote request or guarantee cancellation of an OS operation that cannot be interrupted.

## Required integration order

“RAM first” means before this collector uploads its own helper. The existing native application's successful evidence path already captures `application-ram-before-recovery.bin`, then uploads DRS1 to extract guest/CGA/floppy data. A collector invoked afterward may see DRS1 in RAM.

A physical HD caller must retain and hash-bind the original application RAM captured before any helper upload, or capture that authoritative RAM itself earlier. Use that artifact for native resident code, HD state and diagnostic claims. Keep the collector's later RAM separately labeled and ordered; it is not necessarily pristine application RAM.

Before physical HD execution, finish the owned-image stager/runner and an actual guest AH03 write-history trace, preserve each intent/payload/commit and uncertain write, and compare the entire final image/FAT/files against that history. The present last-sector/handoff snapshots cannot establish every write. Readback, CLOSE and reopen do not establish power-loss durability. Restoring REU does not restore the remote image or prior CPU execution.

Foundation evidence (local development record, not distributed), [HD implementation](HD_IMPLEMENTATION.md), [physical testing](HARDWARE_TESTING.md).
