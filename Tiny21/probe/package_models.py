"""Package both prepared models and a matched native console for local installation."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from probe.build import ROOT, build

INSTALL = '''# Tiny21 and C64PROGINFO for the C64 Ultimate

Set the Ultimate to **64 MHz turbo**, **REU enabled and 16 MB**, and
**Command Interface enabled** for Ultimate DOS to load the model files.
Select C64U Turbo Registers for Turbo Control. The program checks 64 MHz
on startup.

1. Unzip the three files into `{folder}` on the Ultimate's drive.
2. In the Ultimate menu, browse to that folder and run `PROBE.PRG`.
3. Press **F1** for Tiny 2.1 or **F3** for C64PROGINFO. Type a question and
   press RETURN. Hold RUN/STOP during generation to cancel.

`MODEL.BIN` and `C64PROGINFO.BIN` are ready to use. The console loads each
model on first use and keeps it in a separate REU slot. When it finds the
expected image already there, it verifies and reuses it.

Try `what is 7 times 8` in Tiny 2.1. Try `what cpu does the c64 use`,
`show assembler code to set border to red`, or
`show basic code to clear the screen and print ready` in C64PROGINFO.
C64PROGINFO prints BASIC and assembler with line breaks. The small model
can give incorrect technical details or code. Check results before use.

The original Tiny 2.1 model is by WollyMonjac.
https://github.com/WollyMonjac/Tiny-2.1

C64PROGINFO adapts jaydarkseed757's c64-dungeon training tooling.
https://github.com/jaydarkseed757/c64-dungeon
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
