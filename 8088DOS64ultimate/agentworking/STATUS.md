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
* Every existing subagent has finished. Do not spawn, reuse or delegate further work. The main thread owns final installer/config/media/Turbo physical verification and local commits. All ten final physical/human V1 gates remain open. [V1 endpoint](../docs/V1_ENDPOINT.md), [human checklist](../docs/V1_HUMAN_CHECKLIST.md).

Earlier checkpoints are preserved byteexact in [STATUS_HISTORY_20261017.md](STATUS_HISTORY_20261017.md); their superseded next steps are historical.
