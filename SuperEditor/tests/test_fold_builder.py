"""Actual SuperMark + bounded fold builder + checked logical REU objects.
Builds only build/folds/builder. Independent whole-input interval oracle.
"""
from pathlib import Path
import importlib.util,sys,json,subprocess,random,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from supermark_model import blocks
from supermark_probe import petscii
spec=importlib.util.spec_from_file_location('fold_foundation_test',ROOT/'tests/test_folds.py');base=importlib.util.module_from_spec(spec);sys.modules[spec.name]=base;spec.loader.exec_module(base)
OUT=ROOT/'build/folds/builder';OUT.mkdir(parents=True,exist_ok=True);base.OUT=OUT
NAMES=['reu/provider','reu/dma','object/state','object/validate','object/allocate','object/resize','object/copy','supermark/block']+['fold/'+x for x in ['state','store','validate','query','action','probe','builder-state','builder','builder-filter','builder-retain']]
def build():
 objects=[]
 for n in NAMES:
  p=OUT/(n.replace('/','-')+'.o');objects.append(str(p));subprocess.run(['ca65','-I',str(ROOT/'src'),'-g','-o',str(p),str(ROOT/'src'/Path(n+'.s'))],check=True)
 subprocess.run(['ld65','-C',str(ROOT/'src/fold/builder-probe.cfg'),'-o',str(OUT/'probe.bin'),'-m',str(OUT/'probe.map'),'-Ln',str(OUT/'probe.lbl'),*objects],check=True)

# Global heading section semantics stay intact. D093 affects only optional fold
# projection: explicit/fence intervals have priority over crossing headings.
def oracle(data):
 events=blocks(data);raw=[];heads=[];regions=[];code=None
 def opened(e,kind,i):
  hidden=e['end']+int(e['end']<len(data) and data[e['end']]==13)
  raw.append(base.Fold(e['start'],hidden,0,kind=kind,level=e['level'] if kind==1 else 0,lines=i));return len(raw)-1
 def closed(k,end,line,heading=False):
  f=raw[k];f.end=end;f.lines=line-f.lines-int(heading)
 for i,e in enumerate(events):
  kind=e['kind'];after=e['end']+int(e['end']<len(data) and data[e['end']]==13)
  if kind==2:
   while heads and raw[heads[-1]].level>=e['level']:closed(heads.pop(),e['start'],i,True)
   heads.append(opened(e,1,i))
  elif kind==4:code=opened(e,2,i)
  elif kind==6:
   assert code is not None;closed(code,after,i);code=None
  elif kind==7:regions.append(opened(e,3,i))
  elif kind==8:closed(regions.pop(),after,i)
 if code is not None or regions:return None,0,0,0xB5
 for k in heads:closed(k,len(data),len(events),True)
 def cross(a,b):return a.start<b.start<a.end<b.end or b.start<a.start<b.end<a.end
 explicit=[r for r in raw if r.kind!=1]
 omitted={i for i,r in enumerate(raw) if r.kind==1 and any(cross(r,x) for x in explicit)}
 empty={i for i,r in enumerate(raw) if r.hidden>=r.end}
 result=[r for i,r in enumerate(raw) if i not in omitted|empty]
 for i,r in enumerate(result):
  parents=[j for j,p in enumerate(result[:i]) if p.hidden<=r.start and r.end<=p.end]
  r.parent=parents[-1] if parents else 65535;r.depth=result[r.parent].depth+1 if parents else 0
  if r.depth>=16:return None,len(omitted),len(empty),0xB6
 assert base.valid_model(result,len(data)),result
 return result,len(omitted),len(empty),0

