#!/usr/bin/env bash
set -euo pipefail

# Independent-Terminal, no-file-mutation probe for the firmware-3.14
# SoftwareIEC ADD/DEL_PARTITION trailing-NUL compatibility path.
readyfs_root="${READYFS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
c64u_host="${C64U_HOST:-10.0.0.79}"
out_dir="${READYFS_SOFTIEC_OUT:?}"
api="http://$c64u_host/v1"
prg="$readyfs_root/artifacts/readyfs/readyfs.prg"
partition=1
status_file="$out_dir/status.txt"
added=0

mkdir -p "$out_dir"
printf 'running\n' > "$status_file"

type_text() {
  C64U_HOST="$c64u_host" /bin/bash \
    "$readyfs_root/build_support/c64u_type_text.sh" "$1"$'\r' \
    >> "$out_dir/transport.log" 2>&1
  sleep 2
}

snapshot() {
  curl --fail --silent --show-error --max-time 15 "$api/drives" -o "$1"
}

has_partition() {
  python3 - "$1" "$partition" <<'PY'
import json, sys
drives = json.load(open(sys.argv[1], encoding="utf-8"))["drives"]
soft = next(v for item in drives for v in item.values()
            if isinstance(v, dict) and "partitions" in v)
raise SystemExit(0 if any(int(p["id"]) == int(sys.argv[2])
                          for p in soft.get("partitions", [])) else 1)
PY
}

finish() {
  local probe_rc=$?
  trap - EXIT
  snapshot "$out_dir/drives-exit-before.json" || probe_rc=97
  if has_partition "$out_dir/drives-exit-before.json"; then
    type_text "dismount s$partition: --force" || probe_rc=97
    snapshot "$out_dir/drives-exit-after.json" || probe_rc=97
    if has_partition "$out_dir/drives-exit-after.json"; then probe_rc=97; fi
  fi
  if [ "$probe_rc" -eq 0 ]; then printf 'success\n' > "$status_file"
  else printf 'failed:%s\n' "$probe_rc" > "$status_file"; fi
  exit "$probe_rc"
}
trap finish EXIT

snapshot "$out_dir/drives-before.json"
if has_partition "$out_dir/drives-before.json"; then
  printf 'partition 1 already exists; refusing\n' >&2
  exit 64
fi
curl --fail --silent --show-error --max-time 30 \
  -H 'Content-Type: application/octet-stream' --data-binary "@$prg" \
  "$api/runners:run_prg" >> "$out_dir/transport.log" 2>&1
sleep 3
type_text 'mount u:/USB1/ s1: --name RFTEST --force'
snapshot "$out_dir/drives-after-add.json"
has_partition "$out_dir/drives-after-add.json"
added=1
type_text 'dismount s1: --force'
snapshot "$out_dir/drives-after-del.json"
if has_partition "$out_dir/drives-after-del.json"; then exit 1; fi
added=0
