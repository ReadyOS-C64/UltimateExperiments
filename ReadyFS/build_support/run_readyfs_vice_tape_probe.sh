#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_tape_probe}"
tap="$readyfs_root/artifacts/readyfs/readyfs-tape-test.tap"

cd "$readyfs_root"
mkdir -p "$out_dir" "$(dirname "$tap")"
cl65 -t c64 -Os -o artifacts/readyfs/readyfs-tape-probe.prg \
  src/apps/readyfs/readyfs_tape_probe.c
python3 build_support/readyfs_tap_fixture.py "$tap" --create
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_tape_probe.yaml --no-tui \
  | tee "$out_dir/harness.log"
python3 build_support/readyfs_tap_fixture.py "$tap" --require-data \
  | tee "$out_dir/tap-verify.log"
