"""Wrap separately linked fixed-slot modules in checked SEO1 sidecars."""
import argparse
import binascii
import hashlib
import json
from pathlib import Path
import struct


HEADER=36
BINDING_BYTES=16

def wrap(payload, slot, identity, entry=16, *, api, binding_digest):
    assert slot in (0,1) and 1 <= identity <= 255
    assert BINDING_BYTES < len(payload) <= 4096 and BINDING_BYTES <= entry < len(payload)
    assert len(binding_digest)==BINDING_BYTES and payload[:BINDING_BYTES]==binding_digest, 'payload was assembled against another resident build'
    header=struct.pack('<4sBBBBHHHH',b'SEO2',2,slot,identity,0,
                       len(payload),entry,binascii.crc_hqx(payload,0xFFFF),0)+struct.pack('<HH',*api)+binding_digest
    checksum=binascii.crc_hqx(header[:14]+header[16:],0xFFFF)
    return header[:14]+struct.pack('<H',checksum)+header[16:]+payload


def main():
    p=argparse.ArgumentParser()
    p.add_argument('input',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--slot',type=int,required=True)
    p.add_argument('--id',type=int,required=True)
    p.add_argument('--entry',type=int,default=16)
    p.add_argument('--resident-report',type=Path)
    a=p.parse_args()
    report_path=a.resident_report or a.input.parents[1]/'overlay-probe-report.json'
    report=json.loads(report_path.read_text())
    from bindings import verify
    stem=report_path.name.removesuffix('-report.json')
    binding=verify(report_path.with_name(stem+'.prg'),report_path.with_name(stem+'.lbl'))
    assert binding['digest']==report['resident_binding']['digest'] and binding['resident_sha256']==report['sha256']
    resident=report['symbols']
    api=(resident['se_overlay_call'],resident['se_overlay_frame'])
    digest=bytes.fromhex(binding['digest'])
    payload=a.input.read_bytes()
    image=wrap(payload,a.slot,a.id,a.entry,api=api,binding_digest=digest)
    a.output.write_bytes(image)
    a.output.with_suffix('.json').write_text(json.dumps(dict(schema=2,abi=2,binding_digest=digest.hex(),slot=a.slot,
        id=a.id,resident_api=api,load=0xA000+a.slot*0x1000,payload_bytes=len(payload),entry=a.entry,
        crc16=binascii.crc_hqx(payload,0xFFFF),sha256=hashlib.sha256(image).hexdigest()),indent=2)+'\n')
    print(f'{a.output.name}: {len(payload)} payload bytes, slot {a.slot}, ID {a.id}')

if __name__=='__main__':
    main()
