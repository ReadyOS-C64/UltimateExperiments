#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/logs/readyfs_c64u/mount-probe-20261012"
mkdir -p "$out"
cl65 -t c64 -Os -I"$root/src/apps/readyfs" -o "$out/probe.prg" "$root/build_support/readyfs_mount_probe.c" "$root/src/apps/readyfs/readyfs_uci.c" "$root/src/apps/readyfs/readyfs_uci_asm.s"
cat > "$out/run.sh" <<'RUN'
#!/bin/bash
set -euo pipefail
out="$(cd "$(dirname "$0")" && pwd)"
curl --fail --silent --show-error --max-time 45 -H 'Content-Type: application/octet-stream' --data-binary "@$out/probe.prg" http://10.0.0.79/v1/runners:run_prg > "$out/launch.json"
sleep 45
curl --fail --silent --show-error --max-time 20 'http://10.0.0.79/v1/machine:readmem?address=0400&length=1000' -o "$out/screen.bin"
python3 "$out/../../../build_support/decode_c64_screen.py" "$out/screen.bin" --output "$out/screen.txt"
RUN
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"/bin/bash '$out/run.sh' > '$out/terminal.log' 2>&1\""
