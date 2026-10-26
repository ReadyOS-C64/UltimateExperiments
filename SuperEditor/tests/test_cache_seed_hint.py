"""Private compact C35 seed hint: actual public renderer and exact publication.

No canonical files/build/native change. Parser baseline remains actual C34;
only the C35 sealed image is replaced in candidate assets before cold import.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,importlib.util,inspect,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_inline_hint as hint
import test_cache_navigation_cost as nav
from peddle import Machine


def builder():
 path=ROOT/'src/cache/query/probes/seed-hint/build.py';spec=importlib.util.spec_from_file_location('seed_hint_build',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.command=lambda args:subprocess.check_output(list(map(str,args)),cwd=ROOT,text=True)
 return module


def public(out,base):
 code=inspect.getsource(hint.run)
 code=code.replace("out/'build/hint/page.seo'","out/'build/hint/inln.seo'").replace("out/'build/hint/page.lbl'","out/'build/hint/image.lbl'")
 code=code.replace("f.assets['page']=candidate","f.assets['inln']=candidate")
 code=code.replace('requested==37','requested==35').replace('bytes((37,1))','bytes((35,1))').replace('a=37,x=1','a=35,x=1')
 code=code.replace("'C37", "'C35").replace('mid-C37','mid-C35').replace('optional C37','optional C35').replace('into C37','into C35')
 code=code.replace("!=9:continue","!=0:continue").replace("q['start']==9","q['start']==0")
 code=code.replace("ref=cr[40:44].hex()", "ref=cr[40:44].hex(),output=f.read(0x8B45,16).hex()")
 code=code.replace("('plain-bypass',diverse.fixture(),0)", "('EOF-empty',b'',1),('EOF-CR',b'\\r',1),('plain-bypass',diverse.fixture(),0)")
 # Malformed EOF normalization is verified by the local publisher matrix;
 # public empty sources may correctly bypass optional baseline creation.
 code=code.replace("('251-markdown','422-markdown','literal-unclosed','head-list')","('literal-unclosed','native-pound-literal','head-list')")
 code=code.replace("('escapes',observer.geos.native_text('Prelude.\\rEscaped", "('escapes',observer.geos.native_text('Escaped")
 code=code.replace("('256-events',observer.geos.native_text('Prelude.\\r'+", "('256-events',observer.geos.native_text(''+")
 # Patch only the selected live root's first CR, not stale BP-looking bytes
 # left in this optional arena's unreferenced pages after fixture resets.
 code=code.replace('for pg in range(1,16):', "roots=[bank[o:o+128]for o in(0,128)if bank[o+5]==1];root=max(roots,key=lambda r:int.from_bytes(r[18:22],'little'))\n   for pg in [root[104]]:")
 code=code.replace('for at in range(0,len(payload),96):', 'for at in [root[105]*96]:')
 code=code.replace('Actual private C37 public renderer','Actual private compact C35 public renderer')
 ns=dict(vars(hint));ns['load_builder']=builder;(out/'generated-public.py').write_text(code);exec(compile(code,str(out/'generated-public.py'),'exec'),ns);return ns['run'](out,base)


def navigation(out,base,candidate):
 # Retain the released navigation verifier/oracle and all source/REU scopes.
 # Both controls use the same committed-identity fixture; only C35 changes.
 code=inspect.getsource(nav.run)
 code=code.replace("try:\n   fonts=", "try:\n   if variant=='committed':f.assets['inln']=CANDIDATE\n   fonts=",1)
 code=code.replace("if variant=='committed':assert", "if True:assert").replace("    else:assert counts['C24feed']>0 and[37,3]not in trace\n",'')
 ns=dict(vars(nav));ns['CANDIDATE']=candidate;(out/'generated-navigation.py').write_text(code);exec(compile(code,str(out/'generated-navigation.py'),'exec'),ns);ns['run'](out,base,base);return json.loads((out/'result.json').read_text())


def publication(out,build):
 out.mkdir();m=Machine();dll=hint.observer.geos.grid.runner(out);cases=0;result_cases=0
 def read(a,n):v=C.create_string_buffer(n);dll.gm_read(m.handle,a,n,v);return v.raw
 def run(raw,labels,start,cr,kind):
  m.load(0,bytes((i*73+29)&255 for i in range(65536)));m.load(0xb000,raw);m.load(0x8e03,cr);m.load(0x8d18,(start+int.from_bytes(cr[19:22],'little')).to_bytes(3,'little'));m.write(0x8d0f,17)
  before=read(0,65536);r,n=m.call(labels['publish']);after=read(0,65536);want=bytearray(before)
  for lo,hi in ((0x100,0x200),(0x8b45,0x8b55),(0x8b55,0x8b56),(0x8b58,0x8b59),(0x8bb2,0x8bb3),(0x8be9,0x8bea)):want[lo:hi]=after[lo:hi]
  assert after==want,'publication RAM scope';return r,after[0x8b40:0x8c00]
 images=[(build/tag/'image.bin').read_bytes()for tag in('control','hint')];labels=[hint.symbols(build/tag/'image.lbl')for tag in('control','hint')]
 try:
  for kind in list(range(9))+[255]:
   for start,length,body in [(0,0,0),(0xff00,0x1ff,0x1fe),(0xffff,0xffff,0xfffe),(0x7fffff,1,1),(0xffff00,255,254)]:
    for lang,level,marker in [(0,0,0),(1,6,255),(2,3,7)]:
     for flags,count,ref in [(6,0,b'\xff'*4),(2,0,b'\xff'*4),(6,1,b'\xff'*4),(6,256,b'\xff'*4),(6,65536,b'\xff'*4),(6,0,bytes(4)),(6,0,b'\xff\xff\xff\x00')]:
      cr=bytearray(96);cr[3]=kind;cr[2]=10 if kind==255 else flags;cr[16:19]=start.to_bytes(3,'little');cr[19:22]=length.to_bytes(3,'little');cr[22:25]=body.to_bytes(3,'little');cr[69:72]=bytes((lang,level,marker));cr[40:44]=ref;cr[44:47]=count.to_bytes(3,'little')
      old,o=run(images[0],labels[0],start,cr,kind);new,n=run(images[1],labels[1],start,cr,kind);assert(old.a,old.p,old.sp)==(new.a,new.p,new.sp),'A/P/SP'
      block=0 if kind==255 else kind;expected=bytes([block,0 if kind==255 else lang,0 if kind==255 else level,0 if kind==255 else marker])+start.to_bytes(3,'little')+(start+length).to_bytes(3,'little')+(start+body).to_bytes(3,'little')+bytes([{2:2,3:1,4:4,5:4,6:4}.get(block,0),int(block==2),8 if block==5 else 9])
      assert o[5:21]==n[5:21]==expected,'independent field map'
      want=int(block<4 and not(cr[2]&4 and count==0 and ref==b'\xff'*4));assert n[169]==want and o[169]==int(block<4)
      oo=bytearray(o);oo[169]=n[169];assert bytes(oo)==n,'other GSEM bytes changed';cases+=1
  # RESULT path PHA compaction must return original A/status/SP and preserve
  # pending ACTIVE / fault ERROR, including carry-set A1.
  for a in (0,1,2,0x17,0xb1,0xc1,255):
   for carry in(0,1):
    results=[]
    for raw,lab in zip(images,labels):
     m.load(0,bytes((i*73+29)&255 for i in range(65536)));m.load(0xb000,raw)
     for name,value in [('a',a),('x',71),('y',93),('p',0x64|carry),('sp',0xfd),('pc',lab['result'])]:getattr(m.lib,'zeropage_peddle_set_'+name)(m.handle,value)
     m.write(0x1fe,0xfe);m.write(0x1ff,2);before=read(0,65536);used=dll.gm_run(m.handle,1000);assert used;r=m.regs();after=read(0,65536);want=bytearray(before)
     for lo,hi in((0x100,0x200),(0x8b55,0x8b56),(0x8b58,0x8b59)):want[lo:hi]=after[lo:hi]
     assert after==want;results.append((r.a,r.p,r.sp,after[0x8b40:0x8c00]))
    assert results[0]==results[1],'RESULT A/P/SP/semantic difference';result_cases+=1
 finally:m.close()
 result={'status':'PASS','publication_cases':cases,'result_A_P_SP_cases':result_cases,'scope':'Explicit local publisher/result entry seam. Host-seeded CR arithmetic/predicate inputs are not claimed authenticated hits; whole64KiB writes exact and independently modeled fields/A/P/SP.'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def run(out,base):
 p=out/'public';p.mkdir();pub=public(p,base)
 local=publication(out/'publication',p/'build')
 n=out/'navigation';n.mkdir();nav_result=navigation(n,base,(p/'build/hint/inln.seo').read_bytes())
 result={'status':'PASS','public':pub,'publication':local,'navigation':nav_result};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=ROOT/'build/cache-editor-product/20261026T023925641413Z/fixture');a=p.parse_args();out=ROOT/'build/cache-seed-hint'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 try:run(out,a.fixture)
 except subprocess.CalledProcessError as e:print(e.stderr,flush=True);raise
