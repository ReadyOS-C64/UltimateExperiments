#!/usr/bin/env bash
set -euo pipefail

U64_IP="${U64_IP:-10.0.0.79}"
FTP_USER="${FTP_USER:-anonymous}"
FTP_PASS="${FTP_PASS:-anonymous@}"
SAVE_TO_FLASH="${SAVE_TO_FLASH:-0}"

variant=""
show_only=0
skip_upload=0

usage() {
  cat <<'USAGE'
Usage:
  ./apply_readyos_palette.sh --list
  ./apply_readyos_palette.sh <variant> [--save] [--ip 10.0.0.79]
  ./apply_readyos_palette.sh <variant> --show

Variants:
  grey          neutral luminance greyscale
  sepia         warm CRT sepia scale
  neon          ReadyOS retro neon, balanced
  bold          louder electric neon
  pinkborder    bold neon with LIGHTBLUE/borders as hot pink
  matrix        semi-monochrome terminal green
  tokyo-night   Omarchy/Tokyo Night inspired
  catppuccin    Omarchy/Catppuccin inspired
  gruvbox       Omarchy/Gruvbox inspired
  rose-pine     Omarchy/Rose Pine inspired
  nord          Omarchy/Nord inspired
  everforest    Omarchy/Everforest inspired
  kanagawa      Omarchy/Kanagawa inspired
  osaka-jade    Omarchy/Osaka Jade inspired
  ristretto     Omarchy/Ristretto inspired
  pinkscale     readable monochrome pink/magenta scale
  geocities     audacious high-contrast web-1.0 colors
  cyberpunk     hot magenta/yellow/cyan city glare
  cyberpunk-77  C77 yellow-on-black with silver and neon violet-blue
  ultraviolet   blacklight violet with electric accents
  acid-rain     radioactive greens with punchy alerts
  synthwave     sunset magenta/orange/blue
  amber         monochrome amber CRT
  hotdog        deliberately loud red/yellow arcade palette
  ocean-drive   neon teal, coral, and Miami-night blue

Environment:
  U64_IP=10.0.0.79 FTP_USER=anonymous FTP_PASS=anonymous@ SAVE_TO_FLASH=1
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

norm_variant() {
  printf '%s' "$1" | tr '[:upper:]_' '[:lower:]-'
}

list_variants() {
  usage
}

urlencode() {
  local input="$1" output="" i char hex
  LC_ALL=C
  for ((i = 0; i < ${#input}; i++)); do
    char="${input:i:1}"
    case "$char" in
      [a-zA-Z0-9.~_-]) output+="$char" ;;
      ' ') output+="%20" ;;
      *) printf -v hex '%%%02X' "'$char"; output+="$hex" ;;
    esac
  done
  printf '%s' "$output"
}

rest_call() {
  local method="$1" url="$2" label="$3" body_file code
  body_file="$(mktemp)"
  code="$(curl -sS -X "$method" -o "$body_file" -w '%{http_code}' "$url")" || {
    cat "$body_file" >&2 || true
    rm -f "$body_file"
    die "REST ${label} request failed"
  }

  printf '%s HTTP %s\n' "$label" "$code"
  if [[ -s "$body_file" ]]; then
    cat "$body_file"
    printf '\n'
  fi

  if [[ "$code" -lt 200 || "$code" -ge 300 ]]; then
    rm -f "$body_file"
    die "REST ${label} returned HTTP ${code}"
  fi
  rm -f "$body_file"
}

validate_vpl() {
  local file="$1"
  awk '
    NF != 3 { printf("bad VPL line %d: expected 3 bytes, got %d\n", NR, NF); exit 1 }
    $1 !~ /^[0-9A-Fa-f][0-9A-Fa-f]$/ ||
    $2 !~ /^[0-9A-Fa-f][0-9A-Fa-f]$/ ||
    $3 !~ /^[0-9A-Fa-f][0-9A-Fa-f]$/ {
      printf("bad VPL line %d: expected hex byte triplet\n", NR); exit 1
    }
    END {
      if (NR != 16) {
        printf("bad VPL: expected 16 lines, got %d\n", NR);
        exit 1;
      }
    }
  ' "$file"
}

variant_vpl_name() {
  case "$1" in
    grey)        printf 'GREY.VPL' ;;
    sepia)       printf 'SEPIA.VPL' ;;
    neon)        printf 'READYSNEON.VPL' ;;
    bold)        printf 'READYB2.VPL' ;;
    pinkborder)  printf 'READYPINK.VPL' ;;
    matrix)      printf 'READYMATRIX.VPL' ;;
    tokyo-night) printf 'READYTOKYO.VPL' ;;
    catppuccin)  printf 'READYCAT.VPL' ;;
    gruvbox)     printf 'READYGRUV.VPL' ;;
    rose-pine)   printf 'READYROSE.VPL' ;;
    nord)        printf 'READYNORD.VPL' ;;
    everforest)  printf 'READYEVER.VPL' ;;
    kanagawa)    printf 'READYKANA.VPL' ;;
    osaka-jade)  printf 'READYJADE.VPL' ;;
    ristretto)   printf 'READYRIST.VPL' ;;
    pinkscale)   printf 'PINKSCL.VPL' ;;
    geocities)   printf 'GEOCITY.VPL' ;;
    cyberpunk)   printf 'CYBERPNK.VPL' ;;
    cyberpunk-77) printf 'C77CYBER.VPL' ;;
    ultraviolet) printf 'ULTRAVIO.VPL' ;;
    acid-rain)   printf 'ACIDRAIN.VPL' ;;
    synthwave)   printf 'SYNTHWAV.VPL' ;;
    amber)       printf 'AMBERCRT.VPL' ;;
    hotdog)      printf 'HOTDOG.VPL' ;;
    ocean-drive) printf 'OCEANDRV.VPL' ;;
    *) die "unknown variant: $1" ;;
  esac
}

