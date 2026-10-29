"""Actual C35 classification-only profile. No renderer or inline-hit claim."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,ctypes as CT,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_query as query
import test_cache_semantic as sem
from overlays import wrap,HEADER
from supermark_model import blocks
from peddle import VENDOR
F=0x8d00;IO=F+448;C=F+387;G=0x8b40
BASE=query.BASE
PIPE=ROOT/'agentsworking/evidence/M8/20261026T000416825444Z-cache-query-editor-active/run/baseline'
command=query.command

def build(out,base):
 out.mkdir();r=json.loads((base/'build/editor-report.json').read_text());digest=r['resident_binding']['digest'];s=r['symbols'];objects=[]
 (out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 for name in ('classify-entry','query','source','records'):
  obj=out/(name+'.o');command('ca65','-g','-I',out,'-I','src','-D','BCQ_EDITOR_ACTIVE=1','-D','BCQ_CLASSIFY=1','-D','BCQ_SELECTOR_OWNS_OWNER=1','-o',obj,ROOT/'src/cache/query'/(name+'.s'));objects.append(obj)
 for name in ('core','open','page'):
  obj=out/(name+'.o');command('ca65','-g','-I','src','-D','BCA_READONLY_OPEN=1','-o',obj,ROOT/'src/cache/arena'/(name+'.s'));objects.append(obj)
 seam={'se_bc_arena':0x9fb5,'se_bc_ticket':0x9fba,'se_bc_incarnation':0x9fbe,'se_bc_flags':0x9fc2,'se_bc_head':0x9fc3,'se_bc_tail':0x9fc4,'se_bc_count':0x9fc5,'se_bc_ring':0x9d85}
 (out/'state.s').write_text('\n'.join(f'.export {n}: absolute\n{n}=${v:04X}'for n,v in seam.items())+'\n');command('ca65','-o',out/'state.o',out/'state.s');objects.append(out/'state.o')
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects);command('ca65','-o',out/'aliases.o',out/'aliases.s');objects.append(out/'aliases.o')
 (out/'image.cfg').write_text('MEMORY { C:file=%O,start=$B000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; }');command('ld65','-C',out/'image.cfg','-o',out/'image.bin','-Ln',out/'image.lbl','-m',out/'image.map',*objects)
 raw=(out/'image.bin').read_bytes();assert len(raw)<=4096
 image=wrap(raw,1,35,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'image.seo').write_bytes(image)
 # All old profiles must remain exact; this build only changes the selector.
 for active,sha in [(False,'9233b2e7b77ec4a04b17f4c6c4e4dcf32c8197c31d6dc0f9bc56b59a8f61d0c0'),(True,'38621b45225378a3e5dab7e1c6ce7b0894dbdb0080cbce1e700b3d826319c920')]:
  im,_,_=query.build(out/('editor-default'if active else'default'),base,active);assert hashlib.sha256(im[HEADER:]).hexdigest()==sha
 return image,seam

def run(out,base,pipeline):
 frozen,identity=sem.geos.freeze(out,base);report=json.loads((frozen/'build/editor-report.json').read_text());s=report['symbols'];names=identity['names'];digest=report['resident_binding']['digest']
 image,seam=build(out/'classify',frozen);s.update(seam)
 writer=(pipeline/'writer/writer.seo').read_bytes();worker=(pipeline/'semantic/worker.bin').read_bytes();semantic=wrap(worker,1,34,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest))
 sem.geos.grid.editor_fixture.ROOT=sem.geos.grid.cpu_editor.ROOT=frozen;sem.geos.grid.editor_fixture.NAMES=sem.geos.grid.cpu_editor.NAMES=names
 f=sem.Fixture(out,frozen,sem.geos.grid.runner(out),True);f.s.update(seam);cases=[];calls=0
 ext='.dylib'if sys.platform=='darwin'else'.so'
 (out/'trace.cpp').write_text('#include "zeropage_peddle.h"\n#include<cstdint>\nstatic uint64_t c[2][256],o[256];extern "C" void clear(){for(auto&r:c)for(auto&v:r)v=0;for(auto&v:o)v=0;}extern "C" uint64_t metric(int s,int n){return s==2?o[n]:c[s][n];}extern "C" uint64_t run(ZeroPagePeddle*m,unsigned a,unsigned f,uint64_t n){auto b=zeropage_peddle_regs(m).instructions;while(n--){auto r=zeropage_peddle_regs(m);if(r.pc==0x2ff)return r.instructions-b;if(r.pc==a&&r.x<2){c[r.x][r.a]++;if(!r.x&&r.a==14)o[zeropage_peddle_read(m,f)]++;}zeropage_peddle_step_instruction(m);}return 0;}')
 command('clang++','-O2','-std=c++20','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(VENDOR),out/'trace.cpp',ROOT/('build/libse_peddle'+ext),'-o',out/('trace'+ext));trace=CT.CDLL(str(out/('trace'+ext)));trace.metric.argtypes=[CT.c_int,CT.c_int];trace.metric.restype=CT.c_uint64;trace.run.argtypes=[CT.c_void_p,CT.c_uint,CT.c_uint,CT.c_uint64];trace.run.restype=CT.c_uint64
 def invoke(ident,slot,op):
  nonlocal calls
  f.put('se_overlay_frame',op,1)
  if ident==35:
   before=f.read(0,65536)
   for n,v in [('pc',s['se_overlay_call']),('sp',0xfd),('p',0x24),('a',ident),('x',slot),('y',0)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
   f.m.write(0x1fe,0xfe);f.m.write(0x1ff,2);n=trace.run(f.m.handle,s['se_overlay_call'],s['se_overlay_frame'],8_000_000);assert n;r=f.m.regs();calls+=1
   after=f.read(0,65536);wanted=bytearray(before);pairs=[('se_crc_value',2),('se_object_id',12),('new_owner',5),('validate_index',3),('copy_direction',12),('se_reu_c64',16),('ovl_ptr',2),('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_frame',16),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_overlay_header',36),('image_slot',s['se_overlay_capacity']),('se_doc_read_locks',1),('se_bc_flags',1)]
   for lo,hi in [(s[n],s[n]+w)for n,w in pairs]+[(0x100,0x200),(G,G+192),(F,F+576),(0x5000,0x6000),(0xa000,0xc000),(0xcbd5,0xcbd6),(0xdf00,0xdf0b),(0x9136,0x9137)]:wanted[lo:hi]=after[lo:hi]
   assert wanted==after,('RAM',op,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b))
  else:r,n=f.fast_call(s['se_overlay_call'],a=ident,x=slot)
  return r
 def imp(im):
  f.m.load(s['se_overlay_header'],im[:HEADER]);f.m.load(0x5000,im[HEADER:]);r=f.call('se_overlay_import');assert not r.p&1
 def settle():
  for _ in range(1000):
   if f.m.read(C+8)in(0,10):return
   r=invoke(33,0,1);assert not r.p&1
  raise AssertionError('writerstuck')
 def baseline(data,pending=False):
  f.source(data)
  if pending:f.key(sem.geos.native_text('Q')[0]);data=f.merged()
  f.m.load(seam['se_bc_arena'],bytes(17));f.put('se_f_owner',4,1);f.m.load(F,bytes(576));f.m.write(F,1);f.m.write(F+5,1)
  for im in(writer,semantic,image):imp(im)
  assert not invoke(33,0,0).p&1;settle();f.m.load(F+8,f.read(seam['se_bc_arena'],5)+f.read(seam['se_bc_incarnation'],4)+f.read(seam['se_bc_ticket'],4));assert not invoke(34,1,0).p&1;assert not invoke(33,0,4).p&1;settle()
  for _ in range(100000):
   r=invoke(34,1,1);assert not r.p&1
   if not r.a:break
   if f.m.read(F+4):assert not invoke(33,0,5).p&1;settle();assert not invoke(34,1,3).p&1
  else:raise AssertionError('producerstuck')
  assert not invoke(33,0,6).p&1;settle();assert f.m.read(seam['se_bc_flags'])==1 and not f.get('se_doc_read_locks',1)
  return data
 def classify(pos,caps=1,error=None,owner=4):
  f.put('se_f_owner',owner,1);f.put('se_render_caps',caps,1);f.m.load(G,bytes(192));f.m.load(G,pos.to_bytes(3,'little'));old=bytes(range(0xa0,0xb0));f.m.load(G+5,old);trace.clear();reu=f.reu();canonical=f.canonical();r=invoke(35,1,0);steps=0
  while not r.p&1 and r.a==1:
   assert f.read(G+5,16)==old # publication mustwaitforfinalA0
   r=invoke(35,1,1);steps+=1;assert steps<10000
  if error is not None:assert r.p&1 and r.a==error,(r.a,r.p,error)
  else:assert not r.p&1,(r.a,r.p)
  if not r.p&1:assert f.m.read(G+24)==(0 if r.a==0 else 2),(r.a,f.m.read(G+24))
  assert f.reu()==reu and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  assert sum(trace.metric(1,i)for i in range(256)if i!=35)==0 and sum(trace.metric(0,i)for i in range(256)if i!=14)==0
  assert sum(trace.metric(2,i)for i in range(256)if i not in(0,1))==0
  return r,f.read(G+5,16),f.m.read(G+169),steps
 def expected(data,pos):
  e=next((e for e in blocks(data)if e['start']<=pos<=e['end']),None)
  if e is None:kind=lang=level=marker=0;start=end=body=len(data)
  else:
   kind=e['kind'];lang=e['language'];level=e['level'];start=e['start'];end=e['end'];body=e['body'];marker=e.get('marker',body-start)
  role={2:2,3:1,4:4,5:4,6:4}.get(kind,0)
  return bytes([kind,lang,level,marker])+start.to_bytes(3,'little')+end.to_bytes(3,'little')+body.to_bytes(3,'little')+bytes([role,int(kind==2),8 if kind==5 else 9]),int(kind<4)
 def check(tag,data,positions,pending=False):
  data=baseline(data,pending)
  for pos in positions:
   r,got,hint,steps=classify(pos);want,ih=expected(data,pos);assert r.a==0 and got==want and hint==ih,(tag,pos,got.hex(),want.hex(),hint,ih)
  row={'tag':tag,'queries':len(positions),'source_bytes':len(data)};cases.append(row);print('PASS',row,flush=True)
 try:
  data=sem.geos.native_text('# Title **bold**\r\r- list *em*\r:::basic\r10 PRINT "hi"\r:::\r:::asm\rlda #1\r:::\r:::region Group\rbody\r:::end\rTail.')
  assert {e['kind']for e in blocks(data)}==set(range(9))
  positions=sorted({0,len(data),*(e['start']for e in blocks(data)),*(e['end']for e in blocks(data))});check('allkinds/languages',data,positions)
  check('EOFempty',b'',[0]);check('CRsentinel',b'\r\r',[0,1,2]);check('far24bit',b'A'*66000+sem.geos.native_text('\r# Far\rTail.'),[65535,65536,66000,66001,66006,66012]);check('pending',b'Body **bold**',[0,5,13],True)
  navigation=baseline(sem.geos.native_text('Body **bold**\rTail.'));r,_,_,_=classify(0);assert r.a==0
  oldtoken=f.read(seam['se_bc_arena'],5);f.put('se_f_owner',0,1);f.position(1)
  assert f.m.read(seam['se_bc_flags'])&1 and not f.m.read(seam['se_bc_count'])
  r,got,hint,steps=classify(1);assert r.a==2 and not f.get('se_doc_read_locks',1) and f.read(seam['se_bc_arena'],5)==oldtoken
  cases.append({'tag':'actualpublicW_LOADgeometryinapplicableMISS','queries':2,'source_bytes':len(navigation)})
  data=baseline(sem.geos.native_text('Body **bold** £*literal\rTail.'));stable=f.read(0,65536);reu=f.reu();faults=[]
  for owner in (0,1,2,3,5,255):
   for op in (0,1,2):
    f.m.load(0,stable);f.put('se_f_owner',owner,1);phase=f.read(F,576);semantic_frame=f.read(G,192);r=invoke(35,1,op);assert r.p&1 and r.a==0xb2 and f.read(F,576)==phase and f.read(G,192)==semantic_frame
  faults.append('sixforeignowners/all3ops opaque')
  for flags in (0,2,3,4,5):
   f.m.load(0,stable);f.put('se_bc_flags',flags,1);r,got,hint,steps=classify(0);assert r.a==2 and not f.m.read(G+21)
  f.m.load(0,stable);r,got,hint,steps=classify(0,caps=0);assert r.a==2 and not f.m.read(G+21)
  f.m.load(0,stable);f.put('se_bc_count',1,1);r,got,hint,steps=classify(0);assert r.a==2
  faults.append('Plain/unarmed/LOST/MUTATING/nonemptyqueue MISS2 ERROR2 no semanticpublication')
  f.m.load(0,stable);f.m.load(G,bytes(192));f.m.load(G+5,bytes(range(16)));assert invoke(35,1,0).a==1
  for _ in range(100):
   r=invoke(35,1,1);assert not r.p&1
   if f.m.read(F+3):break
  assert f.get('se_doc_read_locks',1)==1 and f.m.read(seam['se_bc_flags'])==9
  saved=f.read(F,576);r=invoke(35,1,0);assert r.p&1 and r.a==0xb2 and f.read(F,576)==saved
  r=invoke(35,1,2);assert not r.p&1 and not f.get('se_doc_read_locks',1) and f.m.read(seam['se_bc_flags'])==1 and not f.m.read(G+21)
  faults.append('competingBEGIN preserveslivequery; CANCEL endsownlease/ACTIVE without publication')
  f.m.load(0,stable);f.m.load(G,bytes(192));f.m.load(G+5,bytes(range(16)));assert invoke(35,1,0).a==1
  for _ in range(100):
   r=invoke(35,1,1);assert not r.p&1
   if f.m.read(F+4):break
  assert f.m.read(F+4)==1 and f.read(G+5,16)==bytes(range(16))
  # A held CR is provisional: final actual R14 guard must reject change.
  f.m.write(s['se_r_revision'],f.m.read(s['se_r_revision'])^1);r=invoke(35,1,1);assert r.p&1 and f.read(G+5,16)==bytes(range(16)) and not f.m.read(G+21) and not f.get('se_doc_read_locks',1)
  faults.append('sourcechange afterheldCR refusesbeforefinalGSEMpublication')
  f.m.load(0,stable)
  def transfer(offset,raw=None,length=0):
   f.m.load(s['se_object_id'],f.read(seam['se_bc_arena'],5));f.put('se_object_offset',offset);f.put('se_object_length',len(raw)if raw is not None else length,2);f.put('se_object_c64',IO,2)
   if raw is not None:f.m.load(IO,raw)
   r=f.call('se_object_copy',a=int(raw is None));assert not r.p&1
   return f.read(IO,len(raw)if raw is not None else length)
  root=transfer(128,length=128);ref=root[104:108];cr=transfer(ref[0]*4096+64+ref[1]*96,length=96);iref=cr[40:44];assert cr[44]and iref[0]!=ref[0]
  inline_offset=iref[0]*4096+64;old=transfer(inline_offset,length=10);bad=bytearray(old);bad[0]=255;bad[9]=255;transfer(inline_offset,bad);damaged=f.reu()
  # Even invalidINLINEschema+wrongpayloadCRC must have no bearing on a pure
  # classification: it returns only fullCR blockfields, noinlinecertificate.
  for caps in (1,3):
   r,got,hint,steps=classify(0,caps);want,ih=expected(data,0);assert r.a==0 and got==want and hint==ih==1 and f.reu()==damaged
  transfer(inline_offset,old);assert f.reu()==reu
  faults.append('corruptunreadINLINEschema/payloadCRC cannot influence classification; hintonly no reuse')
  # Actual CR page remains fully authenticated; corruptits payload independently.
  off=ref[0]*4096+64+ref[1]*96;bad=bytearray(cr);bad[3]^=1;transfer(off,bad);damaged=f.reu();r,got,hint,steps=classify(0,error=0xc2);assert f.reu()==damaged and not f.get('se_doc_read_locks',1)
  transfer(off,cr);assert f.reu()==reu
  faults.append('CRpageCRC corruption refuseswithout output/lease leak')
  print('FAULTS',faults,flush=True)
  result={'status':'PASS','classification_bytes':len(image)-HEADER,'cases':cases,'faults':faults,'wholeRAM_calls':calls,'parser_entries':0,'scope':'Privateclassificationonly, noINLINEcertificate/lexical/cachegeometryreuse'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--pipeline',type=Path,default=PIPE);a=p.parse_args();out=ROOT/'build/cache-classify'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.pipeline)
