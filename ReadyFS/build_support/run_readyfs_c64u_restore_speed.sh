#!/usr/bin/env bash
set -euo pipefail

# Terminal-owned emergency/restoration helper for a saved speed-matrix payload.
# It changes only the two values captured in restore-speed.json and verifies
# both values by a fresh REST readback.

restore_dir="${1:-${READYFS_RESTORE_DIR:-}}"
if [ -z "$restore_dir" ]; then
  printf 'set READYFS_RESTORE_DIR or pass the restore directory\n' >&2
  exit 64
fi
c64u_host="${2:-${C64U_HOST:-10.0.0.79}}"
payload="$restore_dir/restore-speed.json"
status_file="$restore_dir/manual-restore-status.txt"
reboot_restored=0

printf 'running\n' > "$status_file"
finish() {
  local rc=$?
  if [ "$rc" -eq 0 ]; then printf 'success\n' > "$status_file"
  else printf 'failed:%s\n' "$rc" > "$status_file"
  fi
  exit "$rc"
}
trap finish EXIT

test -s "$payload"
if ! curl --fail --silent --show-error --max-time 15 \
  -H 'Content-Type: application/json' --data-binary "@$payload" \
  "http://$c64u_host/v1/configs" -o "$restore_dir/manual-restore-post.json" \
  2> "$restore_dir/manual-restore.log"; then
  # A failed runner/mount transaction can leave the C64 execution side busy
  # while REST itself remains reachable. Reset only the emulated C64, wait,
  # then retry the exact saved two-field payload once.
  curl --fail --silent --show-error --max-time 15 -X PUT \
    "http://$c64u_host/v1/machine:reset" \
    -o "$restore_dir/manual-restore-reset.json" \
    2>> "$restore_dir/manual-restore.log"
  sleep 5
  python3 - "$payload" "$restore_dir/manual-restore-stage.json" \
    "$restore_dir/manual-restore-control.json" \
    "$restore_dir/manual-restore-speed.json" <<'PY'
import json
import sys

saved = json.load(open(sys.argv[1], encoding="utf-8"))["U64 Specific Settings"]
json.dump({"U64 Specific Settings": {
    "Turbo Control": "Manual",
    "CPU Speed": saved["CPU Speed"],
}}, open(sys.argv[2], "w", encoding="utf-8"))
json.dump({"U64 Specific Settings": {
    "Turbo Control": "Manual",
}}, open(sys.argv[3], "w", encoding="utf-8"))
json.dump({"U64 Specific Settings": {
    "CPU Speed": saved["CPU Speed"],
}}, open(sys.argv[4], "w", encoding="utf-8"))
PY
  if ! curl --fail --silent --show-error --max-time 15 \
    -H 'Content-Type: application/json' \
    --data-binary "@$restore_dir/manual-restore-stage.json" \
    "http://$c64u_host/v1/configs" \
    -o "$restore_dir/manual-restore-stage-post.json" \
    2>> "$restore_dir/manual-restore.log"; then
    # If the configuration service itself is wedged, use the established
    # Ultimate-core reboot recovery, then retry the intermediate state once.
    curl --fail --silent --show-error --max-time 15 -X PUT \
      "http://$c64u_host/v1/machine:reboot" \
      -o "$restore_dir/manual-restore-reboot.json" \
      2>> "$restore_dir/manual-restore.log"
    sleep 8
    curl --fail --silent --show-error --max-time 15 -X PUT \
      "http://$c64u_host/v1/machine:resume" \
      -o "$restore_dir/manual-restore-resume.json" \
      2>> "$restore_dir/manual-restore.log"
    sleep 2
    curl --fail --silent --show-error --max-time 15 \
      "http://$c64u_host/v1/configs/U64%20Specific%20Settings" \
      -o "$restore_dir/manual-restore-post-reboot-config.json"
    if python3 - "$payload" \
      "$restore_dir/manual-restore-post-reboot-config.json" <<'PY'
import json
import sys

expected = json.load(open(sys.argv[1], encoding="utf-8"))["U64 Specific Settings"]
actual = json.load(open(sys.argv[2], encoding="utf-8"))["U64 Specific Settings"]
raise SystemExit(0 if all(str(actual[k]).strip() == str(expected[k]).strip()
                          for k in ("Turbo Control", "CPU Speed")) else 1)
PY
    then
      reboot_restored=1
    else
      if ! curl --fail --silent --show-error --max-time 15 \
        -H 'Content-Type: application/json' \
        --data-binary "@$restore_dir/manual-restore-stage.json" \
        "http://$c64u_host/v1/configs" \
        -o "$restore_dir/manual-restore-stage-retry.json" \
        2>> "$restore_dir/manual-restore.log"; then
        read -r saved_control saved_speed < <(python3 - "$payload" <<'PY'
import json
import sys
import urllib.parse

saved = json.load(open(sys.argv[1], encoding="utf-8"))["U64 Specific Settings"]
print(urllib.parse.quote(str(saved["Turbo Control"]), safe=""),
      urllib.parse.quote(str(saved["CPU Speed"]).strip(), safe=""))
PY
)
        curl --fail --silent --show-error --max-time 15 -X PUT \
          "http://$c64u_host/v1/configs/U64%20Specific%20Settings/"\
"Turbo%20Control?value=Manual" \
          -o "$restore_dir/manual-restore-control-put.json" \
          2>> "$restore_dir/manual-restore.log"
        sleep 1
        curl --fail --silent --show-error --max-time 15 -X PUT \
          "http://$c64u_host/v1/configs/U64%20Specific%20Settings/"\
"CPU%20Speed?value=$saved_speed" \
          -o "$restore_dir/manual-restore-speed-put.json" \
          2>> "$restore_dir/manual-restore.log"
        sleep 1
        curl --fail --silent --show-error --max-time 15 -X PUT \
          "http://$c64u_host/v1/configs/U64%20Specific%20Settings/"\
"Turbo%20Control?value=$saved_control" \
          -o "$restore_dir/manual-restore-control-exact-put.json" \
          2>> "$restore_dir/manual-restore.log"
        reboot_restored=1
      fi
    fi
  fi
  if [ "$reboot_restored" -eq 0 ]; then
    sleep 1
    curl --fail --silent --show-error --max-time 15 \
      -H 'Content-Type: application/json' --data-binary "@$payload" \
      "http://$c64u_host/v1/configs" \
      -o "$restore_dir/manual-restore-post-retry.json" \
      2>> "$restore_dir/manual-restore.log"
  fi
fi
sleep 1
curl --fail --silent --show-error --max-time 15 \
  "http://$c64u_host/v1/configs/U64%20Specific%20Settings" \
  -o "$restore_dir/manual-restored-u64-config.json"
python3 - "$payload" "$restore_dir/manual-restored-u64-config.json" <<'PY'
import json
import sys

expected = json.load(open(sys.argv[1], encoding="utf-8"))["U64 Specific Settings"]
actual = json.load(open(sys.argv[2], encoding="utf-8"))["U64 Specific Settings"]
for key in ("Turbo Control", "CPU Speed"):
    if str(actual[key]).strip() != str(expected[key]).strip():
        raise SystemExit(f"restore mismatch for {key}: {actual[key]!r} != {expected[key]!r}")
PY
