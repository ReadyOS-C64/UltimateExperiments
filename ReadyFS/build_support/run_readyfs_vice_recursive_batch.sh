#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_recursive_batch}"
target_disk="$readyfs_root/artifacts/readyfs/readyfs-recursive-target.d81"
resolved_plan="$out_dir/readyfs_vice_recursive_batch.resolved.yaml"

cd "$readyfs_root"
make readyfs
c1541 -format "readyfs target,rf" d81 "$target_disk"
mkdir -p "$out_dir"
# BSS moves as resident features evolve. Resolve the two diagnostic ranges
# from linker labels on every run instead of trusting stale absolute values.
python3 - build_support/readyfs_vice_recursive_batch.yaml \
  artifacts/readyfs/readyfs-overlay.lbl "$resolved_plan" <<'PY'
from pathlib import Path
import re
import sys

source, labels_path, output = map(Path, sys.argv[1:])
labels = labels_path.read_text(encoding="utf-8")

def address(name: str) -> int:
    match = re.search(rf"^al ([0-9A-F]{{6}}) \._{name}$", labels, re.M)
    if match is None:
        raise SystemExit(f"missing ReadyFS linker label: {name}")
    return int(match.group(1), 16)

session = address("reu_available")
if address("overlay_available") != session + 1:
    raise SystemExit("ReadyFS session admission flags are no longer contiguous")
overlay = address("plan_loaded")
expected = ["help_loaded", "backend_loaded", "drive_loaded",
            "utility_loaded", "batch_loaded"]
if [address(name) for name in expected] != list(range(overlay + 1, overlay + 6)):
    raise SystemExit("ReadyFS overlay admission flags are no longer contiguous")
text = source.read_text(encoding="utf-8")
text = re.sub(
    r"(label: readyfs_session_flags, start:) 0x[0-9A-Fa-f]+, end: 0x[0-9A-Fa-f]+",
    rf"\1 0x{session:04X}, end: 0x{session + 1:04X}", text)
text = re.sub(
    r"(label: readyfs_overlay_flags, start:) 0x[0-9A-Fa-f]+, end: 0x[0-9A-Fa-f]+",
    rf"\1 0x{overlay:04X}, end: 0x{overlay + 5:04X}", text)
output.write_text(text, encoding="utf-8")
PY
dotnet run --project "$project" -- run-vice-plan \
  --plan "$resolved_plan" --no-tui \
  | tee "$out_dir/harness.log"

run_dir="$(sed -n 's/.*"RunDir": "\([^"]*\)".*/\1/p' \
  "$out_dir/harness.log" | tail -1)"
session_flags="$run_dir/stages/stop_capability_memory/readyfs_session_flags.bin"
overlay_flags="$run_dir/stages/stop_capability_memory/readyfs_overlay_flags.bin"
if [[ -n "$run_dir" && -f "$session_flags" && -f "$overlay_flags" ]]; then
  python3 - "$session_flags" "$overlay_flags" <<'PY'
from pathlib import Path
import sys

session = Path(sys.argv[1]).read_bytes()
overlay = Path(sys.argv[2]).read_bytes()
if session != b"\x01\x01":
    raise SystemExit("ReadyFS post-stop REU/overlay admission flags changed")
if overlay != b"\x01" * 4 + b"\x07\x01":
    raise SystemExit("ReadyFS post-stop overlay capabilities were stack-clobbered")
print("ReadyFS post-stop capability memory: PASS")
PY
fi
reu_image="$run_dir/dumps/reu_readyfs_recursive_batch_copy_full.img"
if [[ -n "$run_dir" && -f "$reu_image" ]]; then
  python3 build_support/readyfs_journal_report.py "$reu_image" \
    --reu-bank 255 --reu-offset 0x2900 \
    --expect-mode 1 --expect-count 2 --expect-completed 2 --expect-failed 0 \
    --expect-action copy-file --expect-action copy-file \
    --expect-stem RFZA --expect-stem RFZB \
    --json "$run_dir/readyfs-recursive-batch-journal.json" \
    --markdown "$run_dir/readyfs-recursive-batch-journal.md"
fi

continue_reu="$run_dir/dumps/reu_readyfs_recursive_batch_continue_full.img"
if [[ -n "$run_dir" && -f "$continue_reu" ]]; then
  python3 build_support/readyfs_journal_report.py "$continue_reu" \
    --reu-bank 255 --reu-offset 0x2900 \
    --expect-mode 1 --expect-count 2 --expect-completed 1 --expect-failed 1 \
    --expect-action copy-file --expect-action copy-file \
    --expect-stem RFCA --expect-stem RFCB \
    --json "$run_dir/readyfs-recursive-continue-journal.json" \
    --markdown "$run_dir/readyfs-recursive-continue-journal.md"
fi
