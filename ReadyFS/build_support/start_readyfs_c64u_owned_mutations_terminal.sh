#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stamp="$(date +%Y%m%d-%H%M%S)"
run_id="${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}"
out_dir="${READYFS_MUTATION_OUT:-$readyfs_root/logs/readyfs_c64u/owned-mutations-$stamp}"
launch_log="$out_dir/terminal-launch.txt"
suite_script="$readyfs_root/build_support/run_readyfs_c64u_owned_mutations.sh"

mkdir -p "$out_dir"
terminal_command="READYFS_ROOT='$readyfs_root' READYFS_OWNED_RUN_ID='$run_id' READYFS_MUTATION_TAG='$stamp' READYFS_MUTATION_OUT='$out_dir' READYFS_MUTATION_SCOPE='${READYFS_MUTATION_SCOPE:-all}' C64U_HOST='${C64U_HOST:-10.0.0.79}' /bin/bash '$suite_script' >> '$launch_log' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
