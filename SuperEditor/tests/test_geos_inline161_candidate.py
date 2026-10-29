"""Private versioned161-cell inline query and exact C21 publication."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil,subprocess,sys,zipfile,hashlib,re,inspect
import test_geos_semantic_editor as semantic
from overlays import wrap
ROOT=semantic.ROOT;D=ROOT/'src/render/geos/inline161-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T183509461736Z/fixture'
def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True);assert not p.returncode,p.stdout+p.stderr
def build(out,base):
 out.mkdir(parents=True);src=out/'source';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 inc=out/'include/render/geos';inc.mkdir(parents=True);shutil.copy2(D/'inline.inc',inc/'inline.inc');report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];digest=report['resident_binding']['digest'];(out/'editor-api.inc').write_text('.import se_overlay_call,se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');records={}
 for name,id,modules,cfg in [('geosinln',26,[('inline',D/'inline.s'),('parser',src/'src/supermark/inline.s')],'geos-editor-inline.cfg'),('geospage',21,[('page',D/'page.s'),('cache',src/'src/render/geos/cache.s')],'geos-editor-page.cfg')]:
  objects=[]
  for tag,path in modules:
   obj=out/(tag+'.o');command('ca65','-g','-I',out,'-I',out/'include','-I',src/'src','-o',obj,path);objects.append(obj)
  command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-binding.s'),*objects);command('ca65','-g','-o',out/(name+'-binding.o'),out/(name+'-binding.s'));command('ld65','-C',src/'cfg'/cfg,'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objects,out/(name+'-binding.o'))
  raw=(out/(name+'.bin')).read_bytes();assert len(raw)<=4096;image=wrap(raw,1,id,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(image);records[name]=dict(payload=len(raw),sha256=hashlib.sha256(image).hexdigest())
 (out/'build.json').write_text(json.dumps(records,indent=2)+'\n');return records
def install(out,base):
 records=build(out/'link',base);f=out/'fixture';shutil.copytree(base,f);meta=json.loads((f/'freeze.json').read_text())
 for n,r in records.items():shutil.copy2(out/'link'/(n+'.seo'),f/'build/overlays'/(n+'.seo'));meta['assets'][n]=r['sha256']
 meta['private_CPU_overlay_substitutions']={'names':list(records),'source_root':str(D.relative_to(ROOT)),'native_disk_packaged':False}
 (f/'freeze.json').write_text(json.dumps(meta,indent=2)+'\n');return f
def harness(out,base):
 import test_geos_editor as geos
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=base
 names=json.loads((base/'freeze.json').read_text())['names'];geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=names
 dll=geos.grid.runner(out);return geos.Fixture(out,base,dll,True)
def whole(f):
 import ctypes as C
 b=C.create_string_buffer(16*1024*1024);f.dll.gm_reu(f.m.handle,len(b),b);return b.raw

def public(out,base):
 import test_geos_editor as geos
 from geos_packet import rows as raw_rows
 fonts={n:(base/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
 f=harness(out,base);records=[]
 def check(data,tag,pan=1,nowrap=True,caret=0):
  f.source(data);f.command(99);f.position(caret)
  f.put('se_l_mode',int(nowrap),1);f.put('se_l_manual',1,1);f.put('se_l_pan',pan if nowrap else 0);f.put('se_v_top',0)
  f.put('se_gc_valid',0,1);f.put('se_l_valid',0,1)
  canonical,catalog,before=f.canonical(),f.catalog(),whole(f)
  f.render();assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xC600,1024)==f.shim
  sem=semantic.classify(data);shown_caret=f.get('se_hot_caret')
  if nowrap:
   start=data.rfind(b'\r',0,shown_caret)+1;x=sum(fonts['bsw9-widths.bin'][geos.native(data[i])]+(sem.styles[i]&1)+(sem.styles[i]&2)for i in range(start,shown_caret))-pan
   if not 0<=x<320:shown_caret=None
  bits,attrs,lines=semantic.raster(data,fonts,top=f.get('se_v_top'),caret=shown_caret,styles=sem.styles,roles=sem.roles,reverse=sem.reverse,code=sem.code,nowrap=nowrap,pan=pan if nowrap else 0)
  matrix,colors,popup=geos.grid.logical_ui(f,data);bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
  actual=f.read(0x6000,8000);actualattrs=f.read(0x4000,1000)
  (out/(tag+'-ram.bin')).write_bytes(f.read(0,65536));geos.png(actual,actualattrs,out/(tag+'.png'))
  assert actual==bits,(tag,'pixels',next((i,a,b)for i,(a,b)in enumerate(zip(actual,bits))if a!=b))
  assert actualattrs==attrs,(tag,'attributes',next((i,a,b)for i,(a,b)in enumerate(zip(actualattrs,attrs))if a!=b))
  cache,bank=f.raw_cache();rr=raw_rows(cache)
  for row in rr:
   a=row['first'];n=row['count'];assert row['chars']==data[a:a+n] and row['styles']==sem.styles[a:a+n] and row['roles']==sem.roles[a:a+n],(tag,'full161 source/style/roles',row)
   assert row['left']==row['right']==tuple(range(a,a+n+1))
  after=whole(f);start=bank*65536;cursor=0
  spans=[(start,start+64)]+[(start+0x200+i*0x800,start+0x200+(i+1)*0x800)for i in range(22)]+[(start+0xB200,start+0xEA88)]
  for a,b in spans:assert before[cursor:a]==after[cursor:a],(tag,'noncacheREU',cursor,a);cursor=b
  assert before[cursor:]==after[cursor:]
  assert not any(f.get(n,1)for n in ('se_f_owner','se_fs_owned','se_doc_read_locks'))
  records.append(dict(tag=tag,count=[r['count']for r in rr],pan=pan,nowrap=nowrap,pixels=64000,full_REU_guard_bytes=16777216))
 try:
  check(b'.'*200+geos.native_text('**X**\rTail.'),'late-inline-count161')
  for count in (159,160,161,162,200):
   check(b'.'*count+geos.native_text(' **B** *I* @@C@@'),'eof-'+str(count))
  check(b'.'*158+geos.native_text('**X** tail'),'last-glyph-style')
  check(b'.'*158+geos.native_text('@@X@@ tail'),'last-glyph-code')
  check(b'@@'+b'.'*200+b'@@','count161-all-code-role4',2*fonts['bsw9-widths.bin'][geos.native(64)]+1)
  check(b'.'*200+geos.native_text('**X**\rTail.'),'wrap-same-source',0,False)
  check(b'.'*200+geos.native_text('**X**\rTail.'),'pan3',3)
  result=dict(status='passed',frames=records,scope='Actual public root C21/C26 + unchanged C20/C22/R14/R21; independent full64000 pixels/1000attrs, RAW161 maps/source/style/roles, canonical/history/clipboard/shim and noncache whole16MiB guards.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()

def wide(out,base):
 import test_geos_inline as old
 from supermark_model import inline
 f=harness(out,base);records=[];faults=[];state={}
 parent=bytes((i*31+17)&255 for i in range(68));packet=bytes((i*47+29)&255 for i in range(160));prefix=bytes((i*19+53)&255 for i in range(32))
 def setup(data,query=0,body=0,end=None,start=0,count=161,role=0):
  end=len(data)if end is None else end
  f.put('se_f_owner',4,1);f.m.load(0x8D00,bytes([0xA5])*0x334)
  frame=bytearray((i*13+37)&255 for i in range(192))
  for a,v,n in[(0,query,3),(4,count,1),(9,start,3),(12,end,3),(15,body,3),(18,role,1)]:frame[a:a+n]=v.to_bytes(n,'little')
  f.m.load(0x8B40,frame);f.m.load(0x9134,parent);f.m.load(0x8100,prefix);f.m.load(0x8200,packet)
  f.m.load(0x8300,bytes([0xEA])*162);f.m.load(0x8F36,bytes([0xDA])*182);f.m.load(0x8FEB,bytes([0xBE])*5)
  f.m.write(0x912C,0);f.m.write(0x912D,0)
  state.update(frame=bytes(frame),canonical=f.canonical(),reu=whole(f),catalog=f.catalog(),data=data,query=query,body=body,end=end,start=start,count=count,role=role)
 def invoke(op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=26,x=1)
  assert f.read(0x8B40,192)==state['frame']and f.read(0x8200,160)==packet and f.read(0x8100,32)==prefix
  actual=f.read(0x9134,68);assert actual[:1]+actual[3:]==parent[:1]+parent[3:]
  assert f.canonical()==state['canonical']and f.catalog()==state['catalog']and f.read(0xC600,1024)==f.shim
  assert whole(f)==state['reu'],'read-only wide worker changed REU'
  return r,n
 def query(data,tag,**kw):
  setup(data,**kw);r,n=invoke(4);steps=0;peak=n
  while not r.p&1 and r.a:
   oldpos=int.from_bytes(f.read(0x8D00,3),'little');phase=f.m.read(old.CONTROL+1)
   r,n=invoke(1);peak=max(peak,n);steps+=1
   if phase==2:assert 0<=int.from_bytes(f.read(0x8D00,3),'little')-oldpos<=32
   assert steps<len(data)//8+300
  assert not r.p&1 and r.a==0,(tag,hex(r.a),steps)
  want_s,want_r=old.expected(data,state['start'],state['body'],state['end'],state['query'],161,state['role'])
  hidden=bytearray(21)
  for kind,style,width,a,b in inline(data[state['body']:state['end']],state['body'],body_column=(state['body']-state['start'])or None):
   for lo,hi in ([(a,a+width),(b,b+width)]if kind==1 else[(a,a+1)]):
    for p in range(max(lo,state['query']),min(hi,state['query']+161)):
     i=p-state['query'];hidden[i//8]|=128>>(i&7)
  assert f.read(0x8300,161)==want_s,(tag,'161styles')
  assert f.read(0x8F36,160)+f.read(0x8FEB,1)==want_r,(tag,'split161roles')
  assert f.read(0x8FD6,21)==hidden,(tag,'161hidden',f.read(0x8FD6,21).hex(),hidden.hex())
  assert f.m.read(0x83A1)==0xEA and f.read(0x8FEC,4)==bytes([0xBE])*4
  assert not any(f.get(n,1)for n in('se_doc_read_locks','se_fs_owned'))and not f.m.read(0x912D)
  assert whole(f)==state['reu']
  assert not f.call('se_view_init').p&1
  assert f.read(0x8300,161)==want_s and f.read(0x8F36,160)+f.read(0x8FEB,1)==want_r
  f.put('se_f_owner',0,1);records.append(dict(tag=tag,steps=steps,peak_instructions=peak,last_style=want_s[-1],last_role=want_r[-1],hidden160=bool(hidden[20]&128)))
 try:
  samples=[('plain',b'x'*161),('bold-last',b'**'+b'x'*159+b'**'),('italic-last',b'*'+b'x'*160+b'*'),('nested-last',b'***'+b'x'*158+b'***'),('code-last',b'@@'+b'x'*159+b'@@'),('close-hidden160',b'**'+b'x'*158+b'**'),('escape-hidden160',b'x'*160+b'\\*'),('nested-code',b'**'+b'x'*145+b' @@xy *z*@@ tail**')]
  for tag,data in samples:f.source(data);query(data,tag)
  data=b'## '+b'**'+b'x'*170+b'**\rnext';f.source(data);query(data,'heading-prefix',body=3,end=data.index(13),role=2)
  data=b'x'*150+b'\rnext'+b'x'*20;f.source(data);query(data,'window-crosses-body-cr',end=150)
  data=b'x'*65530+b'\r## **'+b'x'*170+b'**\rnext';f.source(data);f.position(65540);f.key(ord('Q'));data=data[:65540]+b'Q'+data[65540:];assert f.get('se_hot_pending',1)
  query(data,'high24-pending',start=65531,body=65534,end=data.index(13,65531),query=65531,role=2);assert f.get('se_hot_pending',1)
  data=b'**'+b'x'*170+b'**';f.source(data)
  for op,count in[(0,161),(3,161),(4,160),(4,162)]:
   setup(data,count=count);before=f.read(0x8D00,1152);r,n=invoke(op);assert r.p&1 and r.a==0x90 and f.read(0x8D00,1152)==before and not f.get('se_doc_read_locks',1);faults.append('versioned-count-'+str(op)+'-'+str(count))
  setup(data,query=30);r,n=invoke(4);assert r.p&1 and r.a==0x7B and not f.get('se_doc_read_locks',1);faults.append('source-window-overflow')
  setup(data);assert not f.call('se_doc_read_acquire').p&1;assert not invoke(4)[0].p&1 and f.get('se_doc_read_locks',1)==2
  for _ in range(2):assert not invoke(2)[0].p&1 and f.get('se_doc_read_locks',1)==1
  assert not f.call('se_doc_read_release').p&1;faults.append('cancel-foreign-counted-lease')
  setup(data);assert not invoke(4)[0].p&1;f.put('se_r_revision',f.get('se_r_revision',4)+1,4);r,n=invoke(1);assert r.p&1 and r.a==0xB1 and not f.get('se_doc_read_locks',1);faults.append('sourcechange-midscan')
  setup(data);r,n=invoke(4)
  while f.m.read(old.CONTROL+1)!=4:r,n=invoke(1);assert not r.p&1
  assert not f.get('se_doc_read_locks',1);r,n=invoke(1);before=f.read(0x8300,162)+f.read(0x8F36,182);f.put('se_r_revision',f.get('se_r_revision',4)+1,4);r,n=invoke(1);assert r.p&1 and r.a==0x74 and before==f.read(0x8300,162)+f.read(0x8F36,182);faults.append('publication-change-no-further-writes')
  for owner in(0,1,2,3,255):
   setup(data);f.put('se_f_owner',owner,1);phase=f.read(0x8D00,1152)
   for op in(0,1,2,3,4,255):r,n=invoke(op);assert r.p&1 and r.a==0xB2 and f.read(0x8D00,1152)==phase
  faults.append('30foreign-owner-ops-opaque')
  result=dict(status='passed',queries=records,faults=faults,full_REU_guard_bytes=16777216,source_context_immutable=192,parent_immutable=66,source_packet_immutable=160)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--suite',choices=['fit','public','legacy','wide','inline','preview','fold','incremental'],default='fit');p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-inline161'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.suite);out.mkdir(parents=True);print('RUN',out,flush=True)
 if a.suite=='fit':print(build(out/'link',a.base),flush=True)
 else:
  base=install(out,a.base);target=out/'gate';target.mkdir()
  if a.suite=='public':print(public(target,base),flush=True)
  elif a.suite=='wide':print(wide(target,base),flush=True)
  elif a.suite in('inline','preview','fold','incremental'):
   if a.suite=='inline':semantic.run(target,base,inline_case=True)
   elif a.suite=='preview':
    import test_geos_preview_editor as gate;gate.run(target,base)
   elif a.suite=='fold':
    import test_geos_fold_editor as gate;gate.run(target,base)
   else:
    import test_geos_incremental_editor as gate;gate.run(target,base)
  else:
   import test_geos_inline as gate
   def worker(where,frozen):
    records=build(where,frozen);return (where/'geosinln.seo').read_bytes(),{}
   original=gate.geos.Fixture
   class Replaced(original):
    def __init__(self,*args,**kw):
     super().__init__(*args,**kw);self.assets.pop('geosinln') #old gate adds private ID26 under its own name; replace, never duplicate
   gate.geos.Fixture=Replaced;gate.build=worker
   source=inspect.getsource(gate.run);needle="f.m.read(f.s['image_slot']+i)==slot";assert source.count(needle)==1
   #Published slot identity only, via existing checked managed-catalog policy.
   ns=dict(gate.__dict__);exec(source.replace(needle,"f.catalog()[f.s['se_overlay_capacity']+i]==slot"),ns);ns['run'](target,base)
