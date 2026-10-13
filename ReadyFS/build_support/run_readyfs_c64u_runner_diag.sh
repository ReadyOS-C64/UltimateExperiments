#!/usr/bin/env bash
set -euo pipefail

# Run only from an independent Terminal-owned shell. This diagnostic changes
# C64 execution state (reset/resume and optional ReadyFS launch), but neither
# mounts media nor issues any filesystem command.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
out_dir="${1:?usage: run_readyfs_c64u_runner_diag.sh <out-dir>}"
c64u_host="${C64U_HOST:-10.0.0.79}"
api="http://${c64u_host}/v1"
prg="${READYFS_APP_PRG:-$readyfs_root/artifacts/readyfs/readyfs.prg}"
upload_mode="${READYFS_DIAG_UPLOAD:-raw}"
content_type="${READYFS_DIAG_CONTENT_TYPE:-}"
expected_screen="${READYFS_DIAG_EXPECT:-READYFS LAB}"
remote_file="${READYFS_DIAG_REMOTE:-}"
owned_run_id="readyfs-20260815-190355-79014"
owned_root="USB1/READYFS_TEST/$owned_run_id"
marker=".readyfs-owner-$owned_run_id"
expected_marker="$readyfs_root/logs/readyfs_c64u/owned-roots-$owned_run_id/ownership-marker.txt"
status_file="$out_dir/status.txt"

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"

finish() {
  local rc=$?
  trap - EXIT
  if [ "$rc" -eq 0 ]; then
    printf 'success\n' > "$status_file"
  else
    printf 'failed:%s\n' "$rc" > "$status_file"
  fi
  exit "$rc"
}
trap finish EXIT

request() {
  local label="$1"
  shift
  curl --silent --show-error --max-time 30 \
    -D "$out_dir/$label.headers" -o "$out_dir/$label.body" \
    -w '%{http_code}\n' "$@" > "$out_dir/$label.code" \
    2> "$out_dir/$label.stderr" || true
}

ftp_get_retry() {
  local remote="$1" output="$2" attempt
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 30 \
      --user anonymous:anonymous@ "ftp://$c64u_host/$remote" \
      -o "$output" 2>> "$out_dir/ftp.log"; then
      test -s "$output" && return 0
    fi
    sleep 2
  done
  return 1
}

ftp_put_retry() {
  local input="$1" remote="$2" attempt
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 60 \
      --user anonymous:anonymous@ --ftp-create-dirs -T "$input" \
      "ftp://$c64u_host/$remote" \
      -o "$out_dir/ftp-upload.body" 2>> "$out_dir/ftp.log"; then
      return 0
    fi
    sleep 2
  done
  return 1
}

request version "$api/version"
request info "$api/info"
request drives "$api/drives"
request configs "$api/configs/U64%20Specific%20Settings"
request runners-get "$api/runners"
request runner-options -X OPTIONS "$api/runners:run_prg"

# Match the proven ReadyOS launch recovery cadence in one Terminal-owned
# process so pause/resume ownership and timing cannot be split across shells.
request reset -X PUT "$api/machine:reset"
sleep 3
request resume -X PUT "$api/machine:resume"
sleep 7

test -s "$prg"
case "$upload_mode" in
  raw)
    if [ -n "$content_type" ]; then
      request runner-post -H "Content-Type: $content_type" \
        --data-binary "@$prg" "$api/runners:run_prg"
    else
      request runner-post --data-binary "@$prg" "$api/runners:run_prg"
    fi
    ;;
  multipart)
    request runner-post -F "file=@$prg" "$api/runners:run_prg"
    ;;
  remote)
    case "$remote_file" in
      "$owned_root"/*) ;;
      *)
        printf 'remote runner path is outside exact owned root: %s\n' \
          "$remote_file" >&2
        exit 65
        ;;
    esac
    test -s "$expected_marker"
    ftp_get_retry "$owned_root/$marker" "$out_dir/owner-before.txt"
    cmp "$expected_marker" "$out_dir/owner-before.txt"
    ftp_put_retry "$prg" "$remote_file"
    request runner-post -X PUT \
      "$api/runners:run_prg?file=/$remote_file"
    ftp_get_retry "$owned_root/$marker" "$out_dir/owner-after.txt"
    cmp "$expected_marker" "$out_dir/owner-after.txt"
    ;;
  *)
    printf 'unknown READYFS_DIAG_UPLOAD=%s\n' "$upload_mode" >&2
    exit 64
    ;;
esac

if [ "$(tr -d '\r\n' < "$out_dir/runner-post.code")" != "200" ]; then
  exit 1
fi

sleep 4
request screen "$api/machine:readmem?address=0400&length=1000"
python3 "$readyfs_root/build_support/decode_c64_screen.py" \
  "$out_dir/screen.body" --output "$out_dir/screen.txt"
if [ -n "$expected_screen" ]; then
  grep -Fq "$expected_screen" "$out_dir/screen.txt"
fi
