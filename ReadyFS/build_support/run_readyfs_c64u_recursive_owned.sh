#!/usr/bin/env bash
set -euo pipefail

# Independent-Terminal hardware suite. It creates and preserves only a unique
# subtree below the pre-existing marker-owned USB1 root. Nothing is deleted.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
owned_id="${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}"
case_tag="${READYFS_RECURSIVE_TAG:?READYFS_RECURSIVE_TAG is required}"
out_dir="${READYFS_RECURSIVE_OUT:?READYFS_RECURSIVE_OUT is required}"
status_file="$out_dir/status.txt"
api="http://$c64u_host/v1"
prg="$readyfs_root/artifacts/readyfs/readyfs.prg"
remote_root="USB1/READYFS_TEST/$owned_id"
udos_root="u:/USB1/READYFS_TEST/$owned_id"
marker_name=".readyfs-owner-$owned_id"
source_marker="$readyfs_root/logs/readyfs_c64u/owned-roots-$owned_id/ownership-marker.txt"
tree_name="recursive-$case_tag"
tree_path="$udos_root/$tree_name"

if [[ ! "$owned_id" =~ ^readyfs-[0-9]{8}-[0-9]{6}-[0-9]+$ ]] ||
   [[ ! "$case_tag" =~ ^[0-9]{8}-[0-9]{6}$ ]]; then
  printf 'unsafe owned id/tag\n' >&2
  exit 64
fi

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"
finish() {
  local rc=$?
  if [ "$rc" -eq 0 ]; then printf 'success\n' > "$status_file"
  else printf 'failed:%s\n' "$rc" > "$status_file"; fi
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
      2>> "$out_dir/transport.log"; then break; fi
    if [ "$attempt" -eq 10 ]; then return 1; fi
    sleep 1
  done
  cmp "$source_marker" "$fetched"
  grep -q '^READYFS-OWNED-ROOT$' "$fetched"
  grep -q "^run_id=$owned_id$" "$fetched"
}

capture_screen() {
  local label="$1"
  local step_dir="$out_dir/$label"
  local attempt
  mkdir -p "$step_dir"
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 10 \
      "$api/machine:readmem?address=0400&length=1000" \
      -o "$step_dir/screen_0400.bin" >> "$out_dir/transport.log" 2>&1; then
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
  for attempt in $(seq 1 60); do
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
  printf 'owned_id=%s\n' "$owned_id"
  printf 'tree=%s\n' "$tree_path"
  printf 'preserve=true\n'
  printf 'delete_operations=0\n'
  printf 'started=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out_dir/manifest.txt"
printf 'case\tresult\tcommand\n' > "$out_dir/results.tsv"

verify_owner prelaunch
launch_readyfs

verify_owner mkdir-root
type_command RF-HW-64-R201 "mkdir $tree_path" 'DIRECTORY CREATED'
verify_owner mkdir-one
type_command RF-HW-64-R202 "mkdir $tree_path/one" 'DIRECTORY CREATED'
verify_owner mkdir-two
type_command RF-HW-64-R203 "mkdir $tree_path/one/two" 'DIRECTORY CREATED'
verify_owner write-root
type_command RF-HW-64-R204 "write $tree_path/root.seq \"root\"" 'WRITE COMPLETE'
verify_owner write-one
type_command RF-HW-64-R205 "write $tree_path/one/one.prg \"one\" --type prg" 'WRITE COMPLETE'
verify_owner write-two
type_command RF-HW-64-R206 "write $tree_path/one/two/two.seq \"two\"" 'WRITE COMPLETE'

type_command RF-HW-64-R207 \
  "copy $tree_path u:/SD/READYFS_TEST/$owned_id/dryrun-$case_tag --recursive --dry-run --include **/*.seq" \
  'RECURSIVE PLAN F3 D2 SELECTED 2'
grep -q 'PLAN W2 D0 M0; DONE W0 D0 M0' "$out_dir/RF-HW-64-R207/screen.txt"

type_command RF-HW-64-R208 \
  "delete $tree_path --recursive --whatif --include **/*.seq" \
  'PLAN W0 D2 M0; DONE W0 D0 M0'

# Read-only host oracles after both dry-runs. These fixtures are intentionally
# preserved as evidence; the suite performs no cleanup or deletion.
for relative in root.seq one/one.prg one/two/two.seq; do
  safe_name="${relative//\//-}"
  curl --fail --silent --show-error --max-time 20 --user anonymous:anonymous@ \
    "ftp://$c64u_host/$remote_root/$tree_name/$relative" \
    -o "$out_dir/oracle-$safe_name"
  test -s "$out_dir/oracle-$safe_name"
done

printf 'completed=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$out_dir/manifest.txt"

