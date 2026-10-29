"""Private actual C24 TRY_SEED: typed FE, counted R14 lease, no BOF lookup."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as heading
from test_geos_semantic_checkpoint_codec import Fixture
from supermark_model import blocks
geos=heading.geos;D=ROOT/'src/render/geos/semantic-checkpoint-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture';F=0x8b40

def run(out,base):
 spec=importlib.util.spec_from_file_location('checkpoint_build',D/'build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);budget=builder.build(out/'link',base)
 frozen,identity=geos.freeze(out,base);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True);f.assets['geossema']=(out/'link/seed/geossema.seo').read_bytes();cases=[]
 def leaf(op,carry=False):
  f.m.write(f.s['se_overlay_frame'],op);r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=1);assert bool(r.p&1)==carry,('C24',op,hex(r.a));return r,n
 def claim():
  f.put('se_f_owner',4,1)
  for n in ['se_i_ready','se_i_count','se_n_cache_count']:f.put(n,0,1)
 def release():
  assert not any(f.get(n,1)for n in ['se_fs_owned','se_doc_read_locks']);f.put('se_f_owner',0,1)
 def query(at,reset=False):
  claim()
  if reset:f.m.write(F+28,0)
  f.m.load(F,at.to_bytes(3,'little'));r,n=leaf(0);used=n;steps=0
  while f.m.read(F+21):r,n=leaf(1);used+=n;steps+=1;assert steps<5000
  assert f.m.read(F+182)==1
  event=dict(kind=f.m.read(F+5),start=int.from_bytes(f.read(F+9,3),'little'),end=int.from_bytes(f.read(F+12,3),'little'),body=int.from_bytes(f.read(F+15,3),'little'),language=f.m.read(F+6))
  incoming=f.read(F+170,9);key=f.read(F+30,28);release();return event,incoming,key,used,steps
 def record(incoming,key):
  r=bytearray(64);r[:4]=bytes([0x53,1,64,1]);r[4:7]=incoming[:3];r[7:35]=key;r[35:41]=incoming[3:];r[62:64]=binascii.crc_hqx(r[:62],0xffff).to_bytes(2,'little');return bytes(r)
 def publish(rec):
  handle=f.get('se_gc_handle',1);before=f.reu();bank=f.m.read(f.s['se_reu_map']+handle);f.m.load(0x9000,rec);f.put('se_reu_logical',handle,1);f.put('se_reu_offset',0x600,2);f.put('se_reu_c64',0x9000,2);f.put('se_reu_length',64,2);assert not f.call('se_reu_copy',0).p&1
  after=f.reu();pos=bank*65536+0x600;assert after[:pos]==before[:pos]and after[pos+64:]==before[pos+64:]and after[pos:pos+64]==rec
 def seed(at,expected,allow=0,poison=False):
  claim()
  if poison:f.m.load(F,bytes([0xa5])*192)
  f.m.load(F,at.to_bytes(3,'little'));f.m.write(F+179,allow);before=f.reu();canonical=f.canonical();r,used=leaf(3)
  proof=f.m.read(F+180);assert r.a==0 and proof==expected,(at,proof,expected,f.read(F,192).hex());assert f.reu()==before and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  assert not any(f.get(n,1)for n in ['se_fs_owned','se_fs_active','se_doc_read_locks'])and f.read(0x912c,2)==b'\0\0'
  assert int.from_bytes(f.read(F+164,3),'little')==0
  if expected:assert f.m.read(F+28)==2
  else:assert f.m.read(F+28)==0
  release();return used
 try:
  for tag,prefix in [('near',geos.native_text('Prelude\r:::basic\r10 PRINT 1\r:::\r')),('far64k',geos.native_text('prefix\r')*9400+geos.native_text(':::asm\r'))]:
   data=prefix+geos.native_text('# Heading words.\rFollowing row.\rTail.');anchor=len(prefix);f.source(data);f.command(99);f.position(anchor+5);f.render();ev,incoming,key,full,steps=query(anchor,True);assert incoming[:3]==anchor.to_bytes(3,'little');rec=record(incoming,key);publish(rec)
   lookup=seed(anchor,1,poison=True);assert f.read(F+170,3)==anchor.to_bytes(3,'little');next_ev,_,_,used,next_steps=query(anchor+5);assert next_ev==ev and next_steps<=2,(tag,next_steps)
   expected=next(e for e in blocks(data)if e['start']==anchor);assert ev['kind']==expected['kind']and ev['end']==expected['end']
   # Current C6 real pending certificate; no flush/rekey is guessed.
   f.key(geos.native_text('Q')[0]);assert f.m.read(0xcfe8)==1;changed=data[:anchor+5]+geos.native_text('Q')+data[anchor+5:];assert f.merged()==changed
   edit_lookup=seed(anchor,2,allow=1,poison=True);changed_ev,_,_,edit_used,edit_steps=query(anchor+6);expected=next(e for e in blocks(changed)if e['start']==anchor);assert changed_ev['kind']==expected['kind']and changed_ev['end']==expected['end']
   seed(anchor,0,allow=0,poison=True)
   # Epoch/CRC/stale-source and map failures are optional misses, not source errors.
   for offset in [0,3,4,7,24,35,62,63]:
    bad=bytearray(rec);bad[offset]^=1;publish(bad);seed(anchor,0,allow=1,poison=True)
   publish(rec);oldwidth=f.get('se_gc_width',1);f.put('se_gc_width',0xfe,1);seed(anchor,0,allow=1);f.put('se_gc_width',oldwidth,1)
   seed(anchor-1,0,allow=1)
   # Two actual unpainted edits cannot reuse a single-mutation ticket.
   f.key(geos.native_text('R')[0]);assert f.m.read(0xcfe8)==0;seed(anchor,0,allow=1)
   f.command(16);seed(anchor,0,allow=1) #actual flush/replay changes graph/gen
   cases.append(dict(tag=tag,source_bytes=len(data),anchor=anchor,original_query_instructions=full,original_query_steps=steps,seed_instructions=lookup,seeded_query_instructions=used,seeded_query_steps=next_steps,actual_edit_seed_instructions=edit_lookup,actual_edit_query_instructions=edit_used));print('PASS',cases[-1],flush=True)
  # Before any phase access: foreign owner is opaque, including checkpoint bytes.
  f.put('se_f_owner',1,1);f.m.write(f.s['se_overlay_frame'],3);ram=f.read(0,65536);reu=f.reu();r,n=f.fast_call(0xb010);assert r.p&1 and r.a==0xb2;after=f.read(0,65536);assert after[:0x100]==ram[:0x100]and after[0x200:]==ram[0x200:]and f.reu()==reu;f.put('se_f_owner',0,1)
  result=dict(status='passed',budget=budget,cases=cases,scope='Actual sealed private C24 op3 + checked FE transport + R14 lease + actual C6 certificate; fixture publishes real incoming9/key28 as64B checked record. Producer/C21 and C23 are not yet integrated. Miss never BOF-parses; source/shim/whole16MiB read-only intervals exact.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-semantic-checkpoint-seed'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);print(run(out,a.fixture.resolve()))
