# Ultimate Experiments

[Source repository on GitHub](https://github.com/ReadyOS-C64/UltimateExperiments)

Outside ReadyOS—and sometimes before ReadyOS—we do random experiments for the Commodore 64 Ultimate. Some may become supported projects; some are one-offs and throwaways. Pick an experiment below for its guides, examples and downloads.

## ReadyFS

ReadyFS aims to provide a full set of command-line tools and a coherent way to work with Ultimate DOS drives, mounted disk images or real C64 drives, SOFTIEC, and SD2IEC. That includes mounting disk images and accessing disk images on the Ultimate **without mounting them**, as if they were folders.

![ReadyFS command-line editor on a physical C64](readyfs/guide-assets/06-long-line.png)

[Explore ReadyFS](readyfs/index.md) · [Illustrated guide](readyfs/READYFS_USER_GUIDE.md) · [Screenshot walkthrough](readyfs/tours/editor.md)

## ReuSQL64

ReuSQL64 explores a SQL-like database engine that keeps its data in a 512 KB–16 MB REU. Create tables, query and join rows, group and aggregate results, and use explicit indexes through a C64 shell or a reusable engine API.

```sql
CREATE TABLE NOTES (ID I16, BODY TEXT)
INSERT INTO NOTES VALUES (1, 'HELLO REU')
SELECT ID, BODY FROM NOTES
```

[Explore ReuSQL64](reusql/index.md) · [SQL language](reusql/sql-language.md) · [Interactive shell](reusql/shell.md)

## C77 Cyberpunk 77

A reconstructed dual-bank character ROM and Cyberpunk palette, explored across ReadyOS applications. Clean and CRT galleries show the same screens with different display treatments.

![ReadyOS launcher with the C77 character ROM and palette](c77/screenshots/c77-cyberpunk-77-charrom/01_launcher.png)

[Explore C77 Cyberpunk 77](c77/index.md) · [Clean gallery](c77/screenshots/c77-cyberpunk-77-charrom/README.md) · [CRT gallery](c77/screenshots/c77-cyberpunk-77-crt/README.md)
