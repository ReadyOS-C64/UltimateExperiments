#!/usr/bin/env bash
set -euo pipefail

# Run only from the independent Terminal launcher. Every mutation is guarded
# by an exact ownership-marker round trip for the selected pre-created root.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
run_id="${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}"
case_tag="${READYFS_MUTATION_TAG:?READYFS_MUTATION_TAG is required}"
out_dir="${READYFS_MUTATION_OUT:?READYFS_MUTATION_OUT is required}"
test_speed="${READYFS_MUTATION_SPEED_MHZ:-64}"
mutation_scope="${READYFS_MUTATION_SCOPE:-all}"
status_file="$out_dir/status.txt"
api="http://$c64u_host/v1"
prg="$readyfs_root/artifacts/readyfs/readyfs.prg"
remote_root="USB1/READYFS_TEST/$run_id"
udos_root="u:/USB1/READYFS_TEST/$run_id"
marker_name=".readyfs-owner-$run_id"
source_marker="$readyfs_root/logs/readyfs_c64u/owned-roots-$run_id/ownership-marker.txt"

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

verify_owner() {
  local label="$1"
  local fetched="$out_dir/marker-$label.txt"
  local attempt
  test -s "$source_marker"
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 20 \
      --user anonymous:anonymous@ \
      "ftp://$c64u_host/$remote_root/$marker_name" > "$fetched" \
      2>> "$out_dir/transport.log"; then
      break
    fi
    if [ "$attempt" -eq 10 ]; then return 1; fi
    sleep 1
  done
  cmp "$source_marker" "$fetched"
  grep -q '^READYFS-OWNED-ROOT$' "$fetched"
  grep -q "^run_id=$run_id$" "$fetched"
}

capture_screen() {
  local label="$1"
  local step_dir="$out_dir/$label"
  local attempt
  mkdir -p "$step_dir"
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 10 \
      "$api/machine:readmem?address=0400&length=1000" \
      -o "$step_dir/screen_0400.bin" \
      >> "$out_dir/transport.log" 2>&1; then
      break
    fi
    if [ "$attempt" -eq 10 ]; then return 1; fi
    sleep 1
  done
  python3 "$readyfs_root/build_support/decode_c64_screen.py" \
    "$step_dir/screen_0400.bin" --output "$step_dir/screen.txt"
}

wait_screen() {
  local label="$1"
  local required="$2"
  local attempt
  for attempt in $(seq 1 45); do
    sleep 1
    capture_screen "$label"
    if grep -q "$required" "$out_dir/$label/screen.txt"; then return 0; fi
  done
  return 1
}

type_command() {
  local case_id="$1"
  local command="$2"
  local expected="$3"
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" $'clear\r' \
    >> "$out_dir/transport.log" 2>&1
  sleep 1
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" "$command"$'\r' \
    >> "$out_dir/transport.log" 2>&1
  wait_screen "$case_id" "$expected"
  printf '%s\tPASS\t%s\n' "$case_id" "$command" >> "$out_dir/results.tsv"
}

launch_readyfs() {
  local attempt
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 30 \
      -H 'Content-Type: application/octet-stream' --data-binary "@$prg" \
      "$api/runners:run_prg" >> "$out_dir/transport.log" 2>&1; then break; fi
    if [ "$attempt" -eq 10 ]; then return 1; fi
    sleep 2
  done
  sleep 3
  capture_screen launch
  grep -q 'READYFS LAB' "$out_dir/launch/screen.txt"
}

test -s "$prg"
{
  printf 'run_id=%s\n' "$run_id"
  printf 'remote_root=/%s\n' "$remote_root"
  printf 'udos_root=%s\n' "$udos_root"
  printf 'cpu_mhz=%s\n' "$test_speed"
  printf 'case_tag=%s\n' "$case_tag"
  printf 'mutation_scope=%s\n' "$mutation_scope"
  printf 'preserve=true\n'
} > "$out_dir/manifest.txt"
printf 'case\tresult\tcommand\n' > "$out_dir/results.tsv"

verify_owner prelaunch
launch_readyfs

if [ "$mutation_scope" != dirs ]; then
verify_owner "RF-HW-$test_speed-101"
type_command "RF-HW-$test_speed-101" "new $udos_root/empty-$case_tag.seq --type seq" 'CREATED'

