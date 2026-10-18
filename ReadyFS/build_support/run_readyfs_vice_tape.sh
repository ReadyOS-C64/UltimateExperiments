#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_tape}"
tap="$readyfs_root/artifacts/readyfs/readyfs-tape-test.tap"
target="$readyfs_root/artifacts/readyfs/readyfs-tape-target.d64"

cd "$readyfs_root"
mkdir -p "$out_dir" "$(dirname "$tap")"
make readyfs
python3 build_support/readyfs_tap_fixture.py "$tap" --create
c1541 -format "readyfs tape,rf" d64 "$target"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_tape.yaml --no-tui \
  | tee "$out_dir/recording-harness.log"
python3 build_support/readyfs_tap_fixture.py "$tap" --require-data \
  | tee "$out_dir/tap-verify.log"
c1541 -format "readyfs tape,rf" d64 "$target"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_tape_readback.yaml --no-tui \
  | tee "$out_dir/readback-harness.log"
c1541 -attach "$target" -list | tee "$out_dir/target-directory.log"
rg -i 'tapout' "$out_dir/target-directory.log" >/dev/null
