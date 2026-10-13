#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_id="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_SOFTPATH_OUT:-$readyfs_root/logs/readyfs_c64u/softpath-readonly-$run_id}"
launch_log="$out_dir/terminal-launch.txt"
suite="$readyfs_root/build_support/run_readyfs_softpath_probe_c64u.sh"

mkdir -p "$out_dir"
terminal_command=" READYFS_ROOT='$readyfs_root' READYFS_SOFTPATH_OUT='$out_dir' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$suite' >> '$launch_log' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
