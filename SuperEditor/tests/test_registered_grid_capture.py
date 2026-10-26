"""Frozen genuine59 C33/R25 capture integration; no product/asset rebuild/swap.

Released raw-boundary/wrapped/matrix/refusal oracles run against the exact
packaged images. Only CPU runners are compiled privately. CRC internals are
entered after actual residentC33 admission, never host-copying executable code.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,random,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_grid_raw_boundary as boundary
import test_grid_capture_stack as capture
from d81_image import D81Image
raw=boundary.raw;wrapped=boundary.wrapped;observer=raw.caret.profile.observer
BASE=ROOT/'build/cache-editor-product/20261026T180419392911Z/fixture'
C33_SHA='91a51068dbebaefc763379a5f6225a9cf0ddaabc098f6b219d2cd7a01eb31f2e'
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()

def authenticate(out,base):
 identity=json.load(open(base/'freeze.json'));assert len(identity['names'])==59 and len(set(identity['names']))==59
 assert sha(base/'build/overlays/grid.seo')==identity['assets']['grid']==C33_SHA
 report=json.load(open(base/'build/editor-report.json'));digest=bytes.fromhex(report['resident_binding']['digest'])
 assert sha(base/'build/editor.prg')==identity['prg_sha256']==report['sha256']
 disk=D81Image((base/'build/supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(base/'build/editor.prg').read_bytes()
 slots=[]
 for n in identity['names']:
  image=(base/f'build/overlays/{n}.seo').read_bytes();assert sha(base/f'build/overlays/{n}.seo')==identity['assets'][n]
  assert disk.read(n.upper().encode(),kind=1).data==image and image[:4]==b'SEO2'and image[20:36]==image[36:52]==digest
  assert len(image)-36==int.from_bytes(image[8:10],'little')and binascii.crc_hqx(image[36:],65535)==int.from_bytes(image[12:14],'little')
  slots.append(tuple(image[5:7]))
 assert len(set(slots))==59 and tuple((base/'build/overlays/grid.seo').read_bytes()[5:7])==(1,33)
 # Snapshot a coherent label/binary pair only. The sealedbin must equal the
 # actualC33 payload, not merely its length or header. CRC tests further check
 # entry semantics independently; no assembler/product rebuild is performed.
 labels=out/'labels';labels.mkdir()
 for suffix in('bin','lbl'):
  shutil.copy2(ROOT/f'build/overlays/grid.{suffix}',labels/f'grid.{suffix}')
 assert (labels/'grid.bin').read_bytes()==(base/'build/overlays/grid.seo').read_bytes()[36:],'sharedC33labels/bin not coherent with frozen product'
 symbols={v[2].lstrip('.'):int(v[1],16)for s in(labels/'grid.lbl').read_text().splitlines()if len(v:=s.split())==3 and v[0]=='al'}
 for n in('capture_tables','packet_crc'):assert 0xb010<=symbols[n]<0xc000
 result=dict(fixture=str(base),resident=identity['prg_sha256'],binding=digest.hex(),D81=sha(base/'build/supereditor.d81'),assets=59,C33=C33_SHA,R25=identity['assets']['geostail'],C33_label_sha256=sha(labels/'grid.lbl'),no_capsule_changes=True)
 (out/'identity.json').write_text(json.dumps(result,indent=2)+'\n');return result,symbols

def crc_component(out,base,symbols):
 out.mkdir();g=observer.Gate(out,base);f=g.f;rng=random.Random(3176)
 try:
  payload=(base/'build/overlays/grid.seo').read_bytes()[36:]
  f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
  assert not r.p&1 and r.a in(0,2)and f.read(0xb000,len(payload))==payload
  tag=next(i+1 for i,n in enumerate(g.identity['names'])if n=='grid');assert f.m.read(f.s['se_overlay_active']+1)==tag
  # Internal data-only arithmetic component. Owner4/exclusive512B phase is
  # supplied explicitly; public capture admission is covered by separate gates.
  f.put('se_f_owner',4,1);f.m.load(0x8d00,b'\x5a'*512);before=f.read(0,65536);reu=g.reu();r,n=f.fast_call(symbols['capture_tables']);after=f.read(0,65536);wanted=bytearray(before);wanted[0x100:0x200]=after[0x100:0x200]
  words=[binascii.crc_hqx(bytes((i,)),0)for i in range(256)];expected=bytes(x&255 for x in words)+bytes(x>>8 for x in words);wanted[0x8d00:0x8f00]=expected
  assert after==wanted and g.reu()==reu,'independent256CRCtable+wholeRAM/REU'
  cases=[];crc=f.s['se_crc_value']
  for i in range(132):
   packet=bytes((i,))*240 if i<4 else bytes(rng.randrange(256)for _ in range(240));f.m.load(0x88c4,packet);f.m.write(0x89c0,0)
   before=f.read(0,65536);r,n=f.fast_call(symbols['packet_crc']);after=f.read(0,65536);wanted=bytearray(before);wanted[0x100:0x200]=after[0x100:0x200];wanted[crc:crc+2]=binascii.crc_hqx(packet,65535).to_bytes(2,'little')
   assert after==wanted and g.reu()==reu,(i,'actualCRC kernel changed outsideCRC/stack')
   assert f.read(0xb000,len(payload))==payload,'no executable mutation';cases.append(n)
  result=dict(status='PASS',cases=132,table_words=256,instruction_min=min(cases),instruction_max=max(cases),residentC33admitted=True,no_executable_copy=True,whole64KiB_guards=133,whole16MiB_readonly=True,scope='Actual authenticated frozenC33 internal CRC kernel only; public capture/owner authority separately tested.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('CRC132_PASS',result,flush=True);return result
 finally:f.close()

def run(out,base,groups):
 out.mkdir(parents=True);identity,symbols=authenticate(out,base);results={}
 try:
  if 'sequence'in groups:results['sequence']=boundary.native_sequence(out/'public-sequence40',base);assert len(results['sequence'])==40
  if 'wrapped'in groups:results['wrapped']=wrapped.frames(out/'raw-wrapped44',base);assert len(results['wrapped'])==44
  if 'matrix'in groups:results['matrix']=raw.matrix(out/'matrix20',base);assert len(results['matrix']['cases'])==20
  if 'faults'in groups:results['faults']=wrapped.refusals(out/'faults24',base);assert len(results['faults'])==24
  if 'crc'in groups:results['crc']=crc_component(out/'crc132',base,symbols)
  result=dict(status='PASS-registered59-capture',identity=identity,groups=groups,results=results,scope=__doc__,gaps='No native/hardware/physical-key/ReadyOS claim; internalCRC component is distinct from actual public authority. Cross-generation substitution tests intentionally excluded.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('REGISTERED_CAPTURE_PASS',groups,flush=True);return result
 except BaseException:
  (out/'completed-groups.json').write_text(json.dumps(list(results),indent=2)+'\n');raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--groups',default='sequence,wrapped,matrix,faults,crc');a=p.parse_args();out=ROOT/'build/registered-grid-capture'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.groups.split(','))
