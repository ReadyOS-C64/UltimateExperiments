# Ultimate Experiments

[GitHub repository](https://github.com/ReadyOS-C64/UltimateExperiments) · [Documentation website](https://readyos-c64.github.io/UltimateExperiments/)

Outside ReadyOS—and sometimes before ReadyOS—we do random experiments for the Commodore 64 Ultimate. Some may grow or pivot into supported projects. Others are one-offs, prototypes, or throwaways. This repository keeps those experiments together without promising a finished product or a ReadyOS integration.

## ReadyFS

ReadyFS aims to provide a full set of command-line tools and a coherent way to work with Ultimate DOS drives, mounted disk images or real C64 drives, SOFTIEC, and SD2IEC. That includes mounting disk images and accessing disk images on the Ultimate **without mounting them**, as if they were folders.

[Project README](ReadyFS/README.md) · [Illustrated user guide](ReadyFS/docs/READYFS_USER_GUIDE.md) · [Online guides and downloads](https://readyos-c64.github.io/UltimateExperiments/readyfs/index.html)

## ReuSQL64

A SQL-like database engine that keeps its database in a 512 KB–16 MB REU, with transactions, explicit indexes, joins, aggregates and an interactive shell. It explores how much useful database work can fit into a C64 with expanded memory.

[Project README](ReuSQL64/README.md) · [SQL reference](ReuSQL64/docs/sql-language.md) · [Online guides and downloads](https://readyos-c64.github.io/UltimateExperiments/reusql/index.html)

## C77 Cyberpunk 77

A reconstructed dual-bank character ROM, a Cyberpunk palette, and clean/CRT galleries of ReadyOS screens. The experiment compares text rendering and presentation across the loader and applications.

[Project README](C77Cyberpunk77/README.md) · [Clean gallery](C77Cyberpunk77/screenshots/c77-cyberpunk-77-charrom/README.md) · [Online galleries](https://readyos-c64.github.io/UltimateExperiments/c77/index.html)

## Documentation and repository

[DOCS/index.html](DOCS/index.html) is the static documentation site, with Markdown and HTML editions, screenshots, command references, walkthroughs and the main disk downloads on each experiment's child pages. See [publishing instructions](DOCS/README.md) to build or maintain it.

The experiments share this Git repository, while their Makefiles, documentation and build rules remain independent. Firmware references, external demo websites, `.repoql`, internal working records, logs and generated builds remain local and ignored. The main ReadyFS and ReuSQL64 D81s are committed; their project READMEs explain how to use them.
