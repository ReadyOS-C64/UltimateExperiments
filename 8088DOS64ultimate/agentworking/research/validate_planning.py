#!/usr/bin/env python3
"""Validate planning links, budgets, inventory, and ignore policy; not emulator tests."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

project = Path(__file__).resolve().parents[2]
errors = []
checked_links = 0
markdowns = sorted(project.rglob("*.md"))
for path in markdowns:
    if "scratch" in path.parts or "runs" in path.parts:
        continue
    text = path.read_text()
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if re.match(r"[a-z]+://", target) or target.startswith("#"):
            continue
        target = target.split("#", 1)[0].strip("<>")
        checked_links += 1
        if not (path.parent / target).exists():
            errors.append(f"Missing link: {path.relative_to(project)} -> {target}")

memory = (project / "docs/MEMORY.md").read_text()
host = [(int(a, 16), int(b, 16), int(n.replace(",", ""))) for a, b, n in
        re.findall(r"\| `([0-9A-F]{4})–([0-9A-F]{4})` \| ([0-9,]+) \|", memory)]
reu = [(int(a, 16), int(b, 16)) for a, b in
       re.findall(r"\| `([0-9A-F]{6})–([0-9A-F]{6})` \|", memory)]

def verify_ranges(label, ranges, size):
    cursor = 0
    for row in ranges:
        start, end = row[:2]
        if start != cursor or end < start:
            errors.append(f"{label} gap/overlap at {start:x}")
        if len(row) == 3 and row[2] != end - start + 1:
            errors.append(f"{label} wrong stated bytes at {start:x}")
        cursor = end + 1
    if cursor != size:
        errors.append(f"{label} wrong total {cursor}")

verify_ranges("host", host, 65536)
verify_ranges("REU", reu, 16777216)
if 0x4000 // 16384 != 0x6000 // 16384:
    errors.append("VIC matrix/bitmap bank mismatch")

manifest = json.loads((project / "agentworking/research/reference-images.json").read_text())
image_checks = []
for item in manifest["images"]:
    path = project / item["path"]
    same = hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    image_checks.append({"path": item["path"], "matches_recorded_hash": same})
    if not same:
        errors.append(f"Reference image changed: {path.name}")
fresh = subprocess.run([sys.executable, str(project / "agentworking/research/inspect_reference_images.py")],
                       capture_output=True, text=True, check=True)
if json.loads(fresh.stdout) != manifest:
    errors.append("Inventory is not reproducible")

checks = {}
for name in ["agentworking/STATUS.md", "agentworking/research/reference-images.json", "agentworking/scratch/test.tmp"]:
    result = subprocess.run(["git", "check-ignore", "-q", name], cwd=project)
    checks[name] = result.returncode == 0
    if result.returncode not in (0, 1):
        errors.append(f"git check-ignore failed: {name}")
if checks["agentworking/STATUS.md"] or checks["agentworking/research/reference-images.json"]:
    errors.append("Planning records remain ignored")
if not checks["agentworking/scratch/test.tmp"]:
    errors.append("Scratch is not ignored")

proof = json.loads((project / "agentworking/research/d81-container-proof.json").read_text())
if not proof["byte_identical"]:
    errors.append("D81 experiment did not preserve bytes")
report = {"scope": "planning-artifact checks only, no emulator/runtime validation",
          "markdown_files": len(markdowns), "local_links_checked": checked_links,
          "host_bytes": sum(end-start+1 for start,end,_ in host),
          "reu_bytes": sum(end-start+1 for start,end in reu),
          "reference_images": image_checks, "inventory_reproducible": json.loads(fresh.stdout) == manifest,
          "ignore_policy": checks, "d81_container_byte_identical": proof["byte_identical"],
          "errors": errors, "passed": not errors}
(project / "agentworking/research/planning-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
raise SystemExit(bool(errors))