class Fixture(base.Fixture):
 def __init__(self):
  super().__init__()
  # The parent fixture's readonly poison includes the new parser/context ranges.
  # Restore actual parser code, zero new caller frames and establish new guards.
  image=(OUT/'probe.bin').read_bytes();self.m.load(0xB000,image[0xA000:0xB000]);self.m.load(self.s['se_fb_state'],bytes(self.s['se_fb_state_size']));self.m.load(self.s['se_sm_state'],bytes(self.s['se_sm_state_size']))
  self.guards=[]
  ranges=[(0,256),(0x1000,0x7000),(0x8820,0x7E0),(0x90A0,0xD60),(0xA800,0x1800),(0xC0C5,0x3B),(self.s['se_fb_state']+self.s['se_fb_state_size'],0xC200-self.s['se_fb_state']-self.s['se_fb_state_size']),(self.s['se_sm_state']+self.s['se_sm_state_size'],0xC600-self.s['se_sm_state']-self.s['se_sm_state_size']),(0xCA00,0x600)]
  for a,n in ranges:self.guards.append((a,self.ram(a,n)))
  self.max_dma=0;self.builder_steps=0
 def seed(self,data,capacity=32768):
  self.source=data;self.write_object(self.source_token,data)
  self.put('se_object_id',self.token);self.put('se_object_offset',capacity*32,3);assert not self.call('se_object_resize').p&1
  self.put('se_fold_caret',min(7,len(data)),3);self.put('se_fold_select_a',len(data),3);self.put('se_fold_select_b',0,3);self.put('se_fb_old_valid',0);self.put('se_fb_source',self.source_token);self.put('se_fb_capacity',capacity,2);self.put('se_fold_token',self.token);self.put('se_fold_length',len(data),3);self.put('se_fold_epoch',0x12345678,4);self.put('se_fb_busy',0);self.put('se_fold_busy',0)
  self.reu_before=self.reu_image()
 def finish(self,limit=100000):
  n=0
  while self.get('se_fb_busy'):
   before=self.get('se_reu_dma_calls',2);pos=self.get('se_sm_pos',3);r=self.call('se_fb_step');dma=(self.get('se_reu_dma_calls',2)-before)&65535;self.max_dma=max(self.max_dma,dma);assert dma<=2
   assert self.get('se_sm_pos',3)-pos<=32
   n+=1;self.builder_steps+=1
   if r.p&1:return r,n
   assert n<limit
  return r,n
 def check(self,data,capacity=32768):
  expected,omitted,empty,error=oracle(data);self.seed(data,capacity);canonical=self.ram('se_fold_caret',3)+self.ram('se_fold_select_a',6);r=self.call('se_fb_begin');assert not r.p&1,(r.a,'begin');r,n=self.finish()
  assert self.object_bytes(self.source_token[0],len(data))==data
  assert self.ram('se_fold_caret',3)+self.ram('se_fold_select_a',6)==canonical
  if error:
   assert r.p&1 and r.a==error and not self.get('se_fold_valid'),(data,error,r.a);return None
  assert not r.p&1,(data,r.a,self.get('se_fb_phase'))
  assert self.get('se_fold_valid')==1 and self.get('se_fold_count',2)==len(expected)
  assert self.get('se_fb_omitted',2)==omitted and self.get('se_fb_empty',2)==empty,(data,omitted,self.get('se_fb_omitted',2),empty,self.get('se_fb_empty',2))
  actual=self.object_bytes(self.fold_id,len(expected)*32);wanted=b''.join(r.bytes() for r in expected);assert actual==wanted,(data,actual.hex(),wanted.hex())
  assert self.object_bytes(self.source_token[0],len(data))==data
  return expected

