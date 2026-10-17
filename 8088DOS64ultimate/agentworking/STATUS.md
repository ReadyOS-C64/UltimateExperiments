# Current V1 checkpoint — 2026-10-17

## Build and accepted model evidence

Native code checkpoint5273c00, runtime1506210a/MNUa2cd29cb; latest accepted installer proofd1a2dad. Local commits only, never push. Development ZIP: `build/development/5273c00/DOS64-development-5273c00.zip`, SHA256`daf98d2ebf17cb4a0d456410d0fcb19b144bcaaadf4661185772e8164e376ab2`. Twelve native files plus four package metadata/guide files; no vendor images. This is not a V1 release.

* [Public source promotion](evidence/v1-reset-public-promotion-root-20261017.json):34 reviewed source/build/test paths; source-built matching12/all16 packagefiles/ZIP exact;518 base tests,25 package and15 media-builder controls pass. No unchanged broad rerun needed.
* [FDISK](evidence/v1-reset-fdisk-root-20261017.json): genuine partition/delete/create/activate, guest warm reset, FORMAT/SYS/COPY, two native Finish/freshC file execution; originalA/B and thirdarena preserved. No Cboot/physical claim.
* [Turbo Pascal](evidence/v1-reset-turbo-root-20261017.json): original7.01 IDE edit/correct/save/diskcompile/IDErun/DOSrun, twoCIAFinish, fresh40 run/fresh80 IDEreopen/full native20MiB readback. Host-prepared vendor20MiB; all360 original/363 final livepayloads preserved. Physical human input remains open.
* [Installer/config](evidence/v1-reset-installer-config-root-20261017.json): six actual native machines; SETUP creates independentA/blankB/2MiBC with58 originalDOS payloads; CONFIG40/80; allthree unmodified generatedSTART→genuineDOS VER/fullDIR/P→CIAFinish/privateSafe/knownCLOSE/full4MiB+C preservation. Model only.

Current native fixes: silent speaker writes, bounded ANSI text clearing and finalized interrupt-vector restoration via ordinary guest reset ROM. Unit coverage is preserved with explicit207B FF00..FFCE tail alongside251B EF00 sidecar. Runtime MAIN56B spare; separate expanded-media UNIT MAIN has0B spare. See MEMORY_BUDGET.md before any source/layout growth. Further speed work and compiled activation stay post-V1.

## Hardware state — recovered in the main thread

[The physical COPY attempt](evidence/native-copy20m-splitread-failure-root-20261017.json) remains failed after 76 verified frames/2,490,368 bytes. [First Root recovery](evidence/wait76-root-recovery-failure-20261017.json) cancelled the read but ended with unknown CLOSE; original settings/media were restored. Do not reinterpret either attempt as a complete20MiB or whole4MiB proof.

[Main-thread recovery](evidence/main-readonly-close-basic-root-20261017.json) now confirms the owned read-only channel closed on the Ultimate, then a fresh closure capture permitted one reset. Advancing BASIC READY observations and final Resume passed; original settings and mounted media are exact. All owned jobs exited; Root is sole hardware owner. Device remains reserved at BASIC for final V1 work. No REU access occurred in this cleanup; current whole4MiB equality and original CPU/RAM/application restoration are not claimed. First padded CPU-enum refusal and subsequent readonly host-type assertion are preserved; native CLOSE was not repeated to repair the host assertion.

## Final model handoffs and remaining work

* [Same-drive copy/save/fresh launch](evidence/v1-same-drive-final-root-20261017.json) accepted: genuine DISKCOPY A:A, actual CIA Insert of a blank target, native SaveAs, C use, Finish, fresh generated START and second Finish. All720 sectors/37payloads, CFG and originalA/B/C verified independently. Root checked1213 sealed records and1583 current/source-copy rows. Retained host path-delivery and post-Resume equality qualifications remain explicit; no native defect or physical acceptance is inferred.
* [Progress site](evidence/progress-site-publication-20261017.json) published at https://dos64-ultimate-lab.klumsy.chatgpt.site with dated historical video/download, source, screenshots and clearly marked development ZIP. Its publication-time hardware status is historical. Static/interaction/asset checks passed; fresh browser visual/playback was unavailable.
* [Installer transfer preparation](evidence/v1-main-transfer-preparation-20261017.json): exact20-file local set prepared, but passive FTP stalled at PASV and a fresh active20s attempt stalled at listener accept before any payload. No native program/REU/C64 control changed; empty/possiblyzero-marker owned folders retained, neither qualifies as staged. Both jobs exited. Do not repeat unchanged FTP probes. A multipart /Temp attachment → native UCI COPY/readback route is a source-backed proposal, not yet implemented or qualified.
* Every existing subagent has finished. Do not spawn, reuse or delegate further work. The main thread owns final installer/config/media/Turbo physical verification and local commits. All ten final physical/human V1 gates remain open. [V1 endpoint](../docs/V1_ENDPOINT.md), [human checklist](../docs/V1_HUMAN_CHECKLIST.md).

