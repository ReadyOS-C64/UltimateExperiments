"""Actual C25/R14 code lexer, independent canonical-span role oracle."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, json, re, subprocess, sys
import test_geos_editor as geos
from supermark_model import lex
from supermark_probe import petscii
from overlays import wrap
ROOT=geos.ROOT
DEFAULT=ROOT/'build/geos-recovery/20261025T022335799891Z/fixture'
F=0x8B40
PRIVATE=0x8D3C

def command(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)

def build(out,base):
 out.mkdir(parents=True,exist_ok=True)
 report=json.loads((base/'build/editor-report.json').read_text());digest=report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 objects=[]
 for name,src in [('worker','src/render/geos/semantic-lex.s'),('lexer','src/supermark/lexer.s')]:
  obj=out/(name+'.o');command('ca65','-g','-I',out,'-I','src','-o',obj,src);objects.append(obj)
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects)
 command('ca65','-g','-o',out/'aliases.o',out/'aliases.s')
 command('ld65','-C','cfg/geos-editor-semantic-lex.cfg','-o',out/'worker.bin','-Ln',out/'worker.lbl','-m',out/'worker.map',*objects,out/'aliases.o')
 labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'worker.lbl').read_text())}
 payload=(out/'worker.bin').read_bytes();assert len(payload)<=4096 and labels['entry']==0xB010
 assert labels['se_sl_state']==0x8D00 and labels['se_sl_state_size']==60
 s=report['symbols'];image=wrap(payload,1,25,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest))
 (out/'worker.seo').write_bytes(image);return image,labels

def run(out,previous,smoke=False,faults_only=False):
 frozen,identity=geos.freeze(out,previous);image,labels=build(out/'leaf',frozen)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);f.assets['lex-private']=image
 frames=[];faults=[];current={}
 parent=bytes((i*31+17)&255 for i in range(68))
 checkpoint=bytes((i*47+29)&255 for i in range(171))
 prefix=bytes((i*53+11)&255 for i in range(256))
 def whole_reu():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def invoke(op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=25,x=1)
  assert f.read(F,192)==current['frame'],'C24 checkpoint/semantic outputs changed'
  assert f.read(0x8100,256)==prefix and f.read(0x8200,256)==current['packet'],'source prefix/packet changed'
  assert f.read(0x8300+current['count'],256-current['count'])==bytes([0xA5])*(256-current['count']),'role tail changed'
  p=f.read(0x9134,68);assert p[:1]+p[3:]==parent[:1]+parent[3:],'parent state changed'
  assert f.read(0xC600,1024)==f.shim
  assert f.read(0x4000,1024)+f.read(0x4800,2048)+f.read(0x6000,8000)==current['display'],('display/font RAM changed',current.get('fault'),[(i,a,b) for i,(a,b) in enumerate(zip(f.read(0x4000,1024)+f.read(0x4800,2048)+f.read(0x6000,8000),current['display'])) if a!=b][:10])
  if f.get('se_f_owner',1)==4:assert f.read(0x8D5F,385)==current['phase_guard'],'unused lexical phase changed'
  return r,n
 def setup(data,body,end,query,count,lang):
  f.put('se_f_owner',4,1)
  frame=bytearray(bytes([0xA5])*21+checkpoint)
  frame[:3]=query.to_bytes(3,'little');frame[3]=lang;frame[4]=count
  frame[5]=5;frame[6]=lang;frame[9:12]=body.to_bytes(3,'little');frame[12:15]=end.to_bytes(3,'little');frame[15:18]=body.to_bytes(3,'little');frame[18:21]=bytes([4,0,8])
  visible=data[query:query+count]
  packet=visible+bytes([0xA5])*(256-len(visible))
  current.update(frame=bytes(frame),packet=packet,count=count,display=f.read(0x4000,1024)+f.read(0x4800,2048)+f.read(0x6000,8000))
  phase_guard=bytes((i*23+7)&255 for i in range(385));f.m.load(0x8D5F,phase_guard);current['phase_guard']=phase_guard
  f.m.load(F,frame);f.m.load(0x8100,prefix);f.m.load(0x8200,packet);f.m.load(0x8300,bytes([0xA5])*256);f.m.load(0x9134,parent)
 def query(data,body,end,query,count,lang):
  setup(data,body,end,query,count,lang);before=f.canonical();reu=whole_reu();expected=bytearray([4])*count
  for a,b,role in lex(data[body:end],lang,body):
   for p in range(max(a,query),min(b,query+count)):expected[p-query]=role
  r,n=invoke(0);steps=0;instructions=n
  while r.a and not r.p&1:
   old=int.from_bytes(f.read(labels['se_sl_pos'],3),'little');r,n=invoke(1);instructions+=n
   new=int.from_bytes(f.read(labels['se_sl_pos'],3),'little');assert 0<=new-old<=32,(old,new)
   assert f.m.read(PRIVATE+34)<=1,'more than one source READ per STEP'
   steps+=1;assert steps<len(data)*5+200,('nonconverging',query,count,r.a)
  assert not r.p&1,('worker failure',query,count,lang,hex(r.a))
  actual=f.read(0x8300,count);assert actual==expected,('roles',query,count,lang,list(actual),list(expected))
  assert f.canonical()==before and whole_reu()==reu
  assert not f.get('se_doc_read_locks',1) and not f.m.read(0x912D) and not f.m.read(0x912C)
  frames.append(dict(body=body,end=end,query=query,count=count,language=lang,steps=steps,instructions=instructions))
  f.put('se_f_owner',0,1)
 try:
  for lang,line in ([] if faults_only else [(1,'10 PRINT "'+('x'*45)+'":REM '+('comment '*15)),(2,'label: lda #$12 ; '+('comment '*18)),(2,'LDAX LDA .byte "'+('q'*45)+'",$AB')]):
   data=petscii('before\n'+line+'\nafter');body=len(petscii('before\n'));end=data.index(13,body)
   f.source(data)
   for start in ([body+40] if smoke else range(body,end+1)):
    for count in ([min(40,end-start)] if smoke else sorted(set([0,min(1,end-start),min(40,end-start),min(160,end-start)]))):query(data,body,end,start,count,lang)
  if not smoke and not faults_only:
   for data_,lang_ in [(b'',0),(petscii('plain words'),0)]:
    f.source(data_);query(data_,0,len(data_),0,len(data_),lang_)
   data=petscii('10 REM ')+b'x'*66000;f.source(data);query(data,0,len(data),65550,160,1)
   data=b'x'*65530+petscii('\n10 PRINT "'+('a'*60)+'":REM tail\n')
   body=65531;end=len(data)-1;f.source(data);query(data,body,end,65560,40,1)
   f.position(65570);f.key(petscii('Q')[0]);data=data[:65570]+petscii('Q')+data[65570:];end+=1
   assert f.get('se_hot_pending',1);query(data,body,end,65560,40,1)
  if not smoke:
   data=petscii('10 PRINT "FAULT":REM '+('x'*80));f.source(data);reu=whole_reu()
   setup(data,0,len(data),40,40,1)
   assert not f.call('se_doc_read_acquire').p&1
   r,_=invoke(0);assert not r.p&1 and f.get('se_doc_read_locks',1)==2
   assert not invoke(2)[0].p&1 and f.get('se_doc_read_locks',1)==1
   assert not invoke(2)[0].p&1 and f.get('se_doc_read_locks',1)==1
   assert not f.call('se_doc_read_release').p&1;faults.append('cancel and repeated cancel preserve foreign counted lease')
   # A subsequent shared source owner must survive inactive lexical CANCEL.
   f.m.load(0x8D00,bytes(32));f.m.load(0x8D02,(320).to_bytes(2,'little'));f.put('se_overlay_frame',0,1)
   r,_=f.fast_call(f.s['se_overlay_call'],a=20,x=1);assert not r.p&1 and f.get('se_doc_read_locks',1)==1
   saved=f.read(0x9040,86);current['phase_guard']=f.read(0x8D5F,385);assert not invoke(2)[0].p&1
   assert f.get('se_doc_read_locks',1)==1 and f.read(0x9040,86)==saved and f.m.read(0x912D)==1
   assert not f.call('se_geos_cancel').p&1;faults.append('inactive cancel preserves subsequent C20 source lease')
   for kind in ['revision','packet','query','missing14','missing25']:
    setup(data,0,len(data),40,40,1);current['fault']=kind;assert not invoke(0)[0].p&1
    idx=None
    if kind=='revision':f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
    elif kind=='packet':
     packet=bytearray(current['packet']);packet[0]^=1;current['packet']=bytes(packet);f.m.load(0x8200,packet)
    elif kind=='query':
     frame=bytearray(current['frame']);frame[0]+=1;current['frame']=bytes(frame);f.m.load(F,frame)
    else:
     id_,slot=(14,0) if kind=='missing14' else (25,1)
     idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)==slot)
     f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0)
    r,_=invoke(1)
    while kind=='packet' and not r.p&1:r,_=invoke(1)
    assert r.p&1 and r.a==(0x17 if idx is not None else 0xB1),(kind,r.a)
    if kind=='missing25':assert not f.call('se_geos_cancel').p&1
    assert not f.get('se_doc_read_locks',1) and not f.m.read(0x912D)
    if idx is not None:f.m.write(f.s['se_overlay_ids']+idx,id_)
    faults.append(kind+' refuses and independent cleanup ends only own lease')
   for query_,count_,lang_,error in [(0,161,1,0x90),(0,40,3,0x90),(len(data)-1,40,1,0x7B)]:
    setup(data,0,len(data),query_,count_,lang_);r,_=invoke(0)
    assert r.p&1 and r.a==error and not f.get('se_doc_read_locks',1)
    assert f.read(0x8300,256)==bytes([0xA5])*256
   faults.append('invalid dimensions and bounds refuse before role writes')
   setup(data,0,len(data),0,40,1)
   for owner in (0,1,2,3,255):
    f.put('se_f_owner',owner,1);phase=f.read(0x8D00,1152)
    for op in (0,1,2,3,255):
     r,_=invoke(op);assert r.p&1 and r.a==0xB2 and f.read(0x8D00,1152)==phase
   f.put('se_f_owner',4,1);assert whole_reu()==reu;faults.append('wrong owners opaque and full16MiB REU unchanged')
  result=dict(status='passed',identity=identity,payload_bytes=len(image)-36,lexer_bytes=2704,phase_bytes=95,new_BSS=0,new_ZP=0,queries=frames,faults=faults,max_feeds_per_STEP=32,scope='Private actual C25/R14 lexer; no integrated UI/native claim')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',queries=len(frames),faults=len(faults),payload=len(image)-36,out=str(out)),indent=2));return result
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--smoke',action='store_true');p.add_argument('--faults-only',action='store_true');args=p.parse_args()
 out=ROOT/'build/geos-semantic-lex'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,args.fixture,args.smoke,args.faults_only)
