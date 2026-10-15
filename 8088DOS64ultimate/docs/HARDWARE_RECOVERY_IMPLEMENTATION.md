# Development recovery and fixture preparation

`build_support/build_bulk_reu_service.py --test` builds a standalone 592-byte native recovery service and runs four actual-assembly tests plus seventeen no-network workflow tests. The service uses the unchanged REU primitive, a sequenced mailbox at 6000 and a 16 KiB staging window at 8000. Only REU addresses below 4 MiB are accepted. Peddle tests independently seed and compare all 16 MiB, including the untouched upper 12 MiB.

`build_support/c64u_bulk_reu_recovery.py` snapshots all first 4 MiB into a complete size/hash-verified, read-only local backup before invoking an application. Restoration reloads the service, writes from verified immutable backup bytes and independently rereads all 4 MiB. Descriptor/staging readback precedes GO publication. Stale sequences, partial transfers, timeouts, corrupted backups, short reads and recovery/storage failures have explicit failure results. Recovery attempts and phase deadlines are bounded. Full RAM is captured before failure recovery and final reset.

This is destructive execution takeover, with explicit CIA2/NMI ownership. Saved machine/turbo/media identities are checked; prior CPU, timers and CIA execution cannot be resumed. A callback must preserve configuration/media and stay inside the first 4 MiB. Unexpected machine configuration prevents restoration DMA and retains the complete backup for explicit recovery. Terminal owns physical invocations. REST is a development control channel, never an emulator runtime dependency.

`build_support/c64u_media_fixture.py` prepares a read-only DOS disk1 fixture through development FTP. It requires the independent 360 KiB source SHA-256, creates a fresh `/usb1/DOS64_TEST/<run-id>` directory, verifies a unique ownership marker, uploads `DOS33A.IMG` and reads every byte back. Existing run directories are rejected before any upload. It never deletes or overwrites an existing fixture. Four no-network tests cover success, ownership rejection, readback corruption and invalid inputs.

The initial preparation proof was host/model-only. Terminal-owned FTP subsequently staged and verified a fresh whole disk1 copy; [staging evidence](../agentworking/evidence/c64u-media-fixture-20261015.json). The first physical recovery/native attempt failed before service loading on REST temporary attachment errors. No DMA/application or backup occurred; full RAM and independent unchanged configuration/media checks are retained. Actual native UCI/DOS and full4MiB restoration remain separate gates. [First failure](../agentworking/evidence/c64u-native-first-failure-20261015.json), [preparation evidence](../agentworking/evidence/bulk-reu-fixture-preparation-20261015.json).


Physical RAM-only bodyless PUT/file-loader gates now pass, but measured whole-restoration cost rejects both tiny PUT payloads and per16KiB packed PRG reloads under the existing600second phase. A single-file native UCI restore is in private development. No fullREU recovery or native DOS acceptance follows yet. [Measured probes](../agentworking/evidence/c64u-rest-transport-probes-20261015.json).


`c64u_native_ftp_put_runner.py --transport ftp-put` now uses strict owned file/hash launch and `DeltaService`. This still snapshots/verifies all4MiB before application; within the600second restoration phase it scans all4MiB, uploads only changed16KiB chunks from verified immutable backup, and the original workflow independently rereads/compares all4MiB. Every bounded retry rescans from scratch. No-change, unexpected region, partial DMA/alias and partial staging cases are tested. This is prepared host/model behavior, not yet physical full-restoration acceptance. [Evidence](../agentworking/evidence/delta-recovery-preparation-20261015.json).

Captured-code validation normalizes only the two UCI absolute pointer operands (four bytes), with source opcode and legal896byte buffer checks; successful DOS requires initialized buffer pointers. All other resident bytes remain exact. The actual native Peddle hostRAM capture passes this verifier; alias/scoping metadata emits identical binaries.


## Physical acceptance

The exhaustive delta workflow passed with frozen native DOS target647eca: ALL4MiB backed,256chunks inspected,37changed/606208bytes restored in282.119seconds scan+write, then ALL4MiB reread and independently compared byte-for-byte. First attempt succeeded; prior configuration/media/reset/resume passed. Fullrun545.455seconds includes genuineDOSscript/evidence. [Accepted physical proof](../agentworking/evidence/c64u-native-dos-20261015.json). The private single-file native UCI restore remains an alternative with host integration pending, not part of this accepted run.
