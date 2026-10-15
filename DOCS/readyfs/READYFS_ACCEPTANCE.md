# ReadyFS acceptance and current boundaries

The maintained overlay build contains 28 sidecars and requires at least 1 MiB REU. ReadyFS remains a standalone experiment; a passed command matrix does not mean every backend or firmware combination is supported.

## Verified milestones

- The full build, host tests, asynchronous UCI contract, overlay DMA boundaries, and disjoint REU regions passed.
- Physical editor/history/paging work passed 55 cases across 1, 16 and 64 MHz, including bounded output history and restoration.
- Cross-backend acceptance covered all twelve directed COPY and MOVE routes among UltimateDOS host storage, IEC9, SoftwareIEC and native SD2IEC FAT. Recursive folder round trips, WhatIf preservation, deletion of created descendants, expanded mounted-image transfers, and independent saved-byte/type checks passed.
- The image matrix covered SEQ/PRG/USR transfers between SD-mounted and Ultimate-contained images. Settings and drive restoration were recorded. This establishes the tested device paths, not universal drive compatibility.
- DOS-style variables, expansion, arithmetic, conditions, labels, calls and config persistence passed 25,636 scripting checks in the recorded implementation pass. VICE exercised a 1 MiB REU; physical config/copy checks covered 1, 16 and 64 MHz.
- The latest physical backup demonstration (`batch-demo-20261013b`) passed eleven checks, including unchanged preview/refusal snapshots, independent backup bytes and hardware restoration.

## Boundaries

### Native SD2IEC

Native paths have 16-byte component limits. Native REL streams, automatic SD image-boundary traversal and simultaneous SD FAT/image transfers on the same partition are unavailable. Explicit intermediate endpoints and mount transitions are required. See the [native SD2IEC reference](SD2IEC_NATIVE.md).

### SoftwareIEC

SoftwareIEC map/unmap depends on firmware commands that are absent from the tested Ultimate firmware 3.14. Existing mapping transfers were covered by the cross-backend matrix. Folder and enumeration behavior remain firmware-sensitive; see the separate [SoftwareIEC guide](READYFS_SOFTWAREIEC_GUIDE.md).

### Wider coverage and batch scripting

Wider physical backend coverage and conversion of legacy handlers to typed results remain open.

RUN provides nine positional arguments and shared session variables, local label calls and bounded IF/GOTO control. External-script calls, nested RUN, SHIFT, FOR, pipes and redirection are unavailable. Use uppercase command option bytes in host-created SEQ scripts. A script's preview or copy verification is not whole-script transactional rollback.

The [screenshot tours](tours/editor.md), [SD2IEC tour](tours/sd2iec.md), [user guide](READYFS_USER_GUIDE.md), and [native support reference](SD2IEC_NATIVE.md) preserve the relevant illustrated behavior and limitations.
