#!/usr/bin/env bash
set -euo pipefail

readyfs_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stamp="${READYFS_RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
out_dir="${READYFS_SOFTWRITE_OUT:-$readyfs_root/logs/readyfs_c64u/softwrite-noftp-$stamp}"
suite="$readyfs_root/build_support/run_readyfs_softwrite_probe_noftp_c64u.sh"
mkdir -p "$out_dir"
# A sacrificial leading blank avoids Terminal occasionally losing the first
# meaningful character while a fresh tab is still being admitted.
selected_mode="${READYFS_SOFTWRITE_MODE:-probe}"
terminal_command=" READYFS_ROOT='$readyfs_root' READYFS_SOFTWRITE_OUT='$out_dir' READYFS_SOFTWRITE_MODE='$selected_mode' READYFS_SOFTWRITE_SPEED_MHZ='${READYFS_SOFTWRITE_SPEED_MHZ:-}' READYFS_IEC_LAUNCH_WAIT_S='${READYFS_IEC_LAUNCH_WAIT_S:-180}' READYFS_OVERLAY_ADMISSION_WAIT_S='${READYFS_OVERLAY_ADMISSION_WAIT_S:-240}' READYFS_FORCE_FAIL_AFTER_OWNERS='${READYFS_FORCE_FAIL_AFTER_OWNERS:-0}' READYFS_APP_PRG='${READYFS_APP_PRG:-$readyfs_root/artifacts/readyfs/readyfs.prg}' C64U_HOST='${C64U_HOST:-10.0.0.79}'"
case "$selected_mode" in
  probe|app|appabs|read)
    terminal_command+=" READYFS_SOFTWRITE_TAG='${READYFS_SOFTWRITE_TAG:-ap0702}' READYFS_SOFTWRITE_DIR='${READYFS_SOFTWRITE_DIR:-rf065128}' READYFS_SOFTWRITE_LEAF='${READYFS_SOFTWRITE_LEAF:-kp065128}'"
    ;;
  compare|copy)
    terminal_command+=" READYFS_SOFTCOMPARE_DIR='${READYFS_SOFTCOMPARE_DIR:-rf081054}' READYFS_SOFTCOMPARE_SOURCE='${READYFS_SOFTCOMPARE_SOURCE:-us081054}' READYFS_SOFTCOPY_LEAF='${READYFS_SOFTCOPY_LEAF:-fx0001}'"
    ;;
  treeverify|recursive|recursiveprep)
    terminal_command+=" READYFS_SOFTTREE_REL='${READYFS_SOFTTREE_REL:-rf091800/rf100154}' READYFS_SOFTTREE_SOURCE='${READYFS_SOFTTREE_SOURCE:-us100154}' READYFS_SOFTRECUR_DEST='${READYFS_SOFTRECUR_DEST:-rr111500}' READYFS_SOFTRECUR_EXISTING='${READYFS_SOFTRECUR_EXISTING:-0}'"
    ;;
  reverse|reverseverify)
    terminal_command+=" READYFS_SOFTREVERSE_SOURCE='${READYFS_SOFTREVERSE_SOURCE:-rf091800/rr111505}' READYFS_SOFTREVERSE_DEST='${READYFS_SOFTREVERSE_DEST:-rv111500}' READYFS_SOFTREVERSE_EXISTING='${READYFS_SOFTREVERSE_EXISTING:-0}'"
    ;;
  media|metadata)
    terminal_command+=" READYFS_MEDIA_DIR='${READYFS_MEDIA_DIR:-md111500}' READYFS_MEDIA_EXISTING='${READYFS_MEDIA_EXISTING:-0}'"
    ;;
  mapwhatif)
    terminal_command+=" READYFS_SOFTTREE_REL='${READYFS_SOFTTREE_REL:-rf091800/rf100154}' READYFS_SOFTMAP_PARTITION='${READYFS_SOFTMAP_PARTITION:-1}' READYFS_WHATIF_DEST='${READYFS_WHATIF_DEST:-wf111500}'"
    ;;
  whatif)
    terminal_command+=" READYFS_SOFTTREE_REL='${READYFS_SOFTTREE_REL:-rf091800/rf100154}' READYFS_SOFTMAP_EXISTING_PARTITION='${READYFS_SOFTMAP_EXISTING_PARTITION:-0}' READYFS_WHATIF_MAP_REL='${READYFS_WHATIF_MAP_REL:-rf091800/rr111505}' READYFS_WHATIF_DEST='${READYFS_WHATIF_DEST:-wf111500}'"
    ;;
esac
terminal_command+=" /bin/bash '$suite' >> '$out_dir/terminal-launch.txt' 2>&1"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"$terminal_command\""
printf '%s\n' "$out_dir"
