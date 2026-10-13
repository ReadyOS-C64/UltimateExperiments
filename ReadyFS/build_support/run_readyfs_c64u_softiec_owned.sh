#!/usr/bin/env bash
set -euo pipefail

# Independent-Terminal only. ReadyFS resets SoftwareIEC to its global root and
# enters USB1 component-by-component; it does not depend on the configured
# partition-0 default. The suite verifies both owner markers before mutations
# and never uses FTP or deletes host files.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
run_id="${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}"
partition="${READYFS_SOFTIEC_PARTITION:-0}"
case_tag="${READYFS_SOFTIEC_TAG:?READYFS_SOFTIEC_TAG is required}"
out_dir="${READYFS_SOFTIEC_OUT:?READYFS_SOFTIEC_OUT is required}"
api="http://$c64u_host/v1"
prg="${READYFS_APP_PRG:-$readyfs_root/artifacts/readyfs/readyfs.prg}"
udos_root="u:/USB1/READYFS_TEST/$run_id"
sd_root="u:/SD/READYFS_TEST/$run_id"
soft_root="s$partition:/"
marker_name=".readyfs-owner-$run_id"
source_marker="$readyfs_root/logs/readyfs_c64u/owned-roots-$run_id/ownership-marker.txt"
mapped_root="$udos_root"
short_tag="${case_tag##*-}"
soft_dir="rf$short_tag"
case_parent="${READYFS_SOFTIEC_PARENT:-}"
if [ -n "$case_parent" ]; then case_rel="$case_parent/$soft_dir"
else case_rel="$soft_dir"; fi
soft_case_root="s$partition:/READYFS_TEST/$run_id/$case_rel"
udos_case_root="$mapped_root/$case_rel"
outside_source="$udos_root/us$short_tag.seq"
outside_copy="$udos_root/fs$short_tag.seq"
status_file="$out_dir/status.txt"
original_config="$out_dir/original-softiec-config.json"
restore_payload="$out_dir/restore-softiec-config.json"
test_payload="$out_dir/test-softiec-config.json"
restore_disabled="$out_dir/restore-softiec-disabled.json"
test_disabled="$out_dir/test-softiec-disabled.json"
configured=0
existing_dir="${READYFS_SOFTIEC_EXISTING_DIR:-0}"
refresh_softiec="${READYFS_SOFTIEC_REFRESH:-0}"
seed_dir="${READYFS_SOFTIEC_SEED_DIR:-0}"

if [[ ! "$run_id" =~ ^readyfs-[0-9]{8}-[0-9]{6}-[0-9]+$ ]]; then
  printf 'unsafe run id: %s\n' "$run_id" >&2
  exit 64
fi
if [[ ! "$partition" =~ ^[0-9]+$ ]] || (( partition < 0 || partition > 255 )); then
  printf 'unsafe SoftwareIEC partition: %s\n' "$partition" >&2
  exit 64
fi
if [[ -n "$case_parent" && ! "$case_parent" =~ ^rf[0-9]{6}$ ]]; then
  printf 'unsafe case parent: %s\n' "$case_parent" >&2
  exit 64
fi
if [[ "$existing_dir" != 0 && "$existing_dir" != 1 ]]; then
  printf 'unsafe existing-dir flag: %s\n' "$existing_dir" >&2
  exit 64
fi
if [[ "$refresh_softiec" != 0 && "$refresh_softiec" != 1 ]]; then
  printf 'unsafe refresh flag: %s\n' "$refresh_softiec" >&2
  exit 64
fi
if [[ "$seed_dir" != 0 && "$seed_dir" != 1 ]]; then
  printf 'unsafe seed-dir flag: %s\n' "$seed_dir" >&2
  exit 64
fi

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"
printf 'case\tresult\tcommand\n' > "$out_dir/results.tsv"

post_config() {
  curl --fail --silent --show-error --max-time 15 \
    -H 'Content-Type: application/json' --data-binary "@$1" \
    "$api/configs" >> "$out_dir/transport.log" 2>&1
}

reboot_machine() {
  curl --fail --silent --show-error --max-time 15 -X PUT \
    "$api/machine:reboot" >> "$out_dir/transport.log" 2>&1
  sleep 6
}

