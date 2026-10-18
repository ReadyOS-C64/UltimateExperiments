#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_editor}"
resolved_plan="$out_dir/readyfs_vice_editor.resolved.yaml"

cd "$readyfs_root"
make readyfs
mkdir -p "$out_dir"
# The resident BSS layout moves as bounded gateways are added. Resolve the
# editor buffer from the linker label on every run so this memory oracle tests
# the current binary rather than a stale absolute address.
python3 - build_support/readyfs_vice_editor.yaml \
  artifacts/readyfs/readyfs-overlay.lbl "$resolved_plan" <<'PY'
from pathlib import Path
import re
import sys

source, labels_path, output = map(Path, sys.argv[1:])
labels = labels_path.read_text(encoding="utf-8")
match = re.search(r"^al ([0-9A-F]{6}) \._line_buf$", labels, re.M)
if match is None:
    raise SystemExit("missing ReadyFS linker label: line_buf")
start = int(match.group(1), 16)
text = source.read_text(encoding="utf-8")
text, count = re.subn(
    r"(label: readyfs_line_255, start:) 0x[0-9A-Fa-f]+, end: 0x[0-9A-Fa-f]+",
    rf"\1 0x{start:04X}, end: 0x{start + 255:04X}", text)
if count != 1:
    raise SystemExit("ReadyFS editor memory range was not resolved exactly once")
output.write_text(text, encoding="utf-8")
PY
dotnet run --project "$project" -- run-vice-plan \
  --plan "$resolved_plan" --no-tui \
  | tee "$out_dir/harness.log"

run_dir="$(sed -n 's/.*"RunDir": "\([^"]*\)".*/\1/p' \
  "$out_dir/harness.log" | tail -1)"
line_dump="$run_dir/stages/rf_ui_05_line_255_memory/readyfs_line_255.bin"
if [[ -z "$run_dir" || ! -f "$line_dump" ]]; then
  echo "ReadyFS 255-byte line dump is missing" >&2
  exit 1
fi
python3 - "$line_dump" <<'PY'
from pathlib import Path
import sys

actual = Path(sys.argv[1]).read_bytes()
expected = b"UNKNOWN " + (b"A" * 234) + b"READYFS255END" + b"\x00"
if len(expected) != 256:
    raise SystemExit("ReadyFS editor oracle has the wrong expected length")
if actual != expected:
    mismatch = next(
        (index for index, pair in enumerate(zip(actual, expected))
         if pair[0] != pair[1]),
        min(len(actual), len(expected)),
    )
    raise SystemExit(
        f"ReadyFS 255-byte line mismatch at offset {mismatch}; "
        f"actual length={len(actual)} expected length={len(expected)}"
    )
print("ReadyFS 255-byte logical line memory: PASS")
PY
