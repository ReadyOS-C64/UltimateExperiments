#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_cmdpath}"

cd "$readyfs_root"
make readyfs
mkdir -p "$out_dir"
fixture_hash_before="$(shasum -a 256 artifacts/readyfs/readyfs-overlay-lab.d81 | awk '{print $1}')"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_cmdpath.yaml --no-tui \
  | tee "$out_dir/harness.log"
fixture_hash_after="$(shasum -a 256 artifacts/readyfs/readyfs-overlay-lab.d81 | awk '{print $1}')"
if [[ "$fixture_hash_before" != "$fixture_hash_after" ]]; then
  echo "ReadyFS cmdpath fixture changed during compatible-profile emulation" >&2
  exit 1
fi
echo "ReadyFS cmdpath fixture remained byte-identical"
