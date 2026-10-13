#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/logs/readyfs_c64u/demo-v3-native-mount-matrix-20261012"
cat > "$out/restore-b.py" <<'PY'
from pathlib import Path
import json,urllib.request,ftplib,io,posixpath
root=Path(__file__).parent
base='http://10.0.0.79/v1'
def api(path,method='GET',body=None):
 req=urllib.request.Request(base+path,data=body,method=method,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
original=json.loads((root/'original-drives.json').read_text())
owned=json.loads((root/'owned-scope.json').read_text())
current=api('/drives');a=next(x['a'] for x in current['drives'] if 'a' in x)
assert a==next(x['a'] for x in original['drives'] if 'a' in x)
b=next(x['b'] for x in current['drives'] if 'b' in x)
path=posixpath.normpath(b['image_file'] if b['image_file'].startswith('/') else b['image_path'].rstrip('/')+'/'+b['image_file'])
assert path.lower()==(owned['root']+'/media.d81').lower()
assert path.startswith('/USB1/READYFS_TEST/')
ftp=ftplib.FTP('10.0.0.79',timeout=20);ftp.login('anonymous','anonymous@');buf=io.BytesIO();ftp.retrbinary('RETR '+owned['root']+'/'+owned['marker'],buf.write);ftp.quit()
assert buf.getvalue()==(root/'ownership-marker.txt').read_bytes()
api('/drives/b:remove','PUT')
config=json.loads((root/'original-drive-b-config.json').read_text())
api('/configs','POST',json.dumps({'Drive B Settings':{k:config[k] for k in ('Drive','Drive Type','Drive Bus ID')}}).encode())
final=api('/drives');(root/'recovery-restored-drives.json').write_text(json.dumps(final,indent=2))
for d in ('a','b'):assert next(x[d] for x in final['drives'] if d in x)==next(x[d] for x in original['drives'] if d in x)
print('Restored original A/B drive state; owned fixture preserved.',flush=True)
PY
/usr/bin/osascript -e "tell application \"Terminal\" to do script \"python3 '$out/restore-b.py' > '$out/recovery-restore.log' 2>&1\""
