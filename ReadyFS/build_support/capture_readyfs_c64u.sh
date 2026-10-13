#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "$0")/.." && pwd)"
host="${C64U_HOST:-10.0.0.79}"
out_dir="${1:-/tmp/readyfs_manual_capture_$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$out_dir"

curl_get() {
  local url="$1"
  local output="$2"
  curl --fail --silent --show-error --max-time 10 "$url" -o "$output"
}

curl_get "http://${host}/v1/machine:readmem?address=0400&length=1000" "$out_dir/screen_0400.bin"
curl_get "http://${host}/v1/machine:readmem?address=0800&length=4096" "$out_dir/readyfs_0800.bin"
curl_get "http://${host}/v1/machine:readmem?address=1800&length=4096" "$out_dir/readyfs_1800.bin"
curl_get "http://${host}/v1/machine:readmem?address=A800&length=3584" "$out_dir/readyfs_a800.bin"
curl_get "http://${host}/v1/drives" "$out_dir/drives.json"

python3 "$readyfs_root/build_support/decode_c64_screen.py" \
  "$out_dir/screen_0400.bin" \
  --output "$out_dir/screen.txt"

for bin in "$out_dir"/*.bin; do
  xxd -g 1 -c 16 "$bin" > "${bin%.bin}.hex.txt"
done

echo "$out_dir"
cat "$out_dir/screen.txt"
