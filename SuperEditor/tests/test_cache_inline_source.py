"""Private actual C20 SOURCE→C39→C20 continuation qualification, no root dispatch."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,inspect,runpy
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_inline as component
from test_cache_query_proof import hooks
from overlays import HEADER
import test_cache_query_forward as forward

def build_adapter(out,base):
 code=inspect.getsource(component.build_inline).replace("ROOT/'src/cache/inline'/(name+'.s')","ROOT/'src/cache/inline'/('probes/source-adapter'if name in('entry','seed','core','page')else'')/(name+'.s')").replace('wrap(raw,1,36','wrap(raw,1,39')
 ns=dict(vars(component));exec(compile(code,str(out/'generated-build.py'),'exec'),ns);return ns['build_inline'](out,base)

def source_images(out,base):
 ns=runpy.run_path(str(ROOT/'src/cache/inline/probes/source-adapter/build-source.py'));candidate=ns['build_source'](out,base)
 return (base/'build/overlays/geosline.seo').read_bytes(),candidate

def build_hint(out,base):
 code=inspect.getsource(forward.build_fast).replace("'BCQ_FORWARD_QUERY=1'","'BCQ_FORWARD_QUERY=1','-D','BCQ_EMPTY_INLINE_HINT=1'")
 ns=dict(vars(forward));exec(compile(code,str(out/'hint-generator.py'),'exec'),ns);return ns['build_fast'](out,base)

SOURCE=r'''  import test_geos_line as line_oracle
  from test_geos_glyphs import native
  from supermark_model import inline
  source_cases=[]
  widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes()
  def line(data,start=0,cached=True,pending=False,poison=False,change=False):
   # Import selected immutable C20 during cold fixture catalog setup; the
   # real manager deliberately refuses replacement of an existing ID.
   f.assets['geosline']=source_candidate if cached else source_control
   data=baseline(data,pending);rr,_,_,_=classify(start);assert rr.a==0
   # Reclassify through the actual released empty-hint C37 profile.
   f.m.write(0x9135,37);f.m.write(0x9136,0);rr=invoke(37,1,0)
   for _ in range(100):
    if rr.p&1 or rr.a!=1:break
    assert f.m.read(0x9135)==37
    rr=invoke(37,1,f.m.read(0x9136))
   assert not rr.p&1 and rr.a==0
   rr,_=f.fast_call(0x900);assert not rr.p&1
   has_inline=f.m.read(G+169)
   # Only this sourceconstant path is replaced; normalC21PS8 remainslegacy.
   f.m.load(0x8d00,bytes(832));f.m.write(0x8d00,0);f.m.write(0x8d01,0);f.m.load(0x8d02,(320).to_bytes(2,'little'));f.m.load(0x8d04,start.to_bytes(3,'little'));f.m.load(0x8d0a,min(start+3,len(data)).to_bytes(3,'little'))
   if poison:f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])&~32,1)
   f.m.write(0x9135,20);f.m.write(0x9136,0);reu=f.reu();canonical=f.canonical();frame=f.read(G,192);counts={20:0,26:0,39:0};initial_instructions=f.m.regs().instructions;initial_dma=f.get('se_reu_dma_calls',2);initial_loads=f.get('se_overlay_loads',2);trace.clear();returns=0;begins=0;backups=[]
   rr=invoke(20,1,0);counts[20]+=1
   for _ in range(20000):
    assert not rr.p&1,(start,cached,poison,rr.a,counts)
    if rr.a==0:break
    ident=f.m.read(0x9135);op=f.m.read(0x9136);assert ident in counts,(ident,op);counts[ident]+=1
    if ident==39 and op==0:
     assert f.m.read(G+167)==1 and not f.get('se_doc_read_locks',1) and not f.m.read(0x912d)
     backups.append(f.read(0x45e6,0x800-0x5e6));begins+=1
    if ident==20 and f.m.read(G+167)==1:
     returns+=1;assert not f.get('se_doc_read_locks',1) and not f.m.read(0x912d)
     if cached and not poison:assert f.read(0x45e6,0x800-0x5e6)==backups[-1],'backuplifetime'
     if change:f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
    rr=invoke(ident,1,op)
    if change and returns:
     assert rr.p&1 and rr.a==0x74 and not f.get('se_doc_read_locks',1);source_cases.append({'fault':'sourcechangebetweenENDandactualC20restore','error':rr.a});return
   else:raise AssertionError('sourceroundtripstuck')
   assert not rr.p&1 and rr.a==0 and f.m.read(0x8d20)==2 and not f.get('se_doc_read_locks',1) and not f.m.read(0x912d) and not f.m.read(G+167)
   elapsed=f.m.regs().instructions-initial_instructions;dma_calls=(f.get('se_reu_dma_calls',2)-initial_dma)&65535;loads=(f.get('se_overlay_loads',2)-initial_loads)&65535
   assert sum(trace.metric(0,i)for i in range(256)if i!=14)==0
   assert sum(trace.metric(1,i)for i in range(256)if i not in(20,26,39))==0
   begin=int.from_bytes(frame[9:12],'little');body=int.from_bytes(frame[15:18],'little');end=int.from_bytes(frame[12:15],'little');styles=bytearray(len(data));exclusive=bytearray(len(data))
   for kind,style,width,a,b in inline(data[body:end],start=body,body_column=body-begin if body>begin else None):
    if kind!=1:continue
    for pos in range(a+width,b):
     if style==4:styles[pos]=0;exclusive[pos]=1
     elif not exclusive[pos]:styles[pos]|=((style&2)>>1)|((style&1)<<1)
   adv=[widths[native(c)]+(styles[i]&1)+(styles[i]&2)for i,c in enumerate(data)]
   want=line_oracle.oracle(data,adv,start,320,0,0,min(start+3,len(data)),0)
   gl=f.read(0x8d00,832);get=lambda at,n=3:int.from_bytes(gl[at:at+n],'little')
   for at,key,size in [(33,'reason',1),(35,'x',3),(41,'end',3),(44,'next',3),(47,'first',3)]:assert get(at,size)==want[key],('geometry',at,get(at,size),want[key],counts)
   count=get(50,2);maps=[get(176+i*2,2)for i in range(count+1)];assert maps==want['maps'],('maps',maps,want['maps'])
   assert f.reu()==reu and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
   if cached:assert (counts[39]>0)==bool(has_inline) and begins==returns
   if cached and not poison:assert counts[26]==0
   if poison:assert counts[26]>0
   source_cases.append({'source_bytes':len(data),'start':start,'cached':cached,'poison':poison,'pending':pending,'counts':counts,'map_cells':count,'end':want['end'],'source_begin_returns':returns,'hint':has_inline,'instructions':elapsed,'dma_calls':dma_calls,'overlay_loads':loads,'r14_ops':{str(i):trace.metric(2,i) for i in range(3)}})
  samples=[sem.geos.native_text('Ordinary short prose.\rNext.'),sem.geos.native_text('*a* tail\rNext.'),sem.geos.native_text('Hi **b**.\rNext.'),sem.geos.native_text('Word **'+('Wim '*240)+'nested *italic* end** tail\rnext'),sem.geos.native_text('**bold *em* tail** and @@code@@ end.\rnext'),sem.geos.native_text('# Heading **title** *em*\rnext'),sem.geos.native_text('A **'+('Wim '*50)+'nested *italic* end** tail\rnext')]
  for data in samples:
   line(data,cached=False);line(data,cached=True)
  line(samples[3],start=100,cached=False);line(samples[3],start=100,cached=True);line(samples[4],cached=True,pending=True);line(samples[4],cached=True,poison=True);line(samples[4],cached=True,change=True)
  result['status']='PASS';result['scope']='Private actual C20 SOURCE continuation with sequential REQUEST/OP C39/C26 frontend; independent geometry and full16MiB/canonical/shim guards; not resident/public/native integration'
  result['source_cases']=source_cases
  result['source_adapter_bytes']=len(consumer)-HEADER
  result['hint_bytes']=len(hint_image)-HEADER
  result['wholeRAM_calls']=calls
'''

def run(out):
 text=(ROOT/'tests/test_cache_inline.py').read_text()
 # Use onlyitsbuilder/driver generation, replacingextra componentmatrixwithsource.
 ns=dict(vars(component));ns['__file__']=str(ROOT/'tests/test_cache_inline.py');ns['INLINE']=SOURCE
 code=inspect.getsource(component.run)
 code=code.replace("consumer=make_inline(out/'inline',frozen)","consumer=make_inline(out/'inline',frozen);source_control,source_candidate=make_source(out/'source',frozen);hint_image=make_hint(out/'hint',frozen)")
 code=code.replace("'if ident in(35,36):'","'if ident in(20,26,35,37,39):'")
 code=code.replace("for im in(writer,semantic,image,consumer):imp(im)","for im in(writer,semantic,image,consumer,hint_image):imp(im)")
 code=code.replace("   if ident==36:","   if ident in(20,26,39):")
 code=code.replace("('se_crc_value',2)","('text_ptr',2),('screen_ptr',2),('se_crc_value',2)")
 code=code.replace("(0x8f36,0x8fec)]", "(0x8f36,0x8fec),(0x8d00,0x9134),(0x4400,0x4800),(0x8c00,0x8d00),(0x8000,0x8080),(0x8400,0x8480),(0x9135,0x9137)]")
 code=code.replace("'make_inline':build_inline", "'make_inline':build_adapter,'make_source':source_images,'make_hint':build_hint")
 ns.update(build_adapter=build_adapter,source_images=source_images,build_hint=build_hint)
 code=code.replace("(out/'generated-verifier.py').write_text(text)","text=text.replace(\"for im in(writer,semantic,image,consumer):imp(im)\",\"for im in(writer,semantic,image,consumer,hint_image):imp(im)\");text=text.replace(\"('se_crc_value',2)\",\"('text_ptr',2),('screen_ptr',2),('se_crc_value',2)\");text=text.replace(\"r=f.call('se_overlay_import');assert not r.p&1\",\"r=f.call('se_overlay_import');assert not r.p&1,(r.a,im[:36].hex())\");(out/'generated-verifier.py').write_text(text)")
 (out/'generator.py').write_text(code);exec(compile(code,str(out/'generator.py'),'exec'),ns);ns['run'](out)

if __name__=='__main__':
 out=ROOT/'build/cache-inline-source'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
