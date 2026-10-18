#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stamp="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_SOFTWRITE_OUT:-$readyfs_root/logs/readyfs_c64u/softwrite-owned-$stamp}"
suite="$readyfs_root/build_support/run_readyfs_softwrite_probe_c64u.sh"
mkdir -p "$out_dir"
terminal_command="READYFS_ROOT='$readyfs_root' READYFS_SOFTWRITE_OUT='$out_dir' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$suite' >> '$out_dir/terminal-launch.txt' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
