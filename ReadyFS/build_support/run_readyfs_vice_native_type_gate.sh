#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
out_dir="${READYFS_VICE_OUT_DIR:-$readyfs_root/logs/readyfs_vice_native_type_gate}"
boot_disk="$readyfs_root/artifacts/readyfs/readyfs-native-type-boot.d71"
source_disk="$readyfs_root/artifacts/readyfs/readyfs-native-type-source.d71"

cd "$readyfs_root"
make readyfs
c1541 -format "readyfs type,rf" d71 "$boot_disk" \
  -write artifacts/readyfs/readyfs-overlay.prg readyfs-overlay \
  -write artifacts/readyfs/readyfs-match.prg rfmatch \
  -write artifacts/readyfs/readyfs-plan.prg rfplan \
  -write artifacts/readyfs/readyfs-help.prg rfhelp \
  -write artifacts/readyfs/readyfs-backend.prg rfbackend \
  -write artifacts/readyfs/readyfs-cmdpath.prg rfcmdpath \
  -write artifacts/readyfs/readyfs-drive.prg rfdrive \
  -write artifacts/readyfs/readyfs-utility.prg rfutil \
  -write artifacts/readyfs/readyfs-tree.prg rftree \
  -write artifacts/readyfs/readyfs-content.prg rfcontent \
  -write artifacts/readyfs/readyfs-batch.prg rfbatch \
  -write artifacts/readyfs/readyfs-recursive.prg rfrecur \
  -write artifacts/readyfs/readyfs-tape.prg rftape
python3 build_support/create_readyfs_rel_fixture.py "$source_disk"
mkdir -p "$out_dir"
dotnet run --project "$project" -- run-vice-plan \
  --plan build_support/readyfs_vice_native_type_gate.yaml --no-tui \
  | tee "$out_dir/harness.log"
