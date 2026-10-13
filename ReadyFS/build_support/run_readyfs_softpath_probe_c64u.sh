#!/usr/bin/env bash
set -euo pipefail

# Read-only physical SoftwareIEC namespace probe. Run only through the
# Terminal-owned launcher. It changes only the drive's transient cwd.
readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
out_dir="${READYFS_SOFTPATH_OUT:?}"
api="http://$c64u_host/v1"
prg="$out_dir/softpath-probe.prg"
status_file="$out_dir/status.txt"

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"

finish() {
  local rc=$?
  trap - EXIT
  if [ "$rc" -eq 0 ]; then printf 'success\n' > "$status_file"
  else printf 'failed:%s\n' "$rc" > "$status_file"; fi
  exit "$rc"
}
trap finish EXIT

cl65 -t c64 -Os -o "$prg" \
  "$readyfs_root/src/apps/readyfs/softpath_probe.c" \
  > "$out_dir/build.log" 2>&1
curl --fail --silent --show-error --max-time 30 \
  -H 'Content-Type: application/octet-stream' --data-binary "@$prg" \
  "$api/runners:run_prg" > "$out_dir/launch.json"

for attempt in $(seq 1 30); do
  sleep 1
  curl --fail --silent --show-error --max-time 10 \
    "$api/machine:readmem?address=0400&length=1000" \
    -o "$out_dir/screen_0400.bin"
  python3 "$readyfs_root/build_support/decode_c64_screen.py" \
    "$out_dir/screen_0400.bin" --output "$out_dir/screen.txt"
  if grep -q 'DONE' "$out_dir/screen.txt"; then break; fi
done

grep -q 'SOFTPATH READ-ONLY' "$out_dir/screen.txt"
grep -q 'DONE' "$out_dir/screen.txt"
printf 'completed=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$out_dir/manifest.txt"
