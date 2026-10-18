#!/usr/bin/env bash
set -euo pipefail

# No-FTP, marker-gated preserve-only SoftIEC write probe. ReadyFS/UltimateDOS
# reads both exact owner markers before and after the one allowed file create.
readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
out_dir="${READYFS_SOFTWRITE_OUT:?}"
api="http://$c64u_host/v1"
run_id="readyfs-20260815-190355-79014"
marker=".readyfs-owner-$run_id"
usb_root="u:/USB1/READYFS_TEST/$run_id"
sd_root="u:/SD/READYFS_TEST/$run_id"
readyfs_prg="${READYFS_APP_PRG:-$readyfs_root/artifacts/readyfs/readyfs.prg}"
overlay_prg="$readyfs_root/artifacts/readyfs/readyfs-overlay.prg"
overlay_disk="$readyfs_root/artifacts/readyfs/readyfs-overlay-lab.d81"
probe_prg="$out_dir/softwrite-probe.prg"
mode="${READYFS_SOFTWRITE_MODE:-probe}"
app_tag="${READYFS_SOFTWRITE_TAG:-ap0702}"
probe_dir="${READYFS_SOFTWRITE_DIR:-rf065128}"
probe_leaf="${READYFS_SOFTWRITE_LEAF:-kp065128}"
compare_dir="${READYFS_SOFTCOMPARE_DIR:-rf081054}"
compare_source="${READYFS_SOFTCOMPARE_SOURCE:-us081054}"
copy_leaf="${READYFS_SOFTCOPY_LEAF:-fx0001}"
tree_rel="${READYFS_SOFTTREE_REL:-rf091800/rf100154}"
tree_source="${READYFS_SOFTTREE_SOURCE:-us100154}"
recursive_dest="${READYFS_SOFTRECUR_DEST:-rr111500}"
recursive_existing="${READYFS_SOFTRECUR_EXISTING:-0}"
reverse_source="${READYFS_SOFTREVERSE_SOURCE:-rf091800/rr111505}"
reverse_dest="${READYFS_SOFTREVERSE_DEST:-rv111500}"
reverse_existing="${READYFS_SOFTREVERSE_EXISTING:-0}"
media_dir="${READYFS_MEDIA_DIR:-md111500}"
media_existing="${READYFS_MEDIA_EXISTING:-0}"
softmap_partition="${READYFS_SOFTMAP_PARTITION:-1}"
softmap_existing_partition="${READYFS_SOFTMAP_EXISTING_PARTITION:-0}"
whatif_map_rel="${READYFS_WHATIF_MAP_REL:-rf091800/rr111505}"
whatif_dest="${READYFS_WHATIF_DEST:-wf111500}"
test_speed="${READYFS_SOFTWRITE_SPEED_MHZ:-}"
force_fail_after_owners="${READYFS_FORCE_FAIL_AFTER_OWNERS:-0}"
mounted=0
softmap_added=0

if [[ ! "$app_tag" =~ ^[a-z0-9]{1,8}$ ]]; then
  printf 'unsafe app tag: %s\n' "$app_tag" >&2
  exit 64
fi
if [[ ! "$probe_dir" =~ ^rf[0-9]{6}$ ]] ||
   [[ ! "$probe_leaf" =~ ^kp[0-9]{6}$ ]]; then
  printf 'unsafe probe target: %s/%s\n' "$probe_dir" "$probe_leaf" >&2
  exit 64
fi
if [[ ! "$compare_dir" =~ ^rf[0-9]{6}$ ]] ||
   [[ ! "$compare_source" =~ ^us[0-9]{6}$ ]]; then
  printf 'unsafe compare target: %s/%s\n' "$compare_dir" "$compare_source" >&2
  exit 64
fi
if [[ ! "$copy_leaf" =~ ^fx[0-9]{4}$ ]]; then
  printf 'unsafe copy leaf: %s\n' "$copy_leaf" >&2
  exit 64
fi
if [[ ! "$tree_rel" =~ ^rf[0-9]{6}/(rf|rr)[0-9]{6}$ ]] ||
   [[ ! "$tree_source" =~ ^us[0-9]{6}$ ]]; then
  printf 'unsafe tree verification target: %s/%s\n' \
    "$tree_rel" "$tree_source" >&2
  exit 64
fi
if [[ ! "$recursive_dest" =~ ^rr[0-9]{6}$ ]]; then
  printf 'unsafe recursive destination: %s\n' "$recursive_dest" >&2
  exit 64
fi
if [[ ! "$media_dir" =~ ^md[0-9]{6}$ ]]; then
  printf 'unsafe media directory: %s\n' "$media_dir" >&2
  exit 64
fi
if [[ "$media_existing" != 0 && "$media_existing" != 1 ]]; then
  printf 'unsafe media existing flag: %s\n' "$media_existing" >&2
  exit 64
fi
if [[ ! "$softmap_partition" =~ ^[0-9]+$ ]] ||
   (( softmap_partition < 1 || softmap_partition > 255 )); then
  printf 'unsafe SoftIEC map partition: %s\n' "$softmap_partition" >&2
  exit 64
fi
if [[ ! "$softmap_existing_partition" =~ ^[0-9]+$ ]] ||
   (( softmap_existing_partition > 255 )); then
  printf 'unsafe existing SoftIEC partition: %s\n' \
    "$softmap_existing_partition" >&2
  exit 64
fi
if [[ ! "$whatif_map_rel" =~ ^rf[0-9]{6}/rr[0-9]{6}$ ]]; then
  printf 'unsafe existing SoftIEC mapping: %s\n' "$whatif_map_rel" >&2
  exit 64
fi
if [[ ! "$whatif_dest" =~ ^wf[0-9]{6}$ ]]; then
  printf 'unsafe WhatIf destination: %s\n' "$whatif_dest" >&2
  exit 64
fi
if [[ "$recursive_existing" != 0 && "$recursive_existing" != 1 ]]; then
  printf 'unsafe recursive existing flag: %s\n' "$recursive_existing" >&2
  exit 64
fi
if [[ ! "$reverse_source" =~ ^rf[0-9]{6}/rr[0-9]{6}$ ]] ||
   [[ ! "$reverse_dest" =~ ^rv[0-9]{6}$ ]]; then
  printf 'unsafe reverse recursive target: %s/%s\n' \
    "$reverse_source" "$reverse_dest" >&2
  exit 64
