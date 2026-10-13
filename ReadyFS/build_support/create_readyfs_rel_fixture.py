#!/usr/bin/env python3
"""Create the standalone D71 REL fixture used by ReadyFS UI tests."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("disk", type=Path)
    args = parser.parse_args()

    args.disk.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="readyfs-rel-") as temp_name:
        payload = Path(temp_name) / "rfreltest.bin"
        payload.write_bytes(
            b"READYFS REL TYPE-GATE FIXTURE".ljust(32, b"\x00")
        )
        subprocess.run(
            [
                "c1541",
                "-format",
                "readyfs rel,rf",
                "d71",
                str(args.disk),
                "-write",
                str(payload),
                "rfrel.rel,l,32",
            ],
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
