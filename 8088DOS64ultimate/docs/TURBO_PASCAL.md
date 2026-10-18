# Turbo Pascal

Original Turbo Pascal 7.01's real-mode TURBO.EXE IDE and TPC.EXE compiler work with the target's 8088/DOS 3.3/640 KiB profile. TPX.EXE is a separate protected-mode IDE and is not the demonstrated program. Use `{$G-}` for 8088-compatible code generation. [Original user guide](https://turbopascal.nl/docs/Turbo_Pascal_Version_7.0_Users_Guide_1992.pdf).

Physical development-fixture tests pass editing, correcting, saving source, compiling an EXE to Disk, IDE run/output, exit to DOS, direct EXE execution, clean native backing-file close, complete 20 MiB retrieval and cold source/EXE reopening. The final fixture preserved 302 initial payloads plus the three test outputs. Earlier larger collections used different inventories; those counts are not interchangeable. Physical automation uses BIOS key injection, so it does not close the human keyboard gate.

The new 18-line [RIPPLE.PAS](../examples/RIPPLE.PAS) was loaded, compiled to Disk in original Turbo and run from DOS on the Ultimate. [Screenshots](SCREENSHOTS.md) show the actual source and finished picture. Its eight colours use 40-column full-block text. All 18 source lines, 1,000 guest cells and six complete native/video frames matched their expectations.

No Turbo Pascal, compiler libraries, DOS or vendor disk image is distributed here. Obtain the original Turbo Pascal distribution separately. The [DOS/GW-BASIC archive](https://archive.org/details/ms-dos-version-3.3-with-gw-basic-3.2-microsoft-1988) does not include Turbo Pascal. The complete installed compiler/demo collection exceeds the available space of the 2 MiB C profile. The successful full Turbo demonstrations used host-prepared 20 MiB development fixtures; the native 20 MiB installer still fails. Do not represent the prebuilt preview as a one-click installation of that full collection.

[Install](INSTALL.md) · [Build](BUILD.md) · [Current limitations](STATUS.md)
