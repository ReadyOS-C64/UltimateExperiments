#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stamp="${READYFS_SOFTIEC_TAG:-$(date +%Y%m%d-%H%M%S)}"
run_id="${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}"
out_dir="${READYFS_SOFTIEC_OUT:-$readyfs_root/logs/readyfs_c64u/softiec-owned-$stamp}"
launch_log="$out_dir/terminal-launch.txt"
suite_script="$readyfs_root/build_support/run_readyfs_c64u_softiec_owned.sh"

mkdir -p "$out_dir"
terminal_command="READYFS_ROOT='$readyfs_root' READYFS_OWNED_RUN_ID='$run_id' READYFS_SOFTIEC_TAG='$stamp' READYFS_SOFTIEC_OUT='$out_dir' READYFS_SOFTIEC_PARTITION='${READYFS_SOFTIEC_PARTITION:-0}' READYFS_SOFTIEC_PARENT='${READYFS_SOFTIEC_PARENT:-}' READYFS_SOFTIEC_EXISTING_DIR='${READYFS_SOFTIEC_EXISTING_DIR:-0}' READYFS_SOFTIEC_REFRESH='${READYFS_SOFTIEC_REFRESH:-0}' READYFS_SOFTIEC_SEED_DIR='${READYFS_SOFTIEC_SEED_DIR:-0}' READYFS_APP_PRG='${READYFS_APP_PRG:-$readyfs_root/artifacts/readyfs/readyfs.prg}' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$suite_script' >> '$launch_log' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
