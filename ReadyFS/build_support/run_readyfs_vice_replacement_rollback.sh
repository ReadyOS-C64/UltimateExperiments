#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_replacement_rollback}"
source_image="$readyfs_root/artifacts/readyfs/readyfs-rollback-source.d71"
target_image="$readyfs_root/artifacts/readyfs/readyfs-rollback-target.d64"
readyfs="$readyfs_root/artifacts/readyfs/readyfs.prg"
seed="$readyfs_root/artifacts/readyfs/readyfs-match.prg"

cd "$readyfs_root"
make readyfs
c1541 -format "rollback src,rf" d71 "$source_image" \
  -write "$readyfs" readyfs -write "$seed" rfmatch
c1541 -format "rollback dst,rf" d64 "$target_image" \
  -write "$seed" old \
  -write "$readyfs" fill1 -write "$readyfs" fill2 -write "$readyfs" fill3
mkdir -p "$out_dir"
c1541 "$target_image" -list > "$out_dir/target-before.txt"
baseline_free="$(awk 'tolower($0) ~ /blocks free/ { print $1; exit }' "$out_dir/target-before.txt")"
if [[ ! "$baseline_free" =~ ^[0-9]+$ ]]; then
  printf 'could not measure rollback fixture free blocks\n' >&2
  exit 1
fi
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_replacement_rollback.yaml --no-tui \
  | tee "$out_dir/harness.log"
manifest_path="$(sed -n 's/.*"Manifest": "\(.*\)".*/\1/p' "$out_dir/harness.log" | tail -1)"
if [[ -z "$manifest_path" || ! -f "$manifest_path" ]]; then
  printf 'could not locate rollback harness manifest\n' >&2
  exit 1
fi
run_dir="$(dirname "$manifest_path")"
screen_text="$run_dir/screen_decoded/rf_ui_45_no_stage_artifact.txt"
if [[ ! -f "$screen_text" ]]; then
  printf 'rollback harness did not capture the final directory screen\n' >&2
  exit 1
fi
grep -qi "FREE: ${baseline_free} C64 BLOCKS" "$screen_text"
c1541 "$target_image" -list > "$out_dir/target-after.txt"
grep -qi '"old"' "$out_dir/target-after.txt"
grep -qi "${baseline_free} blocks free" "$out_dir/target-after.txt"
if grep -Eqi '"rf~[0-9a-f][0-9a-f]"' "$out_dir/target-after.txt"; then
  printf 'rollback left a staged RF~ file\n' >&2
  exit 1
fi
