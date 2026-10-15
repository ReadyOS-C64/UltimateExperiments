#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
host="${C64U_HOST:-10.0.0.79}"
api="http://${host}/v1"
remote_dir="${C77_REMOTE_DIR:-USB1}"
remote_name="${C77_REMOTE_NAME:-readyos-v0.5-c77-ultimate.d81}"
image="${C77_D81:-${repo}/Releases/0.5/precog-ultimate/readyos-v0.5-ultimate.d81}"
palette="${C77_PALETTE:-${repo}/C77CYBER.VPL}"
charrom="${C77_CHARROM:-${repo}/assets/c77-photo-reconstruction-readyos-v3-chargen.bin}"
palette_name="C77CYBER.VPL"
charrom_name="C77CHAR.BIN"
out_dir="${C77_DEPLOY_OUT:-/tmp/c77_full_ultimate_deploy_20260826}"
status_file="${out_dir}/status"
log="${out_dir}/deploy.log"
tmp_dir="${out_dir}/tmp"

mkdir -p "$out_dir" "$tmp_dir"
: > "$log"

finish() {
  printf '%s\n' "$1" > "$status_file"
}

fail() {
  printf 'ERROR: %s\n' "$*" | tee -a "$log" >&2
  finish failed
  exit 1
}

curl_logged() {
  printf '+ curl %s\n' "$*" >> "$log"
  curl "$@" >> "$log" 2>&1
}

trap 'finish failed' ERR

wait_rest() {
  local deadline=$((SECONDS + 90))
  while (( SECONDS <= deadline )); do
    if curl --fail --silent --show-error --max-time 5 \
      "${api}/drives" -o "${tmp_dir}/drives-probe.json" >> "$log" 2>&1; then
      return 0
    fi
    sleep 2
  done
  fail "C64U REST did not become ready"
}

require_file() {
  [[ -f "$1" ]] || fail "missing file: $1"
}

require_file "$image"
require_file "$palette"
require_file "$charrom"
[[ "$(wc -c < "$image" | tr -d ' ')" == "819200" ]] || fail "Ultimate D81 must be 819200 bytes"
[[ "$(wc -c < "$charrom" | tr -d ' ')" == "4096" ]] || fail "Char ROM must be 4096 bytes"
[[ "$(wc -l < "$palette" | tr -d ' ')" == "16" ]] || fail "palette must contain 16 lines"
python3 - "$image" "$remote_dir" "$remote_name" <<'PY'
import pathlib
import sys

image = pathlib.Path(sys.argv[1]).read_bytes()
expected = f"C64U_IMAGE_PATH=/{sys.argv[2]}/{sys.argv[3]}".upper().encode("ascii")
if expected not in image:
    raise SystemExit(
        "Ultimate D81 app config does not contain the mounted image path: "
        + expected.decode("ascii")
    )
PY

printf 'host=%s\nremote=/%s/%s\n' "$host" "$remote_dir" "$remote_name" >> "$log"
shasum -a 256 "$image" "$palette" "$charrom" >> "$log"

wait_rest
curl --fail --silent --show-error --max-time 20 \
  "${api}/configs/U64%20Specific%20Settings" \
  -o "${out_dir}/u64-before.json"
curl --fail --silent --show-error --max-time 20 \
  "${api}/configs/C64%20and%20Cartridge%20Settings" \
  -o "${out_dir}/c64-before.json"

# Upload only the owned C77 deployment paths/assets.
curl_logged --fail --silent --show-error --ftp-create-dirs --max-time 180 \
  --user anonymous:anonymous@ -T "$image" \
  "ftp://${host}/${remote_dir}/${remote_name}"
curl_logged --fail --silent --show-error --ftp-create-dirs --max-time 30 \
  --user anonymous:anonymous@ -T "$palette" \
  "ftp://${host}/flash/data/${palette_name}"
curl_logged --fail --silent --show-error --ftp-create-dirs --max-time 30 \
  --user anonymous:anonymous@ -T "$charrom" \
  "ftp://${host}/flash/roms/${charrom_name}"

# Download the three uploaded files and compare them byte-for-byte.
curl --fail --silent --show-error --max-time 180 --user anonymous:anonymous@ \
  "ftp://${host}/${remote_dir}/${remote_name}" -o "${tmp_dir}/roundtrip.d81"
curl --fail --silent --show-error --max-time 30 --user anonymous:anonymous@ \
  "ftp://${host}/flash/data/${palette_name}" -o "${tmp_dir}/roundtrip.vpl"
curl --fail --silent --show-error --max-time 30 --user anonymous:anonymous@ \
  "ftp://${host}/flash/roms/${charrom_name}" -o "${tmp_dir}/roundtrip.bin"
