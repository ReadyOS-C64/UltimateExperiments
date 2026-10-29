"""Private dual incoming checkpoints and exact pre-flush before-TOP CRjoin proof."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,importlib.util,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as heading
from test_geos_semantic_checkpoint_codec import Fixture
from supermark_model import blocks
geos=heading.geos;semantic=heading.semantic;D=ROOT/'src/render/geos/semantic-previous-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture';F=0x8b40

def run(out,base):
 spec=importlib.util.spec_from_file_location('previous_build',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budget=b.build(out/'link',base)
 frozen,identity=geos.freeze(out,base);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True);f.assets['geossema']=(out/'link/seed/geossema.seo').read_bytes();f.assets['geospage']=(out/'link/producer/geospage.seo').read_bytes();fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def leaf(op):
  f.m.write(f.s['se_overlay_frame'],op);r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=1);assert not r.p&1,('leaf',op,hex(r.a));return r,n
 def source(data,at):
  f.source(data);f.command(99);f.position(at);before=f.reu();catalog=f.catalog();canonical=f.canonical();f.render();assert f.catalog()==catalog and f.canonical()==canonical
  cache,bank=f.raw_cache();after=f.reu();allowed=[(0,64),(0x600,0x680),(0xb200,0xea88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)];cursor=0
  for a,b in sorted((bank*65536+a,bank*65536+b)for a,b in allowed):assert after[cursor:a]==before[cursor:a],('producerforeignREU',cursor,a);cursor=max(cursor,b)
  assert after[cursor:]==before[cursor:]and f.read(0xc600,1024)==f.shim
  assert cache[0xe9e8:0xea68]==fonts['bsw9-widths.bin']and cache[0xe568:0xe9e8]==bytes(fonts['bsw9.bin'][i*18+y*2]for i in range(128)for y in range(9))
  assert f.get('se_v_top')==at,(at,f.get('se_v_top'));assert f.merged()==data
 def seed(selector,query,proof,allow=0):
  f.put('se_f_owner',4,1)
  for n in ['se_i_ready','se_i_count','se_n_cache_count']:f.put(n,0,1)
  f.m.load(F,query.to_bytes(3,'little'));f.m.write(F+179,allow);f.m.write(F+183,selector);canonical=f.canonical();before=f.reu();r,used=leaf(3);assert r.a==0 and f.m.read(F+180)==proof,(selector,query,f.m.read(F+180),proof);assert f.canonical()==canonical and f.reu()==before and not f.get('se_doc_read_locks',1)and not f.get('se_fs_owned',1);f.put('se_f_owner',0,1);return used
 def page(tag,data,at):
  bits,attrs,rows,_=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  cache,bank=f.raw_cache();a=cache[0x600:0x640];p=cache[0x640:0x680];events=list(blocks(data));event=next((e for e in events if e['start']==at),dict(kind=1,start=at,end=at));idx=events.index(event)if event in events else len(events);assert idx>0;prev=events[idx-1]['start']
  for record,anchor in [(a,at),(p,prev)]:assert record[:4]==bytes([0x53,2,64,1])and int.from_bytes(record[4:7],'little')==anchor and binascii.crc_hqx(record[:62],0xffff)==int.from_bytes(record[62:64],'little'),(tag,anchor,record.hex())
  assert a[7:35]==p[7:35]
  direct=seed(0,at,1);previous=seed(1,at,1);assert int.from_bytes(f.read(F+170,3),'little')==prev
  # Normal actual C24 uses incoming2 without cached-event shortcuts.
  f.put('se_f_owner',4,1);f.m.load(F,at.to_bytes(3,'little'));r,used=leaf(0);steps=0
  while f.m.read(F+21):r,n=leaf(1);used+=n;steps+=1;assert steps<100
  assert (f.m.read(F+5),int.from_bytes(f.read(F+9,3),'little'),int.from_bytes(f.read(F+12,3),'little'))==(event['kind'],at,event['end']);f.put('se_f_owner',0,1)
  geos.png(bits,attrs,out/(tag+'.png'));entry=dict(tag=tag,source_bytes=len(data),TOP=at,preceding=prev,current_carry=a[35:41].hex(),preceding_carry=p[35:41].hex(),current_lookup_instructions=direct,previous_lookup_instructions=previous,seeded_steps=steps,seeded_instructions=used);cases.append(entry);print('PASS',entry,flush=True);return prev
 try:
  pre=geos.native_text('prefix\r')*30
  for tag,suffix,needle in [('first-code',':::region A\r:::basic\r10 PRINT 1\r20 PRINT 2\r:::\r:::end\rTail.','10 PRINT'),('after-region',':::region A\rBody.\r:::end\rTail.','Tail.')]:
   data=pre+geos.native_text(suffix);at=data.index(geos.native_text(needle));source(data,at);page(tag,data,at)
  data=pre+geos.native_text(':::region A\r'*20+'# Deep heading\rTail.');at=data.index(b'#');source(data,at);page('region-overflow',data,at)
  data=pre+geos.native_text('Last row.\r');at=len(data);source(data,at);page('empty-EOF',data,at)
  pre=geos.native_text('prefix\r')*9400;data=pre+geos.native_text('# Heading words.\rFollowing row.\rTail.');at=data.index(geos.native_text('Following'));source(data,at);prev=page('far-beforeTOP-baseline',data,at);assert at==65817 and prev==65800
  generation=f.get('se_doc_generation',2);r=f.call('se_hot_call',4);assert not r.p&1 and f.get('se_hot_pending',1)==1 and f.get('se_doc_generation',2)==generation and f.m.read(0xcfe8)==1
  changed=data[:at-1]+data[at:];assert f.merged()==changed and f.document()==data
  miss=seed(0,at-1,0,1);hit=seed(1,at-1,2,1);assert int.from_bytes(f.read(F+170,3),'little')==prev
  f.put('se_f_owner',4,1);f.m.load(F,(at-1).to_bytes(3,'little'));r,used=leaf(0);steps=0
  while f.m.read(F+21):r,n=leaf(1);used+=n;steps+=1;assert steps<100
  event=next(e for e in blocks(changed)if e['start']==prev);assert (f.m.read(F+5),int.from_bytes(f.read(F+9,3),'little'),int.from_bytes(f.read(F+12,3),'little'))==(event['kind'],prev,event['end']);f.put('se_f_owner',0,1)
  cases.append(dict(tag='actual-C6-preflush-CRjoin',TOP=at,previous=prev,generation=generation,current_miss_instructions=miss,previous_hit_instructions=hit,seeded_instructions=used,seeded_steps=steps));print('PASS',cases[-1],flush=True)
  # C24 CANCEL releases only its real counted lease, preserving a foreignread.
  seed(1,at-1,2,1);f.put('se_f_owner',4,1);assert not f.call('se_doc_read_acquire').p&1;f.m.load(F,(at-1).to_bytes(3,'little'));leaf(0);assert f.get('se_doc_read_locks',1)==2;before=f.reu();leaf(2);assert f.get('se_doc_read_locks',1)==1 and not f.get('se_fs_owned',1)and f.reu()==before;assert not f.call('se_doc_read_release').p&1;f.put('se_f_owner',0,1)
  # The old key is not silently rebound when a real commit/replay changes it.
  f.command(16);seed(1,at-1,0,1)
  # BOF publishes current but explicitly invalidates any retained predecessor.
  data=geos.native_text('At BOF.\rTail.');source(data,0);cache,_=f.raw_cache();assert cache[0x603]==1 and cache[0x643]==0;seed(1,0,0)
  # Actual provider refusal during VALID-last must not fail the optional
  # producer or expose a partially trusted record. Only the DMA request is
  # faulted (protected shim destination); the real provider rejects it.
  labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'link/producer/geospage.lbl').read_text())}
  f.put('se_f_owner',4,1);f.m.load(F,bytes(192));leaf(0)
  while f.m.read(F+21):leaf(1)
  f.m.write(f.s['se_overlay_frame'],0);r,n=f.fast_call(f.s['se_overlay_call'],a=21,x=1);assert r.p&1 and r.a==0xb2
  r,n=f.fast_call(labels['se_gp_cache_guard']);assert not r.p&1
  f.m.write(0x9137,0);before=f.reu();canonical=f.canonical();bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));pos=bank*65536+0x600
  for name,value in [('pc',labels['gsc_publish']),('sp',0xfd),('p',0x24),('a',0),('x',0),('y',0)]:getattr(f.m.lib,'zeropage_peddle_set_'+name)(f.m.handle,value)
  f.m.write(0x1fe,0xfe);f.m.write(0x1ff,2);injected=0;steps=0
  while f.m.regs().pc!=0x2ff:
   if f.m.regs().pc==f.s['se_reu_copy']and f.get('se_reu_offset',2)==0x603 and f.get('se_reu_length',2)==1:
    assert not injected;f.put('se_reu_c64',0xc600,2);injected+=1
   f.m.lib.zeropage_peddle_step_instruction(f.m.handle);steps+=1;assert steps<100000
  assert injected==1 and not f.m.regs().p&1 and f.m.regs().a==0
  after=f.reu();assert after[pos+3]==0 and after[:pos]==before[:pos]and after[pos+64:]==before[pos+64:]and f.canonical()==canonical and f.read(0xc600,1024)==f.shim;f.put('se_f_owner',0,1);seed(0,0,0)
  cases.append(dict(tag='actual-VALID-last-provider-refusal',instructions=steps,scope='Actual checked provider rejects protected C64 span beforeDMA; producer optionalfailure Cclear; currentrecordVALID0 and foreignREU/canonical/shim exact.'))
  # A mismatched old C21 publisher writes V1 current records. Even a stale
  # CRC-correct V2 predecessor with matching tokens/key cannot authorize it.
  oldspec=importlib.util.spec_from_file_location('old_checkpoint_build',ROOT/'src/render/geos/semantic-checkpoint-candidate/build.py');old=importlib.util.module_from_spec(oldspec);oldspec.loader.exec_module(old);old.build(out/'old-publisher',base);f.assets['geospage']=(out/'old-publisher/producer/geospage.seo').read_bytes()
  data=geos.native_text('Old publisher.\rTail.');f.source(data);f.command(99);f.position(0);f.render();cache,bank=f.raw_cache();assert cache[0x601]==1
  bogus=bytearray(cache[0x600:0x640]);bogus[1]=2;bogus[35:41]=bytes([3,1,0,0,0,0]);bogus[41:44]=bytes(3);bogus[62:64]=binascii.crc_hqx(bogus[:62],0xffff).to_bytes(2,'little');f.m.load(0x9000,bogus);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',0x640,2);f.put('se_reu_c64',0x9000,2);f.put('se_reu_length',64,2);assert not f.call('se_reu_copy',0).p&1
  seed(1,0,0);assert f.m.read(0x9001)==1 #the stale predecessor was not fetched
  seed(0,0,0);cases.append(dict(tag='old-publisher-stale-previous',scope='Actual V1 C21 plus newC24; forgedCRC-correct V2 staleprior/fullkey is safely ignored.'))
  # Malformed selector fails before source lease creation or phase mutation.
  f.put('se_f_owner',4,1);f.m.write(F+183,2);f.m.write(f.s['se_overlay_frame'],3);ram=f.read(F,192);r,n=f.fast_call(0xb010);assert r.p&1 and r.a==0x90 and f.read(F,192)==ram and not f.get('se_doc_read_locks',1);f.put('se_f_owner',0,1)
  result=dict(status='passed',budget=budget,cases=cases,scope='Actual private C21/C24 producer/transport and actual C6W_BACK before root reveal/flush. Full public BEFORE-TOP routing is not changed; actual original public225M remains open. Both64B records typedFE0600/0640. No addedstate/asset/bank. Whole16MiB read-only lookup guards; source/history/shim exact.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-semantic-previous'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture.resolve());print('RESULT',r['status'],r['budget'],'cases',len(r['cases']))
