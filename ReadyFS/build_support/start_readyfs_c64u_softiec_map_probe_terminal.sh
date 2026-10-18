#!/usr/bin/env bash
set -euo pipefail
readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stamp="$(date +%Y%m%d-%H%M%S)"
out_dir="$readyfs_root/logs/readyfs_c64u/softiec-map-probe-$stamp"
mkdir -p "$out_dir"
command_text="READYFS_ROOT='$readyfs_root' READYFS_SOFTIEC_OUT='$out_dir' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$readyfs_root/build_support/run_readyfs_c64u_softiec_map_probe.sh' >> '$out_dir/terminal-launch.txt' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$command_text\""
printf '%s\n' "$out_dir"
