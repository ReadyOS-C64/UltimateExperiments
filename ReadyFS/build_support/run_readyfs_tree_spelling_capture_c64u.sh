#!/usr/bin/env bash
set -euo pipefail

# Read-only diagnostic for an already running ReadyFS instance. It captures
# the exact UltimateDOS tree spelling without mounting media or changing any
# file/configuration state. Launch only from a Terminal-owned background bash.
readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
out_dir="${READYFS_TREE_CAPTURE_OUT:?}"
tree_path="u:/USB1/READYFS_TEST/readyfs-20260815-190355-79014/rf091800/rf100154"
command_text="${READYFS_CAPTURE_COMMAND:-tree $tree_path}"
expected_text="${READYFS_CAPTURE_EXPECTED:-TREE DONE F3 D1}"

case "$command_text" in
  tree\ *|find\ *|match\ *) ;;
  *) printf 'unsafe read-only capture command: %s\n' "$command_text" >&2
     exit 64 ;;
esac

mkdir -p "$out_dir"
printf 'running\n' > "$out_dir/status.txt"
finish() {
  rc=$?
  trap - EXIT
  if [ "$rc" -eq 0 ]; then printf 'success\n' > "$out_dir/status.txt"
  else printf 'failed:%s\n' "$rc" > "$out_dir/status.txt"; fi
  exit "$rc"
}
trap finish EXIT
C64U_HOST="$c64u_host" /bin/bash \
  "$readyfs_root/build_support/c64u_type_text.sh" $'clear\r' \
  >> "$out_dir/transport.log" 2>&1
sleep 1
C64U_HOST="$c64u_host" /bin/bash \
  "$readyfs_root/build_support/c64u_type_text.sh" \
  "$command_text"$'\r' >> "$out_dir/transport.log" 2>&1
# Directory traversal is read-only, but keep DMA away from its UCI/KERNAL
# transitions just as the mutation harness does.
sleep 60
curl --fail --silent --show-error --max-time 15 \
  "http://$c64u_host/v1/machine:readmem?address=0400&length=1000" \
  -o "$out_dir/screen_0400.bin"
python3 "$readyfs_root/build_support/decode_c64_screen.py" \
  "$out_dir/screen_0400.bin" --output "$out_dir/screen.txt"
if [ -n "${READYFS_CAPTURE_MEMORY_ADDRESS:-}" ]; then
  memory_length="${READYFS_CAPTURE_MEMORY_LENGTH:-256}"
  if [[ ! "$memory_length" =~ ^[0-9]+$ ]] ||
     (( memory_length < 1 || memory_length > 4096 )); then
    printf 'unsafe capture length: %s\n' "$memory_length" >&2
    exit 64
  fi
  curl --fail --silent --show-error --max-time 15 \
    "http://$c64u_host/v1/machine:readmem?address=${READYFS_CAPTURE_MEMORY_ADDRESS}&length=$memory_length" \
    -o "$out_dir/capture_memory.bin"
  od -An -tx1 -v "$out_dir/capture_memory.bin" \
    > "$out_dir/capture_memory.hex"
fi
grep -Fqi "$expected_text" "$out_dir/screen.txt"
