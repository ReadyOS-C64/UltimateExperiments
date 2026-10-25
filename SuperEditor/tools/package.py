"""Build only this project's owned D81; retain the c1541 listing and hashes."""
import argparse
import binascii
import hashlib
import json
from pathlib import Path
import subprocess
from overlays import wrap
from bindings import verify as verify_binding

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--c1541', default='c1541')
args = parser.parse_args()
disk = root/'build/supereditor.d81'
editor_report=json.loads((root/'build/editor-report.json').read_text())
zp=next(s for s in editor_report['segments'] if s['name']=='ZEROPAGE')
assert (zp['start'],zp['end'],zp['size'])==(2,0x19,24), 'lifecycle ABI requires exact 24-byte ZP extent'
editor_seal=verify_binding(root/'build/editor.prg',root/'build/editor.lbl')
assert editor_seal['resident_sha256']==editor_report['sha256'] and editor_seal['digest']==editor_report['resident_binding']['digest']
disk.unlink(missing_ok=True)
command = [args.c1541, '-format', 'supereditor,se', 'd81', str(disk),
           '-write', str(root/'build/editor.prg'), 'supereditor',
           '-write', str(root/'build/supereditor.prg'), 'bootprobe',
           '-write', str(root/'build/display-probe.prg'), 'displayprobe',
           '-write', str(root/'build/memory-probe.prg'), 'memoryprobe',
           '-write', str(root/'build/overlay-probe.prg'), 'overlayprobe',
           '-write', str(root/'build/object-probe.prg'), 'objectprobe',
           '-write', str(root/'build/document-probe.prg'), 'documentprobe',
           '-write', str(root/'build/splice-probe.prg'), 'spliceprobe',
           '-write', str(root/'build/clipboard-probe.prg'), 'clipboardprobe',
           '-write', str(root/'build/local-probe.prg'), 'localprobe',
           '-write', str(root/'build/range-probe.prg'), 'rangeprobe',
           '-write', str(root/'build/history-probe.prg'), 'historyprobe']
for name in ['rone','rtwo','cone','rnest','hedit','hplay','eedit','eplay','window','text40','menu40','engine','navigate','search','block','layout','fileio','aux','styler','viewsource','lexical','gridedit','grid80','grid60','foldparse','foldfinish','foldcore','foldctl','rangeio','foldxform','geosline','geospage','geosrow','geospaint','geosnav','geossema','geoslex','geosinln','popups','geospreview','geosfontrow','geosfontin','geosfold','geostail','geoscaret','lifectrl','lifecopy','geosdelta','gfont','gtype','code','clex','type','grid']:
    command += ['-write',str(root/f'build/overlays/{name}.seo'),name+',s']
command += ['-write',str(root/'build/geos-font-catalog/font-pack.bin'),'geosfonts,s']
resident=json.loads((root/'build/overlay-probe-report.json').read_text())
api_symbols=resident['symbols']
digest=bytes.fromhex(resident['resident_binding']['digest'])
api=(api_symbols['se_overlay_call'],api_symbols['se_overlay_frame'])
fixtures={'short':wrap(digest+bytes([0x60])*8,0,4,api=api,binding_digest=digest)[:-1],
          'extra':wrap(digest+bytes([0x60]),0,4,api=api,binding_digest=digest)+b'X',
          'badcrc':wrap(digest+bytes([0x60]),0,4,api=api,binding_digest=digest)[:-1]+b'Y'}
bad_header=bytearray(wrap(digest+bytes([0x60]),0,4,api=api,binding_digest=digest))
bad_header[5]=1 # valid slot, incorrect header CRC
fixtures['badhdr']=bytes(bad_header)
foreign=bytes([digest[0]^1])+digest[1:]
fixtures['binderr']=wrap(foreign+bytes([0x60]),0,4,api=api,binding_digest=foreign)
payerr=bytearray(wrap(digest+bytes([0x60]),0,4,api=api,binding_digest=digest))
payerr[36]^=1
payerr[12:14]=binascii.crc_hqx(payerr[36:],0xFFFF).to_bytes(2,'little')
payerr[14:16]=binascii.crc_hqx(payerr[:14]+payerr[16:36],0xFFFF).to_bytes(2,'little')
fixtures['payerr']=bytes(payerr)
for name,data in fixtures.items():
    path=root/f'build/overlays/{name}.seo'
    path.write_bytes(data)
    command += ['-write',str(path),name+',s']
command += ['-list']
result = subprocess.run(command, capture_output=True, text=True)
(root/'build/disk-listing.txt').write_text(result.stdout+result.stderr)
result.check_returncode()
assert disk.stat().st_size == 819200
manifest = dict(schema=1, disk=str(disk), bytes=disk.stat().st_size,
                sha256=hashlib.sha256(disk.read_bytes()).hexdigest(), command=command)
(root/'build/disk-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(f'D81 built: {disk} ({manifest["sha256"][:12]})')
