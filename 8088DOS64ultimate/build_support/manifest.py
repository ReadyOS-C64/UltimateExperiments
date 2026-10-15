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
for pattern in ("Makefile", "build.zig", "build_support/*.py", "src/*.s", "include/*.inc", "cfg/*.cfg", "tests/host/*", "tests/fixtures/*", "tests/tooling/*.py", "reference/*.img", "build/*.prg", "build/*overlay*.bin", "build/*overlay*.json", "build/*resident.prg*.bin"):
    for path in sorted(Path().glob(pattern)):
        if path.is_file():
            report["files"][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
pin = json.loads(Path("third_party/peddle/UPSTREAM.json").read_text())
for entry in pin["files"]:
    path = Path("third_party/peddle")/entry["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise SystemExit(f"Vendored Peddle changed: {path}")
report["peddle_commit"] = pin["commit"]
corpus_pin=Path("third_party/sst8088/UPSTREAM.json")
if corpus_pin.exists():
    corpus=json.loads(corpus_pin.read_text())
    fixture=Path(corpus["fixture"])
    if hashlib.sha256(fixture.read_bytes()).hexdigest()!=corpus["fixture_sha256"]:
        raise SystemExit("Pinned 8088 fixture changed; regenerate from the declared upstream pin")
    license_hash=next(f["sha256"] for f in corpus["source_files"] if f["path"]=="LICENSE")
    if hashlib.sha256(Path("third_party/sst8088/LICENSE").read_bytes()).hexdigest()!=license_hash:
        raise SystemExit("Pinned 8088 license changed")
    report["8088_corpus_commit"]=corpus["commit"]
Path("build/manifest.json").write_text(json.dumps(report, indent=2)+"\n")
