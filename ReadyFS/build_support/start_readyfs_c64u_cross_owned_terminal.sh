#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case_tag="${READYFS_CROSS_TAG:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_CROSS_OUT:-$readyfs_root/logs/readyfs_c64u/cross-owned-$case_tag}"
helper="$readyfs_root/build_support/run_readyfs_c64u_cross_owned.sh"
launch_log="$out_dir/terminal-launch.txt"

mkdir -p "$out_dir"
terminal_command=" READYFS_ROOT='$readyfs_root' READYFS_CROSS_TAG='$case_tag' READYFS_CROSS_OUT='$out_dir' READYFS_OWNED_RUN_ID='${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$helper' >> '$launch_log' 2>&1"

/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
