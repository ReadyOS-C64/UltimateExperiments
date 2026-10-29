#!/usr/bin/env python3
"""Create the deterministic public SuperEditor preview archive."""

from pathlib import Path
import hashlib
import json
import zipfile

from d81_image import D81Image


ROOT = Path(__file__).resolve().parents[1]
DISK = ROOT / "build/supereditor-runtime.d81"
CONTENT = ROOT / "build/runtime-disk-content.json"
OUTPUT = ROOT / "releases/SuperEditor-preview.zip"
FIXED_TIME = (2026, 10, 28, 0, 0, 0)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def member(name, data):
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info, data


def main():
    disk = DISK.read_bytes()
    if len(disk) != 819200:
        raise SystemExit("runtime D81 must be exactly 819200 bytes")
    proof = json.loads(CONTENT.read_text())
    if proof["disk_sha256"] != sha256(disk):
        raise SystemExit("runtime content proof does not match D81")
    image = D81Image(disk)
    names = {entry.name for entry in image.entries()}
    if b"SUPEREDITOR" not in names or b"GEOSFONTS" not in names:
        raise SystemExit("runtime D81 lacks editor or font pack")

    readme = """SuperEditor development preview
===================================

SuperEditor is a standalone PETSCII Markdown-lite editor for the Commodore 64,
written in 6510 assembly. This is a development preview, not a finished ReadyOS
application.

Requirements
------------
* PAL or NTSC Commodore 64 or compatible emulator
* 1581/D81 support on device 8
* REU enabled; 2 MiB supports the tested small-document workflow, while 16 MiB
  is recommended for larger documents and the full feature set

Start
-----
1. Attach SUPEREDITOR.D81 as an unpartitioned 1581 disk on device 8.
2. Enable the REU.
3. Enter:

   LOAD\"SUPEREDITOR\",8,1
   RUN

F1 opens menus, F6 opens the three-page help, F7 opens the typed command line,
and F8 cycles 40, 60, 80-column and GEOS-font views. CTRL-O opens a file and
CTRL-S saves. Files are raw PETSCII SEQ text with CR line endings.

The disk must remain mounted because editor modules and the data-only GEOS font
pack are loaded from it. The archive does not contain a GEOS system disk,
applications, executable font software, test probes or diagnostic artifacts.

Complete guide
--------------
https://readyos-c64.github.io/UltimateExperiments/supereditor/USER_GUIDE.html

Source and build instructions
-----------------------------
https://github.com/ReadyOS-C64/UltimateExperiments/tree/main/SuperEditor
""".encode("utf-8")
    build = {
        "schema": 1,
        "product": "SuperEditor",
        "channel": "development-preview",
        "disk": {
            "name": "SUPEREDITOR.D81",
            "bytes": len(disk),
            "sha256": sha256(disk),
            "directory_entries": len(names),
        },
        "runtime": {
            "editor_capsules": len(proof["editor_capsules"]),
            "font_pack_sha256": proof["inputs"]["files"]["build/geos-font-catalog/font-pack.bin"],
            "diagnostic_dependencies": 0,
        },
        "requirements": {
            "drive": "unpartitioned 1581/D81 on device 8",
            "reu_minimum_tested_small_document_mib": 2,
            "reu_recommended_mib": 16,
        },
        "qualification": "development preview; emulator-tested; wider standalone and physical-key qualification remain open",
    }
    build_bytes = (json.dumps(build, indent=2, sort_keys=True) + "\n").encode()
    sums = (
        f"{sha256(disk)}  SUPEREDITOR.D81\n"
        f"{sha256(readme)}  README.txt\n"
        f"{sha256(build_bytes)}  BUILD.json\n"
    ).encode()
    assets = {
        "README.txt": readme,
        "SUPEREDITOR.D81": disk,
        "BUILD.json": build_bytes,
        "SHA256SUMS": sums,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", compresslevel=9) as archive:
        for name in sorted(assets):
            info, data = member(name, assets[name])
            archive.writestr(info, data)
    temporary.replace(OUTPUT)
    with zipfile.ZipFile(OUTPUT) as archive:
        if set(archive.namelist()) != set(assets) or archive.testzip() is not None:
            raise SystemExit("release archive verification failed")
        for name, data in assets.items():
            if archive.read(name) != data:
                raise SystemExit(f"release member differs: {name}")
    print(json.dumps({"archive": str(OUTPUT), "archive_bytes": OUTPUT.stat().st_size,
                      "archive_sha256": sha256(OUTPUT.read_bytes()),
                      "disk": build["disk"]}, indent=2))


if __name__ == "__main__":
    main()