write_palette() {
  local name="$1" out="$2"
  case "$name" in
    grey)
      cat > "$out" <<'VPL'
00 00 00
F7 F7 F7
4C 4C 4C
B4 B4 B4
5F 5F 5F
88 88 88
39 39 39
DE DE DE
5F 5F 5F
3C 3C 3C
87 87 87
4A 4A 4A
7B 7B 7B
CD CD CD
7A 7A 7A
B2 B2 B2
VPL
      ;;
    sepia)
      cat > "$out" <<'VPL'
04 02 00
FF E0 91
59 4D 31
C0 A8 6C
6C 5E 3C
95 82 54
45 3C 26
E8 CB 83
6C 5E 3C
48 3E 27
94 81 53
57 4B 30
88 77 4C
D7 BD 7A
87 76 4C
BE A6 6B
VPL
      ;;
    neon)
      cat > "$out" <<'VPL'
03 00 08
F8 F1 FF
D7 26 5E
05 D9 E8
B9 67 FF
00 B5 6A
17 12 38
F9 F8 71
FF 9F 1C
7A 4E 00
FF 5C 8A
2B 2A 3D
6D 66 8B
6C FF 6B
72 F1 FF
B8 B2 D8
VPL
      ;;
    bold)
      cat > "$out" <<'VPL'
02 00 0A
F4 F2 FF
FF 1E 77
00 F6 FF
D1 3C FF
00 FF 66
12 08 42
FF F4 2A
FF 7A 00
8A 3F 00
FF 4F A3
25 22 44
5B 54 8C
8C FF 2E
5B DD FF
C8 C0 FF
VPL
      ;;
    pinkborder)
      cat > "$out" <<'VPL'
02 00 0A
F4 F2 FF
FF 1E 77
00 F6 FF
D1 3C FF
00 FF 66
12 08 42
FF F4 2A
FF 7A 00
8A 3F 00
FF 4F A3
25 22 44
5B 54 8C
8C FF 2E
FF 00 F0
C8 C0 FF
VPL
      ;;
    matrix)
      cat > "$out" <<'VPL'
00 05 00
D9 FF D2
FF 4D 6D
00 F0 9A
4C FF 8A
00 C8 55
00 18 10
D9 FF 5A
FF A0 22
5C 6A 16
FF 73 92
08 20 14
22 4A 32
78 FF 3D
52 FF C7
A7 D8 A9
VPL
      ;;
    tokyo-night)
      cat > "$out" <<'VPL'
09 0B 18
C0 CA F5
F7 76 8E
7D CF FF
BB 9A F7
9E CE 6A
1A 1B 26
E0 AF 68
FF 9E 64
41 48 68
FF 7A 93
24 2B 45
56 5F 89
C3 E8 8D
9A D8 FF
A9 B1 D6
VPL
      ;;
    catppuccin)
      cat > "$out" <<'VPL'
11 11 1B
CD D6 F4
F3 8B A8
89 DC EB
CB A6 F7
A6 E3 A1
1E 1E 2E
F9 E2 AF
FA B3 87
6C 58 3F
EB A0 AC
31 32 44
58 5B 70
B4 BE FE
74 C7 EC
BA C2 DE
VPL
      ;;
    gruvbox)
      cat > "$out" <<'VPL'
