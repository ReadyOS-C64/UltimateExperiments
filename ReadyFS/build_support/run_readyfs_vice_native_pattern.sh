#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_native_pattern}"
target_disk="$readyfs_root/artifacts/readyfs/readyfs-native-target.d81"

cd "$readyfs_root"
make readyfs
c1541 -format "readyfs native,rf" d81 "$target_disk"
mkdir -p "$out_dir"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_native_pattern.yaml --no-tui \
  | tee "$out_dir/harness.log"

run_dir="$(sed -n 's/.*"RunDir": "\([^"]*\)".*/\1/p' \
  "$out_dir/harness.log" | tail -1)"
copy_reu="$run_dir/dumps/reu_readyfs_native_copy_apply_full.img"
if [[ -n "$run_dir" && -f "$copy_reu" ]]; then
  python3 build_support/readyfs_journal_report.py "$copy_reu" \
    --reu-bank 255 --reu-offset 0x2900 \
    --expect-mode 1 --expect-count 2 --expect-completed 2 --expect-failed 0 \
    --expect-action copy-file --expect-action copy-file \
    --expect-stem RFNC1 --expect-stem RFNC2 \
    --json "$run_dir/readyfs-native-copy-journal.json" \
    --markdown "$run_dir/readyfs-native-copy-journal.md"
fi

move_reu="$run_dir/dumps/reu_readyfs_native_move_apply_full.img"
if [[ -n "$run_dir" && -f "$move_reu" ]]; then
  python3 build_support/readyfs_journal_report.py "$move_reu" \
    --reu-bank 255 --reu-offset 0x2900 \
    --expect-mode 2 --expect-count 1 --expect-completed 1 --expect-failed 0 \
    --expect-action move-file --expect-stem RFNM1 \
    --json "$run_dir/readyfs-native-move-journal.json" \
    --markdown "$run_dir/readyfs-native-move-journal.md"
fi
