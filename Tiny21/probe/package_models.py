"""Package both prepared models and a matched native console for local installation."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from probe.build import ROOT, build

INSTALL = '''# C64 LLM - Little Language Model v0.7

This ZIP contains the console PRG and both prebuilt models.

## Install on the C64 Ultimate

**You need a C64 Ultimate with 64 MHz turbo support, an enabled 16 MB REU,
the Command Interface enabled, and a USB drive.** In the Ultimate settings,
set Turbo Control to **C64U Turbo Registers** (also called **U64 Turbo
Registers** on some firmware). The program selects and verifies 64 MHz.

1. Unzip the archive. Copy `PROBE.PRG`, `MODEL.BIN`, and
   `C64PROGINFO.BIN` into `{folder}` in the Ultimate file browser.
2. In the Ultimate menu, select `PROBE.PRG` and choose **Run**. The console
   starts with Tiny 2.1.
3. Press **F1** for **Tiny 2.1** or **F3** for **C64PROGINFO** when the
   console is ready. Wait for **Model ready.** and check the **Model:** line.
   Then type a question and press **RETURN**.

The console loads each model from USB as needed and reuses a verified copy
in REU. Keep the drive connected for first use and after powering off.
If a model fails to load, check the filenames, folder, and settings above.

## Use the console

Use **DEL** to edit your question. Hold **RUN/STOP** during generation until
**Cancelled. Ready.** appears to interrupt it. Each completed question stays
on screen with its answer until you start typing the next one.

- **Tiny 2.1** answers short general questions. Try `what is 7 times 8`.
- **C64PROGINFO** is trained on C64 hardware, registers, BASIC V2, and 6502
  assembly. Try `what cpu does the c64 use`,
  `show basic code to clear the screen and print ready`, or
  `show assembler code to set border to red`. Code answers can span lines.

Both are small models. Check unfamiliar technical details and generated code.

[Online guide and screenshots](https://readyos-c64.github.io/UltimateExperiments/tiny21/)

The port and C64PROGINFO are MIT-licensed. The package includes notices for
[WollyMonjac’s original Tiny 2.1](https://github.com/WollyMonjac/Tiny-2.1)
and [jaydarkseed757’s c64-dungeon training tooling](https://github.com/jaydarkseed757/c64-dungeon).
'''


def package(output, core_dir, tiny, programmer, remote):
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='tiny21-models-') as path:
        out = Path(path)
        build(out, remote, core_dir, interactive=True, model_image=tiny, second_model=programmer)
        with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for name in ('PROBE.PRG', 'MODEL.BIN', 'C64PROGINFO.BIN'):
                archive.write(out / name, name)
            archive.writestr('README.md', INSTALL.format(folder=remote))
            archive.write(ROOT / 'LICENSE', 'LICENSE')
            archive.write(ROOT / 'training/LICENSE.tiny21-language', 'LICENSE-TINY21.txt')
            archive.write(ROOT / 'training/LICENSE.c64-dungeon', 'LICENSE-C64-DUNGEON.txt')
        with ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError('package CRC verification failed')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--core-dir', type=Path, default=ROOT / 'build/group8')
    parser.add_argument('--tiny', type=Path, required=True)
    parser.add_argument('--programmer', type=Path, required=True)
    parser.add_argument('--remote', default='/USB1/TINY64-MODELS')
    args = parser.parse_args()
    print(package(args.out, args.core_dir, args.tiny, args.programmer, args.remote))