1D 20 21
EB DB B2
CC 24 1D
8E C0 7C
B1 62 86
98 97 1A
28 28 28
FA BD 2F
D6 5D 0E
7C 6F 64
FB 49 34
3C 38 36
66 5C 54
B8 BB 26
83 A5 98
D5 C4 A1
VPL
      ;;
    rose-pine)
      cat > "$out" <<'VPL'
19 17 24
E0 DE F4
EB 6F 92
9C CF D8
C4 A7 E7
95 B1 AC
1F 1D 2E
F6 C1 77
EA 9A 97
6E 6A 86
F0 83 A2
26 24 33
52 4F 67
EB BC BA
9C CF D8
90 8C AA
VPL
      ;;
    nord)
      cat > "$out" <<'VPL'
1C 22 2E
EC EF F4
BF 61 6A
88 C0 D0
B4 8E AD
A3 BE 8C
2E 34 40
EB CB 8B
D0 87 70
4C 56 6A
BF 72 7C
3B 42 52
5E 81 AC
B7 D0 9A
81 A1 C1
D8 DE E9
VPL
      ;;
    everforest)
      cat > "$out" <<'VPL'
1E 23 25
D3 C6 AA
E6 7E 80
83 C0 92
D6 99 B6
A7 C0 80
2D 35 35
DB BC 7F
E6 98 75
5C 6A 72
E6 98 75
3A 45 45
54 5E 62
A7 C0 80
7F BB B3
B8 C7 A4
VPL
      ;;
    kanagawa)
      cat > "$out" <<'VPL'
16 1A 22
DC D7 BA
C3 40 43
7E 9C A8
95 7F A9
76 91 46
1F 1F 28
C0 A3 6E
FF A0 66
54 50 46
E8 24 24
2A 2A 37
72 72 7A
98 BB 6C
7F A1 C3
C8 C0 93
VPL
      ;;
    osaka-jade)
      cat > "$out" <<'VPL'
05 10 12
E7 FF F4
FF 4D 6D
00 E0 C6
8C 7C FF
00 C9 7A
08 1F 26
E8 FF 7A
FF 9D 4A
6D 5C 39
FF 6E A6
17 32 36
3B 63 68
78 FF A6
6B FF E7
B8 F5 E0
VPL
      ;;
    ristretto)
      cat > "$out" <<'VPL'
10 0B 0A
F5 E9 D2
D9 58 58
8B C1 B7
C7 92 EA
A6 C4 72
20 16 17
E5 C0 7B
C8 7A 4A
6A 4C 3A
EA 7D 7D
2D 22 24
5E 4A 4D
B8 D4 8B
9F D8 D3
D8 C8 B8
VPL
      ;;
    pinkscale)
      cat > "$out" <<'VPL'
08 00 08
FF EA FF
FF 2F 8E
FF A4 E8
D3 55 FF
FF 6F B7
23 08 28
FF D1 F0
FF 7A C8
70 2B 55
FF 58 A8
2C 14 32
68 35 72
FF 9A D6
FF B8 F4
C9 9A C8
VPL
      ;;
    geocities)
      cat > "$out" <<'VPL'
00 00 66
FF FF FF
FF 00 66
00 FF FF
CC 00 FF
00 FF 00
00 00 CC
FF FF 00
FF 88 00
66 33 00
FF 66 99
22 22 66
66 66 FF
99 FF 00
66 CC FF
CC CC FF
VPL
      ;;
    cyberpunk)
      cat > "$out" <<'VPL'
05 02 12
F8 F8 E8
FF 2B 6D
00 F5 FF
B7 28 FF
00 F0 80
0B 0B 3B
FF F0 00
FF 8A 00
70 3A 00
FF 5A B8
22 1A 38
5B 4B 90
99 FF 33
66 E6 FF
C6 B8 FF
VPL
      ;;
    cyberpunk-77)
      cat > "$out" <<'VPL'
02 02 05
FC EE 09
FF 2A 68
35 C8 FF
B6 4D FF
5E 8A FF
08 0B 18
FF F3 68
FF B8 00
7A 61 18
FF 62 B0
20 24 2D
55 5D 6A
D7 FF 4C
70 82 FF
B8 C0 CC
VPL
      ;;
    ultraviolet)
      cat > "$out" <<'VPL'
02 00 12
F1 E9 FF
FF 2F 80
25 E8 FF
CA 52 FF
41 F7 8A
12 05 40
F7 FF 60
FF 8A 36
5A 35 7A
FF 70 B5
1E 18 36
55 43 82
9B FF 8A
8E C7 FF
C7 B2 FF
VPL
      ;;
    acid-rain)
      cat > "$out" <<'VPL'