launch_readyfs() {
  local launch_try
  for launch_try in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 30 \
      -H 'Content-Type: application/octet-stream' --data-binary "@$prg" \
      "$api/runners:run_prg" >> "$out_dir/transport.log" 2>&1; then
      sleep 3
      return 0
    fi
    sleep 2
  done
  return 1
}

restore_original() {
  local restore_rc=0
  if [ "$configured" -eq 1 ] && [ -s "$restore_payload" ]; then
    post_config "$restore_disabled" || restore_rc=1
    sleep 1
    post_config "$restore_payload" || restore_rc=1
    reboot_machine || restore_rc=1
    curl --fail --silent --show-error --max-time 15 \
      "$api/configs/SoftIEC%20Drive%20Settings" \
      -o "$out_dir/restored-softiec-config.json" || restore_rc=1
    curl --fail --silent --show-error --max-time 15 "$api/drives" \
      -o "$out_dir/restored-drives.json" || restore_rc=1
    if [ "$restore_rc" -eq 0 ]; then
      python3 - "$original_config" "$out_dir/restored-softiec-config.json" \
        "$out_dir/restored-drives.json" "$partition" <<'PY' || restore_rc=1
import json
import sys
before = json.load(open(sys.argv[1], encoding="utf-8"))["SoftIEC Drive Settings"]
after = json.load(open(sys.argv[2], encoding="utf-8"))["SoftIEC Drive Settings"]
for key in ("IEC Drive", "Soft Drive Bus ID", "Default Path"):
    if before.get(key) != after.get(key):
        raise SystemExit(f"SoftIEC restore mismatch for {key}")
drives = json.load(open(sys.argv[3], encoding="utf-8"))["drives"]
soft = next(value for item in drives for value in item.values()
            if isinstance(value, dict) and "partitions" in value)
part = int(sys.argv[4])
expected = str(before["Default Path"]).rstrip("/")
matches = [item for item in soft.get("partitions", []) if int(item["id"]) == part]
if len(matches) != 1 or matches[0].get("path", "").rstrip("/") != expected:
    raise SystemExit(f"restored partition mismatch: {matches!r}")
PY
    fi
  fi
  return "$restore_rc"
}

