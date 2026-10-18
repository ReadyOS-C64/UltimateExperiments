# Install the prebuilt development preview

This is an experimental preview. Native 2 MiB installation passed physical testing; **native 20 MiB creation currently fails**. Choose 2 MiB. Configuration, floppy swap/Save/Finish and human qualification are still open. [Current status](STATUS.md).

## Obtain the files

- [Download DOS64-development.zip](../downloads/DOS64-development.zip). No compiler is needed to use it.
- Obtain the three original 360 KiB DOS 3.3 raw images from [MS-DOS 3.3 with GW-BASIC 3.2 on Internet Archive](https://archive.org/details/ms-dos-version-3.3-with-gw-basic-3.2-microsoft-1988). They are not included here.
- Optionally [download EXAMPLES.IMG](../downloads/DOS64-examples.img), containing only our RIPPLE program/source, HANGMAN.BAS and instructions. It is not bootable and contains no DOS, GW-BASIC or Turbo Pascal binaries.

Turbo Pascal 7.01 is optional and must be obtained separately. Search the Internet Archive software catalogue for the original Turbo Pascal 7.01 distribution; its compiler is not part of the DOS archive. RIPPLE.EXE runs without installing Turbo Pascal. HANGMAN.BAS needs GW-BASIC, supplied by the linked DOS archive.

## Prepare the Ultimate

Use a C64 Ultimate with at least 4 MiB REU, Ultimate DOS and the UCI command interface enabled. The demonstrated hardware profile is PAL, Turbo Control Manual, CPU Speed 64 MHz; record your normal settings first. Firmware 3.14 was used for the latest tests. The emulator does not need Ethernet, a REST client or a host computer during normal use.

Create a **new** folder such as `/usb1/DOS64`. Extract the ZIP there and keep these twelve matched files together:

```text
SETUP.PRG  SETUP.FAT  SETUP.PUB  CONFIG.PRG
DOS64.PRG  DOS64.REL  DOS64.MNU
START.TPL  START.REL  START.INO  START.RCV  START.RFW
```

Also retain README.txt, BUILD.json, SHA256SUMS and DOS64.INI.example for reference. Copy your DOS images onto the Ultimate, preferably as short-name copies DOS1.IMG, DOS2.IMG and DOS3.IMG in a source subfolder. Keep the originals unchanged. Do not extract the images into an ordinary folder or wrap them in D81s. No dummy launcher D81 or large blank hard-drive download is required.

## Run SETUP

1. Launch SETUP.PRG from the Ultimate file browser.
2. Use its folder/file UI to select the new installation home and the three DOS images in disk order. Do not assume that it knows the folder from which it was launched.
3. Choose a **2 MiB C drive**. The 20 MiB option is experimental and currently fails on the physical installer.
4. Let SETUP create and verify the C backing file, independent A/B images, DOS64.CFG and folder-aware START.PRG. Keep all matched assets beside the generated launcher. Wait for the completion screen.
5. Launch the generated START.PRG to boot DOS. Use `VER` and `DIR` as first checks.

SETUP refuses existing destinations. If it fails, retain the partial files and use a fresh folder for the next attempt. Do not treat a partial image, CFG or launcher as a completed installation.

## Preferences and moving folders

For startup width, copy DOS64.INI.example to DOS64.INI in the same home:

```ini
[emulator]
initial_columns=80
```

Use 40 or 80; missing INI defaults to 80. CONFIG.PRG regenerates folder-aware configuration/launch assets and supports moved-folder paths, but full physical qualification remains open. Do not move an installation and assume its old embedded paths will follow it automatically.

## Floppies, examples and C

A/B are raw IMG files loaded into REU. They are independent disks. Guest writes do not automatically replace the original floppy file. The native disk menu is opened with **Ctrl + Commodore + Run/Stop**: A/B chooses drive, I inserts, S saves to a new managed version, N saves as, E ejects, W changes session write protection, R resumes. Follow dirty-media prompts. These controls are implemented and modeled; the complete current hardware workflow is still under qualification.

Insert EXAMPLES.IMG as B through the native menu after booting DOS from A. `B:\RIPPLE.EXE` draws the static colour picture; a key returns to DOS. From the directory containing GWBASIC.EXE, run `GWBASIC B:\HANGMAN.BAS /F:1`; enter `LIST` to read it and `SYSTEM` to return to DOS. The example readme has copy commands. Keep separate backups of work.

C uses a cached file-backed image. A working 20 MiB C has physical read/write/close/restart evidence from host-prepared fixtures, but this does not fix the 20 MiB native installer. Larger offsets are implemented; power-loss durability is not established.

Before ending a session, exit applications to DOS, open the native menu and choose **F Finish**. Wait for its safe completion message before reset or shutdown. Finish is not Resume. Unknown closure/error state is not a successful save. The current full Finish acceptance remains open; use this preview on disposable media and keep original files.

[Examples](examples/index.md) · [Screenshots](SCREENSHOTS.md) · [Build](BUILD.md) · [Status](STATUS.md)
