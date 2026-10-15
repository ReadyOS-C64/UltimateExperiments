#!/usr/bin/env bash
set -euo pipefail

delay=10
once=0
save=0
skip_upload_first=0
ip_arg=()
variants=()

default_variants=(
  neon
  bold
  pinkborder
  matrix
  pinkscale
  geocities
  cyberpunk
  cyberpunk-77
  ultraviolet
  acid-rain
  synthwave
  amber
  hotdog
  ocean-drive
  tokyo-night
  catppuccin
  gruvbox
  rose-pine
  nord
  everforest
  kanagawa
  osaka-jade
  ristretto
  sepia
  grey
)

usage() {
  cat <<'USAGE'
Usage:
  ./cycle_readyos_palettes.sh [--interval 10] [--once] [--ip 10.0.0.79] [variant...]

Examples:
  ./cycle_readyos_palettes.sh
  ./cycle_readyos_palettes.sh --interval 5 neon pinkborder geocities hotdog
  ./cycle_readyos_palettes.sh --once --skip-upload tokyo-night catppuccin gruvbox

Options:
  --interval, -i N  Seconds between palettes. Default: 10.
  --once           Apply the list once, then exit.
  --save           Ask the Ultimate to save each applied palette config to flash.
  --skip-upload    Assume VPL files already exist in /flash/data.
  --ip IP          Override Ultimate IP.
USAGE
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
apply_script="${script_dir}/apply_readyos_palette.sh"

[[ -x "$apply_script" ]] || {
  printf 'ERROR: missing or non-executable %s\n' "$apply_script" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --interval|-i)
      [[ $# -ge 2 ]] || {
        printf 'ERROR: --interval needs a value\n' >&2
        exit 1
      }
      delay="$2"
      shift 2
      ;;
    --once)
      once=1
      shift
      ;;
    --save)
      save=1
      shift
      ;;
    --skip-upload)
      skip_upload_first=1
      shift
      ;;
    --ip)
      [[ $# -ge 2 ]] || {
        printf 'ERROR: --ip needs a value\n' >&2
        exit 1
      }
      ip_arg=(--ip "$2")
      shift 2
      ;;
    -*)
      printf 'ERROR: unknown option: %s\n' "$1" >&2
      exit 1
      ;;
    *)
      variants+=("$1")
      shift
      ;;
  esac
done

case "$delay" in
  ''|*[!0-9]*)
    printf 'ERROR: interval must be a positive integer\n' >&2
    exit 1
    ;;
esac

if [[ "$delay" -lt 1 ]]; then
  printf 'ERROR: interval must be at least 1 second\n' >&2
  exit 1
fi

if [[ "${#variants[@]}" -eq 0 ]]; then
  variants=("${default_variants[@]}")
fi

apply_args=()
if [[ "${#ip_arg[@]}" -gt 0 ]]; then
  apply_args+=("${ip_arg[@]}")
fi
if [[ "$save" == "1" ]]; then
  apply_args+=(--save)
fi
if [[ "$skip_upload_first" == "1" ]]; then
  apply_args+=(--skip-upload)
fi

pass=1
while :; do
  printf 'Palette cycle pass %d, interval %ss\n' "$pass" "$delay"
  for variant in "${variants[@]}"; do
    printf '\n== applying %s ==\n' "$variant"
    if [[ "${#apply_args[@]}" -gt 0 ]]; then
      "$apply_script" "$variant" "${apply_args[@]}"
    else
      "$apply_script" "$variant"
    fi
    sleep "$delay"
  done

  if [[ "$once" == "1" ]]; then
    break
  fi

  if [[ "$skip_upload_first" != "1" ]]; then
    apply_args+=(--skip-upload)
    skip_upload_first=1
    printf '\nUploaded one full pass; future passes will use --skip-upload.\n'
  fi

  pass=$((pass + 1))
done