def main():
 build();(OUT/'result.json').unlink(missing_ok=True);f=Fixture();rng=random.Random(0xB01D6510);fixtures=queries=0
 try:
  texts=['','plain text\n','# Empty','# Heading\nbody\n','# A\n## B\nbody\n# C\nend',':::basic\n10PRINT"Mixed Case"\n:::\n',':::region A\n:::asm\nloop: lda #$00\n rts\n:::\n:::end\n',
   '# Outer\n:::region A\nbody\n:::end\n## Inner\nend\n',
   ':::region A\n# Crossing\n:::end\nafter\n# Next\nbody\n',
   '# Crossing\n:::region A\n# Next\nbody\n:::end\n',
   '# Outer\n:::region A\n## Crossing\n:::end\nbody\n# End\n',
   '# A\n:::region B\n## C\nbody\n## D\nbody\n:::end\n',
   ':::region A\n# Inside\n:::end\n',
   ':::basic\n# literal\n:::region literal\n:::end\n:::\n',
   ':::region incomplete\ntext',':::asm\nlda #0',':::end\n# H\nx\n',
   '£# literal\n£:::region literal\n# Valid\nx\n']
  texts+=[':::region X\n'*n+'body\n'+':::end\n'*n for n in [1,15,16,17]]
  for text in texts:
   data=petscii(text);tree=f.check(data);fixtures+=1
   if tree is not None:
    for action in [3,4,5]:
     tree,p=f.action(tree,action,0,0,query=max(0,len(data)//2))
     for pos in sorted({0,len(data),*[r.hidden for r in tree],*[r.end-1 for r in tree]}):f.query(tree,pos,0,len(data),0);queries+=1
  # Crossings in either direction omit each heading once even with several
  # explicit intervals; containing/nested/disjoint headings survive unchanged.
  for _ in range(80):
   parts=[]
   for i in range(rng.randrange(1,20)):
    parts.append(rng.choice(['# H\n','## I\n','body *text*\n',':::region R\n',':::end\n',':::asm\nlda #$00\n:::\n','\n']))
   tree=f.check(petscii(''.join(parts)));fixtures+=1
  # Long physical lines/chunk seams and actual source offsets across64KiB.
  data=petscii('# Long\n')+b'A'*66000+petscii('\n:::region Later\n:::basic\n10 PRINT "X"\n:::\n:::end\n# End\nbody')
  tree=f.check(data);fixtures+=1;assert any(x.start>65535 for x in tree)
  # Record metadata crosses64KiB as well, without a giant RAM fold array.
  data=petscii(''.join(f'# H{i}\nx\n' for i in range(2050)));tree=f.check(data);fixtures+=1;assert len(tree)==2050
  for i in [2047,2048,2049]:f.query(tree,tree[i].hidden);queries+=1
  # Capacity failure never publishes the partially built private candidate.
  f.seed(petscii('# A\nx\n# B\ny\n'),1);assert not f.call('se_fb_begin').p&1;r,n=f.finish();assert r.p&1 and r.a==0xB4 and not f.get('se_fold_valid')
  # Caller cancellation and source revision changes are bounded and fail closed.
  for fault in ['cancel','epoch','source_token','dest_token']:
   f.seed(petscii('# A\nbody\n'));assert not f.call('se_fb_begin').p&1;f.call('se_fb_step')
   before=f.get('se_reu_dma_calls',2)
   if fault=='cancel':f.call('se_fb_cancel');assert not f.get('se_fb_busy')
   else:
    name,width={'epoch':('se_fold_epoch',4),'source_token':('se_fb_source',5),'dest_token':('se_fold_token',5)}[fault];f.put(name,f.get(name,width)+1,width);r=f.call('se_fb_step');assert r.p&1
   assert not f.get('se_fold_valid') and f.get('se_reu_dma_calls',2)==before
  # Boundary edits/rebuilds are exact fresh parser runs; default is expanded.
  data=petscii('# A\n:::region R\nbody\n:::end\n# B\nx\n')
  for edit in [data,data.replace(b':::',b'::',1),data.replace(b'# ',b'## ',1),data+b'\r',data[:-1],data]:f.check(edit);fixtures+=1
  # Same immutable source identity can retain collapsed flags from a distinct
  # independently validated old map. Inner caret state is intentionally reset.
  data=petscii('# A\n:::region R\nbody\n:::end\n## B\nmore\n')
  tree=f.check(data);closed,p=f.action(tree,3,0,tree[0].hidden);oldbytes=f.object_bytes(f.fold_id,len(tree)*32)
  assert not f.call('se_object_create',0x46,1).p&1;oldtoken=f.ram('se_object_id',5);f.write_object(oldtoken,oldbytes)
  def old_inputs(epoch=0x12345678,source=None):
   f.put('se_fb_old_token',oldtoken);f.put('se_fb_old_count',len(tree),2);f.put('se_fb_old_source',f.source_token if source is None else source);f.put('se_fb_old_epoch',epoch,4);f.put('se_fb_old_length',len(data),3);f.put('se_fb_old_valid',1)
  retained_cases=0
  for matching in [True,False]:
   f.seed(data);old_inputs(0x12345678 if matching else 0x12345679)
   assert not f.call('se_fb_begin').p&1;r,n=f.finish();assert not r.p&1
   wanted=[base.replace(x,flags=1 if matching else 0,saved=0,motion=0) for x in tree]
   assert f.object_bytes(f.fold_id,len(tree)*32)==b''.join(x.bytes() for x in wanted)
   assert f.get('se_fb_retained',2)==(len(tree) if matching else 0)
   assert f.object_bytes(oldtoken[0],len(oldbytes))==oldbytes;retained_cases+=1
  # Even after an edit retaining byte length/anchors, changed authoritative
  # source revision defeats the old proof and defaults to expanded.
  edited=data.replace(b'BODY',b'EDIT');f.seed(edited);f.put('se_fold_epoch',0x12345679,4);old_inputs()
  assert not f.call('se_fb_begin').p&1;r,n=f.finish();assert not r.p&1 and not f.get('se_fb_retained',2);retained_cases+=1
  # Candidate/retention alias and revoked old generation must fail before any
  # candidate byte changes. A stale old source proof simply resets expansion.
  f.seed(data);old_inputs();f.put('se_fb_old_token',f.token);before=f.object_bytes(f.fold_id,96);assert f.call('se_fb_begin').p&1;assert f.object_bytes(f.fold_id,96)==before
  f.seed(data);old_inputs();address=f.s['object_gen_lo']+oldtoken[0];generation=f.m.read(address);f.m.write(address,generation+1);before=f.get('se_reu_dma_calls',2);assert f.call('se_fb_begin').p&1 and f.get('se_reu_dma_calls',2)==before;f.m.write(address,generation)
  # Real projection remains linked to validated source anchors after retention.
  f.seed(data);old_inputs();assert not f.call('se_fb_begin').p&1;r,n=f.finish();assert not r.p&1
  collapsed=[base.replace(x,flags=1,saved=0,motion=0) for x in tree]
  for pos in [0,len(data),*[x.hidden for x in tree]]:f.query(collapsed,pos,1,len(data),0);queries+=1
  # Continuations transfer all caller-owned bytes, including pending source
  # and fresh-record buffers, to an independently initialized fresh CPU.
  transfers=0;checkpoint_dir=OUT/'checkpoints';checkpoint_dir.mkdir(exist_ok=True)
  for phase in [2,5,9]:
   f.seed(data)
   if phase==9:old_inputs()
   assert not f.call('se_fb_begin').p&1
   for _ in range(1000):
    if f.get('se_fb_phase')==phase:break
    assert not f.call('se_fb_step').p&1
   else:raise AssertionError(('checkpoint phase missing',phase))
   spans=[('se_fold_state',f.s['se_fold_state_size']),('se_fb_state',f.s['se_fb_state_size']),('se_sm_state',f.s['se_sm_state_size']),('se_fold_record',32),('se_fb_buffer',160)]
   state=[(name,f.ram(name,length)) for name,length in spans];raw_count=f.get('se_fb_raw_count',2);metadata=f.object_bytes(f.fold_id,raw_count*32)
   (checkpoint_dir/f'phase{phase}-context.bin').write_bytes(b''.join(blob for _,blob in state));(checkpoint_dir/f'phase{phase}-candidate.bin').write_bytes(metadata)
   q=Fixture()
   try:
    q.seed(data)
    if phase==9:
     assert not q.call('se_object_create',0x46,1).p&1;assert q.ram('se_object_id',5)==oldtoken;q.write_object(oldtoken,oldbytes)
    q.write_object(q.token,metadata);q.put('se_object_id',q.token);q.put('se_object_offset',32768*32,3);assert not q.call('se_object_resize').p&1
    for name,blob in state:q.put(name,blob)
    q.reu_before=q.reu_image();r,n=q.finish();assert not r.p&1;r,n=f.finish();assert not r.p&1
    for name,length in spans:assert q.ram(name,length)==f.ram(name,length),(phase,name)
    assert q.object_bytes(q.fold_id,q.get('se_fold_count',2)*32)==f.object_bytes(f.fold_id,f.get('se_fold_count',2)*32)
    q.safe();transfers+=1
   finally:q.close()
  # Real provider failure at an actual candidate WRITE never changes source or
  # the separately retained old tree; no partial candidate becomes trusted.
  f.seed(data);old_inputs();assert not f.call('se_fb_begin').p&1
  while not (f.get('se_fb_phase')==2 and f.get('se_sm_kind')==2):assert not f.call('se_fb_step').p&1
  source_before=f.object_bytes(f.source_token[0],len(data));old_before=f.object_bytes(oldtoken[0],len(oldbytes));address=f.s['se_reu_physical_owner']+f.fold_banks[0];owner=f.m.read(address)
  r=f.hooked_call('se_fb_step','se_fold_write',lambda:f.m.write(address,99));f.m.write(address,owner)
  assert r.p&1 and r.a==0x34 and not f.get('se_fb_busy') and not f.get('se_fold_valid')
  assert f.object_bytes(f.source_token[0],len(data))==source_before and f.object_bytes(oldtoken[0],len(oldbytes))==old_before
  (OUT/'failed-write-context.bin').write_bytes(f.ram('se_fold_state',197)+f.ram('se_fb_state',f.s['se_fb_state_size'])+f.ram('se_sm_state',79)+f.ram('se_fold_record',32)+f.ram('se_fb_buffer',160))
  # Revoking an admitted old token after work has started also fails before DMA.
  f.seed(data);old_inputs();assert not f.call('se_fb_begin').p&1;f.call('se_fb_step');address=f.s['object_gen_lo']+oldtoken[0];owner=f.m.read(address);f.m.write(address,owner+1);before=f.get('se_reu_dma_calls',2);r=f.call('se_fb_step');f.m.write(address,owner)
  assert r.p&1 and r.a==0x31 and not f.get('se_fold_valid') and f.get('se_reu_dma_calls',2)==before
  f.safe()
  names=['FOLD_BUILD_PARSE','FOLD_BUILD_FILTER','FOLD_BUILD_RETAIN','FOLD_BUILD_STATE','FOLD_BUILD_BUFFER','SM_BLOCK','SM_STATE'];sizes={name:f.s['__'+name+'_SIZE__'] for name in names if '__'+name+'_SIZE__' in f.s}
  files=sorted(set([ROOT/'src'/Path(x+'.s') for x in NAMES]+list((ROOT/'src/fold').glob('*'))+[ROOT/'src/supermark/api.inc',ROOT/'src/object/api.inc',Path(__file__).resolve(),ROOT/'tools/supermark_model.py',ROOT/'tools/supermark_probe.py',ROOT/'tests/test_folds.py']))
  result=dict(status='passed',fixtures=fixtures,projection_queries=queries,builder_step_calls=f.builder_steps,max_dma_per_step=f.max_dma,module_bytes=sizes,builder_context_bytes=f.s['se_fb_state_size'],total_phase_bytes=197+32+160+f.s['se_fb_state_size']+f.s['se_sm_state_size'],zero_page_bytes=0,resident_allocation_bytes=0,source_chunk_bytes=128,feed_bytes_per_step=32,source_over64k=True,fold_records_over64k=2050,original_source_immutable=True,fresh_cpu_checkpoints=transfers,actual_candidate_write_failures=1,revoked_old_token_failures=1,unchanged_source_retention_cases=retained_cases,shim_bytes=1024,peak_instructions=f.peak,probe_sha256=hashlib.sha256((OUT/'probe.bin').read_bytes()).hexdigest(),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},policy='D093 explicit/fence intervals win; only crossing heading folds omitted, styles/source unchanged',limits=['Isolated builder, no editor/VIC integration.','Incomplete explicit/fence pairs fail closed.','Collapse flags retain only exact unchanged immutable source identity; changed revisions reset expanded.','Stable edited-anchor transforms and inner-caret retention across rebuild are not implemented.'])
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()

if __name__=='__main__':main()
