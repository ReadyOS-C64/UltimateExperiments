# Ultimate Experiments

[GitHub repository](https://github.com/ReadyOS-C64/UltimateExperiments) · [Documentation website](https://readyos-c64.github.io/UltimateExperiments/)

Outside ReadyOS—and sometimes before ReadyOS—we do random experiments for the Commodore 64 Ultimate. Some may grow or pivot into supported projects. Others are one-offs, prototypes, or throwaways. This repository keeps those experiments together without promising a finished product or a ReadyOS integration.

## Experiments

| Project | What we are exploring | Start here |
|---|---|---|
| **ReadyFS** | A DOS-like C64 shell and common filesystem model across Ultimate storage, IEC disks, SoftwareIEC and native SD2IEC, with verified transfers and REU-backed scripting. | [Project README](ReadyFS/README.md) · [Illustrated user guide](DOCS/readyfs/READYFS_USER_GUIDE.md) |
| **ReuSQL64** | A SQL-like database engine that keeps its database in a 512 KB–16 MB REU, with transactions, explicit indexes, joins, aggregates and an interactive shell. | [Project README](ReuSQL64/README.md) · [SQL reference](ReuSQL64/docs/sql-language.md) |
| **C77 Cyberpunk 77** | A reconstructed dual-bank character ROM, a Cyberpunk palette, and clean/CRT galleries of ReadyOS screens. | [Project README](C77Cyberpunk77/README.md) · [Gallery](C77Cyberpunk77/screenshots/c77-cyberpunk-77-charrom/README.md) |

## Try the main disk images

- [ReadyFS overlay shell](ReadyFS/artifacts/readyfs/readyfs-overlay-lab.d81): the main interactive build, with all 28 sidecars on one disk; requires at least 1 MiB REU.
- [ReadyFS diagnostic build](ReadyFS/artifacts/readyfs/readyfs-lab.d81): the simpler monolithic diagnostic reader.
- [ReuSQL64 interactive shell](ReuSQL64/build/rsql64_shell.d81): the database shell and its engine overlays; requires a 512 KB–16 MB REU. Database state is volatile until explicitly checkpointed and captured.

Each project README explains how to load, build and test its image. These are experiments: use disposable media and read the filesystem safety notes before trying mutations.

## Documentation

[DOCS/index.html](DOCS/index.html) is the static documentation site. It includes Markdown and HTML editions, screenshots, command references, and screenshot walkthroughs of ReadyFS. Video files are excluded. The site works locally and is prepared for GitHub Pages; see [publishing instructions](DOCS/README.md).

## Repository layout

The three experiments share this Git repository and its branches. Their own Makefiles, documentation and ignore rules keep builds independent. `DOCS/` is the publishable documentation tree; `tools/` contains its builder and validator.

Firmware reference checkouts, external demo website repositories, `.repoql`, internal agent working records, logs, caches, and generated build products remain local and ignored. The three main D81s above are intentionally committed. The separately managed music website also contains the Simple Game and Waltzing Matilda SID experiments; its source is outside the committed project set.

The 14 October 2026 cleanup retains only the latest ReadyFS capture run and its final appendix output, plus the latest ReuSQL64 VICE run. Older local logs were deleted. Historical run names in design and test documents describe earlier evidence and do not imply those raw logs are still shipped.
