"""Package a previously built REU console and its matching raw images."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import json

from probe.build import ROOT, digest

PROGRAM = "C64LLM.PRG"
IMAGES = ("TINY21.REU", "C64PROGINFO.REU", "E2JROMAJI.REU")


def package(bundle, output):
    manifest = json.loads((bundle / "bundle.json").read_text())
    program = bundle / PROGRAM
    if digest(program) != manifest.get("prg_sha256"):
        raise ValueError("PRG differs from the REU build manifest")
    for name in IMAGES:
        image = bundle / name
        if image.stat().st_size != 1 << 20 or digest(image) != manifest["reu_images"].get(name):
            raise ValueError(f"{name} differs from the REU build manifest")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in (PROGRAM, *IMAGES):
            archive.write(bundle / name, name)
        archive.write(ROOT / "docs/REU.md", "README.md")
        archive.write(ROOT / "LICENSE", "LICENSE")
        archive.write(ROOT / "training/LICENSE.tiny21-language", "LICENSE-TINY21.txt")
        archive.write(ROOT / "training/LICENSE.c64-dungeon", "LICENSE-C64-DUNGEON.txt")
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("package CRC verification failed")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(package(args.bundle, args.out))
