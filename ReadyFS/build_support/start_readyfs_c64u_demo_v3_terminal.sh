#!/usr/bin/env bash
set -euo pipefail
readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_id="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_DEMO_OUT:-$readyfs_root/logs/readyfs_c64u/demo-v3-$run_id}"
mkdir -p "$out_dir"
# Keep Terminal's submitted command short; long interactive input can lose its
# trailing bytes while a new shell initializes. Store exact shell-quoted values.
launch_script="$out_dir/terminal-run.sh"
{
  printf '#!/usr/bin/env bash\nset -euo pipefail\n'
  printf 'export READYFS_BATCH_BASELINE=%q\n' "${READYFS_BATCH_BASELINE:-0}"
  printf 'export READYFS_SD2IEC_IMAGE_RUN=%q\n' "${READYFS_SD2IEC_IMAGE_RUN:-}"
  printf 'export READYFS_SD2IEC_OWNED=%q\n' "${READYFS_SD2IEC_OWNED:-}"
  printf 'export READYFS_DEMO_ARTIFACTS=%q\n' "${READYFS_DEMO_ARTIFACTS:-$readyfs_root/artifacts/readyfs}"
  printf 'export READYFS_SD2IEC_BASELINE=%q\n' "${READYFS_SD2IEC_BASELINE:-0}"
  printf 'export READYFS_DEMO_PREFLIGHT=%q\n' "${READYFS_DEMO_PREFLIGHT:-0}"
  printf 'export READYFS_DEMO_FROM=%q\n' "${READYFS_DEMO_FROM:-1}"
  printf 'export READYFS_DEMO_ATTACH_LIVE=%q\n' "${READYFS_DEMO_ATTACH_LIVE:-0}"
  printf 'export READYFS_DEMO_OUT=%q\n' "$out_dir"
  printf 'export C64U_HOST=%q\n' "${C64U_HOST:-10.0.0.79}"
  printf 'exec %q %q >> %q 2>&1\n' \
    '/Users/karlprosserpp/dev/c64projects/skyleapgame/c64/.venv/bin/python' \
    "$readyfs_root/build_support/run_readyfs_c64u_demo_v3.py" "$out_dir/terminal-launch.txt"
} > "$launch_script"
/usr/bin/osascript - "$launch_script" <<'APPLESCRIPT'
on run argv
  tell application "Terminal" to do script (" /bin/bash " & quoted form of (item 1 of argv))
end run
APPLESCRIPT
printf '%s\n' "$out_dir"