verify_owner "RF-HW-$test_speed-102"
type_command "RF-HW-$test_speed-102" "write $udos_root/text-$case_tag.seq \"hw alpha\" --line" \
  'WRITE COMPLETE'
printf 'HW ALPHA\n' > "$out_dir/expected-text.seq"
curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/text-$case_tag.seq" > "$out_dir/actual-text.seq"
cmp "$out_dir/expected-text.seq" "$out_dir/actual-text.seq"

verify_owner "RF-HW-$test_speed-103"
type_command "RF-HW-$test_speed-103" "write $udos_root/text-$case_tag.seq \"hw replaced\" --force" \
  'WRITE COMPLETE'
printf 'HW REPLACED' > "$out_dir/expected-replaced.seq"
curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/text-$case_tag.seq" > "$out_dir/actual-replaced.seq"
cmp "$out_dir/expected-replaced.seq" "$out_dir/actual-replaced.seq"

verify_owner "RF-HW-$test_speed-104"
type_command "RF-HW-$test_speed-104" "append $udos_root/text-$case_tag.seq \" tail\" --line" \
  'APPEND COMPLETE'
printf 'HW REPLACED TAIL\n' > "$out_dir/expected-appended.seq"
curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/text-$case_tag.seq" > "$out_dir/actual-appended.seq"
cmp "$out_dir/expected-appended.seq" "$out_dir/actual-appended.seq"

verify_owner "RF-HW-$test_speed-105"
type_command "RF-HW-$test_speed-105" \
  "copy $udos_root/text-$case_tag.seq $udos_root/copy-$case_tag.seq" 'COPIED'
curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/copy-$case_tag.seq" > "$out_dir/actual-copy.seq"
cmp "$out_dir/expected-appended.seq" "$out_dir/actual-copy.seq"

verify_owner "RF-HW-$test_speed-106"
type_command "RF-HW-$test_speed-106" \
  "move $udos_root/copy-$case_tag.seq $udos_root/moved-$case_tag.seq" \
  'MOVE COMPLETE'
curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/moved-$case_tag.seq" > "$out_dir/actual-moved.seq"
cmp "$out_dir/expected-appended.seq" "$out_dir/actual-moved.seq"
if curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/copy-$case_tag.seq" \
  -o "$out_dir/unexpected-move-source.seq" 2>> "$out_dir/transport.log"; then
  printf 'move source unexpectedly remains\n' >> "$out_dir/transport.log"
  exit 1
fi
fi

dir_name="dir-$case_tag"
verify_owner "RF-HW-$test_speed-107"
type_command "RF-HW-$test_speed-107" "mkdir $udos_root/$dir_name" \
  'DIRECTORY CREATED'
curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/$dir_name/" \
  -o "$out_dir/directory-listing-after-create.txt"

verify_owner "RF-HW-$test_speed-108"
type_command "RF-HW-$test_speed-108" \
  "new $udos_root/$dir_name/inside.seq --type seq" 'CREATED'
curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/$dir_name/inside.seq" \
  -o "$out_dir/inside.seq"

verify_owner "RF-HW-$test_speed-109"
type_command "RF-HW-$test_speed-109" "rmdir $udos_root/$dir_name --force" \
  'RMDIR FAILED'
curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/$dir_name/inside.seq" \
  -o "$out_dir/inside-after-rejected-rmdir.seq"

verify_owner "RF-HW-$test_speed-110"
type_command "RF-HW-$test_speed-110" \
  "delete $udos_root/$dir_name/inside.seq --force" 'DELETED'
if curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/$dir_name/inside.seq" \
  -o "$out_dir/unexpected-deleted-inside.seq" 2>> "$out_dir/transport.log"; then
  printf 'deleted inner file unexpectedly remains\n' >> "$out_dir/transport.log"
  exit 1
fi

verify_owner "RF-HW-$test_speed-111"
type_command "RF-HW-$test_speed-111" "rmdir $udos_root/$dir_name --force" \
  'DIRECTORY REMOVED'
if curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
  "ftp://$c64u_host/$remote_root/$dir_name/" \
  -o "$out_dir/unexpected-removed-directory.txt" 2>> "$out_dir/transport.log"; then
  printf 'removed directory unexpectedly remains\n' >> "$out_dir/transport.log"
  exit 1
fi
