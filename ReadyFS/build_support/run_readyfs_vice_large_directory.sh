#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_large_directory}"
fixture="$readyfs_root/artifacts/readyfs/readyfs-large-directory.d81"
seed="$readyfs_root/artifacts/readyfs/readyfs-match.prg"

cd "$readyfs_root"
make readyfs
cp "$readyfs_root/artifacts/readyfs/readyfs-overlay-lab.d81" "$fixture"
c1541_args=("$fixture")
for index in $(seq -w 1 40); do
  c1541_args+=(-write "$seed" "f$index")
done
c1541 "${c1541_args[@]}"
mkdir -p "$out_dir"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_large_directory.yaml --no-tui \
  | tee "$out_dir/harness.log"
