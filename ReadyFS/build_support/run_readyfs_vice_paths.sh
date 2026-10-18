#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_paths}"
resolved_plan="$out_dir/readyfs_vice_paths.resolved.yaml"

cd "$readyfs_root"
make readyfs
mkdir -p "$out_dir"
python3 - build_support/readyfs_vice_paths.yaml "$resolved_plan" <<'PY'
from pathlib import Path
import sys

source, output = map(Path, sys.argv[1:])
text = source.read_text(encoding="utf-8")
# Several assertions intentionally match text printed by an immediately
# preceding command. Give the C64 time to render its following prompt before
# injecting the next sequence, or a stale match can concatenate two commands.
text = text.replace("post_delay_s: 0.2", "post_delay_s: 1.0")
output.write_text(text, encoding="utf-8")
PY
dotnet run --project "$project" -- run-vice-plan \
  --plan "$resolved_plan" --no-tui \
  | tee "$out_dir/harness.log"
