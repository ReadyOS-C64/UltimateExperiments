#!/usr/bin/env bash
set -euo pipefail

# Run only from the independent Terminal launcher. This suite starts ReadyFS
# and exercises read-only UCI/UI commands; it performs no media mutations.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
run_id="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_UI_OUT:-$readyfs_root/logs/readyfs_c64u/ui-readonly-$run_id}"
test_speed="${READYFS_UI_SPEED_MHZ:-64}"
ui_wait_seconds="${READYFS_UI_WAIT_SECONDS:-300}"
ui_dir_path="${READYFS_UI_DIR_PATH:-u:/SD}"
status_file="$out_dir/status.txt"
api="http://$c64u_host/v1"
prg="$readyfs_root/artifacts/readyfs/readyfs.prg"

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
trap 'exit 130' INT
trap 'exit 143' TERM

capture_screen() {
  local label="$1"
  local step_dir="$out_dir/$label"
  mkdir -p "$step_dir"
  curl --fail --silent --show-error --max-time 10 \
    "$api/machine:readmem?address=0400&length=1000" \
    -o "$step_dir/screen_0400.bin"
  python3 "$readyfs_root/build_support/decode_c64_screen.py" \
    "$step_dir/screen_0400.bin" --output "$step_dir/screen.txt"
}

launch_readyfs() {
  local attempt
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 30 \
      -H 'Content-Type: application/octet-stream' \
      --data-binary "@$prg" "$api/runners:run_prg" \
      >> "$out_dir/transport.log" 2>&1; then
      break
    fi
    if [ "$attempt" -eq 10 ]; then
      printf 'ReadyFS launch failed after %s attempts\n' "$attempt" \
        >> "$out_dir/transport.log"
      return 1
    fi
    sleep 2
  done
  sleep 3
}

run_case() {
  local case_id="$1"
  local command="$2"
  local required="$3"
  local prompt_count
  local attempt
  local more_count=0
  launch_readyfs
  capture_screen "${case_id}-launch"
  grep -q 'READYFS LAB' "$out_dir/${case_id}-launch/screen.txt"
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" "$command" \
    >> "$out_dir/transport.log" 2>&1
  for attempt in $(seq 1 "$ui_wait_seconds"); do
    sleep 1
    capture_screen "$case_id"
    if grep -q -- '-- MORE --' "$out_dir/$case_id/screen.txt"; then
      more_count=$((more_count + 1))
      if [ "$more_count" -gt 32 ]; then
        printf '%s: directory paging exceeded 32 pages\n' "$case_id" \
          >> "$out_dir/transport.log"
        return 1
      fi
      C64U_HOST="$c64u_host" /bin/bash \
        "$readyfs_root/build_support/c64u_type_text.sh" ' ' \
        >> "$out_dir/transport.log" 2>&1
      sleep 1
      continue
    fi
    prompt_count="$(grep -c 'RF>' "$out_dir/$case_id/screen.txt" || true)"
    if grep -q "$required" "$out_dir/$case_id/screen.txt" \
      && [ "$prompt_count" -ge 2 ]; then
      break
    fi
  done
  grep -q "$required" "$out_dir/$case_id/screen.txt"
  [ "$prompt_count" -ge 2 ]
  if grep -q 'TRANSPORT FLAGS' "$out_dir/$case_id/screen.txt"; then
    printf '%s: unexpected transport failure\n' "$case_id" \
      >> "$out_dir/transport.log"
    return 1
  fi
  printf '%s\tPASS\t%s\n' "$case_id" "$command" >> "$out_dir/results.tsv"
  printf '%s: acknowledged %s directory page prompts\n' \
    "$case_id" "$more_count" >> "$out_dir/transport.log"
}

test -s "$prg"
{
  printf 'run_id=%s\n' "$run_id"
  printf 'host=%s\n' "$c64u_host"
  printf 'suite=readyfs-readonly-ui\n'
  printf 'expected_cpu_mhz=%s\n' "$test_speed"
  printf 'directory_probe=%s\n' "$ui_dir_path"
  printf 'started=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out_dir/manifest.txt"
printf 'case\tresult\tcommand\n' > "$out_dir/results.tsv"

case "${READYFS_UI_CASE:-all}" in
  all)
    run_case "RF-HW-$test_speed-001" $'probe uci\r' 'UCI: BASE'
    run_case "RF-HW-$test_speed-002" $'probe udos\r' 'DOS V'
    run_case "RF-HW-$test_speed-003" $'probe softiec\r' 'SOFTWARE IEC TARGET'
    run_case "RF-HW-$test_speed-004" $'probe recover\r' 'DOS V'
    grep -q 'UCI RECOVER: QUIET' "$out_dir/RF-HW-$test_speed-004/screen.txt"
    run_case "RF-HW-$test_speed-005" "dir $ui_dir_path"$'\r' 'ENTRIES:'
    ;;
  dir)
    run_case "RF-HW-$test_speed-005" "dir $ui_dir_path"$'\r' 'ENTRIES:'
    ;;
  custom)
    run_case "RF-HW-$test_speed-CUSTOM" "${READYFS_UI_COMMAND:?set READYFS_UI_COMMAND}"$'\r' \
      "${READYFS_UI_REQUIRED:-RF>}"
    ;;
  *)
    printf 'unknown READYFS_UI_CASE=%s\n' "$READYFS_UI_CASE" >&2
    exit 64
    ;;
esac

printf 'completed=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >> "$out_dir/manifest.txt"
