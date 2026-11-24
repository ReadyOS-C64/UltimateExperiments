# Download and run C64 LLM v0.7

[Download the v0.7 verification ZIP](../releases/Tiny21-v0.7-C64PROGINFO.zip)

This package passed in Peddle. The GitHub release is pending a check of this exact ZIP on a physical C64 Ultimate.

**Required hardware — a C64 Ultimate with 64 MHz turbo support, a 16 MB REU, and a USB drive.** Enable the RAM Expansion Unit and Command Interface before starting.

## Install and run

1. Unzip the archive. On the drive shown as **USB1** in the Ultimate menu, create **TINY64-MODELS** at the root. Copy **PROBE.PRG**, **MODEL.BIN**, and **C64PROGINFO.BIN** into that folder. The packaged PRG looks for the two model files at `/USB1/TINY64-MODELS` when it needs to load them.
2. Open the Ultimate menu and press **F2** to check the settings.

   | Ultimate menu | Setting | Value |
   | --- | --- | --- |
   | C64 and Cartridge Settings | RAM Expansion Unit | **Enabled** |
   | C64 and Cartridge Settings | REU Size | **16 MB** |
   | C64 and Cartridge Settings | Command Interface | **Enabled** |
   | U64 Specific Settings | Turbo Control | **C64U Turbo Registers** (called **U64 Turbo Registers** on some firmware) |

3. In the Ultimate file browser, select **PROBE.PRG** and choose **Run**. The program selects and verifies **64 MHz** at startup. It starts with Tiny 2.1 and loads `MODEL.BIN` through Ultimate DOS if needed.
4. Type `what is 7 times 8` and press **RETURN**. The expected answer is `7 times 8 is 56.`

Both model files are ready to use. The console checks each model's REU slot before loading from USB and reuses a verified resident copy. Keep the USB drive connected for a model's first use and after powering off.

## Switch models and ask questions

| Key | Model | Example question |
| --- | --- | --- |
| **F1** | **Tiny 2.1** for general short questions | `what is 7 times 8` |
| **F3** | **C64PROGINFO** for C64 hardware, BASIC V2, and 6502 assembly | `show assembler code to set border to red` |

Press the function key while the console is ready. Wait for **Model ready.** and check the **Model:** line. **RETURN** submits your question and **DEL** edits the prompt. To interrupt a running answer, hold **RUN/STOP** until **Cancelled. Ready.** appears. An answered question stays visible. Start typing to replace it with the next question.

C64PROGINFO can return code on multiple lines. It performs best with familiar wording. Check generated code and register details before using them.

## If a model fails to load

Check the folder, filenames, and settings above. If the first model fails, return to the Ultimate browser and run the PRG after correcting the setup. If a switch reports **Load failed. Current model kept.**, correct the setup and press the model key again.

| Packaged model | SHA-256 |
| --- | --- |
| `MODEL.BIN` | `ba89630a6bb1fd2d385e6daeae6bbc27a919996703e12e4beb4ab06136f61a1b` |
| `C64PROGINFO.BIN` | `439c2203b8f8084808c08de4f06249026feb91e262246054482d3f56d3ee0b2e` |

[Project overview and screenshots](../README.md) · [Technical details](TECHNICAL.md) · [Original Tiny 2.1 for Pentium/486 DOS](https://github.com/WollyMonjac/Tiny-2.1)