Earlier checkpoints are preserved byteexact in [STATUS_HISTORY_20261017.md](STATUS_HISTORY_20261017.md); their superseded next steps are historical.

## Latest user-directed reboot and retry

[Reboot/retry evidence](evidence/reboot-transfer-retry-root-20261017.json): user-authorized `machine:reboot` acknowledged; actual advancing BASIC7/24 and settings/media equality passed. This source-backed endpoint restarts the C64 cartridge; it does not reboot network services or power-cycle the device. One new passive FTP attempt still timed out at PASV before payload. One new named REST multipart probe still returned404 attachment-read failure before DMA; original32 bytes remained exact, final Resume and settings/media equality passed. Both detached workers exited. No native/REU execution or final-package staging. A physical power cycle has not been performed.

Between the preceding commit and this retry, a read-only native Temp directory inspection succeeded; no files were deleted. A cached REU staging helper was compiled but remains unqualified and was not run on hardware. No definitive firmware/network root cause established.

## Transfer blocker cleared after user reboot

[Successful physical staging](evidence/powercycle-transfer-success-root-20261017.json): following the user-reported full reboot, passiveFTP transferred and independently read back all20 files in fresh `/usb1/DOS64_TEST/v1-powercycle-20261017` (twelve exact native assets, four package documents, three original DOS images, one historical preparation marker). Every byte/source pin matched, exact listing/221QUIT and original settings/media equality passed. Detached Terminal1654 worker exited0 without watchdog. No C64 control/REU/native execution; final installer/runtime/human gates remain open. This supersedes the transfer blocker and cached-helper workaround as next work. Root cause remains unproven; no need to repeat REST upload diagnostics. The copied OWNER.JSON still names the earlier preparation directory; actual destination ownership/provenance is in the freshMKD/PWD/fullreadback evidence.

## Final SETUP now running on the Ultimate

[Live final SETUP evidence](evidence/final-setup-live-root-20261017.json): native unchangedf4335eb7 is running at verifiedPAL/Manual64 and showing its real home-folder browser. Actual currentlower4MiB after user reboot was captured through128 source/nonce/CRC-checked32KiB frames, persisted byFTP and reread byteexact:6e7c4fae1254ca5c5e775e454d3b18e80aa20a7eb0f0bb22a72ef68e2adf3ff1 at `/usb1/DOS64_TEST/v1-baseline-20261017/BASELINE.REU`. This is the new current baseline, not historicalac43 restoration. Backup helper only readsREU; before/after settings/media/BASIC passed.

Initial controller path error stopped before network; initial fullcoldSETUP comparison saw BASICROM A000..B527 rather than hiddenRAM and stopped beforeSYS. Both retained. Source-bound successor verified visible0801..9FFF plus previously completeFTP source, adopted sameLOAD and observed genuine unmodified bootstrap/CRC→nativeUI. No hidden-preSYS source equality claim. Current nativeUI is active; original turbo profile is intentionally temporarilyManual64 until this session ends. Do not reset/replace while installation may be writing.

Physical keys have not been injected. User was asked to select `/usb1/DOS64_TEST/v1-powercycle-20261017`, DOS1/2/3, skipimport and2MiBC, then confirm. Read-only observer is finite and does not reset or perform files operations. Its first filename-serialization error after twoGETs is retained; corrected observer saw actual root browser/state2/error0. Independent output checker passed prior genuine native model outputs (all58DOSpayloads/wholeFAT/CFG/STARTpatch/runtimeassets); physical outputs, finalDOS and Turbo remain pending. No V1 gate closed merely by displaying SETUP.
