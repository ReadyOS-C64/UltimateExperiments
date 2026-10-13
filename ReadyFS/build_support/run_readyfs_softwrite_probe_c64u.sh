#!/usr/bin/env bash
set -euo pipefail

# Marker-gated, preserve-only physical SoftwareIEC write probe. It may create
# exactly kp065128.seq inside the already-owned preserved rf065128 folder.
readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
out_dir="${READYFS_SOFTWRITE_OUT:?}"
api="http://$c64u_host/v1"
run_id="readyfs-20260815-190355-79014"
remote_root="USB1/READYFS_TEST/$run_id"
sd_root="SD/READYFS_TEST/$run_id"
marker=".readyfs-owner-$run_id"
marker_source="$readyfs_root/logs/readyfs_c64u/owned-roots-$run_id/ownership-marker.txt"
prg="$out_dir/softwrite-probe.prg"

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

fetch_marker() {
  curl --fail --silent --show-error --max-time 30 --user anonymous:anonymous@ \
    "ftp://$c64u_host/$1/$marker" -o "$2"
  cmp "$marker_source" "$2"
}

fetch_marker "$remote_root" "$out_dir/usb-marker-before.txt"
fetch_marker "$sd_root" "$out_dir/sd-marker-before.txt"
cl65 -t c64 -Os -o "$prg" \
  "$readyfs_root/src/apps/readyfs/softwrite_probe.c" \
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
  grep -qi 'done' "$out_dir/screen.txt" && break
done
grep -qi 'softwrite owned probe' "$out_dir/screen.txt"
grep -qi 'done' "$out_dir/screen.txt"
fetch_marker "$remote_root" "$out_dir/usb-marker-after.txt"
fetch_marker "$sd_root" "$out_dir/sd-marker-after.txt"
curl --fail --silent --show-error --max-time 30 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/rf065128/kp065128.seq" \
  -o "$out_dir/kp065128.seq"
printf 'completed=%s\npreserve=%s/rf065128/kp065128.seq\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$remote_root" > "$out_dir/manifest.txt"
