#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_floppy_formats}"
d64="$readyfs_root/artifacts/readyfs/readyfs-empty.d64"
d71="$readyfs_root/artifacts/readyfs/readyfs-empty.d71"

cd "$readyfs_root"
make readyfs
c1541 -format "readyfs d64,rf" d64 "$d64"
c1541 -format "readyfs d71,rf" d71 "$d71" \
  -write "$readyfs_root/artifacts/readyfs/readyfs.prg" readyfs
mkdir -p "$out_dir"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_floppy_formats.yaml --no-tui \
  | tee "$out_dir/harness.log"