fi
if [[ "$reverse_existing" != 0 && "$reverse_existing" != 1 ]]; then
  printf 'unsafe reverse existing flag: %s\n' "$reverse_existing" >&2
  exit 64
fi
if [[ -n "$test_speed" && "$test_speed" != 1 &&
      "$test_speed" != 16 && "$test_speed" != 64 ]]; then
  printf 'unsafe test speed: %s\n' "$test_speed" >&2
  exit 64
fi
if [[ "$force_fail_after_owners" != 0 &&
      "$force_fail_after_owners" != 1 ]]; then
  printf 'unsafe forced-failure flag: %s\n' "$force_fail_after_owners" >&2
  exit 64
fi
if [[ "$force_fail_after_owners" == 1 &&
      ( "$mode" != whatif || -z "$test_speed" ) ]]; then
  printf 'forced failure requires WhatIf mode and an explicit test speed\n' >&2
  exit 64
fi

mkdir -p "$out_dir"
printf 'running\n' > "$out_dir/status.txt"
printf 'case\tresult\tcommand\n' > "$out_dir/results.tsv"
finish() {
  rc=$? restore_rc=0 speed_rc=0
  trap - EXIT
  if [ "$force_fail_after_owners" -eq 1 ] &&
     [ -s "$out_dir/forced-failure.txt" ]; then
    # The deliberate exit has occurred, but the app and test-speed state are
    # still live. Re-read both filesystem owners before any drive/config
    # restoration (which may require a core reboot and erase the app).
    if ! verify_owners RF-HW-FAIL-owner-after-trigger; then
      restore_rc=1
    fi
  fi
  if [ "$softmap_added" -eq 1 ]; then
    C64U_HOST="$c64u_host" /bin/bash \
      "$readyfs_root/build_support/c64u_type_text.sh" $'clear\r' \
      >> "$out_dir/transport.log" 2>&1 || restore_rc=1
    sleep 1
    C64U_HOST="$c64u_host" /bin/bash \
      "$readyfs_root/build_support/c64u_type_text.sh" \
      "dismount s$softmap_partition: --force"$'\r' \
      >> "$out_dir/transport.log" 2>&1 || restore_rc=1
    sleep 30
    curl --fail --silent --show-error --max-time 15 "$api/drives" \
      -o "$out_dir/softmap-exit-drives.json" || restore_rc=1
    if [ "$restore_rc" -eq 0 ]; then
      python3 - "$out_dir/softmap-exit-drives.json" \
        "$softmap_partition" <<'PY' || restore_rc=1
import json
import sys
drives = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
soft = next(value for item in drives for value in item.values()
            if isinstance(value, dict) and "partitions" in value)
part = int(sys.argv[2])
if any(int(item["id"]) == part for item in soft.get("partitions", [])):
    raise SystemExit(f"SoftIEC partition {part} survived emergency unmap")
PY
    fi
  fi
  if [ "$mounted" -eq 1 ]; then
    curl --fail --silent --show-error --max-time 15 -X PUT \
      "$api/drives/a:remove" >> "$out_dir/transport.log" 2>&1 || restore_rc=1
  fi
  if [ -s "$out_dir/restore-drive-a.json" ]; then
    curl --fail --silent --show-error --max-time 15 \
      -H 'Content-Type: application/json' \
      --data-binary "@$out_dir/restore-drive-a.json" \
      "$api/configs" >> "$out_dir/transport.log" 2>&1 || restore_rc=1
  fi
  if [ -s "$out_dir/original-drives.json" ]; then
    sleep 1
    curl --fail --silent --show-error --max-time 15 "$api/drives" \
      -o "$out_dir/restored-drives.json" || restore_rc=1
    if [ "$restore_rc" -eq 0 ]; then
      python3 - "$out_dir/original-drives.json" \
        "$out_dir/restored-drives.json" <<'PY' || restore_rc=1
import json
import sys

def drive_a(path):
    data = json.load(open(path, encoding="utf-8"))["drives"]
    return next(item["a"] for item in data if "a" in item)

before = drive_a(sys.argv[1])
after = drive_a(sys.argv[2])
for key in ("enabled", "bus_id", "type", "image_file", "image_path"):
    if before.get(key) != after.get(key):
        raise SystemExit(f"drive A restore mismatch for {key}")
PY
    fi
  fi
  if [ -s "$out_dir/restore-speed.json" ]; then
    if ! curl --fail --silent --show-error --max-time 15 \
      -H 'Content-Type: application/json' \
      --data-binary "@$out_dir/restore-speed.json" \
      "$api/configs" >> "$out_dir/transport.log" 2>&1; then
      /bin/bash "$readyfs_root/build_support/run_readyfs_c64u_restore_speed.sh" \
        "$out_dir" "$c64u_host" >> "$out_dir/transport.log" 2>&1 || speed_rc=1
    fi
    sleep 1
    curl --fail --silent --show-error --max-time 15 \
      "$api/configs/U64%20Specific%20Settings" \
      -o "$out_dir/restored-u64-config.json" || speed_rc=1
    if [ "$speed_rc" -eq 0 ]; then
      python3 - "$out_dir/original-u64-config.json" \
        "$out_dir/restored-u64-config.json" \
        "$force_fail_after_owners" <<'PY' || speed_rc=1
import json
import sys

def settings(path):
    return json.load(open(path, encoding="utf-8"))["U64 Specific Settings"]

before = settings(sys.argv[1])
after = settings(sys.argv[2])
for key in ("Turbo Control", "CPU Speed"):
    if before[key] != after[key]:
        raise SystemExit(f"CPU-speed restore mismatch for {key}")
if int(sys.argv[3]) and before != after:
    raise SystemExit("full U64 Specific Settings object was not restored exactly")
PY
    fi
    if [ "$speed_rc" -ne 0 ]; then restore_rc=1; fi
  fi
  if [ "$restore_rc" -ne 0 ]; then rc=97; fi
  if [ "$rc" -eq 0 ]; then printf 'success\n' > "$out_dir/status.txt"
  else printf 'failed:%s\n' "$rc" > "$out_dir/status.txt"; fi
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

configure_test_speed() {
  [ -n "$test_speed" ] || return 0
  curl --fail --silent --show-error --max-time 15 \
    "$api/configs/U64%20Specific%20Settings" \
    -o "$out_dir/original-u64-config.json"
  python3 - "$test_speed" "$out_dir/original-u64-config.json" \
    "$out_dir/restore-speed.json" "$out_dir/set-speed-stage.json" \
    "$out_dir/set-speed-manual.json" "$out_dir/set-speed.json" <<'PY'
import json
import sys

mhz = int(sys.argv[1])
source = json.load(open(sys.argv[2], encoding="utf-8"))["U64 Specific Settings"]
json.dump({"U64 Specific Settings": {
    "Turbo Control": source["Turbo Control"],
    "CPU Speed": source["CPU Speed"],
}}, open(sys.argv[3], "w", encoding="utf-8"))
json.dump({"U64 Specific Settings": {
    "Turbo Control": "Manual",
    "CPU Speed": source["CPU Speed"],
}}, open(sys.argv[4], "w", encoding="utf-8"))
json.dump({"U64 Specific Settings": {
    "Turbo Control": "Manual",
    "CPU Speed": f"{mhz:2d}",
}}, open(sys.argv[5], "w", encoding="utf-8"))
json.dump({"U64 Specific Settings": {
    "Turbo Control": "Off" if mhz == 1 else "Manual",
    "CPU Speed": f"{mhz:2d}",
}}, open(sys.argv[6], "w", encoding="utf-8"))
PY
  # Firmware can reject the aggregate JSON endpoint with HTTP 500 while its
  # per-setting interface remains healthy. Change only the two captured
  # fields, entering Manual before changing speed and applying Off last for
  # the 1 MHz case. The EXIT trap still restores the exact saved payload.
  curl --fail --silent --show-error --max-time 15 -X PUT \
    "$api/configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual" \
    >> "$out_dir/transport.log" 2>&1
  sleep 1
  curl --fail --silent --show-error --max-time 15 -X PUT \
    "$api/configs/U64%20Specific%20Settings/CPU%20Speed?value=$test_speed" \
    >> "$out_dir/transport.log" 2>&1
  sleep 1
  if [ "$test_speed" -eq 1 ]; then
    curl --fail --silent --show-error --max-time 15 -X PUT \
      "$api/configs/U64%20Specific%20Settings/Turbo%20Control?value=Off" \
      >> "$out_dir/transport.log" 2>&1
    sleep 1
  fi
  curl --fail --silent --show-error --max-time 15 \
    "$api/configs/U64%20Specific%20Settings" \
    -o "$out_dir/observed-u64-config.json"
  python3 - "$test_speed" "$out_dir/observed-u64-config.json" <<'PY'
import json
import sys

expected = int(sys.argv[1])
settings = json.load(open(sys.argv[2], encoding="utf-8"))["U64 Specific Settings"]
if int(str(settings["CPU Speed"]).strip()) != expected:
    raise SystemExit("test CPU speed was not admitted")
PY
}

mount_overlay_fixture() {
  test -s "$overlay_prg"
  test -s "$overlay_disk"
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/original-drives.json"
  python3 - "$out_dir/original-drives.json" \
    "$out_dir/restore-drive-a.json" "$out_dir/test-drive-a.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
drive = next(item["a"] for item in data if "a" in item)
if drive.get("image_file") or drive.get("image_path"):
    raise SystemExit("drive A is occupied; refusing to replace mounted media")
restore = {"Drive A Settings": {
    "Drive": "Enabled" if drive["enabled"] else "Disabled",
    "Drive Type": drive["type"],
    "Drive Bus ID": drive["bus_id"],
}}
test = {"Drive A Settings": {
    "Drive": "Enabled", "Drive Type": "1581", "Drive Bus ID": 8,
}}
if not (drive["enabled"] and drive["bus_id"] == 8 and
        drive["type"] == "1581"):
    json.dump(restore, open(sys.argv[2], "w", encoding="utf-8"))
    json.dump(test, open(sys.argv[3], "w", encoding="utf-8"))
PY
  if [ -s "$out_dir/test-drive-a.json" ]; then
    curl --fail --silent --show-error --max-time 15 \
      -H 'Content-Type: application/json' \
      --data-binary "@$out_dir/test-drive-a.json" \
      "$api/configs" >> "$out_dir/transport.log" 2>&1
    sleep 1
  fi
  curl --fail --silent --show-error --max-time 60 -X POST \
    -F "file=@$overlay_disk" -F 'mode=readwrite' -F 'type=d81' \
    "$api/drives/a:mount" > "$out_dir/mount-response.json"
  mounted=1
  readyfs_prg="$overlay_prg"
  sleep 2
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/mounted-drives.json"
  python3 - "$out_dir/mounted-drives.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
drive = next(item["a"] for item in data if "a" in item)
if not drive["enabled"] or drive["bus_id"] != 8 or drive["type"] != "1581":
    raise SystemExit("ReadyFS overlay fixture mount was not admitted")
PY
}

launch_prg() {
  local attempt
  for attempt in $(seq 1 10); do
    if curl --fail --silent --show-error --max-time 30 \
      -H 'Content-Type: application/octet-stream' --data-binary "@$1" \
      "$api/runners:run_prg" >> "$out_dir/transport.log" 2>&1; then
      sleep 3
      return 0
    fi
    sleep 2
  done

  # Firmware 3.14 can leave the REST attachment handoff returning
  # 404/"Cannot open file" while drive mounting and C64 DMA memory access
  # remain healthy. The overlay fixture is already mounted on the exact
  # snapshotted Drive A, so use the normal C64 LOAD path as a bounded fallback.
  # This launches only the build-owned READYFS-OVERLAY program and does not
  # issue a filesystem mutation; the caller still waits for BATCH: READY and
  # performs both owner-marker gates before any test command.
  if [ "$1" = "$overlay_prg" ] && [ "$mounted" -eq 1 ]; then
    printf 'runner unavailable; falling back to IEC fixture launch\n' \
      >> "$out_dir/transport.log"
    curl --fail --silent --show-error --max-time 15 -X PUT \
      "$api/machine:reset" >> "$out_dir/transport.log" 2>&1
    sleep 3
    curl --fail --silent --show-error --max-time 15 -X PUT \
      "$api/machine:resume" >> "$out_dir/transport.log" 2>&1
    sleep 7
    C64U_HOST="$c64u_host" /bin/bash \
      "$readyfs_root/build_support/c64u_type_text.sh" \
      $'load"readyfs-overlay",8,1\r' \
      >> "$out_dir/transport.log" 2>&1
    # READYFS-OVERLAY is 167 disk blocks. Stock serial IEC can take well over
    # a minute, especially when the REST harness has just released DMA. Wait
    # without screen-memory polling so the KERNAL transfer is not stalled.
    local load_wait="${READYFS_IEC_LAUNCH_WAIT_S:-180}"
    local load_step
    while [ "$load_wait" -gt 0 ]; do
      if [ "$load_wait" -gt 60 ]; then load_step=60
      else load_step="$load_wait"
      fi
      sleep "$load_step"
      load_wait=$((load_wait - load_step))
      printf 'IEC fixture load wait remaining=%s\n' "$load_wait" \
        >> "$out_dir/transport.log"
    done
    C64U_HOST="$c64u_host" /bin/bash \
      "$readyfs_root/build_support/c64u_type_text.sh" $'sys2061\r' \
      >> "$out_dir/transport.log" 2>&1
    sleep 3
    return 0
  fi
  return 1
}

capture_screen() {
  local label="$1" dir="$out_dir/$1"
  mkdir -p "$dir"
  curl --fail --silent --show-error --max-time 10 \
    "$api/machine:readmem?address=0400&length=1000" \
    -o "$dir/screen_0400.bin" >> "$out_dir/transport.log" 2>&1
  python3 "$readyfs_root/build_support/decode_c64_screen.py" \
    "$dir/screen_0400.bin" --output "$dir/screen.txt"
}

wait_screen() {
  local label="$1" expected="$2" attempts="${3:-60}"
  local interval="${4:-1}" pre_delay="${5:-0}"
  if [ "$pre_delay" -gt 0 ]; then sleep "$pre_delay"; fi
  for attempt in $(seq 1 "$attempts"); do
    sleep "$interval"
    capture_screen "$label"
    grep -Fqi "$expected" "$out_dir/$label/screen.txt" && return 0
  done
  return 1
}

wait_command_screen() {
  local label="$1" expected="$2" attempts="${3:-60}"
  local pre_delay="${4:-0}" prompts
  local delay_step
  # REST screen DMA can stall active physical KERNAL/SoftwareIEC transfers.
  # Long file operations therefore get a quiet admission window, split into
  # at-most-60-second waits so progress remains observable in the log.
  while [ "$pre_delay" -gt 0 ]; do
    if [ "$pre_delay" -gt 60 ]; then delay_step=60
    else delay_step="$pre_delay"
    fi
    sleep "$delay_step"
    pre_delay=$((pre_delay - delay_step))
    printf 'command quiet wait remaining=%s label=%s\n' \
      "$pre_delay" "$label" >> "$out_dir/transport.log"
  done
  for attempt in $(seq 1 "$attempts"); do
    sleep 1
    capture_screen "$label"
    prompts="$(grep -Fc 'RF>' "$out_dir/$label/screen.txt" || true)"
    if grep -Fqi "$expected" "$out_dir/$label/screen.txt" &&
       [ "$prompts" -ge 2 ]; then return 0; fi
  done
  return 1
}

type_command() {
  local label="$1" command="$2" expected="$3" attempts="${4:-60}"
  local pre_delay="${5:-0}"
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" $'clear\r' \
    >> "$out_dir/transport.log" 2>&1
  sleep 1
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" "$command"$'\r' \
    >> "$out_dir/transport.log" 2>&1
  wait_command_screen "$label" "$expected" "$attempts" "$pre_delay"
  printf '%s\tPASS\t%s\n' "$label" "$command" >> "$out_dir/results.tsv"
}

verify_owners() {
  local prefix="$1"
  type_command "$prefix-usb" "type $usb_root/$marker" 'READ 116 BYTES'
  grep -Fq 'READYFS-OWNED-ROOT' "$out_dir/$prefix-usb/screen.txt"
  grep -Fq "run.id=$run_id" "$out_dir/$prefix-usb/screen.txt"
  type_command "$prefix-sd" "type $sd_root/$marker" 'READ 116 BYTES'
  grep -Fq 'READYFS-OWNED-ROOT' "$out_dir/$prefix-sd/screen.txt"
  grep -Fq "run.id=$run_id" "$out_dir/$prefix-sd/screen.txt"
}

configure_test_speed
if [ "$mode" = recursive ] || [ "$mode" = treeverify ] ||
   [ "$mode" = reverse ] || [ "$mode" = reverseverify ] ||
   [ "$mode" = media ] || [ "$mode" = metadata ] ||
   [ "$mode" = mapwhatif ] ||
   [ "$mode" = whatif ]; then
  mount_overlay_fixture
fi
test -s "$readyfs_prg"
if [ "$mode" = probe ]; then
  cl65 -t c64 -Os -o "$probe_prg" \
    -DSOFTWRITE_DIR="\"$probe_dir\"" \
    -DSOFTWRITE_LEAF="\"$probe_leaf\"" \
    "$readyfs_root/src/apps/readyfs/softwrite_probe.c" \
    > "$out_dir/build.log" 2>&1
elif [ "$mode" != app ] && [ "$mode" != appabs ] &&
     [ "$mode" != read ] && [ "$mode" != compare ] &&
     [ "$mode" != copy ] && [ "$mode" != treeverify ] &&
     [ "$mode" != recursive ] && [ "$mode" != recursiveprep ] &&
     [ "$mode" != reverse ] && [ "$mode" != reverseverify ] &&
     [ "$mode" != media ] && [ "$mode" != metadata ] &&
     [ "$mode" != mapwhatif ] &&
     [ "$mode" != whatif ]; then
  printf 'unsupported mode: %s\n' "$mode" >&2
  exit 64
fi
launch_prg "$readyfs_prg"
if [ "$mode" = recursive ] || [ "$mode" = treeverify ] ||
   [ "$mode" = reverse ] || [ "$mode" = reverseverify ] ||
   [ "$mode" = media ] || [ "$mode" = metadata ] ||
   [ "$mode" = mapwhatif ] ||
   [ "$mode" = whatif ]; then
  # Do not take an early READYFS-LAB screenshot: it can land just as RFMATCH
  # starts loading and permanently pin that KERNAL transfer at 64 MHz. Give
  # the complete sidecar preload one uninterrupted interval, then use sparse
  # bounded admission polls.
  wait_screen launch-overlay 'BATCH: READY' 60 5 \
    "${READYFS_OVERLAY_ADMISSION_WAIT_S:-240}"
else
  wait_screen launch 'READYFS LAB'
fi
verify_owners RF-HW-SW-owner-before
if [ "$force_fail_after_owners" -eq 1 ]; then
  verify_owners RF-HW-FAIL-owner-before-trigger
  printf 'forced failure after admitted speed change and dual owner checks\n' \
    > "$out_dir/forced-failure.txt"
  exit 73
fi
if [ "$mode" = probe ]; then
  launch_prg "$probe_prg"
  wait_screen RF-HW-SW-probe 'DONE'
  grep -Fqi 'PATH 00' "$out_dir/RF-HW-SW-probe/screen.txt"
  grep -Fqi 'PREFLIGHT 62' "$out_dir/RF-HW-SW-probe/screen.txt"
  grep -Fqi 'OPEN 00' "$out_dir/RF-HW-SW-probe/screen.txt"
  grep -Fqi 'WRITE 6' "$out_dir/RF-HW-SW-probe/screen.txt"
  grep -Fqi 'REOPEN 00' "$out_dir/RF-HW-SW-probe/screen.txt"
  grep -Fqi 'READ 6' "$out_dir/RF-HW-SW-probe/screen.txt"
  launch_prg "$readyfs_prg"
  wait_screen relaunch 'READYFS LAB'
  type_command RF-HW-SW-readback \
    "type $usb_root/$probe_dir/$probe_leaf.seq" 'PROBE'
  preserve="USB1/READYFS_TEST/$run_id/$probe_dir/$probe_leaf.seq"
elif [ "$mode" = app ] || [ "$mode" = appabs ]; then
  type_command RF-HW-SW-app-cd \
    "cd s0:/READYFS_TEST/$run_id/$probe_dir" 'RF>'
  if [ "$mode" = appabs ]; then
    write_target="s0:/READYFS_TEST/$run_id/$probe_dir/$app_tag"
  else
    write_target="$app_tag"
  fi
  type_command RF-HW-SW-app-write \
    "write $write_target \"app\" --line" \
    'WRITE COMPLETE'
  type_command RF-HW-SW-app-soft-read \
    "type $write_target" 'APP'
  type_command RF-HW-SW-app-udos-read \
    "type $usb_root/$probe_dir/$app_tag.seq" 'APP'
  preserve="USB1/READYFS_TEST/$run_id/$probe_dir/$app_tag.seq"
elif [ "$mode" = read ]; then
  type_command RF-HW-SW-read-cd \
    "cd s0:/READYFS_TEST/$run_id/$probe_dir" 'RF>'
  type_command RF-HW-SW-read-stat "stat $app_tag" 'RF>'
  type_command RF-HW-SW-read-udos \
    "type $usb_root/$probe_dir/$app_tag.seq" 'RF>'
  preserve="read-only"
elif [ "$mode" = compare ]; then
  type_command RF-HW-SW-compare \
    "compare $usb_root/$compare_source.seq s0:/READYFS_TEST/$run_id/$compare_dir/fromu" \
    'VERIFY: IDENTICAL'
  type_command RF-HW-SW-compare-immediate-read \
    "type s0:/READYFS_TEST/$run_id/$compare_dir/fromu" \
    'HOST BETA'
  preserve="read-only"
elif [ "$mode" = copy ]; then
  copy_target="s0:/READYFS_TEST/$run_id/$compare_dir/$copy_leaf"
  type_command RF-HW-SW-copy \
    "copy $usb_root/$compare_source.seq $copy_target" 'COPIED'
  grep -Fqi 'VERIFY: IDENTICAL' "$out_dir/RF-HW-SW-copy/screen.txt"
  type_command RF-HW-SW-copy-soft-read "type $copy_target" 'HOST BETA'
  type_command RF-HW-SW-copy-compare \
    "compare $usb_root/$compare_source.seq $copy_target" \
    'VERIFY: IDENTICAL'
  preserve="USB1/READYFS_TEST/$run_id/$compare_dir/$copy_leaf.seq"
elif [ "$mode" = treeverify ]; then
  tree_soft="s0:/READYFS_TEST/$run_id/$tree_rel"
  type_command RF-HW-SW-tree-sfa "type $tree_soft/sfa" 'SOFT ALPHA'
  type_command RF-HW-SW-tree-fromu "type $tree_soft/fromu" 'HOST BETA'
  type_command RF-HW-SW-tree-compare \
    "compare $usb_root/$tree_source.seq $tree_soft/fromu" \
    'VERIFY: IDENTICAL' 240
  type_command RF-HW-SW-tree-dir "dir $usb_root/$tree_rel" 'fromu.seq'
  type_command RF-HW-SW-tree-nested \
    "type $usb_root/$tree_rel/nested/inside.seq" 'INSIDE'
  preserve="read-only"
elif [ "$mode" = reverse ] || [ "$mode" = reverseverify ]; then
  reverse_parent="${reverse_source%/*}"
  reverse_soft="s0:/READYFS_TEST/$run_id/$reverse_source"
  reverse_udos="$usb_root/$reverse_parent/$reverse_dest"

  if [ "$mode" = reverse ] && [ "$reverse_existing" -eq 0 ]; then
    verify_owners RF-HW-RV-owner-before-mkdir
    type_command RF-HW-RV-mkdir "mkdir $reverse_udos" \
      'DIRECTORY CREATED'

    verify_owners RF-HW-RV-owner-before-whatif
    type_command RF-HW-RV-whatif \
      "copy $reverse_soft $reverse_udos --recursive --whatif" \
      'RECURSIVE PLAN F3 D1 SELECTED 4' 240 240
    type_command RF-HW-RV-whatif-empty \
      "dir $reverse_udos" 'DIRECTORY EMPTY'
    if grep -Eqi 'SFA|FROMU|NESTED' \
        "$out_dir/RF-HW-RV-whatif-empty/screen.txt"; then
      printf 'reverse whatif destination was not empty\n' >&2
      exit 1
    fi
  fi

  if [ "$mode" = reverse ]; then
    verify_owners RF-HW-RV-owner-before-copy
    type_command RF-HW-RV-copy \
      "copy $reverse_soft $reverse_udos --recursive --force" \
      'BATCH DONE 4/4 FAIL 0' 480 240
  fi

  type_command RF-HW-RV-compare-sfa \
    "compare $reverse_soft/sfa $reverse_udos/sfa.seq" \
    'VERIFY: IDENTICAL' 240
  type_command RF-HW-RV-compare-fromu \
    "compare $reverse_soft/fromu $reverse_udos/fromu.seq" \
    'VERIFY: IDENTICAL' 240
  type_command RF-HW-RV-compare-nested \
    "compare $reverse_soft/nested/inside $reverse_udos/nested/inside.seq" \
    'VERIFY: IDENTICAL' 240
  type_command RF-HW-RV-destination-dir \
    "dir $reverse_udos" 'fromu.seq'
  type_command RF-HW-RV-destination-nested \
    "type $reverse_udos/nested/inside.seq" 'INSIDE'
  type_command RF-HW-RV-source-nested \
    "type $reverse_soft/nested/inside" 'INSIDE'
  if [ "$mode" = reverseverify ]; then preserve="read-only reverse verify"
  else preserve="USB1/READYFS_TEST/$run_id/$reverse_parent/$reverse_dest"; fi
elif [ "$mode" = recursiveprep ]; then
  tree_parent="${tree_rel%/*}"
  tree_udos="$usb_root/$tree_rel"
  recursive_udos="$usb_root/$tree_parent/$recursive_dest"
  recursive_soft="s0:/READYFS_TEST/$run_id/$tree_parent/$recursive_dest"

  verify_owners RF-HW-RP-owner-before-root
  type_command RF-HW-RP-mkdir-root \
    "mkdir $recursive_udos" 'DIRECTORY CREATED'
  verify_owners RF-HW-RP-owner-before-nested
  type_command RF-HW-RP-mkdir-nested \
    "mkdir $recursive_udos/nested" 'DIRECTORY CREATED'
  verify_owners RF-HW-RP-owner-before-whatif
  type_command RF-HW-RP-whatif \
    "copy $tree_udos $recursive_soft --recursive --whatif" \
    'RECURSIVE PLAN F3 D1 SELECTED 4'
  type_command RF-HW-RP-empty "dir $recursive_udos" 'nested'
  if grep -Eqi 'SFA|FROMU' "$out_dir/RF-HW-RP-empty/screen.txt"; then
    printf 'prepared destination already contains files\n' >&2
    exit 1
  fi
  preserve="USB1/READYFS_TEST/$run_id/$tree_parent/$recursive_dest"
elif [ "$mode" = metadata ]; then
  media_udos="$usb_root/$media_dir"
  image1="$media_udos/disk1.d81"

  # Report canonical display identity, the exact UltimateDOS access spelling,
  # and the decoded host filename as three deliberately separate values.
  type_command RF-HW-META-stat "stat $image1" \
    'SIZE EXACT: 819200 BYTES' 120 30
  grep -Fqi 'DISPLAY: U:/USB1/' \
    "$out_dir/RF-HW-META-stat/screen.txt"
  grep -Fqi 'ACCESS: disk1.d81' \
    "$out_dir/RF-HW-META-stat/screen.txt"
  grep -Fqi 'HOST: DISK1.D81' \
    "$out_dir/RF-HW-META-stat/screen.txt"

  type_command RF-HW-META-soft-volume 'volume s0:/' \
    'FREE UNAVAILABLE' 120 30
  grep -Fqi 'TARGET: $01' \
    "$out_dir/RF-HW-META-soft-volume/screen.txt"

  # The contained volume identity is distinct from the lowercase host image
  # filename. EXIT cleanup restores Drive A from its exact saved JSON state.
  verify_owners RF-HW-META-owner-before-mount
  type_command RF-HW-META-mount \
    "mount $image1 8: --force" 'MOUNTED ON 8:' 120 30
  mounted=1
  type_command RF-HW-META-volume 'volume 8:/' \
    'VOLUME: RFMEDIA1' 120 10
  grep -Fqi 'FREE: 3160 C64 BLOCKS' \
    "$out_dir/RF-HW-META-volume/screen.txt"
  verify_owners RF-HW-META-owner-before-dismount
  type_command RF-HW-META-dismount 'dismount 8: --force' \
    'MEDIA DISMOUNTED' 120 30
  mounted=0
  preserve="USB1/READYFS_TEST/$run_id/$media_dir/{disk1.d81,disk2.d81}"
elif [ "$mode" = media ]; then
  media_udos="$usb_root/$media_dir"
  image1="$media_udos/DISK1.D81"
  image2="$media_udos/DISK2.D81"

  if [ "$media_existing" -eq 0 ]; then
    verify_owners RF-HW-MEDIA-owner-before-mkdir
    # Do not let REST screen DMA race the UCI completion/status phase.
    type_command RF-HW-MEDIA-mkdir "mkdir $media_udos" \
      'DIRECTORY CREATED' 120 30

    # REST image creates require fresh C64-side reads of both owner markers.
    # The unique directory and both images are always preserved.
    verify_owners RF-HW-MEDIA-owner-before-create1
    curl --fail --silent --show-error --max-time 60 -X PUT \
      "$api/files/USB1/READYFS_TEST/$run_id/$media_dir/DISK1.D81:create_d81?diskname=RFMEDIA1" \
      -o "$out_dir/create-disk1.json"
    verify_owners RF-HW-MEDIA-owner-before-create2
    curl --fail --silent --show-error --max-time 60 -X PUT \
      "$api/files/USB1/READYFS_TEST/$run_id/$media_dir/DISK2.D81:create_d81?diskname=RFMEDIA2" \
      -o "$out_dir/create-disk2.json"
    python3 - "$out_dir/create-disk1.json" "$out_dir/create-disk2.json" <<'PY'
import json
import sys
for path, expected in zip(sys.argv[1:], (819200, 819200)):
    data = json.load(open(path, encoding="utf-8"))
    if data.get("bytes_written") != expected:
        raise SystemExit(f"D81 create size mismatch in {path}: {data}")
PY
  fi
  type_command RF-HW-MEDIA-dir "dir $media_udos" 'disk2.d81'

  verify_owners RF-HW-MEDIA-owner-before-mount
  type_command RF-HW-MEDIA-mount \
    "mount $image1 8: --force" 'MOUNTED ON 8:' 120 30
  sleep 2
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/after-mount-drives.json"
  python3 - "$out_dir/after-mount-drives.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
drive = next(item["a"] for item in data if "a" in item)
if drive.get("image_file", "").lower() != "disk1.d81":
    raise SystemExit(f"ReadyFS mount did not select disk1.d81: {drive}")
PY

  verify_owners RF-HW-MEDIA-owner-before-swap
  type_command RF-HW-MEDIA-swap "swap 8: --force" \
    'DISK SWAP REQUESTED' 120 30
  sleep 2
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/after-swap-drives.json"
  python3 - "$out_dir/after-swap-drives.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
drive = next(item["a"] for item in data if "a" in item)
if drive.get("image_file", "").lower() != "disk2.d81":
    raise SystemExit(f"ReadyFS swap did not select disk2.d81: {drive}")
PY

  verify_owners RF-HW-MEDIA-owner-before-dismount
  type_command RF-HW-MEDIA-dismount "dismount 8: --force" \
    'MEDIA DISMOUNTED' 120 30
  sleep 2
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/after-dismount-drives.json"
  python3 - "$out_dir/after-dismount-drives.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
drive = next(item["a"] for item in data if "a" in item)
if drive.get("image_file") or drive.get("image_path"):
    raise SystemExit(f"ReadyFS dismount left media attached: {drive}")
PY
  mounted=0
  preserve="USB1/READYFS_TEST/$run_id/$media_dir/{DISK1.D81,DISK2.D81}"
elif [ "$mode" = whatif ]; then
  tree_udos="$usb_root/$tree_rel"
  mapped_raw="$usb_root/$whatif_map_rel"
  mapped_dest="s$softmap_existing_partition:/$whatif_dest"

  # This mode is deliberately read-only. It uses an already configured
  # partition and refuses unless REST reports that partition at the exact
  # marker-owned path expected by the test. It never sends $20/$21.
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/whatif-original-drives.json"
  python3 - "$out_dir/whatif-original-drives.json" \
    "$softmap_existing_partition" "/USB1/READYFS_TEST/$run_id/$whatif_map_rel/" <<'PY'
import json
import sys

drives = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
soft = next(value for item in drives for value in item.values()
            if isinstance(value, dict) and "partitions" in value)
part = int(sys.argv[2])
expected = sys.argv[3].upper()
matches = [item for item in soft.get("partitions", [])
           if int(item["id"]) == part]
if len(matches) != 1 or matches[0].get("path", "").upper() != expected:
    raise SystemExit(
        f"existing SoftIEC partition is not exact owned mapping: {matches!r}")
PY

  type_command RF-HW-WI-before-source-dir "dir $tree_udos" 'nested'
  type_command RF-HW-WI-before-source-nested \
    "dir $tree_udos/nested" 'inside.seq'
  type_command RF-HW-WI-before-dest-dir "dir $mapped_raw" 'nested'
  if grep -Fqi "$whatif_dest" \
      "$out_dir/RF-HW-WI-before-dest-dir/screen.txt"; then
    printf 'WhatIf destination already exists: %s\n' "$whatif_dest" >&2
    exit 1
  fi
  type_command RF-HW-WI-before-sfa "crc32 $tree_udos/sfa.seq" 'CRC32 $'
  type_command RF-HW-WI-before-fromu \
    "crc32 $tree_udos/fromu.seq" 'CRC32 $'
  type_command RF-HW-WI-before-inside \
    "crc32 $tree_udos/nested/inside.seq" 'CRC32 $'

  verify_owners RF-HW-WI-owner-before-whatif
  type_command RF-HW-WI-whatif \
    "copy $tree_udos $mapped_dest --recursive --whatif --include **/inside" \
    'RECURSIVE PLAN F4 SELECTED 1' 240 60
  grep -Fqi 'PLAN W1 D0 M0; DONE W0 D0 M0' \
    "$out_dir/RF-HW-WI-whatif/screen.txt"

  type_command RF-HW-WI-after-source-dir "dir $tree_udos" 'nested'
  type_command RF-HW-WI-after-source-nested \
    "dir $tree_udos/nested" 'inside.seq'
  type_command RF-HW-WI-after-dest-dir "dir $mapped_raw" 'nested'
  if grep -Fqi "$whatif_dest" \
      "$out_dir/RF-HW-WI-after-dest-dir/screen.txt"; then
    printf 'WhatIf created destination: %s\n' "$whatif_dest" >&2
    exit 1
  fi
  type_command RF-HW-WI-after-sfa "crc32 $tree_udos/sfa.seq" 'CRC32 $'
  type_command RF-HW-WI-after-fromu \
    "crc32 $tree_udos/fromu.seq" 'CRC32 $'
  type_command RF-HW-WI-after-inside \
    "crc32 $tree_udos/nested/inside.seq" 'CRC32 $'

  for stem in source-dir source-nested dest-dir; do
    cmp "$out_dir/RF-HW-WI-before-$stem/screen.txt" \
        "$out_dir/RF-HW-WI-after-$stem/screen.txt"
  done
  for leaf in sfa fromu inside; do
    before_crc="$(grep -Fi 'CRC32 $' \
      "$out_dir/RF-HW-WI-before-$leaf/screen.txt" | tail -1)"
    after_crc="$(grep -Fi 'CRC32 $' \
      "$out_dir/RF-HW-WI-after-$leaf/screen.txt" | tail -1)"
    [ "$before_crc" = "$after_crc" ] || {
      printf 'WhatIf changed CRC for %s\n' "$leaf" >&2
      exit 1
    }
  done
  verify_owners RF-HW-WI-owner-after-whatif
  preserve="read-only source and mapped destination; no config command"
elif [ "$mode" = mapwhatif ]; then
  tree_udos="$usb_root/$tree_rel"
  raw_parent="$usb_root/${tree_rel%/*}"
  mapped_dest="s$softmap_partition:/${tree_rel%/*}/$whatif_dest"

  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/softmap-original-drives.json"
  python3 - "$out_dir/softmap-original-drives.json" \
    "$softmap_partition" <<'PY'
import json
import sys
drives = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
soft = next(value for item in drives for value in item.values()
            if isinstance(value, dict) and "partitions" in value)
part = int(sys.argv[2])
if any(int(item["id"]) == part for item in soft.get("partitions", [])):
    raise SystemExit(f"SoftIEC partition {part} already exists; refusing")
PY

  type_command RF-HW-MW-before-dir "dir $raw_parent" 'ENTRIES:'
  type_command RF-HW-MW-before-sfa "crc32 $tree_udos/sfa.seq" 'CRC32 $'
  type_command RF-HW-MW-before-fromu \
    "crc32 $tree_udos/fromu.seq" 'CRC32 $'
  type_command RF-HW-MW-before-inside \
    "crc32 $tree_udos/nested/inside.seq" 'CRC32 $'

  verify_owners RF-HW-MW-owner-before-map
  type_command RF-HW-MW-map \
    "mount $usb_root s$softmap_partition: --name RFMAP --force" \
    "SOFTIEC S$softmap_partition: MAPPED TO RAW" 120 30
  softmap_added=1
  sleep 2
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/softmap-after-add-drives.json"
  python3 - "$out_dir/softmap-after-add-drives.json" \
    "$softmap_partition" <<'PY'
import json
import sys
drives = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
soft = next(value for item in drives for value in item.values()
            if isinstance(value, dict) and "partitions" in value)
part = int(sys.argv[2])
matches = [item for item in soft.get("partitions", [])
           if int(item["id"]) == part]
if len(matches) != 1 or "READYFS_TEST" not in matches[0].get("path", "").upper():
    raise SystemExit(f"SoftIEC map not admitted exactly once: {matches!r}")
PY
  type_command RF-HW-MW-volume \
    "volume s$softmap_partition:/" 'RAW MAPPING:'

  type_command RF-HW-MW-whatif \
    "copy $tree_udos $mapped_dest --recursive --whatif --include **/inside" \
    'RECURSIVE PLAN F4 SELECTED 1' 240 60
  grep -Fqi 'PLAN W1 D0 M0; DONE W0 D0 M0' \
    "$out_dir/RF-HW-MW-whatif/screen.txt"

  type_command RF-HW-MW-after-dir "dir $raw_parent" 'ENTRIES:'
  type_command RF-HW-MW-after-sfa "crc32 $tree_udos/sfa.seq" 'CRC32 $'
  type_command RF-HW-MW-after-fromu \
    "crc32 $tree_udos/fromu.seq" 'CRC32 $'
  type_command RF-HW-MW-after-inside \
    "crc32 $tree_udos/nested/inside.seq" 'CRC32 $'
  cmp "$out_dir/RF-HW-MW-before-dir/screen.txt" \
      "$out_dir/RF-HW-MW-after-dir/screen.txt"
  for leaf in sfa fromu inside; do
    before_crc="$(grep -Fi 'CRC32 $' \
      "$out_dir/RF-HW-MW-before-$leaf/screen.txt" | tail -1)"
    after_crc="$(grep -Fi 'CRC32 $' \
      "$out_dir/RF-HW-MW-after-$leaf/screen.txt" | tail -1)"
    [ "$before_crc" = "$after_crc" ] || {
      printf 'WhatIf changed CRC for %s\n' "$leaf" >&2
      exit 1
    }
  done

  verify_owners RF-HW-MW-owner-before-unmap
  type_command RF-HW-MW-unmap \
    "dismount s$softmap_partition: --force" 'SOFTIEC UNMAPPED' 120 30
  sleep 2
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/softmap-after-del-drives.json"
  python3 - "$out_dir/softmap-original-drives.json" \
    "$out_dir/softmap-after-del-drives.json" <<'PY'
import json
import sys
def partitions(path):
    drives = json.load(open(path, encoding="utf-8"))["drives"]
    soft = next(value for item in drives for value in item.values()
                if isinstance(value, dict) and "partitions" in value)
    return soft.get("partitions", [])
if partitions(sys.argv[1]) != partitions(sys.argv[2]):
    raise SystemExit("SoftIEC partition list was not restored exactly")
PY
  softmap_added=0
  preserve="read-only tree; transient SoftIEC map restored"
else
  tree_parent="${tree_rel%/*}"
  tree_udos="$usb_root/$tree_rel"
  recursive_udos="$usb_root/$tree_parent/$recursive_dest"
  recursive_soft="s0:/READYFS_TEST/$run_id/$tree_parent/$recursive_dest"

  if [ "$recursive_existing" -eq 0 ]; then
    verify_owners RF-HW-RR-owner-before-mkdir
    type_command RF-HW-RR-mkdir "mkdir $recursive_udos" 'DIRECTORY CREATED'

    verify_owners RF-HW-RR-owner-before-whatif
    type_command RF-HW-RR-whatif \
      "copy $tree_udos $recursive_soft --recursive --whatif" \
      'RECURSIVE PLAN F3 D1 SELECTED 4'
    type_command RF-HW-RR-whatif-empty \
      "dir $recursive_udos" 'DIRECTORY EMPTY'
    if grep -Eqi 'SFA|FROMU|NESTED' \
        "$out_dir/RF-HW-RR-whatif-empty/screen.txt"; then
      printf 'whatif destination was not empty\n' >&2
      exit 1
    fi
  fi

  verify_owners RF-HW-RR-owner-before-copy
  type_command RF-HW-RR-copy \
    "copy $tree_udos $recursive_soft --recursive --force" \
    'BATCH DONE 4/4 FAIL 0' 480 240
  type_command RF-HW-RR-compare-sfa \
    "compare $tree_udos/sfa.seq $recursive_soft/sfa" \
    'VERIFY: IDENTICAL' 240
  type_command RF-HW-RR-compare-fromu \
    "compare $tree_udos/fromu.seq $recursive_soft/fromu" \
    'VERIFY: IDENTICAL' 240
  type_command RF-HW-RR-compare-nested \
    "compare $tree_udos/nested/inside.seq $recursive_soft/nested/inside" \
    'VERIFY: IDENTICAL' 240
  type_command RF-HW-RR-destination-dir "dir $recursive_udos" 'fromu.seq'
  type_command RF-HW-RR-destination-nested \
    "type $recursive_soft/nested/inside" 'INSIDE'
  preserve="USB1/READYFS_TEST/$run_id/$tree_parent/$recursive_dest"
fi
verify_owners RF-HW-SW-owner-after
printf 'completed=%s\nmode=%s\npreserve=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$mode" "$preserve" \
  > "$out_dir/manifest.txt"
