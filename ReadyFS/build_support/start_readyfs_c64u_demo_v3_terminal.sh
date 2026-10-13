#!/usr/bin/env bash
set -euo pipefail
readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_id="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_DEMO_OUT:-$readyfs_root/logs/readyfs_c64u/demo-v3-$run_id}"
mkdir -p "$out_dir"
terminal_command=" READYFS_DEMO_PREFLIGHT='${READYFS_DEMO_PREFLIGHT:-0}' READYFS_DEMO_FROM='${READYFS_DEMO_FROM:-1}' READYFS_DEMO_ATTACH_LIVE='${READYFS_DEMO_ATTACH_LIVE:-0}' READYFS_DEMO_OUT='$out_dir' C64U_HOST='${C64U_HOST:-10.0.0.79}' '/Users/karlprosserpp/dev/c64projects/skyleapgame/c64/.venv/bin/python' '$readyfs_root/build_support/run_readyfs_c64u_demo_v3.py' >> '$out_dir/terminal-launch.txt' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
