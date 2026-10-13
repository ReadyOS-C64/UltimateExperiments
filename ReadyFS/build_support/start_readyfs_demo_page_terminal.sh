#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/logs/readyfs_c64u/demo-v3-native-mount-matrix-20261012b"
cat > "$out/advance-pager.py" <<'PY'
from pathlib import Path
import urllib.request,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'build_support'))
from decode_c64_screen import decode_screen
api='http://10.0.0.79/v1'
def req(path,method='GET'):
 with urllib.request.urlopen(urllib.request.Request(api+path,method=method),timeout=15) as r:return r.read()
screen=req('/machine:readmem?address=0400&length=1000')
text='\n'.join(decode_screen(screen));Path(__file__).with_name('pager-screen.txt').write_text(text)
assert '-- MORE --' in text.upper(),text
assert req('/machine:readmem?address=C6&length=1')==b'\0'
req('/machine:writemem?address=0277&data=20','PUT');req('/machine:writemem?address=C6&data=01','PUT')
print('Advanced one confirmed directory page.',flush=True)
PY
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"python3 '$out/advance-pager.py' > '$out/advance-pager.log' 2>&1\""
