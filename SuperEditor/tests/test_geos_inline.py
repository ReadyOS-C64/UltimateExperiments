"""Actual private C26/R14 complete-body inline appearance; no raster/UI claim."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, json, re, subprocess, sys
import test_geos_editor as geos
from supermark_model import inline
from supermark_probe import petscii
from overlays import wrap
ROOT=geos.ROOT
DEFAULT=ROOT/'build/geos-semantic-recovery/20261025T031218325670Z/fixture'
F=0x8B40; CONTROL=0x8E84; ROLES=0x8F36

def command(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def build(out,base):
 out.mkdir(parents=True,exist_ok=True)
 report=json.loads((base/'build/editor-report.json').read_text());digest=report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 objects=[]
 for name,source in [('worker','src/render/geos/inline.s'),('parser','src/supermark/inline.s')]:
  obj=out/(name+'.o');command('ca65','-g','-I',out,'-I','src','-o',obj,source);objects.append(obj)
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects)
 command('ca65','-g','-o',out/'aliases.o',out/'aliases.s')
 command('ld65','-C','cfg/geos-editor-inline.cfg','-o',out/'inline.bin','-Ln',out/'inline.lbl','-m',out/'inline.map',*objects,out/'aliases.o')
 labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'inline.lbl').read_text())}
 payload=(out/'inline.bin').read_bytes();assert len(payload)<=4096 and labels['entry']==0xB010
 assert labels['se_si_state']==0x8D00 and labels['se_si_state_size']==68
 s=report['symbols'];image=wrap(payload,1,26,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest))
 (out/'inline.seo').write_bytes(image);return image,labels

def expected(data,start,body,end,query,count,base):
 styles=bytearray(count);roles=bytearray([base])*count;code=bytearray(count)
 events=inline(data[body:end],start=body,body_column=body-start if body>start else None)
 for kind,style,width,a,b in events:
  if kind!=1:continue
  lo=max(query,a+width);hi=min(query+count,b)
  for p in range(lo,hi):
   i=p-query
   if style==4:code[i]=1;styles[i]=0;roles[i]=4
   elif not code[i]:styles[i]|=(1 if style&2 else 0)|(2 if style&1 else 0)
 return bytes(styles),bytes(roles)

def run(out,previous,smoke=False):
 frozen,identity=geos.freeze(out,previous);image,labels=build(out/'leaf',frozen)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);f.assets['inline-private']=image
 frames=[];faults=[];state={}
 parent=bytes((i*31+17)&255 for i in range(68));packet=bytes((i*47+29)&255 for i in range(160));prefix=bytes((i*19+53)&255 for i in range(32))
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def setup(data,start,body,end,query,count,base=0):
  f.put('se_f_owner',4,1);f.m.load(0x8D00,bytes([0xA5])*0x334)
  frame=bytearray((i*13+37)&255 for i in range(192))
  for at,val,n in [(0,query,3),(4,count,1),(9,start,3),(12,end,3),(15,body,3),(18,base,1)]:frame[at:at+n]=val.to_bytes(n,'little')
  f.m.load(F,frame);f.m.load(0x9134,parent);f.m.load(0x8100,prefix);f.m.load(0x8200,packet)
  f.m.load(0x8300,bytes([0xEA])*160);f.m.load(ROLES,bytes([0xDA])*160)
  f.m.write(0x912C,0);f.m.write(0x912D,0)
  state.update(frame=bytes(frame),canonical=f.canonical(),reu=whole(),catalog=f.catalog())
 def invoke(op,check=True):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=26,x=1)
  if check:
   assert f.read(F,192)==state['frame'],'GSEM/checkpoint/C20 continuation changed'
   assert f.read(0x8200,160)==packet and f.read(0x8100,32)==prefix,'parent packet/prefix changed'
   actual=f.read(0x9134,68);assert actual[:1]+actual[3:]==parent[:1]+parent[3:],'parent controller changed'
   assert f.canonical()==state['canonical'] and f.read(0xC600,1024)==f.shim
  return r,n
 def query(data,start=0,body=0,end=None,query=0,count=None,base=0,source_return=False):
  end=len(data) if end is None else end;count=min(160,len(data)-query) if count is None else count
  setup(data,start,body,end,query,count,base)
  r,n=invoke(3 if source_return else 0);steps=0;max_feed=0;max_n=n;pub=0
  while not r.p&1 and r.a and not (source_return and f.m.read(0x9135)==20):
   before=int.from_bytes(f.read(0x8D00,3),'little');phase=f.m.read(CONTROL+1)
   r,n=invoke(1);after=int.from_bytes(f.read(0x8D00,3),'little')
   if phase==2:max_feed=max(max_feed,after-before);assert 0<=after-before<=32
   if phase==4:pub+=1;assert not f.get('se_doc_read_locks',1) and not f.m.read(0x912D),'publication held lease'
   max_n=max(max_n,n);steps+=1;assert steps<len(data)//16+200
  assert not r.p&1,('query error',hex(r.a),steps, f.read(CONTROL,43).hex())
  assert r.a==(1 if source_return else 0)
  if source_return:assert f.m.read(0x9135)==20 and f.m.read(0x9136)==1
  want_s,want_r=expected(data,start,body,end,query,count,base)
  got_s=f.read(0x8300,count);got_r=f.read(ROLES,count)
  assert got_s==want_s,('styles',query,count,list(got_s),list(want_s))
  assert got_r==want_r,('roles',query,count,list(got_r),list(want_r))
  assert f.read(0x8300+count,160-count)==bytes([0xEA])*(160-count)
  assert f.read(ROLES+count,160-count)==bytes([0xDA])*(160-count)
  assert not f.m.read(CONTROL) and not f.m.read(0x912C) and not f.m.read(0x912D) and not f.get('se_doc_read_locks',1)
  assert whole()==state['reu'] and f.catalog()==state['catalog'],'read-only worker changed REU/catalog'
  # Parent C21 starts with document/cache guards. Role publication must survive
  # an actual view init that may fetch the overlapping document leaf8400.
  assert not f.call('se_view_init').p&1
  assert f.read(ROLES,count)==want_r and f.read(0x8300,count)==want_s
  f.put('se_f_owner',0,1)
  frames.append(dict(query=query,count=count,body=body,end=end,steps=steps,publication_slices=pub,max_feeds=max_feed,max_instructions=max_n,source_handoff=source_return))
  (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
 try:
  data=petscii('**bold '+('x'*135)+' @@code *literal*@@ end**\nnext')
  f.source(data);query(data,end=data.index(13),count=160,source_return=True)
  if not smoke:
   samples=['*italic* **bold** ***both***','**outer *inner* and @@code **notbold**@@ final**',r'\*literal* **yes** unmatched ***', '@@a@@ **b** @@c@@', '## Heading **title**', '- **item** *tail*', 'abc **'+('x'*320)+'** z', '**'+('x'*125)+'**'+('z'*80)+'\nnext']
   for text in samples:
    data=petscii(text);f.source(data);end=data.find(13);end=len(data) if end<0 else end
    body=3 if text.startswith('## ') else 2 if text.startswith('- ') else 0
    for q in sorted(set([0,body,min(end,3),max(0,end-128)])):
     query(data,body=body,end=end,query=q,count=min(160,len(data)-q),base=2 if body==3 else 1 if body else 0)
   for data in [b'',petscii('no styles'),petscii('***@@code@@***'),petscii('*x*\n')]:
    f.source(data);query(data,end=data.find(13) if 13 in data else len(data))
   data=b'x'*65530+petscii('\n# **high *nested* '+('w'*150)+'**\nnext')
   f.source(data);at=65535;f.position(at);f.key(petscii('Q')[0]);data=data[:at]+petscii('Q')+data[at:]
   assert f.get('se_hot_pending',1)
   query(data,start=65531,body=65533,end=data.index(13,65531),query=65531,count=160,base=2)
   assert f.get('se_hot_pending',1)
   data=petscii('**'+('word '*100)+'**');f.source(data)
   # Counted foreign lease remains owned by its original caller after cancel.
   assert not f.call('se_doc_read_acquire').p&1
   setup(data,0,0,len(data),0,160);assert not invoke(0)[0].p&1
   assert f.get('se_doc_read_locks',1)==2
   assert not invoke(2)[0].p&1 and f.get('se_doc_read_locks',1)==1
   assert not invoke(2)[0].p&1 and f.get('se_doc_read_locks',1)==1
   assert not f.call('se_doc_read_release').p&1;faults.append('cancel releases only counted own lease/idempotent')
   setup(data,0,0,len(data),0,160);assert not invoke(0)[0].p&1
   f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
   r,_=invoke(1);assert r.p&1 and r.a==0xB1 and not f.get('se_doc_read_locks',1);faults.append('source revision change ends own lease')
   # Publication is separately guarded after END; editing the frozen revision
   # between output slices must fail before another output write.
   setup(data,0,0,len(data),0,160);r,_=invoke(0)
   while f.m.read(CONTROL+1)!=4:r,_=invoke(1);assert not r.p&1
   assert not f.get('se_doc_read_locks',1);r,_=invoke(1);assert not r.p&1
   old=f.read(0x8300,160)+f.read(ROLES,160);f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
   r,_=invoke(1);assert r.p&1 and r.a==0x74 and f.read(0x8300,160)+f.read(ROLES,160)==old
   faults.append('publication full frozen source guard rejects change without DOC DMA')
   for id_,slot in [(14,0),(26,1)]:
    setup(data,0,0,len(data),0,160);assert not invoke(0)[0].p&1
    idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)==slot)
    f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0)
    r,_=invoke(1);assert r.p&1 and r.a==0x17
    if id_==26:assert not f.call('se_geos_cancel').p&1
    assert not f.get('se_doc_read_locks',1) and not f.m.read(0x912D)
    f.m.write(f.s['se_overlay_ids']+idx,id_);faults.append('missing'+str(id_)+' cleanup preserves17')
   for owner in [0,1,2,3,255]:
    setup(data,0,0,len(data),0,160);f.put('se_f_owner',owner,1);phase=f.read(0x8D00,1152)
    for op in [0,1,2,3,255]:
     r,_=invoke(op);assert r.p&1 and r.a==0xB2 and f.read(0x8D00,1152)==phase
   faults.append('all foreign phase owners refuse before scratch access')
   for count,end in [(161,len(data)),(1,len(data)+1)]:
    setup(data,0,0,end,0,count);r,_=invoke(0);assert r.p&1 and r.a in (0x90,0x7B) and not f.get('se_doc_read_locks',1)
   f.put('se_f_owner',0,1);faults.append('malformed count/end rejection')
  result=dict(status='passed',identity=identity,payload_bytes=len(image)-36,parser_code_bytes=911,parser_state_bytes=68,new_BSS=0,new_ZP=0,queries=frames,faults=faults,roles_address=ROLES,full_REU_guard_bytes=16*1024*1024,source_packet_immutable=160,GSEM_immutable=192,parent_immutable=66,scope='Actual C26/R14 merged-source complete-body inline appearance; no raster/UI/native claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',queries=len(frames),faults=len(faults),payload_bytes=len(image)-36,out=str(out)),indent=2));return result
 finally:f.close()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--fixture',type=Path,default=DEFAULT);parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
 out=ROOT/'build/geos-inline'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,args.fixture,args.smoke)
