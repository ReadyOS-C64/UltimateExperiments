#!/usr/bin/env bash
set -euo pipefail
readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out_dir="$readyfs_root/logs/readyfs_c64u/sd2iec-native-${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$out_dir"
terminal_command=" READYFS_INSPECT_OWNED='${READYFS_INSPECT_OWNED:-}' READYFS_PROBE_SOURCE='${READYFS_PROBE_SOURCE:-sd2iec_readonly_probe.c}' READYFS_SD2IEC_OUT='$out_dir' C64U_HOST='${C64U_HOST:-10.0.0.79}' python3 '$readyfs_root/build_support/run_readyfs_sd2iec_probe.py' >> '$out_dir/terminal-launch.txt' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
