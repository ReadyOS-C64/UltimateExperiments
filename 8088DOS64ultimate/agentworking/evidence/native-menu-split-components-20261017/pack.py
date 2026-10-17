"""Private runtime-role-only asset packing; no public release publication."""
from pathlib import Path
import hashlib,json,shutil,zlib
P=Path(__file__).resolve().parent;E=P.parent/'live-media-runtime-assets-root-20261017';W=P/'work'
binding=json.loads((E/'BINDING.json').read_text())
def check(path,record):
 b=path.read_bytes();assert len(b)==record['bytes']and hashlib.sha256(b).hexdigest()==record['sha256'];return b
main=check(E/'work/build/dos64.prg',binding['main']);broker=check(E/'broker-runtime/broker.prg',binding['runtime_broker']);ui=check(E/'ui/panel.prg',binding['UI']);header=check(E/'HEADER.bin',binding['header'])
assert broker[:2]==b'\x00p'and ui[:2]==b'\x00\x80'and len(header)==64
assert int.from_bytes(header[24:26],'little')==len(broker)-2 and int.from_bytes(header[31:33],'little')==len(ui)-2
body=bytearray(32768);body[:64]=header;body[512:512+len(broker)-2]=broker[2:];body[2560:2560+len(ui)-2]=ui[2:]
body[24576:]=bytes((i*37+(i>>8))&255 for i in range(8192)) # data fixture only; no controller execution claimed
(W/'DOS64.MNU').write_bytes(body);(W/'modal-header.bin').write_bytes(header)
(W/'modal_capsule.s').write_text('.export _sm_modal_spec,_sm_modal_header\n.segment "DATA"\n_sm_modal_spec:\n.byte "D64M",1,16\n.word 32768\n.dword '+str(zlib.crc32(body))+'\n.dword $3da000\n_sm_modal_header:\n.incbin "modal-header.bin"\n')
(P/'inputs/build/dos64.prg').write_bytes(main);shutil.copyfile(E/'work/build/dos64.labels',P/'inputs/build/dos64.labels')
(P/'ROLE_BINDING.json').write_text(json.dumps({'scope':'runtime broker/main only; unit assets deliberately separate','native':binding['main'],'runtime_broker':binding['runtime_broker'],'unit_broker':binding['broker'],'UI':binding['UI'],'cohort_source_tag':binding['source_tag'],'menu_bytes':len(body),'menu_crc':zlib.crc32(body),'menu_sha256':hashlib.sha256(body).hexdigest()},indent=2)+'\n')
print('Packed32KiB split-asset data fixture; trailing8KiB not executable')
