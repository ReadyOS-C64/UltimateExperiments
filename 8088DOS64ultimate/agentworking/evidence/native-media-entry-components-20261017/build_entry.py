"""Rebuild the private unit-linked entry cohort; not a START container builder."""
from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-entry-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import hashlib,json,subprocess,shutil
W=P/'work'
def info(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def run(args,cwd,name):
 with (P/(name+'.stdout')).open('wb')as out,(P/(name+'.stderr')).open('wb')as err:
  subprocess.run(args,cwd=cwd,stdout=out,stderr=err,check=True)
def symbols(p):return {x.split()[2].lstrip('.'):int(x.split()[1],16)for x in p.read_text().splitlines()if x.startswith('al ')}
source={}
for root in [W/'src',W/'include',W/'cfg',W/'build_support',P/'broker']:
 for p in sorted(root.rglob('*')):
  if p.is_file()and p.suffix in ['.s','.inc','.cfg','.py','.json','.mk']and p.name!='modal_assets.inc':source[str(p.relative_to(P))]=info(p)
source['build_entry.py']=info(P/'build_entry.py')
source['work/Makefile']=info(W/'Makefile')
source['ui/panel.prg']=info(P/'ui/panel.prg')
source['ui/panel.labels']=info(P/'ui/panel.labels')
flags={'DOS64_MODAL_MENU':1,'DOS64_SAVE_HD_CONTEXT':1,'DOS64_EXPORT_CRC':1}
tag=hashlib.sha256(json.dumps({'source':source,'flags':flags},sort_keys=True,separators=(',',':')).encode()).digest()[:16]
run(['ca65','-g','-I',str(P/'broker'),'-o','broker.o','broker.s'],P/'broker','final-broker-assemble')
run(['ld65','-C','broker.cfg','-o','broker.prg','-m','broker.map','-Ln','broker.labels','broker.o'],P/'broker','final-broker-link')
broker=(P/'broker/broker.prg').read_bytes();ui=(P/'ui/panel.prg').read_bytes();assert broker[:2]==b'\x00p' and ui[:2]==b'\x00\x80'
assert len(broker)-2<=1792 and len(ui)-2<=8192
header=bytearray(64);header[:8]=b'D64M\x01\x01\x40\x00';header[8:24]=tag;header[24:26]=(len(broker)-2).to_bytes(2,'little');header[26:28]=(0x7000).to_bytes(2,'little');header[28:31]=(0x3da200).to_bytes(3,'little');header[31:33]=(len(ui)-2).to_bytes(2,'little');header[33:36]=(0x3daa00).to_bytes(3,'little')
(P/'HEADER.bin').write_bytes(header)
(W/'include/modal_assets.inc').write_text('MM_BROKER_BYTES='+str(len(broker)-2)+'\nMM_HEADER_REU=$3da000\nMM_BROKER_REU=$3da200\n.macro MM_EXPECTED_HEADER\n.byte '+','.join(map(str,header))+'\n.endmacro\n')
run(['make','build/dos64.prg','build/dos64-tests.prg','build/dos64-tests.prg.unit-extra.bin','build/dos64-tests.bin','verify-memory']+[k+'='+str(v)for k,v in flags.items()],W,'final-native-build')
# The broker must call this exact linked native layout, never predecessor labels.
native=symbols(W/'build/dos64-tests.labels')
for line in (P/'broker/symbols.inc').read_text().splitlines():
 if '=' in line:
  name,value=line.split('=',1);assert native[name.strip()]==int(value.strip().lstrip('$'),16),(name,value,native.get(name.strip()))
record={'scope':'private actual CIA/INPUT/footer/native CUI Resume; exact seeded REU assets; no START container or disk-worker routing','flags':flags,'source':source,'source_tag':tag.hex(),'broker_payload_bytes':len(broker)-2,'UI_payload_bytes':len(ui)-2,'header':info(P/'HEADER.bin'),'main':info(W/'build/dos64.prg'),'unit':info(W/'build/dos64-tests.prg'),'broker':info(P/'broker/broker.prg'),'UI':info(P/'ui/panel.prg'),'color_snapshot_REU':[0x3e2000,0x3e2000+1000]}
(P/'BINDING.json').write_text(json.dumps(record,indent=2)+'\n')
run(['/usr/bin/python3','-B','test_entry.py','-v'],P,'final-entry-tests')
print(json.dumps({k:record[k]for k in ['source_tag','broker_payload_bytes','UI_payload_bytes','main','unit']}))
