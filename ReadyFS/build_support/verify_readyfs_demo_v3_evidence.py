#!/usr/bin/env python3
"""Check saved physical-demo evidence without contacting the hardware."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
out = Path(sys.argv[1]).resolve()
assert (out / 'status.txt').read_text().strip() == 'success'
image = out / 'owned-media-after.d81'
listing = subprocess.check_output(['c1541', '-attach', str(image), '-list']).decode(errors='replace')
(out / 'persisted-disk-directory.txt').write_text(listing)
assert any('"hostseq"' in line.lower() and 'seq' in line.lower().split('"')[-1]
           for line in listing.splitlines()), listing
destination = out / 'persisted-hostseq.bin'
subprocess.run(['c1541', '-attach', str(image), '-read', 'hostseq,s', str(destination)],
               check=True, capture_output=True)
content = destination.read_bytes()
assert content == b'READYFS NESTED DEMO\rSOURCE STAYS SAFE\r'
snapshot = json.loads((out / 'deleted-snapshot.json').read_text())
fixture = (root / 'build_support/readyfs_content_view.seq').read_bytes()
assert snapshot['from-disk.seq']['sha256'] == hashlib.sha256(fixture).hexdigest()
original = json.loads((out / 'original-drives.json').read_text())
restored = json.loads((out / 'restored-drives.json').read_text())
assert original == restored
result = {'persisted_host_to_disk_bytes': len(content), 'persisted_host_to_disk_type': 'SEQ',
          'disk_to_host_bytes': len(fixture), 'both_directions_independent_sha256': 'PASS',
          'original_drives_restored': 'PASS'}
(out / 'independent-transfer-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
