"""Isolated actual6510 fold service; no editor build, VICE, or modeled DMA.

Run python3 tests/test_folds.py. Builds only build/folds. The independent host
oracle treats folds as nested source intervals; actual metadata lives in the
existing generational logical-object provider and crosses real REU DMA banks.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,json,random,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
OUT=ROOT/'build/folds';OUT.mkdir(exist_ok=True)
SOURCES=['reu/provider','reu/dma','object/state','object/validate','object/allocate','object/resize','object/copy']+['fold/'+x for x in ['state','store','validate','query','action','probe']]

def build():
 objects=[]
 for name in SOURCES:
  out=OUT/(name.replace('/','-')+'.o');objects.append(str(out));subprocess.run(['ca65','-I',str(ROOT/'src'),'-g','-o',str(out),str(ROOT/'src'/Path(name+'.s'))],check=True)
 subprocess.run(['ld65','-C',str(ROOT/'src/fold/probe.cfg'),'-o',str(OUT/'probe.bin'),'-m',str(OUT/'probe.map'),'-Ln',str(OUT/'probe.lbl'),*objects],check=True)

@dataclass
class Fold:
 start:int;hidden:int;end:int;parent:int=65535;depth:int=0;kind:int=1;flags:int=0;saved:int=0;lines:int=0;level:int=1;motion:int=0
 def bytes(self):
  return b''.join([self.start.to_bytes(3,'little'),self.hidden.to_bytes(3,'little'),self.end.to_bytes(3,'little'),self.parent.to_bytes(2,'little'),bytes([self.depth,self.kind,self.flags]),self.saved.to_bytes(3,'little'),self.lines.to_bytes(3,'little'),bytes([self.level]),self.motion.to_bytes(4,'little'),bytes(7)])

# Independent recursive-tree validation, deliberately not the assembly's stack.
def valid_model(folds,length):
 def subtree(i,parent=None):
  f=folds[i]
  assert 0<=f.start<f.hidden<f.end<=length and f.kind in (1,2,3) and f.flags in range(4)
  assert f.level in range(1,7) if f.kind==1 else f.level==0
  assert f.flags&2==0 or f.flags&1 and f.hidden<=f.saved<f.end
  assert 0<=f.depth<16 and (f.parent==65535 if parent is None else f.parent==parent and f.depth==folds[parent].depth+1)
  assert f.depth==0 if parent is None else folds[parent].hidden<=f.start and f.end<=folds[parent].end
  j=i+1;end=f.hidden
  while j<len(folds) and folds[j].depth>f.depth:
   assert folds[j].depth==f.depth+1 and folds[j].start>=end
   end=folds[j].end;j=subtree(j,i)
  return j
 try:
  i=0;end=0
  while i<len(folds):
   assert folds[i].depth==0 and folds[i].start>=end
   end=folds[i].end;i=subtree(i)
  assert all(a.start<b.start for a,b in zip(folds,folds[1:]));return True
 except AssertionError:return False

def projection(folds,pos,mode,a,b):
 found=next((f for f in folds if f.flags&1 and f.hidden<=pos<f.end),None)
 if found is None:return(pos,0,0)
 return(found.end if mode==1 else found.start,1,int(min(a,b)<found.end and max(a,b)>found.hidden and a!=b))

def action_model(folds,action,target,caret,motion,query):
 result=[replace(f) for f in folds];p=caret
 for i,f in enumerate(result):
  if action<3 and i!=target:continue
  if action==5 and not f.hidden<=query<f.end:continue
  collapse=(not f.flags&1) if action==0 else action in (1,3)
  if collapse:
   if f.flags&1:continue
   f.flags=1
   if f.hidden<=p<f.end:f.saved=p;f.motion=motion;f.flags=3;p=f.start
  elif f.flags&1:
   if action!=5 and f.flags&2 and p==f.start and motion==f.motion:p=f.saved
   f.flags=0
 return result,p

class Fixture:
 def __init__(self):
  self.s={p[2].lstrip('.'):int(p[1],16) for line in (OUT/'probe.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
  self.m=Machine();self.m.load(0x1000,(OUT/'probe.bin').read_bytes());self.peak={};self.calls={};self.steps=0
  self.put('se_reu_banks',32,2);self.call('se_reu_provider_init');self.call('se_object_init')
  for logical,physical in [(200,2),(201,4)]:assert not self.call('se_reu_bind',99,logical,physical).p&1
  assert not self.call('se_object_create',0x46,16).p&1
  self.token=self.ram('se_object_id',5);self.fold_id=self.token[0];self.fold_banks=self.banks(self.fold_id)
  assert len(self.fold_banks)==16 and self.fold_banks[:3]==[1,3,5],self.fold_banks
  self.source=bytes((i*73+29)&255 for i in range(100003))
  assert not self.call('se_object_create',0x47,2).p&1
  self.source_token=self.ram('se_object_id',5);self.write_object(self.source_token,self.source)
  self.put('se_fold_token',self.token);self.put('se_fold_epoch',0x12345678,4);self.put('se_fold_length',len(self.source),3)
  self.canary=bytes((i*37+17)&255 for i in range(1024));self.m.load(0xC600,self.canary)
  self.guards=[]
  for a,n in [(0,256),(0x1000,0x7000),(0x8820,0x15E0),(0xA800,0x1800),(self.s['se_fold_state']+self.s['se_fold_state_size'],0x600-self.s['se_fold_state_size']),(0xCA00,0x600)]:
   if a not in (0x1000,):self.m.load(a,bytes((i*11+7)&255 for i in range(n)))
   self.guards.append((a,bytes(self.m.read(a+i) for i in range(n))))
  self.reu_before=self.reu_image()
 def close(self):self.m.close()
 def ram(self,name,n):
  a=self.s[name] if isinstance(name,str) else name;return bytes(self.m.read(a+i) for i in range(n))
 def get(self,name,n=1):return int.from_bytes(self.ram(name,n),'little')
 def put(self,name,value,n=1):self.m.load(self.s[name],value if isinstance(value,bytes) else value.to_bytes(n,'little'))
 def call(self,name,a=0,x=0,y=0):
  r,n=self.m.call(self.s[name],a=a,x=x,y=y);self.peak[name]=max(self.peak.get(name,0),n);self.calls[name]=self.calls.get(name,0)+1;return r
 def hooked_call(self,name,at,hook):
  # Deterministic actual-provider failure after READ, just before WRITE; this
  # changes a provider ownership input, never substitutes a modeled result.
  for key,value in [('a',0),('x',0),('y',0),('p',0x24),('sp',0xFD),('pc',self.s[name])]:getattr(self.m.lib,'zeropage_peddle_set_'+key)(self.m.handle,value)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,0x02);hit=False;before=self.m.regs().instructions
  for _ in range(10000):
   regs=self.m.regs()
   if regs.pc==0x2FF:
    assert hit;self.peak[name]=max(self.peak.get(name,0),regs.instructions-before);return regs
   if regs.pc==self.s[at] and not hit:hook();hit=True
   self.m.lib.zeropage_peddle_step_instruction(self.m.handle)
  raise AssertionError('injected service did not return')
 def banks(self,id):return [self.m.read(self.s['se_reu_map']+self.m.read(self.s['object_extents']+16*id+i)) for i in range(self.m.read(self.s['object_banks']+id))]
 def object_bytes(self,id,length):
  banks=self.banks(id);return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,banks[i>>16]*65536+(i&65535)) for i in range(length))
 def reu_image(self):return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,i) for i in range(32*65536))
 def write_object(self,token,data):
  for i in range(0,len(data),2048):
   chunk=data[i:i+2048];self.m.load(0x8000,chunk);self.put('se_object_id',token);self.put('se_object_offset',i,3);self.put('se_object_length',len(chunk),2);self.put('se_object_c64',0x8000,2);assert not self.call('se_object_copy',0).p&1
  self.put('se_object_id',token);self.put('se_object_offset',len(data),3);assert not self.call('se_object_resize').p&1
 def load(self,folds,length=100003):
  data=b''.join(f.bytes() for f in folds);self.write_object(self.token,data);self.put('se_fold_token',self.token);self.put('se_fold_count',len(folds),2);self.put('se_fold_length',length,3);self.put('se_fold_valid',0);self.put('se_fold_busy',0);self.put('se_fold_epoch',0x12345678,4)
 def complete(self,operation):
  count=0
  while self.get('se_fold_busy'):
   before=self.get('se_reu_dma_calls',2);r=self.call('se_fold_'+operation+'_step');after=self.get('se_reu_dma_calls',2);assert (after-before)&65535 <= (2 if operation=='action' else 1)
   count+=1;self.steps+=1
   if r.p&1:return r,count
   assert count<=32770
  return r if count else None,count
 def validate(self,folds,length=100003):
  self.load(folds,length);r=self.call('se_fold_validate_begin');assert not r.p&1
  r,n=self.complete('validate');assert n<=len(folds)+1;return not r.p&1
 def query(self,folds,pos,mode=0,a=0,b=0):
  self.put('se_fold_query',pos,3);self.put('se_fold_mode',mode);self.put('se_fold_select_a',a,3);self.put('se_fold_select_b',b,3);old=self.ram('se_fold_select_a',6)
  assert not self.call('se_fold_query_begin').p&1;r,n=self.complete('query');assert not r.p&1
  assert self.ram('se_fold_select_a',6)==old
  actual=self.get('se_fold_result',3),self.get('se_fold_hidden'),self.get('se_fold_selected');expected=projection(folds,pos,mode,a,b);assert actual==expected,(folds,pos,mode,a,b,actual,expected)
 def action(self,folds,action,target,caret,motion=7,query=0):
  expected,p=action_model(folds,action,target,caret,motion,query)
  for name,v,n in [('se_fold_action',action,1),('se_fold_target',target,2),('se_fold_caret',caret,3),('se_fold_motion',motion,4),('se_fold_query',query,3)]:self.put(name,v,n)
  old=self.ram('se_fold_caret',3)+self.ram('se_fold_select_a',6)
  assert not self.call('se_fold_action_begin').p&1;r,n=self.complete('action');assert not r.p&1
  assert self.ram('se_fold_caret',3)+self.ram('se_fold_select_a',6)==old
  assert self.get('se_fold_result',3)==p,(action,caret,p,self.get('se_fold_result',3))
  assert self.object_bytes(self.fold_id,len(folds)*32)==b''.join(f.bytes() for f in expected),(action,'actual metadata')
  assert self.get('se_fold_valid')==1;return expected,p
 def safe(self):
  for a,data in self.guards:assert self.ram(a,len(data))==data,hex(a)
  assert self.ram(0xC600,1024)==self.canary
  assert self.object_bytes(self.source_token[0],len(self.source))==self.source
  image=self.reu_image();assert all(image[i*65536:(i+1)*65536]==self.reu_before[i*65536:(i+1)*65536] for i in range(32) if i not in self.fold_banks)


def main():
 build();(OUT/'result.json').unlink(missing_ok=True);f=Fixture();rng=random.Random(0xF01D6510);checks=actions=queries=invalid=0
 try:
  trees=[[],[Fold(0,3,100003)], [Fold(0,2,100),Fold(5,7,30,0,1,2,level=0),Fold(40,43,90,0,1,3,level=0),Fold(45,48,80,2,2),Fold(100,104,100003)], [Fold(65530,65536,100000)], [Fold(0xFFFF00,0xFFFF10,0xFFFFFF)]]
  trees.append([Fold(i*3,i*3+1,200-i*3,65535 if i==0 else i-1,i) for i in range(16)])
  for tree in trees:
   length=max([x.end for x in tree]+[100003]);assert valid_model(tree,length);assert f.validate(tree,length);checks+=1
   for action in range(6):
    if not tree and action<3:continue
    for caret in [0,length]+[x.hidden for x in tree]:
     assert f.validate(tree,length);changed,p=f.action(tree,action,0,caret,query=caret);actions+=1
     for pos in sorted({0,length,*[x.start for x in tree],*[x.hidden for x in tree],*[x.end-1 for x in tree]}):
      for mode in range(3):f.query(changed,pos,mode,length,0);queries+=1
  # Collapse/expand caret restore requires unchanged caller movement serial.
  tree=[Fold(2,5,90),Fold(10,12,40,0,1)]
  assert f.validate(tree);closed,p=f.action(tree,1,0,20,7);assert p==2
  opened,p=f.action(closed,2,0,p,7);assert p==20;actions+=2
  assert f.validate(tree);closed,p=f.action(tree,1,0,20,7);opened,p=f.action(closed,2,0,p,8);assert p==2;actions+=2
  assert f.validate(tree);closed,p=f.action(tree,1,0,20,7);opened,p=f.action(closed,2,0,70,7);assert p==70;actions+=2
  # Real record addressing crosses64KiB and reaches exact1MiB capacity end.
  large=[Fold(i*3,i*3+1,i*3+3,flags=1 if i%7==0 else 0) for i in range(2050)]
  assert f.validate(large);checks+=1
  for i in [0,2047,2048,2049]:f.query(large,i*3+1);queries+=1
  f.put('se_fold_count',32768,2);f.put('se_object_id',f.token);f.put('se_object_offset',1048576,3);assert not f.call('se_object_resize').p&1
  f.put('se_fold_index',32767,2);assert not f.call('se_fold_guard').p&1;assert not f.call('se_fold_read').p&1
  f.put('se_fold_count',32769,2);assert f.call('se_fold_guard').p&1;checks+=2
  # Invalid trees are never published, including source-coordinate crossings.
  base=[Fold(0,2,100),Fold(5,7,30,0,1),Fold(40,43,90,0,1)]
  bads=[[replace(x) for x in base] for _ in range(12)]
  changes=[(0,dict(hidden=0)),(0,dict(end=100004)),(0,dict(parent=0)),(0,dict(depth=1)),(1,dict(parent=2)),(1,dict(depth=2)),(1,dict(end=101)),(2,dict(start=20)),(1,dict(kind=4)),(1,dict(flags=2)),(1,dict(level=7)),(1,dict(flags=3,saved=99))]
  bads=[t[:i]+[replace(t[i],**v)]+t[i+1:] for t,(i,v) in zip(bads,changes)]
  bads.append([Fold(i*3,i*3+1,200-i*3,65535 if i==0 else i-1,i) for i in range(17)])
  for tree in bads:assert not valid_model(tree,100003);assert not f.validate(tree);assert not f.get('se_fold_valid');invalid+=1
  # Random valid laminar records; repeated all/single transforms never alter source.
  for case in range(40):
   tree=[Fold(0,3,300)]
   for j in range(rng.randrange(1,8)):
    start=5+j*35;tree.append(Fold(start,start+2,start+30,0,1,rng.randrange(1,4),level=0))
    if tree[-1].kind==1:tree[-1].level=rng.randrange(1,7)
   assert f.validate(tree);checks+=1
   for _ in range(6):
    a=rng.randrange(6);target=rng.randrange(len(tree));caret=rng.randrange(301);tree,p=f.action(tree,a,target,caret,query=rng.randrange(301));actions+=1
    for _ in range(3):f.query(tree,rng.randrange(301),rng.randrange(3),rng.randrange(301),rng.randrange(301));queries+=1
  # Revision, token, geometry and provider epoch invalidation before further DMA.
  for field,width in [('se_fold_epoch',4),('se_fold_token',5),('se_fold_count',2),('se_fold_length',3)]:
   assert f.validate(base);f.put('se_fold_query',20,3);f.put('se_fold_mode',0);assert not f.call('se_fold_query_begin').p&1;before=f.get('se_reu_dma_calls',2);f.put(field,f.get(field,width)+1,width)
   assert f.call('se_fold_query_step').p&1 and not f.get('se_fold_valid') and f.get('se_reu_dma_calls',2)==before;checks+=1
  assert f.validate(base);f.put('se_fold_query',20,3);f.put('se_fold_mode',0);assert not f.call('se_fold_query_begin').p&1;f.call('se_fold_cancel');assert f.get('se_fold_valid')==1;checks+=1
  assert f.validate(base);f.put('se_fold_action',3);f.put('se_fold_caret',20,3);f.put('se_fold_result',0xDEAD,3);assert not f.call('se_fold_action_begin').p&1;assert not f.call('se_fold_action_step').p&1;f.call('se_fold_cancel');assert not f.get('se_fold_valid') and f.get('se_fold_result',3)==0xDEAD;assert f.call('se_fold_query_begin').p&1;checks+=1
  # Invalidated edit/undo map fails closed; a fresh candidate may be validated.
  assert f.validate(base);f.call('se_fold_invalidate');assert f.call('se_fold_query_begin').p&1;assert f.validate([Fold(0,2,80)]);checks+=1
  # Reserved bytes, committed-size truncation and foreign object types reject
  # before becoming trusted. An authentic source token is not a fold token.
  f.load(base);raw=bytearray(b''.join(x.bytes() for x in base));raw[-1]=1;f.write_object(f.token,raw)
  assert not f.call('se_fold_validate_begin').p&1;r,n=f.complete('validate');assert r.p&1 and not f.get('se_fold_valid');invalid+=1
  f.load(base);f.put('se_object_id',f.token);f.put('se_object_offset',len(base)*32-1,3);assert not f.call('se_object_resize').p&1
  assert f.call('se_fold_validate_begin').p&1;checks+=1
  f.load(base);f.put('se_fold_token',f.source_token);assert f.call('se_fold_validate_begin').p&1;checks+=1
  # Full token generation and provider lifetime are checked on each operation,
  # including the zero-DMA completion step. Restore injected inputs afterward.
  for address in [f.s['object_gen_lo']+f.fold_id,f.s['se_reu_epoch']]:
   assert f.validate(base);f.put('se_fold_query',70,3);f.put('se_fold_mode',0);assert not f.call('se_fold_query_begin').p&1
   old=f.m.read(address);f.m.write(address,old+1);before=f.get('se_reu_dma_calls',2)
   assert f.call('se_fold_query_step').p&1 and not f.get('se_fold_valid') and f.get('se_reu_dma_calls',2)==before
   f.m.write(address,old);checks+=1
  # Actual failed metadata WRITE: root may already be privately changed, but
  # no partial map or proposed caret is published; no source/selection changes.
  assert f.validate(base);f.put('se_fold_action',3);f.put('se_fold_caret',20,3);f.put('se_fold_result',0xBAD,3)
  assert not f.call('se_fold_action_begin').p&1;assert not f.call('se_fold_action_step').p&1
  first=f.object_bytes(f.fold_id,len(base)*32);assert first!=b''.join(x.bytes() for x in base)
  address=f.s['se_reu_physical_owner']+f.fold_banks[0];old=f.m.read(address);dma=f.get('se_reu_dma_calls',2)
  r=f.hooked_call('se_fold_action_step','se_fold_write',lambda:f.m.write(address,99));f.m.write(address,old)
  assert r.p&1 and r.a==0x34 and not f.get('se_fold_valid') and not f.get('se_fold_busy')
  assert f.get('se_fold_result',3)==0xBAD and f.get('se_fold_caret',3)==20
  assert f.object_bytes(f.fold_id,len(base)*32)==first and ((f.get('se_reu_dma_calls',2)-dma)&65535)==1
  assert f.call('se_fold_query_begin').p&1;checks+=1
  # Contexts transfer to fresh CPUs without hidden ZP/stack/self-modified code.
  transfers=0
  for operation in ['validate','query','action']:
   f.load(base)
   if operation!='validate':assert f.validate(base)
   if operation=='query':f.put('se_fold_query',70,3);f.put('se_fold_mode',0)
   if operation=='action':f.put('se_fold_action',3);f.put('se_fold_caret',20,3);f.put('se_fold_motion',7,4);f.put('se_fold_query',0,3)
   assert not f.call('se_fold_'+operation+'_begin').p&1;assert not f.call('se_fold_'+operation+'_step').p&1;assert f.get('se_fold_busy')
   state=f.ram('se_fold_state',f.s['se_fold_state_size']);metadata=f.object_bytes(f.fold_id,len(base)*32)
   q=Fixture()
   try:
    q.load(base);q.write_object(q.token,metadata);q.put('se_fold_state',state)
    r,n=q.complete(operation);assert not r.p&1
    r,n=f.complete(operation);assert not r.p&1
    assert q.ram('se_fold_state',q.s['se_fold_state_size'])==f.ram('se_fold_state',f.s['se_fold_state_size'])
    assert q.object_bytes(q.fold_id,len(base)*32)==f.object_bytes(f.fold_id,len(base)*32)
    q.safe();transfers+=1
   finally:q.close()
  f.safe()
  segments={k:f.s['__'+k+'_SIZE__'] for k in ['FOLD_STORE','FOLD_VALIDATE','FOLD_QUERY','FOLD_ACTION','FOLD_STATE']}
  sources=[ROOT/'src'/Path(n+'.s') for n in SOURCES]+list((ROOT/'src/fold').glob('*'))+[Path(__file__).resolve()];sources=sorted(set(sources));result=dict(status='passed',engine='Peddle MOS6510 actual logical object/DMA modules',checks=checks,malformed_trees_rejected=invalid,actions=actions,visibility_navigation_selection_oracles=queries,bounded_step_calls=f.steps,fresh_cpu_context_transfers=transfers,actual_metadata_write_failures=1,maximum_step_record_dma=2,module_bytes=segments,caller_context_bytes=f.s['se_fold_state_size'],caller_dma_buffer_bytes=32,zero_page_bytes=0,resident_bytes_reserved=0,source_bytes_preserved=len(f.source),shim_bytes=1024,unchanged_reu_bytes=(32-len(f.fold_banks))*65536,maximum_verified_record_index=32767,record64k_crossing_indices=[2047,2048,2049],source_anchor_maximum=0xFFFFFF,peak_instructions=f.peak,probe_sha256=hashlib.sha256((OUT/'probe.bin').read_bytes()).hexdigest(),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},limits=['Isolated service, no editor integration or VICE/screenshots.','Caller supplies exclusive typed logical fold object and authoritative document revision/length.','No SuperMark fold builder or anchor transform/unaffected collapse retention implemented.','Metadata action cancellation/failure leaves map untrusted until rebuilt; no partial trusted publish.'])
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()

if __name__=='__main__':main()
