"""Fetch and verify the original source and model into the private reference folder."""
import hashlib
from pathlib import Path
from urllib.request import urlopen

from tools.model import MODEL_SHA

COMMIT = "1d5cf54677addf188a090ca1c91acb3d02989a1d"
BASE = f"https://raw.githubusercontent.com/WollyMonjac/Tiny-2.1/{COMMIT}"
FILES = {
    "TINY.C": "1615cc7db53d758bbfa538484c99e4d925b9d51da89f2fb90397862e7abc85db",
    "TINY.BIN": MODEL_SHA,
}


def fetch(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        path = destination / name
        if path.exists():
            data = path.read_bytes()
        else:
            with urlopen(f"{BASE}/{name}", timeout=30) as response:
                data = response.read()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise ValueError(f"{path} has SHA-256 {digest}, expected {expected}")
        if not path.exists():
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_bytes(data)
            temporary.replace(path)
        print(f"{name}: {len(data):,} bytes, verified SHA-256 {digest}")


if __name__ == "__main__":
    fetch(Path("reference"))
