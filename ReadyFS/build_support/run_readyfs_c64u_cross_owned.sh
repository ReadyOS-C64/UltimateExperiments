#!/usr/bin/env bash
set -euo pipefail

# Run only from start_readyfs_c64u_cross_owned_terminal.sh. This suite uses a
# REST-uploaded disposable D81 and writes UltimateDOS files only below a fresh
# subdirectory of the exact marker-owned USB1 root. It never uses FTP.

readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
owned_id="${READYFS_OWNED_RUN_ID:-readyfs-20260815-190355-79014}"
case_tag="${READYFS_CROSS_TAG:?READYFS_CROSS_TAG is required}"
out_dir="${READYFS_CROSS_OUT:?READYFS_CROSS_OUT is required}"
status_file="$out_dir/status.txt"
api="http://$c64u_host/v1"
prg="$readyfs_root/artifacts/readyfs/readyfs.prg"
source_prg="$readyfs_root/artifacts/readyfs/readyfs-match.prg"
fixture="$out_dir/readyfs-cross.d81"
owned_usb="u:/USB1/READYFS_TEST/$owned_id"
owned_sd="u:/SD/READYFS_TEST/$owned_id"
marker_name=".readyfs-owner-$owned_id"
marker_source="$readyfs_root/logs/readyfs_c64u/owned-roots-$owned_id/ownership-marker.txt"
cross_root="$owned_usb/cross-$case_tag"
mounted=0

if [[ ! "$owned_id" =~ ^readyfs-[0-9]{8}-[0-9]{6}-[0-9]+$ ]] ||
   [[ ! "$case_tag" =~ ^[a-z0-9-]+$ ]]; then
  printf 'unsafe ReadyFS owned id or cross tag\n' >&2
  exit 64
fi

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"

post_config() {
  curl --fail --silent --show-error --max-time 15 \
    -H 'Content-Type: application/json' --data-binary "@$1" \
    "$api/configs" >> "$out_dir/transport.log" 2>&1
}

restore_original() {
  local rc=0
  if [ ! -s "$out_dir/original-drives.json" ]; then
    return 0
  fi
  if [ "$mounted" -eq 1 ]; then
    curl --fail --silent --show-error --max-time 15 -X PUT \
      "$api/drives/a:remove" >> "$out_dir/transport.log" 2>&1 || rc=1
  fi
  if [ -s "$out_dir/restore-drive-a.json" ]; then
    post_config "$out_dir/restore-drive-a.json" || rc=1
  fi
  sleep 1
  curl --fail --silent --show-error --max-time 15 "$api/drives" \
    -o "$out_dir/restored-drives.json" || rc=1
  if [ "$rc" -eq 0 ]; then
    python3 - "$out_dir/original-drives.json" \
      "$out_dir/restored-drives.json" <<'PY' || rc=1
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
  return "$rc"
}

