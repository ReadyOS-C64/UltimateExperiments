"""Private actual C24/R14 + parser incoming-checkpoint codec; no product integration."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,importlib.util,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as heading
from supermark_model import blocks
geos=heading.geos;D=ROOT/'src/render/geos/semantic-checkpoint-candidate'
BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
F=0x8b40;RECORD=0x9000;PARSER=0x8d00
class Fixture(heading.Fixture):
 def reu(self):
  b=C.create_string_buffer(16*1024*1024);self.dll.gm_reu(self.m.handle,len(b),b);return b.raw

def run(out,base):
 spec=importlib.util.spec_from_file_location('checkpoint_build',D/'build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);budget=builder.build(out/'link',base)
 frozen,identity=geos.freeze(out,base);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out)
 labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'link/codec/geossema.lbl').read_text())};seo=(out/'link/codec/geossema.seo').read_bytes();f=Fixture(out,frozen,dll,True);f.assets['geossema']=seo;cases=[]
 def invoke(name,a=0):
  r,n=f.fast_call(labels[name],a=a);assert not r.p&1,(name,hex(r.a));return r.a
 def leaf(op):
  f.m.write(f.s['se_overlay_frame'],op);r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=1);assert not r.p&1,('C24',op,hex(r.a));return r.a
 def current():
  raw=f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_r_revision'],4)+f.read(f.s['se_fs_length'],3)+f.read(f.s['se_reu_epoch'],2)+f.read(f.s['se_doc_epoch'],2);assert len(raw)==28;f.m.load(F+30,raw);return raw
 def acquire(query):
  f.put('se_f_owner',4,1);f.put('se_i_ready',0,1);f.put('se_i_count',0,1);f.put('se_n_cache_count',0,1);f.m.load(F+28,bytes(160));f.m.load(F,query.to_bytes(3,'little'));leaf(0);current();assert f.get('se_fs_owned',1)==1
 def end():
  leaf(2);f.put('se_f_owner',0,1);assert f.get('se_doc_read_locks',1)==0
 def event():
  return tuple(int.from_bytes(f.read(labels[n],w),'little')for n,w in [('se_sm_kind',1),('se_sm_start',3),('se_sm_end',3),('se_sm_body',3),('se_sm_language',1)])
 def parser_event(data,anchor):
  for byte in data[anchor:]:
   invoke('se_sm_feed',byte)
   if f.m.read(labels['se_sm_ready']):return event()
  invoke('se_sm_finish');return event()
 def encode(data,anchor):
  invoke('se_sm_init')
  for byte in data[:anchor]:invoke('se_sm_feed',byte)
  # Capture late in the target prefix: sm_line is still its incoming START.
  for byte in data[anchor:min(data.find(b'\r',anchor)if b'\r'in data[anchor:]else len(data),anchor+4)]:invoke('se_sm_feed',byte)
  before=f.reu();invoke('se_gsc_encode');assert f.reu()==before
  raw=f.read(RECORD,64);assert int.from_bytes(raw[4:7],'little')==anchor and int.from_bytes(raw[62:64],'little')==binascii.crc_hqx(raw[:62],0xffff)
  return raw
 def restore(record,query,allow=0,expect=1):
  f.m.load(RECORD,record);f.m.load(F,query.to_bytes(3,'little'));f.m.write(F+179,allow);f.m.load(PARSER,bytes((i*29+73)&255 for i in range(79)));old=f.read(PARSER,79);reu=f.reu();catalog=f.catalog();a=invoke('se_gsc_restore');assert a==expect,(a,expect,record.hex());assert f.reu()==reu and f.catalog()==catalog and f.read(RECORD,64)==record and f.read(0xc600,1024)==f.shim
  if not expect:assert f.read(PARSER,79)==old
 def check(tag,data,anchor):
  acquire(anchor);record=encode(data,anchor);restore(record,anchor);actual=parser_event(data,anchor);expected=next(e for e in blocks(data)if e['start']==anchor);want=(expected['kind'],anchor,expected['end'],expected['body'],expected['language']);assert actual==want,(tag,actual,want)
  # Every record byte is integrity-covered. Miss preserves the complete79B parser.
  for at in range(64):
   bad=bytearray(record);bad[at]^=1;restore(bytes(bad),anchor,expect=0)
  # Recomputed-CRC semantic and immutable identity mutations still fail.
  for at in [0,1,2,3,7,12,17,22,31,33,35,36]:
   bad=bytearray(record);bad[at]=2 if at==35 else 3 if at==36 else bad[at]^1;bad[62:64]=binascii.crc_hqx(bad[:62],0xffff).to_bytes(2,'little');restore(bytes(bad),anchor,expect=0)
  restore(record,max(0,anchor-1),expect=int(anchor==0));end();cases.append(dict(tag=tag,anchor=anchor,source_bytes=len(data),event=want));print('PASS',cases[-1],flush=True);return record
 try:
  data=geos.native_text('Prose\r:::basic\r10 PRINT 1\r:::\r:::region A\r# Heading\r:::end\rTail.')
  f.source(data)
  for anchor in [0,data.index(geos.native_text('10 PRINT')),data.index(geos.native_text('# Heading')),data.index(geos.native_text('Tail.'))]:check('mixed-'+str(anchor),data,anchor)
  # Source>64KiB: actual merged provider, no truncated anchors; direct feed is
  # deliberately component input, not a claim that C24 transport is integrated.
  data=geos.native_text('prefix\r')*9400+geos.native_text(':::asm\rstart: lda #1\r:::\rTail.');anchor=data.index(geos.native_text('start:'));f.source(data);check('24bit-fence',data,anchor)
  # Actual public C6 mutation certificate, actual R14 counted reader and source.
  data=geos.native_text('Prelude\r# Heading words.\rFollowing row.');anchor=data.index(b'#');at=anchor+5;f.source(data);f.command(99);f.position(at);f.render();acquire(anchor);old=encode(data,anchor);end();f.key(geos.native_text('Q')[0]);assert f.m.read(0xcfe8)==1
  changed=data[:at]+geos.native_text('Q')+data[at:];assert f.merged()==changed;acquire(anchor);restore(old,at,allow=1);actual=parser_event(changed,anchor);ev=next(e for e in blocks(changed)if e['start']==anchor);assert actual==(ev['kind'],anchor,ev['end'],ev['body'],ev['language']);restore(old,at,allow=0,expect=0)
  # Wrong epoch/generation/length/current-global snapshots reject before writes.
  key=f.read(F+30,28)
  for at2 in range(28):
   bad=bytearray(key);bad[at2]^=1;f.m.load(F+30,bad);restore(old,at,allow=1,expect=0)
  f.m.load(F+30,key);end();cases.append(dict(tag='actual-C6-incremental-GEC',anchor=anchor,source_bytes=len(changed)))
  # Foreign owner must be rejected before frame/parser/token access.
  f.put('se_f_owner',1,1);ram=f.read(0,65536);reu=f.reu();r,n=f.fast_call(labels['se_gsc_restore']);assert r.p&1 and r.a==0xb2;after=f.read(0,65536);assert after[:0x100]==ram[:0x100]and after[0x200:]==ram[0x200:]and f.reu()==reu;f.put('se_f_owner',0,1)
  result=dict(status='passed',budget=budget,cases=cases,record_faults=5*77,current_identity_faults=28,scope='Private actual sealed C24+R14 codec component; actual parser carry and C6 GEC, no FE publication/transport/C23 integration claim. All intervals whole16MiB REU immutable; malformed miss preserves79B parser and64B record.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-semantic-checkpoint-codec'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);print(run(out,a.fixture.resolve()))
