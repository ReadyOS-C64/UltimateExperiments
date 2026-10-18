#!/usr/bin/env bash
set -euo pipefail
readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out_dir="$readyfs_root/logs/readyfs_c64u/demo-resident-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out_dir"
terminal_command=" READYFS_DEMO_INSPECT_OUT='$out_dir' python3 '$readyfs_root/build_support/inspect_readyfs_demo_resident.py' >> '$out_dir/terminal-launch.txt' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
