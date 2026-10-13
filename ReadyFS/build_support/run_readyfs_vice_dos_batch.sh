#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readyfs_root="$(cd "$script_dir/.." && pwd)"
harness_root="${VICE_TASKS_REPO:-$readyfs_root/../../agenticdevharness}"
project="$harness_root/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj"
cd "$readyfs_root"
make readyfs
# Both independent VICE processes share this disposable copy. The second
# starts with an empty environment and loads the first process's saved config.
cp artifacts/readyfs/readyfs-overlay-lab.d81 artifacts/readyfs/readyfs-dos-test.d81
# The harness defaults to 16 MiB. This local launcher also proves the
# documented 1 MiB minimum without changing the shared harness project.
real_vice="$(command -v x64sc)"
wrapper_dir="$(mktemp -d "${TMPDIR:-/tmp}/readyfs-reu.XXXXXX")"
trap 'rm -rf "$wrapper_dir"' EXIT
export READYFS_REAL_VICE="$real_vice"
export READYFS_REU_KIB=1024
cat > "$wrapper_dir/x64sc" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
args=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        -reusize) args+=("$1" "$READYFS_REU_KIB"); shift 2 ;;
        -reuimage)
            python3 - "$2" "$READYFS_REU_KIB" <<'PYREU'
import sys
from pathlib import Path
image = Path(sys.argv[1])
if image.exists():
    with image.open('r+b') as target:
        target.truncate(int(sys.argv[2]) * 1024)
PYREU
            args+=("$1" "$2"); shift 2 ;;
        *) args+=("$1"); shift ;;
    esac
done
exec "$READYFS_REAL_VICE" "${args[@]}"
WRAPPER
chmod +x "$wrapper_dir/x64sc"
export PATH="$wrapper_dir:$PATH"
for plan in readyfs_vice_dos_batch readyfs_vice_dos_config_fresh; do
    dotnet run --project "$project" -- run-vice-plan --plan "build_support/$plan.yaml" --no-tui
    python3 - "$readyfs_root/logs/vice_auto_latest/manifest.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8-sig') as source:
    result = json.load(source)
if result.get('status', result.get('Status')) != 'success':
    raise SystemExit('VICE scripting plan did not pass; inspect the retained manifest')
PY
done
