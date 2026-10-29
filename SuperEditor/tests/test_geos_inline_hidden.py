"""Actual private C26 hidden-pair/confirmed-escape output, canonical windows.

The old packaged C26 is also executed for output compatibility. No renderer,
geometry, source hiding or user-visible mode is changed by this component gate.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,hashlib
import test_geos_inline as old
geos=old.geos;ROOT=geos.ROOT;F=old.F;CONTROL=old.CONTROL;HIDDEN=0x8FD6
DEFAULT=ROOT/'build/geos-pan-dispatch/20261025T040756394080Z/fixture'

def hidden(data,start,body,end,query,count):
 result=bytearray(20)
 for kind,style,width,a,b in old.inline(data[body:end],start=body,body_column=body-start if body>start else None):
  spans=[(a,a+width),(b,b+width)] if kind==1 else [(a,a+1)]
  for lo,hi in spans:
   for p in range(max(query,lo),min(query+count,hi)):
    i=p-query;result[i>>3]|=128>>(i&7)
 return bytes(result)

def run(out,previous,smoke=False):
 frozen,identity=geos.freeze(out,previous);image,labels=old.build(out/'leaf',frozen)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);baseline=geos.Fixture(out/'baseline',frozen,dll,True)
 f.assets['geosinln']=image;assert len(f.assets)==len(baseline.assets)==32
 cases=[];faults=[];state={};parent=bytes((i*31+17)&255 for i in range(68));packet=bytes((i*47+29)&255 for i in range(160));prefix=bytes((i*19+53)&255 for i in range(32))
 def whole(machine):
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(machine.m.handle,len(b),b);return b.raw
 def setup(machine,data,start,body,end,query,count,base=0):
  machine.put('se_f_owner',4,1);machine.m.load(0x8D00,bytes([0xA5])*0x334)
  frame=bytearray((i*13+37)&255 for i in range(192))
  for at,val,n in [(0,query,3),(4,count,1),(9,start,3),(12,end,3),(15,body,3),(18,base,1)]:frame[at:at+n]=val.to_bytes(n,'little')
  machine.m.load(F,frame);machine.m.load(0x9134,parent);machine.m.load(0x8100,prefix);machine.m.load(0x8200,packet)
  machine.m.load(0x8300,bytes([0xEA])*160);machine.m.load(old.ROLES,bytes([0xDA])*160)
  machine.m.load(HIDDEN-1,b'\xDA'+b'\xC7'*20+b'\x6B'*86)
  machine.m.write(0x912C,0);machine.m.write(0x912D,0)
  state[machine]=dict(frame=bytes(frame),canonical=machine.canonical(),reu=whole(machine),catalog=machine.catalog(),screen=machine.read(0x4000,0x1000)+machine.read(0x6000,8000),tail=machine.read(HIDDEN+20,86))
 def invoke(machine,op,guard=True):
  machine.put('se_overlay_frame',op,1);r,n=machine.fast_call(machine.s['se_overlay_call'],a=26,x=1)
  if guard:
   st=state[machine]
   assert machine.read(F,192)==st['frame'] and machine.read(0x8200,160)==packet and machine.read(0x8100,32)==prefix
   actual=machine.read(0x9134,68);assert actual[:1]+actual[3:]==parent[:1]+parent[3:]
   assert machine.canonical()==st['canonical'] and machine.read(0xC600,1024)==machine.shim
   assert machine.read(HIDDEN+20,86)==st['tail'],'hidden output crossed20B'
   assert machine.read(0x4000,0x1000)+machine.read(0x6000,8000)==st['screen'],'worker drew pixels/fonts/UI'
  return r,n
 def execute(machine,source_return=False):
  r,n=invoke(machine,3 if source_return else 0);steps=0;max_feed=0;max_n=n
  while not r.p&1 and r.a and not (source_return and machine.m.read(0x9135)==20):
   before=int.from_bytes(machine.read(0x8D00,3),'little');phase=machine.m.read(CONTROL+1)
   r,n=invoke(machine,1);after=int.from_bytes(machine.read(0x8D00,3),'little')
   if phase==2:assert 0<=after-before<=32;max_feed=max(max_feed,after-before)
   if phase>=4:assert not machine.get('se_doc_read_locks',1) and not machine.m.read(0x912D)
   max_n=max(max_n,n);steps+=1;assert steps<100000
  assert not r.p&1,(hex(r.a),steps,machine.read(CONTROL,67).hex())
  assert r.a==(1 if source_return else 0)
  if source_return:assert machine.m.read(0x9135)==20 and machine.m.read(0x9136)==1
  assert not any(machine.m.read(a) for a in (CONTROL,0x912C,0x912D)) and not machine.get('se_doc_read_locks',1)
  assert whole(machine)==state[machine]['reu'] and machine.catalog()==state[machine]['catalog']
  machine.put('se_f_owner',0,1);return steps,max_feed,max_n
 def query(data,start=0,body=0,end=None,query=0,count=None,base=0,source_return=False,compat=True):
  end=len(data) if end is None else end;count=min(160,len(data)-query) if count is None else count
  setup(f,data,start,body,end,query,count,base);steps,feed,max_n=execute(f,source_return)
  want_s,want_r=old.expected(data,start,body,end,query,count,base);want_h=hidden(data,start,body,end,query,count)
  assert f.read(0x8300,count)==want_s and f.read(old.ROLES,count)==want_r
  assert f.read(HIDDEN,20)==want_h,('hidden',query,count,f.read(HIDDEN,20).hex(),want_h.hex())
  assert f.read(0x8300+count,160-count)==b'\xEA'*(160-count)
  # HIDDEN-1 shares the last role byte, so it is guarded by this old-output tail.
  assert f.read(old.ROLES+count,160-count)==b'\xDA'*(160-count)
  if compat:
   setup(baseline,data,start,body,end,query,count,base);execute(baseline,source_return)
   assert f.read(0x8300,160)==baseline.read(0x8300,160) and f.read(old.ROLES,160)==baseline.read(old.ROLES,160),'published oldoutputs changed'
   assert baseline.read(HIDDEN,20)==b'\xC7'*20
  assert not f.call('se_view_init').p&1
  assert f.read(HIDDEN,20)==want_h and f.read(old.ROLES,count)==want_r,'parent cache/document guard destroyed mask'
  cases.append(dict(start=start,body=body,end=end,query=query,count=count,steps=steps,max_feed=feed,max_instructions=max_n,mask=want_h.hex(),source_handoff=source_return,baseline_compatible=compat))
  (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
 def source(data):f.source(data);baseline.source(data)
 try:
  data=old.petscii('**bold** £*literal* @@code *literal*@@ ***both***')
  source(data);query(data,source_return=True)
  print('FIRST HIDDEN MASK PASS: actual private C26, matched delimiters/escape only; old styles/roles byte-identical',flush=True)
  if not smoke:
   samples=['*x* **yy** ***zzz***','**outer *inner* and @@code **literal**@@ end**',
    'unmatched * ** *** **** @ @@@ £?', '£*literal* **yes** ££ £@ £# bad',
    '£# Heading','  £- item','1£. item','£:::asm','@@£*literal* @@',
    '## Heading **title**','- **item** *tail*','**'+('x'*320)+'** z',
    '**'+('x'*125)+'**'+('z'*80)+'\nnext','*a* **b** ***c*** @@d@@']
   for text in samples:
    data=old.petscii(text);source(data);end=data.find(13);end=len(data) if end<0 else end
    body=3 if text.startswith('## ') else 2 if text.startswith('- ') else 0
    for q in sorted(set([0,body,min(end,1),min(end,7),min(end,8),max(0,end-1),max(0,end-128)])):
     query(data,body=body,end=end,query=q,count=min(160,len(data)-q),base=2 if body==3 else 1 if body else 0)
   for shift in range(16):
    data=b'x'*shift+old.petscii('***z*** £* @@q@@')+b't'*170;source(data)
    for q in (0,shift+1,shift+6):query(data,query=q,count=min(160,len(data)-q))
   for data in [b'',b'x',old.petscii('**a**\nnext')]:
    source(data);end=data.find(13);end=len(data) if end<0 else end
    for q,count in [(0,0),(len(data),0),(0,min(1,len(data)))]:query(data,end=end,query=q,count=count)
   # Query lies beyond64KiB while the matching opener is far outside the window.
   data=old.petscii('**')+b'x'*66000+old.petscii('**');source(data)
   query(data,query=65900,count=104);query(data,query=0,count=160,source_return=True)
   data=b'x'*65530+old.petscii('\n# **high *nested* '+('w'*150)+'**\nnext');source(data)
   at=65535;q=old.petscii('Q');f.position(at);f.key(q[0]);baseline.position(at);baseline.key(q[0]);data=data[:at]+q+data[at:]
   query(data,start=65531,body=65533,end=data.index(13,65531),query=65531,count=160,base=2)
   assert f.get('se_hot_pending',1)
   data=old.petscii('**'+('word '*100)+'**');source(data)
   assert not f.call('se_doc_read_acquire').p&1
   setup(f,data,0,0,len(data),0,160);invoke(f,0);assert f.get('se_doc_read_locks',1)==2
   invoke(f,2);invoke(f,2);assert f.get('se_doc_read_locks',1)==1 and f.read(HIDDEN,20)==b'\xC7'*20
   f.call('se_doc_read_release');faults.append('cancel idempotent and foreignlease preserved; no mask publication')
   setup(f,data,0,0,len(data),0,160);invoke(f,0);f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
   r,_=invoke(f,1);assert r.p&1 and r.a==0xB1 and not f.get('se_doc_read_locks',1) and f.read(HIDDEN,20)==b'\xC7'*20
   faults.append('source revision rejects before hidden publication')
   setup(f,data,0,0,len(data),0,160);r,_=invoke(f,0)
   while f.m.read(CONTROL+1)!=5:r,_=invoke(f,1);assert not r.p&1
   f.put('se_r_revision',f.get('se_r_revision',4)+1,4);r,_=invoke(f,1)
   assert r.p&1 and r.a==0x74 and f.read(HIDDEN,20)==b'\xC7'*20
   faults.append('post-END fullidentity rejects before mask publication')
   # Frozen caller descriptors and all resident source-lifetime guards remain
   # active before any further output slice. Catalog absence uses real fail17.
   for field,delta in [(0,1),(4,1),(9,1),(12,-1),(15,1),(18,1)]:
    setup(f,data,0,0,len(data),0,160);invoke(f,0)
    f.m.write(F+field,(f.m.read(F+field)+delta)&255);state[f]['frame']=f.read(F,192)
    r,_=invoke(f,1);assert r.p&1 and r.a==0x74 and not f.get('se_doc_read_locks',1) and f.read(HIDDEN,20)==b'\xC7'*20
   faults.append('all frozen inputfields reject mutation before output')
   for id_,slot in [(14,0),(26,1)]:
    setup(f,data,0,0,len(data),0,160);invoke(f,0)
    idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)==slot)
    f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0)
    r,_=invoke(f,1);assert r.p&1 and r.a==0x17
    if id_==26:f.call('se_geos_cancel')
    assert not f.get('se_doc_read_locks',1) and not f.m.read(0x912D) and f.read(HIDDEN,20)==b'\xC7'*20
    f.m.write(f.s['se_overlay_ids']+idx,id_);faults.append('missing'+str(id_)+' originalerror17 and safeownedcleanup')
   for owner in [0,1,2,3,255]:
    setup(f,data,0,0,len(data),0,160);f.put('se_f_owner',owner,1);phase=f.read(0x8B40,0x640)
    for op in [0,1,2,3,255]:
     r,_=invoke(f,op);assert r.p&1 and r.a==0xB2 and f.read(0x8B40,0x640)==phase
   faults.append('foreign owner phaseopaque for allentryoperations')
   for values in [(0,0,len(data),0,161),(0,0,len(data)+1,0,1),(0,2,1,0,1),(0,0,len(data),len(data),1)]:
    setup(f,data,*values);r,_=invoke(f,0);assert r.p&1 and r.a in (0x90,0x7B) and not f.get('se_doc_read_locks',1) and f.read(HIDDEN,20)==b'\xC7'*20
   faults.append('count/body/end/query overflow bounds fail without output')
   f.put('se_f_owner',0,1)
  result=dict(status='passed',identity=identity,payload_bytes=len(image)-36,new_BSS=0,new_ZP=0,private_bytes=67,hidden_output=dict(address=HIDDEN,bytes=20,bit_order='MSB-first; zero afterCOUNT'),queries=cases,faults=faults,catalog_entries=32,scope='Actual private C26/R14 hidden-mask foundation, unchanged styles/roles compared to sealed baseline; no geometry/frontend/native claim')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',queries=len(cases),faults=len(faults),payload_bytes=len(image)-36,out=str(out)),indent=2));return result
 finally:f.close();baseline.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-inline-hidden'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.fixture,a.smoke)
