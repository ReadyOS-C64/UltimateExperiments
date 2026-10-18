#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_id="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_MATRIX_OUT:-$readyfs_root/logs/readyfs_c64u/speed-matrix-$run_id}"
launch_log="$out_dir/terminal-launch.txt"
suite_script="$readyfs_root/build_support/run_readyfs_c64u_speed_matrix.sh"

mkdir -p "$out_dir"
# A sacrificial leading blank avoids a sporadic first-character loss while
# Terminal opens a fresh tab and types the command.
terminal_command=" READYFS_ROOT='$readyfs_root' READYFS_RUN_ID='$run_id' READYFS_MATRIX_OUT='$out_dir' READYFS_MATRIX_SPEEDS='${READYFS_MATRIX_SPEEDS:-1 16}' READYFS_MATRIX_CASE='${READYFS_MATRIX_CASE:-all}' READYFS_MATRIX_RUN_MUTATIONS='${READYFS_MATRIX_RUN_MUTATIONS:-0}' READYFS_OWNED_RUN_ID='${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$suite_script' >> '$launch_log' 2>&1"

/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
