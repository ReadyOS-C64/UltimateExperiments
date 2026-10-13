#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stamp="$(date +%Y%m%d-%H%M%S)"
out_dir="${READYFS_CAPTURE_OUT:-$readyfs_root/logs/readyfs_c64u/manual-capture-$stamp}"
capture_script="$readyfs_root/build_support/capture_readyfs_c64u.sh"

mkdir -p "$out_dir"
terminal_command="READYFS_CAPTURE=1 C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$capture_script' '$out_dir' > '$out_dir/terminal-launch.txt' 2>&1 && printf 'success\\n' > '$out_dir/status.txt'"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
