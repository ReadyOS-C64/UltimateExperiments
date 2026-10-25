"""Fault proof for oversized private refresh helper, not an integration release."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_consumer as c

def run(out,candidate):
 result=json.loads((candidate/'result.json').read_text());assert result['status']=='passed'and len(result['cases'])==30
 frozen,identity=c.geos.freeze(out,candidate/'fixture');c.geos.grid.editor_fixture.ROOT=c.geos.grid.cpu_editor.ROOT=frozen;c.geos.grid.editor_fixture.NAMES=c.geos.grid.cpu_editor.NAMES=identity['names'];dll=c.geos.grid.runner(out);f=c.Fixture(out,frozen,dll,True);aux=result.get('variant')=='AUX';f.assets['aux' if aux else 'viewsource']=(candidate/'link/helper'/('aux.seo' if aux else'viewsource.seo')).read_bytes();f.assets['geossema']=(candidate/'consumer-link/seed/geossema.seo').read_bytes();f.assets['geospage']=(candidate/'consumer-link/producer/geospage.seo').read_bytes();cases=[];data=b''
 def setup():
  nonlocal data
  pre=c.geos.native_text('prefix\r')*30;data=pre+c.geos.native_text('# Heading words.\rSecond plain row.\rTail.');top=len(pre);f.source(data);f.command(99);f.position(top);f.render();f.position(top+22);f.render();at=f.get('se_hot_caret');data=data[:at]+c.geos.native_text('Q')+data[at:];f.key(c.geos.native_text('Q')[0]);f.render();assert f.merged()==data
 def call(want=False,locks=0,owner=0):
  before=f.reu();canonical=f.canonical();body=f.read(0x6000,8000);shim=f.read(0xc600,1024);catalog=f.catalog();f.m.write(f.s['se_overlay_frame'],6);r,n=f.fast_call(f.s['se_overlay_call'],a=13 if aux else 14,x=1 if aux else 0);assert not r.p&1 and r.a==int(want),(r.a,want)
  assert f.canonical()==canonical and f.read(0x6000,8000)==body and f.read(0xc600,1024)==shim==f.shim and f.catalog()==catalog and f.get('se_doc_read_locks',1)==locks and f.get('se_f_owner',1)==owner
  if not want:assert f.reu()==before
  else:
   _,bank=f.raw_cache();start=bank*65536+0x600;after=f.reu();assert after[:start]==before[:start]and after[start+128:]==before[start+128:]
  return n
 def done(tag,**kw):cases.append(dict(tag=tag,**kw));print('PASS',cases[-1],flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
 def write_record(offset,change):
  cache,_=f.raw_cache();r=bytearray(cache[offset:offset+64]);change(r);r[62:64]=binascii.crc_hqx(r[:62],65535).to_bytes(2,'little');f.m.load(0x9000,r)
  for n,v,w in [('se_reu_logical',f.get('se_gc_handle',1),1),('se_reu_offset',offset,2),('se_reu_c64',0x9000,2),('se_reu_length',64,2)]:f.put(n,v,w)
  assert not f.call('se_reu_copy',0).p&1
 try:
  # All faults are deliberate fixture mutations, snapshotted after injection.
  # Genuine source/key/cap failures decline before any retention write.
  fields=[('old-sequence',0xcfe8+14),('old-revision',0xcfe8+7),('old-length',0xcfe8+11),('op',0xcfe8+1),('insert-old-byte',0xcfe8+5),('GEC-docepoch',0xcfe8+16),('GEC-REUepoch',0xcfe8+18),('GCC-epoch',0xcf90+5),('current-key-token',0xcf90+7),('GCC-sequence',0xcf90+1),('cache-epoch',f.s['se_gc_epoch']),('logical-FE-handle',f.s['se_gc_handle'])]
  for tag,a in fields:
   setup();f.m.write(a,f.m.read(a)^0x40);done(tag,instructions=call())
  setup();f.m.load(0xcfea,bytes(3));done('edit-before-current-anchor',instructions=call())
  setup();f.render();done('intervening-readonly-publication',instructions=call())
  setup();f.put('se_f_owner',1,1);f.m.load(0x8880,bytes([0x5a])*640);f.m.load(0x8d00,bytes([0xa5])*1152);phase=f.read(0x8880,640)+f.read(0x8d00,1152);done('foreign-owner-opaque',instructions=call(owner=1));assert f.read(0x8880,640)+f.read(0x8d00,1152)==phase;f.put('se_f_owner',0,1)
  setup();assert not f.call('se_doc_read_acquire').p&1;done('foreign-counted-lease',instructions=call(True,locks=1));assert not f.call('se_doc_read_release').p&1
  for tag,offset,mutate in [('CRC-correct-oldkey-gap',0x600,lambda r:r.__setitem__(24,r[24]^4)),('CRC-correct-wrong-TOP',0x640,lambda r:r.__setitem__(41,r[41]^1)),('CRC-correct-prior-at-TOP',0x640,lambda r:r.__setitem__(slice(4,7),f.get('se_v_top').to_bytes(3,'little')))]:
   setup();write_record(offset,mutate);done(tag,instructions=call())
  setup();cache,_=f.raw_cache();f.m.write(0x9000,cache[0x63e]^1)
  for n,v,w in [('se_reu_logical',f.get('se_gc_handle',1),1),('se_reu_offset',0x63e,2),('se_reu_c64',0x9000,2),('se_reu_length',1,2)]:f.put(n,v,w)
  assert not f.call('se_reu_copy',0).p&1;done('actual-bad-CRC',instructions=call())
  # Fault the actual VALID-last transfer request into protected C600; the
  # provider refuses it. Earlier VALID0/body write is permitted and preserved.
  for fault_offset in(0x603,0x643):
   setup();before=f.reu();canonical=f.canonical();_,bank=f.raw_cache();start=bank*65536+0x600;f.m.write(f.s['se_overlay_frame'],6)
   for n,v in [('pc',f.s['se_overlay_call']),('sp',0xfd),('p',0x24),('a',13 if aux else 14),('x',1 if aux else 0),('y',0)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
   f.m.write(0x1fe,0xfe);f.m.write(0x1ff,2);injected=0;steps=0
   while f.m.regs().pc!=0x2ff:
    if f.m.regs().pc==f.s['se_reu_copy']and f.get('se_reu_logical',1)==f.get('se_gc_handle',1)and f.get('se_reu_offset',2)==fault_offset and f.get('se_reu_length',2)==1:
     assert not injected;f.put('se_reu_c64',0xc600,2);injected+=1
    f.m.lib.zeropage_peddle_step_instruction(f.m.handle);steps+=1;assert steps<100000
   after=f.reu();assert injected==1 and not f.m.regs().p&1 and f.m.regs().a==0 and f.canonical()==canonical and after[:start]==before[:start]and after[start+128:]==before[start+128:]and after[start+fault_offset-0x600]==0 and f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in ['se_f_owner','se_doc_read_locks','se_fs_owned'])
   # Real C24 must never see a half-published pair as predecessor authority.
   f.put('se_f_owner',4,1)
   for selector in(0,1):
    f.m.load(0x8b40,f.get('se_v_top').to_bytes(3,'little'));f.m.write(0x8b40+179,1);f.m.write(0x8b40+183,selector);f.m.write(f.s['se_overlay_frame'],3);r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=1);assert not r.p&1 and f.m.read(0x8b40+180)==(1 if fault_offset==0x643 and selector==0 else 0),(fault_offset,selector,f.m.read(0x8b40+180));assert f.reu()==after and f.canonical()==canonical and not f.get('se_doc_read_locks',1)
   f.put('se_f_owner',0,1);done('actual-VALID-last-provider-refusal-'+hex(fault_offset),instructions=steps,scope='Current may remain independentlytrusted only afterits fullVALID-last; predecessor alwaysmisses untilbothkeys/CRC/VALIDagree.')
  result=dict(status='passed',candidate=str(candidate),cases=cases,scope='Privateauthoritycomponent variant '+str(aux)+'; actualCPU/FS/provider and16MiB no-outputfault/foreignlease/partialVALIDlast proof; no producthook or finalSP2fit.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);a=p.parse_args();out=ROOT/'build/geos-semantic-refresh-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.candidate.resolve());print('RESULT',r['status'],'cases',len(r['cases']))