finish() {
  local rc=$?
  trap - EXIT
  if ! restore_original; then rc=97; fi
  if [ "$rc" -eq 0 ]; then printf 'success\n' > "$status_file"
  else printf 'failed:%s\n' "$rc" > "$status_file"
  fi
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

capture_screen() {
  local label="$1" step_dir="$out_dir/$1"
  mkdir -p "$step_dir"
  curl --fail --silent --show-error --max-time 10 \
    "$api/machine:readmem?address=0400&length=1000" \
    -o "$step_dir/screen_0400.bin" >> "$out_dir/transport.log" 2>&1
  python3 "$readyfs_root/build_support/decode_c64_screen.py" \
    "$step_dir/screen_0400.bin" --output "$step_dir/screen.txt"
}

wait_screen() {
  local label="$1" required="$2" attempt
  for attempt in $(seq 1 60); do
    sleep 1
    capture_screen "$label"
    if grep -Fqi "$required" "$out_dir/$label/screen.txt"; then return 0; fi
  done
  return 1
}

type_command() {
  local label="$1" command="$2" required="$3"
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" $'clear\r' \
    >> "$out_dir/transport.log" 2>&1
  sleep 1
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" "$command"$'\r' \
    >> "$out_dir/transport.log" 2>&1
  wait_screen "$label" "$required"
  printf '%s\tPASS\t%s\n' "$label" "$command" >> "$out_dir/results.tsv"
}

verify_owner_ui() {
  local volume="$1" label="$2" root marker_screen
  if [ "$volume" = USB1 ]; then root="$owned_usb"; else root="$owned_sd"; fi
  type_command "$label" "type $root/$marker_name" 'READ 116 BYTES'
  marker_screen="$out_dir/$label/screen.txt"
  grep -q 'READYFS-OWNED-ROOT' "$marker_screen"
  grep -q "run.id=$owned_id" "$marker_screen"
  grep -q 'created.utc=2026-08-16T02:03:56Z' "$marker_screen"
  grep -q 'policy=preserve-by-default' "$marker_screen"
}

test -s "$prg"
test -s "$source_prg"
test -s "$marker_source"
grep -q '^READYFS-OWNED-ROOT$' "$marker_source"
grep -q "^run_id=$owned_id$" "$marker_source"

{
  printf 'owned_id=%s\n' "$owned_id"
  printf 'cross_root=%s\n' "$cross_root"
  printf 'fixture=REST attachment; disposable D81\n'
  printf 'preserve=true\n'
} > "$out_dir/manifest.txt"
printf 'case\tresult\tcommand\n' > "$out_dir/results.tsv"

curl --fail --silent --show-error --max-time 15 "$api/drives" \
  -o "$out_dir/original-drives.json"
python3 - "$out_dir/original-drives.json" \
  "$out_dir/restore-drive-a.json" \
  "$out_dir/test-drive-a.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
drive = next(item["a"] for item in data if "a" in item)
if drive.get("image_file") or drive.get("image_path"):
    raise SystemExit("drive A is not empty; exact restoration cannot be guaranteed")
payload = {"Drive A Settings": {
    "Drive": "Enabled" if drive["enabled"] else "Disabled",
    "Drive Type": drive["type"],
    "Drive Bus ID": drive["bus_id"],
}}
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
with open(sys.argv[3], "w", encoding="utf-8") as handle:
    json.dump({"Drive A Settings": {
        "Drive": "Enabled", "Drive Type": "1581", "Drive Bus ID": 8,
    }}, handle)
PY

c1541 -format "rfcross,rf" d81 "$fixture" \
  -write "$source_prg" RFIECPRG >> "$out_dir/fixture.log" 2>&1

post_config "$out_dir/test-drive-a.json"
sleep 1
curl --fail --silent --show-error --max-time 60 -X POST \
  -F "file=@$fixture" -F 'mode=readwrite' -F 'type=d81' \
  "$api/drives/a:mount" > "$out_dir/mount-response.json"
mounted=1
sleep 2
curl --fail --silent --show-error --max-time 15 "$api/drives" \
  -o "$out_dir/mounted-drives.json"
python3 - "$out_dir/mounted-drives.json" <<'PY'
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
drive = next(item["a"] for item in data if "a" in item)
if not drive["enabled"] or drive["bus_id"] != 8 or drive["type"] != "1581":
    raise SystemExit("disposable drive A mount was not admitted")
PY

curl --fail --silent --show-error --max-time 30 \
  -H 'Content-Type: application/octet-stream' --data-binary "@$prg" \
  "$api/runners:run_prg" >> "$out_dir/transport.log" 2>&1
sleep 3
capture_screen launch
grep -q 'READYFS LAB' "$out_dir/launch/screen.txt"

# Prove the disposable IEC fixture is visible before any owned-root mutation.
type_command dir-iec-fixture "dir 8:/" 'RFIECPRG'
type_command stat-iec-fixture "stat 8:/RFIECPRG" 'TYPE: $11'

# Every mutation is immediately preceded by both exact marker round trips.
verify_owner_ui USB1 marker-usb-before-mkdir
verify_owner_ui SD marker-sd-before-mkdir
type_command mkdir-owned "mkdir $cross_root" 'DIRECTORY CREATED'

verify_owner_ui USB1 marker-usb-before-copy40
verify_owner_ui SD marker-sd-before-copy40
type_command copy-iec-to-udos \
  "copy 8:/RFIECPRG $cross_root/iec-to-udos.prg" 'COPIED 4069 BYTES'
grep -Fqi 'VERIFY: IDENTICAL' "$out_dir/copy-iec-to-udos/screen.txt"
type_command compare-iec-udos \
  "compare 8:/RFIECPRG $cross_root/iec-to-udos.prg" 'VERIFY: IDENTICAL'
type_command stat-udos "stat $cross_root/iec-to-udos.prg" 'TYPE: $11'
grep -Fqi 'SIZE EXACT: 4069 BYTES' "$out_dir/stat-udos/screen.txt"

verify_owner_ui USB1 marker-usb-before-copy41
verify_owner_ui SD marker-sd-before-copy41
type_command copy-udos-to-iec \
  "copy $cross_root/iec-to-udos.prg 8:/RFROUND" 'COPIED 4069 BYTES'
grep -Fqi 'VERIFY: IDENTICAL' "$out_dir/copy-udos-to-iec/screen.txt"
type_command compare-iec-roundtrip \
  'compare 8:/RFIECPRG 8:/RFROUND' 'VERIFY: IDENTICAL'
type_command stat-iec-roundtrip 'stat 8:/RFROUND' 'TYPE: $11'
type_command dir-final 'dir 8:/' 'RFROUND'
