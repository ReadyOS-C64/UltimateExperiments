# Ultimate Experiments

[Source repository on GitHub](https://github.com/ReadyOS-C64/UltimateExperiments)

Outside ReadyOS—and sometimes before ReadyOS—we do random experiments for the Commodore 64 Ultimate. Some may become supported projects; some are one-offs and throwaways. These guides describe what each experiment currently does and how to try it.

## Pick an experiment

| Project | Explore | Read |
|---|---|---|
| **ReadyFS** | Filesystem paths, typed transfers, native SD2IEC and a DOS-style shell | [Project guide](readyfs/index.md) · [Illustrated user guide](readyfs/READYFS_USER_GUIDE.md) |
| **ReuSQL64** | A SQL-like database in REU memory, from tables and indexes to joins and aggregates | [Project guide](reusql/index.md) · [SQL language](reusql/sql-language.md) |
| **C77 Cyberpunk 77** | Dual-bank character ROM, palette and ReadyOS screenshot galleries | [Project guide](c77/index.md) |

## ReadyFS in pictures

![ReadyFS command-line editor on a physical C64](readyfs/guide-assets/06-long-line.png)

The [editor and filesystem walkthrough](readyfs/tours/editor.md) follows help, editing, history, previews, transfers and a parameterized backup script. The [SD2IEC walkthrough](readyfs/tours/sd2iec.md) follows real native folder and image operations. Every step includes a command, explanation and actual C64 screenshot. No video files are needed or bundled.

## Main disk images

- [ReadyFS overlay shell](downloads/readyfs-overlay-lab.d81): the main interactive build and all 28 sidecars; at least 1 MiB REU.
- [ReadyFS monolithic diagnostic](downloads/readyfs-lab.d81): the earlier, simpler reader.
- [ReuSQL64 interactive shell](downloads/rsql64_shell.d81): SQL client and engine overlays; 512 KB–16 MB REU.

Read each project guide before loading an image. For filesystem writes, use disposable fixtures and follow the ownership rules. REU database state needs an explicit checkpoint/capture workflow to survive reset.

## Read offline or publish

Every reference has a Markdown source and an HTML edition. Open `index.html` for the website, or browse the Markdown files directly. Images, styles and downloads are local; there is no runtime CDN dependency. The [portable ReadyFS guide](readyfs/portable-guide.html) embeds its illustrations for printing and single-file offline reading.

[Build and GitHub Pages instructions](README.md)
