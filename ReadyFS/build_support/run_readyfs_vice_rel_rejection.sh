#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_rel_rejection}"
boot="$readyfs_root/artifacts/readyfs/readyfs-rel-boot.d71"
source_fixture="$readyfs_root/artifacts/readyfs/readyfs-rel-source.d71"

cd "$readyfs_root"
make readyfs
c1541 -format "readyfs rel,rf" d71 "$boot" \
  -write "$readyfs_root/artifacts/readyfs/readyfs.prg" readyfs
python3 build_support/create_readyfs_rel_fixture.py "$source_fixture"
mkdir -p "$out_dir"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_rel_rejection.yaml --no-tui \
  | tee "$out_dir/harness.log"