capture_screen() {
  local label attempt step_dir
  label="$1"
  step_dir="$out_dir/$label"
  mkdir -p "$step_dir"
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 10 \
      "$api/machine:readmem?address=0400&length=1000" \
      -o "$step_dir/screen_0400.bin" >> "$out_dir/transport.log" 2>&1; then
      python3 "$readyfs_root/build_support/decode_c64_screen.py" \
        "$step_dir/screen_0400.bin" --output "$step_dir/screen.txt"
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_screen() {
  local label="$1" required="$2" attempt prompt_count
  for attempt in $(seq 1 60); do
    sleep 1
    capture_screen "$label"
    prompt_count="$(grep -c 'RF>' "$out_dir/$label/screen.txt" || true)"
    if grep -q "$required" "$out_dir/$label/screen.txt" &&
       [ "$prompt_count" -ge 2 ]; then return 0; fi
    if grep -q 'UNKNOWN; TYPE HELP' "$out_dir/$label/screen.txt"; then return 2; fi
  done
  return 1
}

verify_owner_ui() {
  local root="$1" label="$2" marker_screen
  type_command "$label" "type $root/$marker_name" 'READ 116 BYTES'
  marker_screen="$out_dir/$label/screen.txt"
  grep -q 'READYFS-OWNED-ROOT' "$marker_screen"
  grep -q "run.id=$run_id" "$marker_screen"
  grep -q 'created.utc=2026-08-16T02:03:56Z' "$marker_screen"
  grep -q 'policy=preserve-by-default' "$marker_screen"
}

verify_both_owners() {
  local label="$1"
  verify_owner_ui "$udos_root" "$label-usb"
  verify_owner_ui "$sd_root" "$label-sd"
}

type_command() {
  local case_id="$1" command="$2" expected="$3"
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" $'clear\r' \
    >> "$out_dir/transport.log" 2>&1
  sleep 1
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" "$command"$'\r' \
    >> "$out_dir/transport.log" 2>&1
  if wait_screen "$case_id" "$expected"; then :
  elif [ "$?" -eq 2 ]; then
    printf '%s\tRETRY-UNKNOWN\t%s\n' "$case_id" "$command" \
      >> "$out_dir/results.tsv"
    C64U_HOST="$c64u_host" /bin/bash \
      "$readyfs_root/build_support/c64u_type_text.sh" $'clear\r' \
      >> "$out_dir/transport.log" 2>&1
    sleep 1
    C64U_HOST="$c64u_host" /bin/bash \
      "$readyfs_root/build_support/c64u_type_text.sh" "$command"$'\r' \
      >> "$out_dir/transport.log" 2>&1
    wait_screen "$case_id" "$expected"
  else return 1
  fi
  printf '%s\tPASS\t%s\n' "$case_id" "$command" >> "$out_dir/results.tsv"
}

finish() {
  rc=$?
  trap - EXIT
  if ! restore_original; then rc=97; fi
  if [ "$rc" -eq 0 ]; then printf 'success\n' > "$status_file"
  else printf 'failed:%s\n' "$rc" > "$status_file"; fi
  exit "$rc"
}
trap finish EXIT

test -s "$prg"
{
  printf 'run_id=%s\n' "$run_id"
  printf 'partition=%s\n' "$partition"
  printf 'owned_udos_root=%s\n' "$udos_root"
  printf 'owned_sd_root=%s\n' "$sd_root"
  printf 'mapped_root=%s\n' "$mapped_root"
  printf 'mapping_policy=cd:/ then relative cd:usb1; no config alteration\n'
  printf 'soft_case_root=%s\n' "$soft_case_root"
  printf 'case_parent=%s\n' "$case_parent"
  printf 'softiec_root=%s\n' "$soft_root"
  printf 'existing_dir_phase=%s\n' "$existing_dir"
  printf 'softiec_refresh_phase=%s\n' "$refresh_softiec"
  printf 'seed_dir_phase=%s\n' "$seed_dir"
  printf 'preserve_files=true\n'
} > "$out_dir/manifest.txt"

if [ "$refresh_softiec" -eq 1 ]; then
  curl --fail --silent --show-error --max-time 15 \
    "$api/configs/SoftIEC%20Drive%20Settings" \
    -o "$out_dir/pre-refresh-softiec-config.json"
  reboot_machine
  curl --fail --silent --show-error --max-time 15 \
    "$api/configs/SoftIEC%20Drive%20Settings" \
    -o "$out_dir/post-refresh-softiec-config.json"
  python3 - "$out_dir/pre-refresh-softiec-config.json" \
    "$out_dir/post-refresh-softiec-config.json" <<'PY'
import json
import sys
before = json.load(open(sys.argv[1], encoding="utf-8"))["SoftIEC Drive Settings"]
after = json.load(open(sys.argv[2], encoding="utf-8"))["SoftIEC Drive Settings"]
for key in ("IEC Drive", "Soft Drive Bus ID", "Default Path"):
    if before.get(key) != after.get(key):
        raise SystemExit(f"SoftIEC refresh changed {key}")
PY
fi

if ! launch_readyfs; then
  printf 'ReadyFS launch failed after retries\n' >> "$out_dir/transport.log"
  exit 1
fi
capture_screen launch
grep -q 'READYFS LAB' "$out_dir/launch/screen.txt"

type_command RF-HW-SI-001 "probe softiec" 'SOFTWARE IEC TARGET'
curl --fail --silent --show-error --max-time 15 \
  "$api/configs/SoftIEC%20Drive%20Settings" -o "$original_config"
curl --fail --silent --show-error --max-time 15 "$api/drives" \
  -o "$out_dir/drives-before.json"
python3 - "$out_dir/drives-before.json" "$partition" <<'PY'
import json
import sys
drives = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
soft = next(value for item in drives for value in item.values()
            if isinstance(value, dict) and "partitions" in value)
part = int(sys.argv[2])
matches = [item for item in soft.get("partitions", []) if int(item["id"]) == part]
if len(matches) != 1:
    raise SystemExit(f"SoftwareIEC partition {part} missing: {matches!r}")
PY
type_command RF-HW-SI-002 "volume s$partition:/" 'FREE UNAVAILABLE'

verify_both_owners RF-HW-SI-005-owner-before-udos-mkdir
# Firmware 3.14 exposes ordinary SoftwareIEC file opens and CD:, but not MD:.
# Create the owned test container through UltimateDOS, then exercise its files
# through SoftwareIEC's independent IEC data path.
if [ "$existing_dir" -eq 1 ]; then
  type_command RF-HW-SI-005 "dir $udos_case_root" 'ENTRIES:'
else
  type_command RF-HW-SI-005 "mkdir $udos_case_root" 'DIRECTORY CREATED'
fi
verify_both_owners RF-HW-SI-005B-owner-before-soft-write
if [ "$seed_dir" -eq 1 ]; then
  type_command RF-HW-SI-005C \
    "write $udos_case_root/rfseed.seq \"seed\" --line" 'WRITE COMPLETE'
  type_command RF-HW-SI-005D "type $udos_case_root/rfseed.seq" 'SEED'
fi
type_command RF-HW-SI-005B "write $soft_case_root/sfa \"soft alpha\" --line" \
  'WRITE COMPLETE'
type_command RF-HW-SI-006 "type $soft_case_root/sfa" 'SOFT ALPHA'

verify_both_owners RF-HW-SI-007-owner-before-soft-to-udos
type_command RF-HW-SI-007 \
  "copy $soft_case_root/sfa $outside_copy" 'COPIED'
type_command RF-HW-SI-008 "type $outside_copy" 'SOFT ALPHA'

verify_both_owners RF-HW-SI-009-owner-before-udos-write
type_command RF-HW-SI-009 "write $outside_source \"host beta\" --line" \
  'WRITE COMPLETE'
verify_both_owners RF-HW-SI-010-owner-before-udos-to-soft
type_command RF-HW-SI-010 \
  "copy $outside_source $soft_case_root/fromu" 'COPIED'
grep -Fqi 'VERIFY: IDENTICAL' "$out_dir/RF-HW-SI-010/screen.txt"
type_command RF-HW-SI-011 "type $soft_case_root/fromu" 'HOST BETA'
type_command RF-HW-SI-011B "compare $outside_source $soft_case_root/fromu" \
  'VERIFY: IDENTICAL'

verify_both_owners RF-HW-SI-012-owner-before-udos-mkdir
type_command RF-HW-SI-012 "mkdir $udos_case_root/nested" 'DIRECTORY CREATED'
verify_both_owners RF-HW-SI-013-owner-before-nested-write
type_command RF-HW-SI-013 "write $soft_case_root/nested/inside \"inside\" --line" \
  'WRITE COMPLETE'
type_command RF-HW-SI-014 "type $soft_case_root/nested/inside" 'INSIDE'

restore_original
configured=0
curl --fail --silent --show-error --max-time 15 "$api/drives" \
  -o "$out_dir/drives-after.json"
curl --fail --silent --show-error --max-time 15 \
  "$api/configs/SoftIEC%20Drive%20Settings" -o "$out_dir/config-after.json"
python3 - "$out_dir/drives-after.json" "$partition" "$original_config" \
  "$out_dir/config-after.json" <<'PY'
import json
import sys
drives = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
soft = next(value for item in drives for value in item.values()
            if isinstance(value, dict) and "partitions" in value)
part = int(sys.argv[2])
matches = [item for item in soft.get("partitions", []) if int(item["id"]) == part]
if len(matches) != 1:
    raise SystemExit(f"SoftwareIEC partition disappeared: {matches!r}")
before = json.load(open(sys.argv[3], encoding="utf-8"))["SoftIEC Drive Settings"]
after = json.load(open(sys.argv[4], encoding="utf-8"))["SoftIEC Drive Settings"]
for key in ("IEC Drive", "Soft Drive Bus ID", "Default Path"):
    if before.get(key) != after.get(key):
        raise SystemExit(f"SoftIEC config changed for {key}")
PY
type_command RF-HW-SI-016 "volume s$partition:/" 'FREE UNAVAILABLE'
type_command RF-HW-SI-017 "dir $mapped_root/$case_rel" 'fromu.seq'
type_command RF-HW-SI-018 "type $mapped_root/$case_rel/nested/inside.seq" 'INSIDE'
verify_both_owners RF-HW-SI-019-owner-after

printf 'completed=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$out_dir/manifest.txt"
