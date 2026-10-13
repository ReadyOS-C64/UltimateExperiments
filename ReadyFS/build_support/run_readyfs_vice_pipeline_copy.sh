#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_pipeline_copy}"

cd "$readyfs_root"
make readyfs
mkdir -p "$out_dir"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_pipeline_copy.yaml --no-tui \
  | tee "$out_dir/harness.log"

run_dir="$(sed -n 's/.*"RunDir": "\([^"]*\)".*/\1/p' \
  "$out_dir/harness.log" | tail -1)"
reu_image="$run_dir/dumps/reu_readyfs_pipeline_copy_full.img"
if [[ -n "$run_dir" && -f "$reu_image" ]]; then
  python3 build_support/readyfs_journal_report.py "$reu_image" \
    --reu-bank 255 --reu-offset 0x2900 \
    --json "$run_dir/readyfs-pipeline-journal.json" \
    --markdown "$run_dir/readyfs-pipeline-journal.md"
  python3 build_support/readyfs_action_report.py "$reu_image" \
    --reu-bank 255 --reu-offset 0xA300 \
    --json "$run_dir/readyfs-pipeline-action.json" \
    --markdown "$run_dir/readyfs-pipeline-action.md"
fi
