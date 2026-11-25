# C64 LLM v0.8 REU edition

[Download the REU edition ZIP](https://github.com/ReadyOS-C64/UltimateExperiments/releases/download/v0.8-reu/C64LLM-v0.8-REU.zip)

Run the three C64 LLM models in VICE or on a C64 with a **compatible REU of
at least 1 MiB** and a way to restore an image into it. The console tests the
REU, identifies the image at address zero, and checks its CRC before running
inference. The ZIP contains `C64LLM.PRG` and three ready-to-attach REU images.

## Start in VICE

1. Unzip the package. In VICE's RAM Expansion Module settings, enable the
   REU, set its size to **1024 KiB**, and set the REU image filename to
   `TINY21.REU`. Turn off writing back to the image file.
2. Autostart `C64LLM.PRG`. Wait for **Model ready.** and confirm
   **Model: Tiny 2.1**. You can start with any of the three images.
3. Type a prompt and press **RETURN**. Try `what is 7 times 8`.

From a terminal in the unzipped folder, the same setup is:

```sh
x64sc -reu -reusize 1024 -reuimage TINY21.REU +reuimagerw \
  -autostartprgmode 1 -warp -autostart C64LLM.PRG
```

Enable **Warp mode** in VICE to shorten the wait. On a stock 1 MHz C64, even
short replies can take many minutes. The model generates one character at a
time. [VICE REU settings and flags](https://vice-emu.sourceforge.io/vice_7.html)

On hardware, restore one of the raw images to REU address **$000000** using
your REU loader. Load the PRG like any BASIC program and run it.

## Switch models

| Key | Model | REU image |
| --- | --- | --- |
| **F1** | Tiny 2.1 | `TINY21.REU` |
| **F3** | C64PROGINFO | `C64PROGINFO.REU` |
| **F5** | English to Japanese in spaced romaji | `E2JROMAJI.REU` |

1. While the console is ready, press **F1**, **F3**, or **F5**. The screen
   names the image to attach.
2. In VICE, change the **REU image filename** in the REU settings. On hardware,
   restore the requested image to REU address **$000000**.
3. Return to the console and press **RETURN** to verify the image. If
   changing it restarted the C64, run `C64LLM.PRG` again. It recognizes the
   newly loaded image at startup.
4. Wait for **Model ready.** before typing. **DEL** edits a prompt. Hold
   **RUN/STOP** during generation to cancel it.

![The REU edition asks for E2JROMAJI.REU in VICE](https://readyos-c64.github.io/UltimateExperiments/tiny21/screenshots/reu-vice-switch.png)

## Try the three models

| Model | Type this | Expected reply |
| --- | --- | --- |
| Tiny 2.1 | `what is 7 times 8` | `7 times 8 is 56.` |
| C64PROGINFO | `what cpu does the c64 use` | `A MOS 6510.` |
| English to Japanese | `i ate an apple` | `watashi wa ringo o tabemashita` |
| English to Japanese | `this is a book` | `kore wa hon desu` |
| English to Japanese | `i don't want to eat an apple` | `watashi wa ringo o tabetakunai desu` |

For Japanese, type the English sentence directly and press **RETURN**.
[More Japanese prompts and the video demo](https://readyos-c64.github.io/UltimateExperiments/tiny21/#try-english-to-japanese)

## When an image fails verification

Check that the REU is enabled and that the file is restored at address zero.
If the console reports a different model, it displays the model it found
and keeps asking for the requested image. A corrupt image is rejected.
After replacing the image, press **RETURN** to recheck.

VICE 3.10 verified all three example answers, in-session model switching,
and rejection of disabled and undersized REUs and invalid images. The
packaged PRG and images match the tested files.

[Source for the REU edition](https://github.com/ReadyOS-C64/UltimateExperiments/tree/v0.8-reu/Tiny21) ·
[Original Tiny 2.1 for Pentium/486 DOS](https://github.com/WollyMonjac/Tiny-2.1)
