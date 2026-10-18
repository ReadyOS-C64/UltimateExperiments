#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_format}"
disposable="$readyfs_root/artifacts/readyfs/readyfs-format-disposable.d81"

cd "$readyfs_root"
make readyfs
# This image is created solely for this plan and is the only formatted media.
c1541 -format "format source,aa" d81 "$disposable"
mkdir -p "$out_dir"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_format.yaml --no-tui \
  | tee "$out_dir/harness.log"
