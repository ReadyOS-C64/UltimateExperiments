#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
run_id="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_UI_OUT:-$readyfs_root/logs/readyfs_c64u/ui-readonly-$run_id}"
launch_log="$out_dir/terminal-launch.txt"
suite_script="$readyfs_root/build_support/run_readyfs_c64u_readonly_ui.sh"

mkdir -p "$out_dir"
# Preserve the first meaningful character if Terminal consumes one while a
# new tab is opening and receiving the scripted command.
terminal_command=" READYFS_ROOT='$readyfs_root' READYFS_RUN_ID='$run_id' READYFS_UI_OUT='$out_dir' READYFS_UI_CASE='${READYFS_UI_CASE:-all}' READYFS_UI_COMMAND='${READYFS_UI_COMMAND:-}' READYFS_UI_REQUIRED='${READYFS_UI_REQUIRED:-}' READYFS_UI_DIR_PATH='${READYFS_UI_DIR_PATH:-u:/SD}' READYFS_UI_WAIT_SECONDS='${READYFS_UI_WAIT_SECONDS:-300}' READYFS_UI_SPEED_MHZ='${READYFS_UI_SPEED_MHZ:-64}' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$suite_script' >> '$launch_log' 2>&1"

/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
