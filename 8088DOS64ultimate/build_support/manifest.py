"""Capture tool, input, dependency, and output identity for reproducible tests."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser()
for tool in ("zig", "ca65", "ld65"):
    parser.add_argument("--"+tool, required=True)
args = parser.parse_args()
report = {"schema": 1, "tools": {}, "files": {}}
for name, command in vars(args).items():
    path = Path(shutil.which(command) or command).resolve()
    version = subprocess.run([str(path), "version" if name == "zig" else "--version"],
                             capture_output=True, check=True, text=True)
    report["tools"][name] = {"path": str(path), "version": (version.stdout+version.stderr).strip(),
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
for pattern in ("Makefile", "build.zig", "build_support/*.py", "src/*.s", "include/*.inc", "cfg/*.cfg", "tests/host/*", "tests/fixtures/*", "reference/*.img", "build/*.prg"):
    for path in sorted(Path().glob(pattern)):
        if path.is_file():
            report["files"][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
pin = json.loads(Path("third_party/peddle/UPSTREAM.json").read_text())
for entry in pin["files"]:
    path = Path("third_party/peddle")/entry["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise SystemExit(f"Vendored Peddle changed: {path}")
report["peddle_commit"] = pin["commit"]
Path("build/manifest.json").write_text(json.dumps(report, indent=2)+"\n")
