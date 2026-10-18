#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
restore_dir="${READYFS_RESTORE_DIR:?set READYFS_RESTORE_DIR}"
helper="$readyfs_root/build_support/run_readyfs_c64u_restore_speed.sh"
launch_log="$restore_dir/manual-restore-terminal.txt"
# Terminal can consume the first typed character while opening a new tab.
# Keep a sacrificial leading blank so the absolute /bin/bash path survives.
terminal_command=" /bin/bash '$helper' '$restore_dir' '${C64U_HOST:-10.0.0.79}' >> '$launch_log' 2>&1"

/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$restore_dir"
