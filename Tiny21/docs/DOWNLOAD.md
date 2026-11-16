# Download and run Tiny 2.1 v0.6

[Download the v0.6 install kit](../releases/Tiny21-C64-Ultimate-v0.6.zip)

Use a Commodore 64 Ultimate with 64 MHz turbo support, a USB drive, and a host with Python 3. Firmware 3.14 with FPGA 121 and core 1.47 was used for the physical tests. The ZIP contains `PROBE.PRG`, the local converter `make_model.py`, this guide, and the port’s MIT license.

## Prepare the two files

1. Unzip the install kit on your computer.
2. Download the [pinned original TINY.BIN from WollyMonjac](https://raw.githubusercontent.com/WollyMonjac/Tiny-2.1/1d5cf54677addf188a090ca1c91acb3d02989a1d/TINY.BIN) and save it as `TINY.BIN` in the unzipped folder. The upstream checkpoint comes directly from its author.
3. Open a terminal in that folder. Run:

   ```sh
   python3 make_model.py TINY.BIN MODEL.BIN --layout group8
   ```

   On Windows, use `py -3` if that is how you start Python. The converter checks the upstream SHA-256. It creates the 380,995-byte `MODEL.BIN` with SHA-256 `ba89630a6bb1fd2d385e6daeae6bbc27a919996703e12e4beb4ab06136f61a1b`. The generated `MODEL.json` is a manifest for the host.

If you already have the matching converted `MODEL.BIN`, start with the steps below.

## Set up the Ultimate

1. Create a directory named `TINY64-G8-INLINE-READY` in the root of the USB drive. Copy `PROBE.PRG` and the converted `MODEL.BIN` into it.
2. Plug it into the Ultimate and open its file browser. Confirm the directory appears as `/USB1/TINY64-G8-INLINE-READY`. This v0.6 PRG uses that exact model path. If the drive appears under another USB volume, adjust the connected drives so the folder is under `USB1`.
3. In **C64 and Cartridge Settings**, enable **Command Interface** and **RAM Expansion Unit**, and set **REU Size** to **16 MB**.
4. In **U64 Specific Settings**, select **C64U Turbo Registers** for **Turbo Control** (some firmware calls this **U64 Turbo Registers**). The PRG selects and verifies 64 MHz at startup.
5. In the Ultimate browser, select `PROBE.PRG` in the folder and choose **Run**. The ready screen reports `64 MHz checked, 16 MiB REU`, followed by the Ultimate DOS load time and the question field.

The program tests and uses the REU and takes over the current C64 session. Save any work on the machine before running it.

## Ask a question

Type `what is 7 times 8` or `what is the capital of peru` and press **RETURN**. **DEL** erases a character. The console reports progress while reading, shows answer characters as they arrive, and displays elapsed time at the end. At the ready prompt, enter another question using the same loaded model.

The console also supports **RUN/STOP** to clear an idle question or cancel between inference tokens. The 0.6 release verified cancel and retry in Peddle. The physical RUN/STOP check is listed in the [future-version notes](../FUTURE.md).

If startup fails, check the USB volume and directory, the converted filename, the turbo mode, and the REU and Command Interface settings. The bundled PRG expects the group-eight model format and verifies its CRC before running.

[Original Tiny 2.1 for Pentium/486 DOS](https://github.com/WollyMonjac/Tiny-2.1)
