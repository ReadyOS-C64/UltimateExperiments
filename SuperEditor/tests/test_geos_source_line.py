"""Private actual C20/R14 merged-source GEOS line/maps; no shared build/native."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,sys
import test_fold_retention as r
import test_grid_modes as g
import test_geos_line as line
from test_geos_glyphs import native
from overlays import wrap
ROOT=g.ROOT;L=0x8D00;GS=0x912C

def run(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
def build(out,base):
 report=json.loads((base/'build/editor-report.json').read_text());d=report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 objs=[]
 for name in ['source-line','line','measure','assets','bands']:
  p=out/(name+'.o');run('ca65','-g','-I',out,'-I','src','-o',p,'src/render/geos/'+name+'.s');objs.append(p)
 aliases=out/'aliases.s';run(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',aliases,*objs);run('ca65','-g','-I','src','-o',out/'aliases.o',aliases)
 (out/'leaf.cfg').write_text('MEMORY { C:file=%O,start=$B000,size=$1000,type=rw; } SEGMENTS { GEOS_SOURCE:load=C,type=ro; CODE:load=C,type=ro; GEOS_BANDS:load=C,type=ro; RODATA:load=C,type=ro; }')
 run('ld65','-C',out/'leaf.cfg','-o',out/'source-line.bin','-Ln',out/'source-line.lbl','-m',out/'source-line.map',*objs,out/'aliases.o')
 payload=(out/'source-line.bin').read_bytes();assert len(payload)<=4096;s=report['symbols'];image=wrap(payload,1,20,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'source-line.seo').write_bytes(image);return image,report

class Fixture(r.Fixture):
 def p(self,n,v,w=1):self.m.load(L+n,v.to_bytes(w,'little'))
 def q(self,n,w=3):return int.from_bytes(self.read(L+n,w),'little')
 def invoke(self,op):
  self.put('se_overlay_frame',op,1);reg,_=self.m.call(self.s['se_overlay_call'],a=20,x=1);return reg
 def claim(self):
  self.saved=self.read(L,1152)
  for n in ['se_i_ready','se_i_count','se_n_cache_count']:self.put(n,0,1)
  self.put('se_f_owner',4,1);self.m.load(L,bytes(1152))
 def release(self):
  assert not self.invoke(2).p&1;self.put('se_f_owner',0,1);self.m.load(L,self.saved)

def main():
 a=argparse.ArgumentParser();a.add_argument('--fixture',type=Path);a.add_argument('--smoke',action='store_true');args=a.parse_args();out=ROOT/'build/geos-source-line'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);base,identity=r.freeze(out,args.fixture);image,report=build(out,base)
 g.cpu_editor.ROOT=g.editor_fixture.ROOT=base;g.cpu_editor.NAMES=g.editor_fixture.NAMES=identity['names'];dll=g.runner(out);f=Fixture(out,base,dll,True);f.assets['geosline-private']=image;cases=[];steps=0
 widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes()
 def check(data,start=0,width=320,mode=0,pan=0,pending=False,encoding=0):
  nonlocal steps
  f.source(data)
  merged=data
  if pending:f.position(1);f.key(ord('Q'));merged=data[:1]+b'Q'+data[1:];assert f.get('se_hot_pending',1)
  f.claim();f.p(0,mode);f.p(1,encoding);f.p(2,width,2);f.p(4,start,3);f.p(7,pan,3);f.p(10,start+1,3);canonical=f.canonical();reu=f.reu();catalog=f.catalog();guard=f.read(0x8800,1280)+f.read(0x9180,128);locks=f.get('se_doc_read_locks',1)
  reg=f.invoke(0);assert not reg.p&1 and reg.a==1 and f.get('se_doc_read_locks',1)==locks+1,(reg.a,'begin')
  assert f.q(1,1)==encoding and f.read(0x910C,32)==bytes([8 if encoding else 0])*32
  previous=start
  for _ in range(len(merged)//1+100):
   reads=f.m.read(GS+3);reg=f.invoke(1);steps+=1;assert not reg.p&1,(reg.a,'step');assert (f.m.read(GS+3)-reads)&255==1
   assert 0<=f.q(38)-previous<=32;previous=f.q(38)
   if reg.a==0:break
   assert reg.a==1
  else:raise AssertionError('not bounded')
  adv=[8 if encoding else widths[native(v)] for v in merged];want=line.oracle(merged,adv,start,width,mode,pan,start+1,0)
  for n,k in [(33,'reason'),(41,'end'),(44,'next'),(35,'x'),(47,'first')]:assert f.q(n,1 if n==33 else 3)==want[k],(n,f.q(n),want)
  count=f.q(50,2);max_mapped=min(320,f.q(38)-start);assert f.read(L+176+(max_mapped+1)*2,832-176-(max_mapped+1)*2)==bytes(832-176-(max_mapped+1)*2),'unused GL map overwritten by reader context'
  maps=[f.q(176+i*2,2) for i in range(count+1)];assert maps==want['maps']
  for x in [0,4,12,width,width//2,65535]:
   f.p(30,x,2);reg=f.invoke(3);assert not reg.p&1;target=min(width,x);index=min(range(len(maps)),key=lambda i:(abs(maps[i]-target),-i));assert f.q(56)==want['first']+index
  assert f.canonical()==canonical and f.reu()==reu and f.catalog()==catalog and f.read(0x8800,1280)+f.read(0x9180,128)==guard and f.get('se_doc_read_locks',1)==locks and not f.m.read(GS+1);assert f.read(0xC600,1024)==f.shim
  f.release();assert f.merged()==merged;cases.append(dict(pending=pending,length=len(merged),mode=mode,encoding=encoding,start=start,reason=want['reason'],end=want['end']))
 try:
  check(b'Wide words and mixed CASE\rnext',pending=True)
  check(b'A'*41+b'\r',encoding=1)
  if not args.smoke:
   for mode,pan in [(0,0),(1,0),(1,71)]:check(b'Wim. '*25+b'\r',width=67,mode=mode,pan=pan)
   check(b'x'*65540+b'\rHigh iW body\r',start=65541,width=71)
   check(b'i'*66000+b'\r',mode=1,pan=130900)
   check(b'i'*200+b'\r',width=320)
   for pan in [0,1,7,8,319,65540]:check(b'Code bytes '+b'A'*9000+b'\r',mode=1,pan=pan,encoding=1)
   check(b'P'*65520+b'A'*45+b'\rEND',start=65520,encoding=1)
   check(b'A'*40+b'\r',encoding=1)
   check(b'A'*40,encoding=1)
   check(b'A'*39,encoding=1)
   check(b'',encoding=1)
   check(b'P'*65520+b'A'*45+b'\rEND',start=65520,mode=1,pan=7,encoding=1)
   check(b'\r',encoding=1)
   # Poison every one of the86 overlapped GL bytes. This short line never
   # legitimately writes that distant map suffix, so GUARD/READ/END exchange
   # must restore all86 exactly, including bytes beyond active map_count.
   f.source(b'abc\r');f.claim();f.p(2,320,2);assert not f.invoke(0).p&1
   poison=bytes((i*71+19)&255 for i in range(86));f.m.load(0x8EE0,poison);reg=f.invoke(1)
   assert not reg.p&1 and reg.a==0 and f.read(0x8EE0,86)==poison and not f.get('se_doc_read_locks',1)
   f.release();cases.append(dict(all86_GL_overlap_bytes_preserved_across_guard_read_END=True))
   # Wrong owner must refuse before any union byte access, including CANCEL.
   f.source(b'line\r');f.claim();saved=f.read(L,1152)
   for owner in [0,1,2,3,255]:
    f.put('se_f_owner',owner,1)
    for op in range(4):reg=f.invoke(op);assert reg.p&1 and reg.a==0xB2 and f.read(L,1152)==saved
   f.put('se_f_owner',4,1)
   # Foreign lease survives cancellation and source-revision failure.
   f.call('se_doc_read_acquire');f.p(2,320,2);assert not f.invoke(0).p&1;assert f.get('se_doc_read_locks',1)==2
   reg=f.invoke(2);assert not reg.p&1 and f.get('se_doc_read_locks',1)==1;assert not f.invoke(2).p&1
   assert not f.invoke(0).p&1;old=f.get('se_r_revision',4);f.put('se_r_revision',old+1,4);reg=f.invoke(1);assert reg.p&1 and reg.a==0xB1 and f.get('se_doc_read_locks',1)==1;f.put('se_r_revision',old,4);f.call('se_doc_read_release');f.release();cases.append(dict(foreign_owner=True,cancel=True,source_change=True))
   f.source(b'fault source\r');f.claim();f.p(2,320,2);assert not f.invoke(0).p&1
   idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==14 and f.m.read(f.s['image_slot']+i)==0)
   f.m.write(f.s['se_overlay_ids']+idx,0);reu=f.reu();reg=f.invoke(1);assert reg.p&1 and reg.a==0x17 and f.get('se_doc_read_locks',1)==0 and not f.m.read(GS+1) and f.reu()==reu
   f.m.write(f.s['se_overlay_ids']+idx,14);f.release();cases.append(dict(missing_R14=True,load_free_END=True))
   f.source(b'bad width\r');f.claim();f.p(2,0,2);reu=f.reu();reg=f.invoke(0);assert reg.p&1 and reg.a==0x90 and not f.get('se_doc_read_locks',1) and not f.m.read(GS+1) and f.reu()==reu;f.release();cases.append(dict(invalid_layout_after_reader_BEGIN_releases_lease=True))
   for encoding in [2,255]:
    f.source(b'bad encoding\r');f.claim();f.p(1,encoding);f.p(2,320,2);phase=f.read(L,1152);reu=f.reu();reg=f.invoke(0)
    assert reg.p&1 and reg.a==0x90 and f.read(L,1152)==phase and not f.get('se_doc_read_locks',1) and f.reu()==reu;f.release()
   f.source(b'encoding change\r');f.claim();f.p(2,320,2);assert not f.invoke(0).p&1;f.p(1,1);reu=f.reu();reg=f.invoke(1)
   assert reg.p&1 and reg.a==0x74 and not f.get('se_doc_read_locks',1) and not f.m.read(GS+1) and f.reu()==reu;f.release();cases.append(dict(invalid_encoding_before_lease=True,changed_encoding_releases_lease=True))
  result=dict(status='passed',identity=identity,payload_bytes=len(image)-36,phase_bytes=1152,source_context_bytes=86,packet_bytes=32,steps=steps,cases=cases,new_BSS=0,new_ZP=0,checked_REU_bytes=16777216,scope='Actual private C20 plus sealed resident/R14 merged-source metrics/maps/hits. No raster/native/editableGEOS claim.',source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['src/render/geos/source-line.s','src/render/geos/source-line.inc','tests/test_geos_source_line.py']})
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()
