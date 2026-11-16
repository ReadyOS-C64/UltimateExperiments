# Download and run Tiny 2.1 v0.6

You need a **64 MHz-capable C64 Ultimate**, a USB drive, plus `PROBE.PRG` and the matching v0.6 `MODEL.BIN`. **Already have both?** [Go straight to USB setup](#set-up-the-ultimate).

## Get the two files

1. [Download and unzip the v0.6 install kit](../releases/Tiny21-C64-Ultimate-v0.6.zip). It contains `PROBE.PRG` and `make_model.py`.
2. [Download the original TINY.BIN from WollyMonjac](https://raw.githubusercontent.com/WollyMonjac/Tiny-2.1/1d5cf54677addf188a090ca1c91acb3d02989a1d/TINY.BIN). Save it as `TINY.BIN` in the unzipped folder.
3. Open a terminal in that folder and run this once on your computer to create `MODEL.BIN`.

   ```sh
   python3 make_model.py TINY.BIN MODEL.BIN --layout group8
   ```

   On Windows, use `py -3` in place of `python3` if needed.

## Set up the Ultimate

1. Copy the two files to this exact folder on the USB drive. In the Ultimate file browser, the drive must appear as `/USB1`.

   ```text
   /USB1/TINY64-G8-INLINE-READY/
     PROBE.PRG
     MODEL.BIN
   ```

2. Set these options once.

   | Ultimate menu | Setting | Value |
   | --- | --- | --- |
   | C64 and Cartridge Settings | Command Interface | Enabled |
   | C64 and Cartridge Settings | RAM Expansion Unit | Enabled |
   | C64 and Cartridge Settings | REU Size | 16 MB |
   | U64 Specific Settings | Turbo Control | C64U Turbo Registers (called U64 Turbo Registers on some firmware) |

3. Save any open work on the C64. In the Ultimate file browser, select `PROBE.PRG` and choose **Run**. Wait for the question field, type `what is 7 times 8`, and press **RETURN**. On the tested Ultimate, the answer was `7 times 8 is 56.` in about 36 seconds.

## If startup fails

Check the `/USB1` volume, the exact folder name, the two filenames, and the settings above. The original checkpoint is `TINY.BIN`. The PRG loads the converted `MODEL.BIN` and checks its CRC before opening the question field. The verified model file is 380,995 bytes with SHA-256 `ba89630a6bb1fd2d385e6daeae6bbc27a919996703e12e4beb4ab06136f61a1b`. The tested firmware was 3.14 with FPGA 121 and core 1.47.

Once the console returns to the question field, you can try `what is the capital of peru` without loading the model again. Use **DEL** to erase a character. Physical RUN/STOP cancellation and retry are in the [future-version notes](../FUTURE.md).

[Original Tiny 2.1 for Pentium/486 DOS](https://github.com/WollyMonjac/Tiny-2.1)