cmp "$image" "${tmp_dir}/roundtrip.d81" || fail "D81 round-trip mismatch"
cmp "$palette" "${tmp_dir}/roundtrip.vpl" || fail "palette round-trip mismatch"
cmp "$charrom" "${tmp_dir}/roundtrip.bin" || fail "Char ROM round-trip mismatch"

# Apply the two firmware settings and make them persistent.
curl_logged --fail --silent --show-error --max-time 20 -X PUT \
  "${api}/configs/U64%20Specific%20Settings/Palette%20Definition?value=${palette_name}"
curl_logged --fail --silent --show-error --max-time 20 -X PUT \
  "${api}/configs/C64%20and%20Cartridge%20Settings/Char%20ROM?value=${charrom_name}"
curl_logged --fail --silent --show-error --max-time 20 -X PUT \
  "${api}/configs:save_to_flash"

curl --fail --silent --show-error --max-time 20 \
  "${api}/configs/U64%20Specific%20Settings" \
  -o "${out_dir}/u64-after.json"
curl --fail --silent --show-error --max-time 20 \
  "${api}/configs/C64%20and%20Cartridge%20Settings" \
  -o "${out_dir}/c64-after.json"
python3 - "${out_dir}/u64-after.json" "${out_dir}/c64-after.json" <<'PY'
import json
import sys

u64 = json.load(open(sys.argv[1]))["U64 Specific Settings"]
c64 = json.load(open(sys.argv[2]))["C64 and Cartridge Settings"]
if u64.get("Palette Definition") != "C77CYBER.VPL":
    raise SystemExit(f"palette readback mismatch: {u64.get('Palette Definition')!r}")
if c64.get("Char ROM") != "C77CHAR.BIN":
    raise SystemExit(f"Char ROM readback mismatch: {c64.get('Char ROM')!r}")
PY

# Reboot so the FPGA-backed character ROM setting is active.
curl_logged --fail --silent --show-error --max-time 20 -X PUT "${api}/machine:reboot"
sleep 4
wait_rest
curl_logged --fail --silent --show-error --max-time 20 -X PUT "${api}/machine:resume"
sleep 3

# Hardware proof: execute a small probe that banks in the character ROM and
# copies bank-1 glyph A ($D808-$D80F) to RAM, then compare with the source ROM.
python3 "${repo}/build_support/build_c77_charrom_probe.py" \
  --output "${tmp_dir}/charrom_probe.prg" >> "$log"
for attempt in $(seq 1 10); do
  if curl --fail --silent --show-error --max-time 30 \
    -H "Content-Type: application/octet-stream" \
    --data-binary "@${tmp_dir}/charrom_probe.prg" \
    "${api}/runners:run_prg" >> "$log" 2>&1; then
    break
  fi
  (( attempt < 10 )) || fail "could not run character-ROM hardware probe"
  sleep 2
done
sleep 2
curl --fail --silent --show-error --max-time 20 \
  "${api}/machine:readmem?address=6000&length=8" \
  -o "${tmp_dir}/hardware-bank1-a.bin"
dd if="$charrom" of="${tmp_dir}/expected-bank1-a.bin" bs=1 skip=2056 count=8 status=none
cmp "${tmp_dir}/expected-bank1-a.bin" "${tmp_dir}/hardware-bank1-a.bin" \
  || fail "hardware bank-1 character-ROM proof mismatch"

# Use the repository's physical-Ultimate boot harness.  It performs the proven
# pre-mount reset, mount, post-mount reset, LOAD"BOOT",8 / RUN sequence and a
# quiet initialization interval before it begins REST screen polling.  Polling
# the command interface while BOOT is initializing can otherwise wedge the
# Ultimate DOS DMA transaction at LOADING LAUNCHER.
boot_out="${out_dir}/boot"
C64U_HOST="$host" \
  C64U_SKIP_UPLOAD=1 \
  C64U_SKIP_CONFIG=1 \
  C64U_REMOTE_DIR="$remote_dir" \
  READYOS_EXPECT_DMA_READY=1 \
  READYOS_BOOT_INITIAL_WAIT_S=90 \
  /bin/bash "${repo}/build_support/run_readyos_boot_c64u_rest.sh" \
    "$image" "$remote_name" "$boot_out" >> "$log" 2>&1
[[ "$(<"${boot_out}/status")" == "READYOS_BOOT_PASS" ]] \
  || fail "physical-Ultimate boot harness did not reach READYOS_BOOT_PASS"

curl --fail --silent --show-error --max-time 20 \
  "${api}/drives" -o "${out_dir}/drives-final.json"
printf 'D81, palette, and Char ROM verified; ReadyOS launcher is running.\n' >> "$log"
finish success
