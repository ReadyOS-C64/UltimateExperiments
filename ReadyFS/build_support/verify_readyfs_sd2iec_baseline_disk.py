#!/usr/bin/env python3
"""Independent offline byte/type/source-removal checks on the owned D81."""
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys


def verify(out):
    out = Path(out)
    expected = json.loads((out/'baseline-expected-iec-files.json').read_text())
    image = out/'owned-media-after.d81'
    listing = subprocess.check_output(['c1541', '-attach', str(image), '-list']).decode(errors='replace')
    (out/'baseline-persisted-disk-directory.txt').write_text(listing)
    assert not re.search(r'"bm-[^"]+"', listing.lower()), 'MOVE source still on owned disk'
    result = {}
    for leaf, wanted in expected.items():
        destination = out/('baseline-persisted-'+leaf+'.bin')
        assert '/' not in leaf and '\\' not in leaf
        subprocess.run(['c1541', '-attach', str(image), '-read', leaf+',s', str(destination)],
                       check=True, capture_output=True)
        data = destination.read_bytes()
        got = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        assert got == wanted, (leaf, got, wanted)
        result[leaf] = {**got, 'type': 'SEQ'}
    (out/'baseline-independent-disk-checks.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    print(json.dumps(verify(sys.argv[1]), indent=2))
