# Download and run Tiny 2.1 v0.6

**Required hardware: a C64 Ultimate with 64 MHz turbo support and a 16 MB REU.** Bring a USB drive.

<button type="button" id="tiny21-download" disabled>Download ready-to-use v0.6 ZIP</button>
<p id="tiny21-download-status" role="status">Preparing the download button…</p>
<noscript><p>Enable JavaScript to prepare the ZIP in your browser.</p></noscript>
<script type="module" src="install.js"></script>

<p id="tiny21-github-download"><a href="https://readyos-c64.github.io/UltimateExperiments/tiny21/DOWNLOAD.html">Open the live download page</a> to use the button from GitHub.</p>

Unzip the download. It contains `PROBE.PRG`, `MODEL.REU`, and this setup guide. `MODEL.REU` is the ready-to-load model image.

## Set up the Ultimate

1. Copy `MODEL.REU` and `PROBE.PRG` to any folder on the USB drive. Open the Ultimate menu and press **F2** to check these settings.

   | Ultimate menu | Setting | Value |
   | --- | --- | --- |
   | C64 and Cartridge Settings | RAM Expansion Unit | **Enabled** |
   | C64 and Cartridge Settings | REU Size | **16 MB** |
   | U64 Specific Settings | Turbo Control | **C64U Turbo Registers** (called U64 Turbo Registers on some firmware) |

2. In the Ultimate file browser, select **`MODEL.REU`**, press **RETURN**, and choose **Load into REU**. Acknowledge the completion message.
3. Select **`PROBE.PRG`** and choose **Run**. The startup screen should say **Preloaded REU model verified**. Type `what is 7 times 8` and press **RETURN**. The expected answer is `7 times 8 is 56.`

The program selects and checks **64 MHz** at startup. You can run the PRG again while the same model remains in REU. Reload the model after powering off or using the REU for another program. Save any open work before running the PRG.

## If startup fails

If the console asks you to load the model, go back to the Ultimate menu and select **Load into REU** for `MODEL.REU`, then run `PROBE.PRG` again. Keep the `.REU` extension so the file browser offers the correct action. The verified model file is 380,995 bytes with SHA-256 `ba89630a6bb1fd2d385e6daeae6bbc27a919996703e12e4beb4ab06136f61a1b`. The tested firmware was 3.14 with FPGA 121 and core 1.47.

Once the console returns to the question field, you can try `what is the capital of peru` without loading the model again. Use **DEL** to erase a character. Physical RUN/STOP cancellation and retry are in the [future-version notes](FUTURE.md).

[Original Tiny 2.1 for Pentium/486 DOS](https://github.com/WollyMonjac/Tiny-2.1)
