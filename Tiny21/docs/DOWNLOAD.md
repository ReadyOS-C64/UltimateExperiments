# Download and run Tiny 2.1 v0.6

**Required hardware: a C64 Ultimate with 64 MHz turbo support and a 16 MB REU.** Bring a USB drive.

<button type="button" id="tiny21-download" disabled>Download ready-to-use v0.6 ZIP</button>
<p id="tiny21-download-status" role="status">Preparing the download button…</p>
<noscript><p>Enable JavaScript to prepare the ZIP in your browser.</p></noscript>
<script type="module" src="install.js"></script>

<p id="tiny21-github-download"><a href="https://readyos-c64.github.io/UltimateExperiments/tiny21/DOWNLOAD.html">Open the live download page</a> to use the button from GitHub.</p>

Unzip the download. It contains `PROBE.PRG`, the matching `MODEL.BIN`, and this setup guide.

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
   | C64 and Cartridge Settings | REU Size | **16 MB** |
   | U64 Specific Settings | Turbo Control | C64U Turbo Registers (called U64 Turbo Registers on some firmware) |

3. Save any open work on the C64. In the Ultimate file browser, select `PROBE.PRG` and choose **Run**. Wait for the question field, type `what is 7 times 8`, and press **RETURN**. On the tested Ultimate, the answer was `7 times 8 is 56.` in about 36 seconds.

## If startup fails

Check the `/USB1` volume, the exact folder name, the two filenames, and the settings above. The PRG loads the converted `MODEL.BIN` and checks its CRC before opening the question field. The verified model file is 380,995 bytes with SHA-256 `ba89630a6bb1fd2d385e6daeae6bbc27a919996703e12e4beb4ab06136f61a1b`. The tested firmware was 3.14 with FPGA 121 and core 1.47.

Once the console returns to the question field, you can try `what is the capital of peru` without loading the model again. Use **DEL** to erase a character. Physical RUN/STOP cancellation and retry are in the [future-version notes](../FUTURE.md).

[Original Tiny 2.1 for Pentium/486 DOS](https://github.com/WollyMonjac/Tiny-2.1)
