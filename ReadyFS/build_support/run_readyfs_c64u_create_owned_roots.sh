#!/usr/bin/env bash
set -euo pipefail

# Run only from the independent Terminal launcher. Creates new, unique test
# roots and ownership markers. It never deletes or reuses a remote path.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
run_id="${READYFS_RUN_ID:?READYFS_RUN_ID is required}"
out_dir="${READYFS_ROOTS_OUT:?READYFS_ROOTS_OUT is required}"
status_file="$out_dir/status.txt"

if [[ ! "$run_id" =~ ^readyfs-[0-9]{8}-[0-9]{6}-[0-9]+$ ]]; then
  printf 'unsafe run id: %s\n' "$run_id" >&2
  exit 64
fi

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"

finish() {
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    printf 'success\n' > "$status_file"
  else
    printf 'failed:%s\n' "$rc" > "$status_file"
  fi
  exit "$rc"
}
trap finish EXIT

marker_file="$out_dir/ownership-marker.txt"
marker_name=".readyfs-owner-$run_id"
{
  printf 'READYFS-OWNED-ROOT\n'
  printf 'run_id=%s\n' "$run_id"
  printf 'created_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'policy=preserve-by-default\n'
} > "$marker_file"

create_root() {
  local volume="$1"
  local remote_dir="$volume/READYFS_TEST/$run_id"
  local probe="$out_dir/${volume}-preexisting.txt"
  if curl --fail --silent --show-error --max-time 20 \
    --user anonymous:anonymous@ "ftp://$c64u_host/$remote_dir/" \
    > "$probe" 2>/dev/null; then
    printf 'refusing to reuse existing path: /%s\n' "$remote_dir" >&2
    return 65
  fi
  curl --fail --silent --show-error --max-time 30 --ftp-create-dirs \
    --user anonymous:anonymous@ -T "$marker_file" \
    "ftp://$c64u_host/$remote_dir/$marker_name"
  curl --fail --silent --show-error --max-time 20 \
    --user anonymous:anonymous@ \
    "ftp://$c64u_host/$remote_dir/$marker_name" \
    > "$out_dir/${volume}-marker-roundtrip.txt"
  cmp "$marker_file" "$out_dir/${volume}-marker-roundtrip.txt"
}

{
  printf 'run_id=%s\n' "$run_id"
  printf 'host=%s\n' "$c64u_host"
  printf 'marker=%s\n' "$marker_name"
  printf 'ftp_usb1=/USB1/READYFS_TEST/%s\n' "$run_id"
  printf 'ftp_sd=/SD/READYFS_TEST/%s\n' "$run_id"
  printf 'udos_usb1=u:/USB1/READYFS_TEST/%s\n' "$run_id"
  printf 'udos_sd=u:/SD/READYFS_TEST/%s\n' "$run_id"
} > "$out_dir/owned-roots.env"

create_root USB1
create_root SD
