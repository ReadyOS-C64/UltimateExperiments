"""Seal a linked resident PRG and its complete link-symbol contract in place.

The 16-byte digest is zeroed for hashing, so stamping is deterministic and
idempotent. No instruction/data address or PRG length moves during sealing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

DOMAIN=b'SuperEditor resident ABI 2\0'
DIGEST_BYTES=16

def link_symbols(path):
    pairs=[]
    for line in Path(path).read_text().splitlines():
        match=re.fullmatch(r'al ([0-9a-fA-F]+) \.([^\s]+)',line.strip())
        if match:pairs.append((match[2],int(match[1],16)))
    if not pairs:raise ValueError('empty link-symbol contract')
    return sorted(set(pairs))

def binding_digest(image,pairs):
    candidates={value for name,value in pairs if name=='se_overlay_binding_digest'}
    if len(candidates)!=1:raise ValueError('missing or ambiguous binding digest symbol')
    address=candidates.pop();load=int.from_bytes(image[:2],'little');at=address-load+2
    if not 2<=at<=len(image)-DIGEST_BYTES:raise ValueError('binding digest outside resident image')
    normalized=bytearray(image);normalized[at:at+DIGEST_BYTES]=bytes(DIGEST_BYTES)
    contract=json.dumps(pairs,separators=(',',':'),ensure_ascii=True).encode('ascii')
    digest=hashlib.sha256(DOMAIN+bytes(normalized)+b'\0'+contract).digest()[:DIGEST_BYTES]
    return digest,at

def seal(prg,labels):
    prg=Path(prg);image=prg.read_bytes();pairs=link_symbols(labels);digest,at=binding_digest(image,pairs)
    sealed=image[:at]+digest+image[at+DIGEST_BYTES:]
    assert len(sealed)==len(image)
    prg.write_bytes(sealed)
    return dict(schema=2,digest=digest.hex(),digest_bytes=DIGEST_BYTES,
        resident_sha256=hashlib.sha256(sealed).hexdigest(),symbol_pairs=len(pairs),
        contract='normalized complete PRG and complete unique link-symbol pairs; semantic domain ABI2')

def verify(prg,labels):
    image=Path(prg).read_bytes();pairs=link_symbols(labels);digest,at=binding_digest(image,pairs)
    if image[at:at+DIGEST_BYTES]!=digest:raise ValueError('resident binding seal is missing or stale')
    return dict(schema=2,digest=digest.hex(),digest_bytes=DIGEST_BYTES,
        resident_sha256=hashlib.sha256(image).hexdigest(),symbol_pairs=len(pairs))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stem',required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];build=root/'build'
    record=seal(build/f'{a.stem}.prg',build/f'{a.stem}.lbl')
    (build/f'{a.stem}-bindings.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f'Resident ABI2 sealed: {record["digest"]} ({record["symbol_pairs"]} link symbols)')
