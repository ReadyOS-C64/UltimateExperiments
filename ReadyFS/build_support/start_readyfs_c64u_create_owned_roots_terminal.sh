#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stamp="$(date +%Y%m%d-%H%M%S)"
run_id="${READYFS_RUN_ID:-readyfs-$stamp-$$}"
out_dir="${READYFS_ROOTS_OUT:-$readyfs_root/logs/readyfs_c64u/owned-roots-$run_id}"
launch_log="$out_dir/terminal-launch.txt"
setup_script="$readyfs_root/build_support/run_readyfs_c64u_create_owned_roots.sh"

mkdir -p "$out_dir"
terminal_command="READYFS_ROOT='$readyfs_root' READYFS_RUN_ID='$run_id' READYFS_ROOTS_OUT='$out_dir' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$setup_script' >> '$launch_log' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
