#!/usr/bin/env bash
set -euo pipefail

# Run only from start_readyfs_c64u_speed_matrix_terminal.sh. This wrapper
# changes only U64 turbo control/CPU speed, runs read-only ReadyFS cases, and
# restores the exact original values in its EXIT trap.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
run_id="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_MATRIX_OUT:-$readyfs_root/logs/readyfs_c64u/speed-matrix-$run_id}"
speeds="${READYFS_MATRIX_SPEEDS:-1 16}"
run_mutations="${READYFS_MATRIX_RUN_MUTATIONS:-0}"
matrix_case="${READYFS_MATRIX_CASE:-all}"
api="http://$c64u_host/v1"
status_file="$out_dir/status.txt"
original_json="$out_dir/original-u64-config.json"
restore_payload="$out_dir/restore-speed.json"

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"

post_config() {
  local payload="$1"
  curl --fail --silent --show-error --max-time 15 \
    -H 'Content-Type: application/json' --data-binary "@$payload" \
    "$api/configs" >> "$out_dir/transport.log" 2>&1
}

restore_original() {
  if [ -s "$restore_payload" ]; then
    post_config "$restore_payload"
    sleep 1
    curl --fail --silent --show-error --max-time 15 \
      "$api/configs/U64%20Specific%20Settings" \
      -o "$out_dir/restored-u64-config.json"
  fi
}

finish() {
  local rc=$?
  trap - EXIT
  if ! restore_original; then
    printf 'RESTORE FAILED; inspect %s immediately\n' "$out_dir" \
      >> "$out_dir/transport.log"
    rc=97
  fi
  if [ "$rc" -eq 0 ]; then
    printf 'success\n' > "$status_file"
  else
    printf 'failed:%s\n' "$rc" > "$status_file"
  fi
  exit "$rc"
}
trap finish EXIT

curl --fail --silent --show-error --max-time 15 \
  "$api/configs/U64%20Specific%20Settings" -o "$original_json"
python3 - "$original_json" "$restore_payload" <<'PY'
import json, sys
source = json.load(open(sys.argv[1], encoding="utf-8"))
settings = source["U64 Specific Settings"]
payload = {"U64 Specific Settings": {
    "Turbo Control": settings["Turbo Control"],
    "CPU Speed": settings["CPU Speed"],
}}
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
PY

printf 'speed\tresult\trun_dir\n' > "$out_dir/results.tsv"
for speed in $speeds; do
  case "$speed" in
    1|16|64) ;;
    *) printf 'unsupported ReadyFS matrix speed: %s\n' "$speed" >&2; exit 64 ;;
  esac
  speed_payload="$out_dir/set-${speed}mhz.json"
  python3 - "$speed" "$speed_payload" <<'PY'
import json, sys
mhz = int(sys.argv[1])
payload = {"U64 Specific Settings": {
    "Turbo Control": "Off" if mhz <= 1 else "Manual",
    "CPU Speed": f"{mhz:2d}",
}}
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
PY
  post_config "$speed_payload"
  sleep 1
  observed="$out_dir/observed-${speed}mhz.json"
  curl --fail --silent --show-error --max-time 15 \
    "$api/configs/U64%20Specific%20Settings" -o "$observed"
  python3 - "$speed" "$observed" <<'PY'
import json, sys
expected = int(sys.argv[1])
settings = json.load(open(sys.argv[2], encoding="utf-8"))["U64 Specific Settings"]
actual = int(str(settings["CPU Speed"]).strip())
if actual != expected:
    raise SystemExit(f"CPU speed mismatch: expected {expected}, got {actual}")
PY
  case_out="$out_dir/${speed}mhz"
  case "$matrix_case" in
    all)
      READYFS_ROOT="$readyfs_root" C64U_HOST="$c64u_host" \
        READYFS_RUN_ID="$run_id-$speed" READYFS_UI_OUT="$case_out" \
        READYFS_UI_SPEED_MHZ="$speed" READYFS_UI_CASE=all \
        /bin/bash "$readyfs_root/build_support/run_readyfs_c64u_readonly_ui.sh" \
        >> "$out_dir/transport.log" 2>&1
      ;;
    recover)
      READYFS_ROOT="$readyfs_root" C64U_HOST="$c64u_host" \
        READYFS_RUN_ID="$run_id-$speed" READYFS_UI_OUT="$case_out" \
        READYFS_UI_SPEED_MHZ="$speed" READYFS_UI_CASE=custom \
        READYFS_UI_COMMAND='probe recover' READYFS_UI_REQUIRED='DOS V' \
        /bin/bash "$readyfs_root/build_support/run_readyfs_c64u_readonly_ui.sh" \
        >> "$out_dir/transport.log" 2>&1
      grep -q 'UCI RECOVER: QUIET' \
        "$case_out/RF-HW-$speed-CUSTOM/screen.txt"
      ;;
    *)
      printf 'unsupported ReadyFS matrix case: %s\n' "$matrix_case" >&2
      exit 64
      ;;
  esac
  grep -q '^success$' "$case_out/status.txt"
  printf '%s\tPASS\t%s\n' "$speed" "$case_out" >> "$out_dir/results.tsv"
  if [ "$run_mutations" = 1 ]; then
    mutation_out="$out_dir/${speed}mhz-mutations"
    READYFS_ROOT="$readyfs_root" C64U_HOST="$c64u_host" \
      READYFS_OWNED_RUN_ID="${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}" \
      READYFS_MUTATION_TAG="$run_id-$speed" \
      READYFS_MUTATION_OUT="$mutation_out" \
      READYFS_MUTATION_SPEED_MHZ="$speed" \
      /bin/bash "$readyfs_root/build_support/run_readyfs_c64u_owned_mutations.sh" \
      >> "$out_dir/transport.log" 2>&1
    grep -q '^success$' "$mutation_out/status.txt"
    printf '%s-mutations\tPASS\t%s\n' "$speed" "$mutation_out" \
      >> "$out_dir/results.tsv"
  fi
done
