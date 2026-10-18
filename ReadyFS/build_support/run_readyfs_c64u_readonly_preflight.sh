#!/usr/bin/env bash
set -euo pipefail

# This script is designed to run in a Terminal-owned shell, never directly as
# a foreground Codex curl. It is deliberately read-only.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
run_id="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_PREFLIGHT_OUT:-$readyfs_root/logs/readyfs_c64u/preflight-$run_id}"
status_file="$out_dir/status.txt"

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"

finish() {
  rc=$?
  if [ "$rc" -eq 0 ]; then
    printf 'success\n' > "$status_file"
  else
    printf 'failed:%s\n' "$rc" > "$status_file"
  fi
  exit "$rc"
}
trap finish EXIT

fetch_http() {
  local output="$1" url="$2" attempt
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 30 \
      "$url" -o "$output" >> "$out_dir/transport.log" 2>&1 &&
      test -s "$output"; then return 0; fi
    sleep 1
  done
  return 1
}

fetch_ftp_list() {
  local output="$1" url="$2" attempt
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 30 --list-only \
      --user anonymous:anonymous@ "$url" -o "$output" \
      >> "$out_dir/transport.log" 2>&1 && test -s "$output"; then return 0; fi
    sleep 1
  done
  return 1
}

{
  printf 'run_id=%s\n' "$run_id"
  printf 'host=%s\n' "$c64u_host"
  printf 'started=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out_dir/manifest.txt"

fetch_http "$out_dir/version.json" "http://$c64u_host/v1/version"
fetch_http "$out_dir/info.json" "http://$c64u_host/v1/info"
fetch_http "$out_dir/drives.json" "http://$c64u_host/v1/drives"
fetch_http "$out_dir/configs.json" "http://$c64u_host/v1/configs"
fetch_http "$out_dir/config-softiec.json" \
  "http://$c64u_host/v1/configs/SoftIEC%20Drive%20Settings"
fetch_http "$out_dir/config-u64.json" \
  "http://$c64u_host/v1/configs/U64%20Specific%20Settings"
fetch_http "$out_dir/config-c64.json" \
  "http://$c64u_host/v1/configs/C64%20and%20Cartridge%20Settings"
fetch_ftp_list "$out_dir/ftp-root.txt" "ftp://$c64u_host/"
fetch_ftp_list "$out_dir/ftp-sd-root.txt" "ftp://$c64u_host/SD/"
fetch_ftp_list "$out_dir/ftp-usb1-root.txt" "ftp://$c64u_host/USB1/"

printf 'completed=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >> "$out_dir/manifest.txt"