02 08 02
E8 FF B8
FF 3B 55
7D FF D0
B2 FF 00
00 F0 3D
07 22 12
E6 FF 00
CC FF 33
52 6B 00
FF 6A 7A
1E 33 1B
4E 70 3A
B7 FF 32
77 FF E0
C3 F7 AE
VPL
      ;;
    synthwave)
      cat > "$out" <<'VPL'
08 02 1F
FF E6 FF
FF 3C 9E
39 E7 FF
B1 42 FF
33 FF B0
1A 0B 4F
FF D8 4A
FF 8A 3D
7A 3E 5C
FF 64 C7
2C 1B 4A
66 4D 94
8D FF C7
74 C8 FF
C6 B4 FF
VPL
      ;;
    amber)
      cat > "$out" <<'VPL'
08 03 00
FF F0 B8
C2 47 21
FF C0 58
D0 7A 24
BF 8F 22
1F 0E 00
FF D2 45
F5 8B 18
70 38 05
FF 76 38
2D 16 04
6B 3A 10
F0 B8 38
FF CF 73
C8 9C 68
VPL
      ;;
    hotdog)
      cat > "$out" <<'VPL'
13 00 00
FF FF D8
FF 00 00
00 F0 FF
FF 33 CC
00 D0 3A
36 00 00
FF EA 00
FF 72 00
78 24 00
FF 55 55
40 1A 00
91 45 00
BC FF 00
7D D7 FF
FF C2 66
VPL
      ;;
    ocean-drive)
      cat > "$out" <<'VPL'
02 09 1F
E8 FF FF
FF 5D 7D
00 F7 D9
B8 6C FF
00 D6 8F
04 2A 4A
FF F0 82
FF 9D 5C
6A 54 35
FF 7F A8
16 32 4A
4C 72 8A
A2 FF 8A
5E C9 FF
B8 E6 F2
VPL
      ;;
    *) die "unknown variant: $name" ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list|-l)
      list_variants
      exit 0
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --ip)
      [[ $# -ge 2 ]] || die "--ip needs a value"
      U64_IP="$2"
      shift 2
      ;;
    --save)
      SAVE_TO_FLASH=1
      shift
      ;;
    --show)
      show_only=1
      shift
      ;;
    --skip-upload)
      skip_upload=1
      shift
      ;;
    --variant)
      [[ $# -ge 2 ]] || die "--variant needs a value"
      variant="$(norm_variant "$2")"
      shift 2
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      if [[ -n "$variant" ]]; then
        die "variant already set to $variant"
      fi
      variant="$(norm_variant "$1")"
      shift
      ;;
  esac
done

[[ -n "$variant" ]] || {
  usage
  exit 1
}

command -v curl >/dev/null 2>&1 || die 'curl is required'

VPL_NAME="$(variant_vpl_name "$variant")"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
vpl_file="${workdir}/${VPL_NAME}"
api_base="http://${U64_IP}/v1"

write_palette "$variant" "$vpl_file"
validate_vpl "$vpl_file" || die 'VPL validation failed'

if [[ "$show_only" == "1" ]]; then
  printf '# %s -> %s\n' "$variant" "$VPL_NAME"
  cat "$vpl_file"
  exit 0
fi

printf 'Palette variant: %s\n' "$variant"
printf 'Palette file:    %s\n' "$VPL_NAME"
printf 'Target:          %s\n' "$U64_IP"

if [[ "$skip_upload" == "1" ]]; then
  printf 'Skipping FTP upload; expecting /flash/data/%s to exist already\n' "$VPL_NAME"
else
  printf 'Uploading to /flash/data/%s over FTP\n' "$VPL_NAME"
  curl --fail --silent --show-error --ftp-create-dirs \
    --user "${FTP_USER}:${FTP_PASS}" \
    -T "$vpl_file" \
    "ftp://${U64_IP}/flash/data/${VPL_NAME}" \
    || die 'FTP upload failed'
fi

rest_call GET "${api_base}/files/flash/data/${VPL_NAME}:info" 'verify file'

category="$(urlencode 'U64 Specific Settings')"
item="$(urlencode 'Palette Definition')"
value="$(urlencode "$VPL_NAME")"

rest_call PUT "${api_base}/configs/${category}/${item}?value=${value}" 'apply palette'
rest_call GET "${api_base}/configs/${category}/${item}" 'read palette config'

if [[ "$SAVE_TO_FLASH" == "1" ]]; then
  rest_call PUT "${api_base}/configs:save_to_flash" 'save config'
else
  printf 'Not saving config to flash. Use --save or SAVE_TO_FLASH=1 to persist.\n'
fi

printf 'Done.\n'
