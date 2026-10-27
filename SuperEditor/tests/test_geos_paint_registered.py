"""Actual cold-registered paint collector: public edits, faults, modal repaint and stack.

Use a frozen current63 fixture; no executable replacement or manual import.
ROM/font transport remains modeled. Native timing is a separate test.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,inspect,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_observer as observer
import test_cache_hotpath_profile as hot
import test_plain_geos as plain
import test_geos_paint_convergence_guards as guards
import font_fixture
ob=observer
native=ob.geos.native_text
data=native('Ordinary words make a continuing paragraph with enough text to wrap. '*6+'\rTail remains.\r')

def run_public(out,base):
 out.mkdir(parents=True);identity=json.loads((base/'freeze.json').read_text());assert len(identity['names'])==63 and identity['names'][-1]=='paint'
 spec=importlib.util.spec_from_file_location('paint63_runner',ROOT/'src/render/geos/paint-convergence-probe/runner.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
 old,freeze=observer.runner,observer.geos.freeze;observer.runner=r.build;observer.geos.freeze=lambda *_:(base,identity);fontroot=font_fixture.ROOT;font_fixture.ROOT=base
 try:g=observer.Gate(out,base)
 finally:observer.runner=old;observer.geos.freeze=freeze
 f=g.f;assert set(f.assets)==set(identity['names']);fonts={n:(base/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)};native=observer.geos.native_text;cases=[]
 points,returns=hot.points(f);g.dll.hp_config(f.s['se_overlay_active'],f.s['se_overlay_frame'],f.s['se_e_draw_sequence'],(C.c_uint16*8)(*points),len(returns),(C.c_uint16*len(returns))(*returns),identity['names'].index('gtype')+1,identity['names'].index('code')+1)
 def pixels(data,caps,tag):
  bits,attrs,rows=plain.expected(f,data,fonts,caps);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels');raw,_=f.raw_cache();assert raw[0]==1 and raw[1]==len(rows)
  for i,row in enumerate(rows):
   p=raw[0x200+i*0x800:0x220+i*0x800];assert tuple(int.from_bytes(p[j:j+3],'little')for j in(0,3,6))==(row.start,row.end,row.next)and(p[14],p[15])==(row.height,row.top)
  assert f.get('se_v_bottom')==rows[-1].next
  observer.geos.png(bits,attrs,out/(tag+'.png'));return hashlib.sha256(bits+attrs).hexdigest()
 try:
  for doc,data in [('prose',native('Ordinary words make a continuing paragraph with enough text to wrap. '*6+'\rTail remains.\r')),('styled',native('Alpha **bold words inside the continuing styled paragraph '*6+'** omega.\rTail remains.\r'))]:
   for preset,caps in [('full',3),('markdown',1)]:
    for action,key in [('insert',native('Q')[0]),('BACK',0x14),('CR',13)]:
     tag=doc+'-'+preset+'-'+action;f.source(data,physical=256);f.typed(native('syntax '+preset));f.command(99);hot.drain(f);f.position(85);f.render();hot.drain(f);f.typed(native('syntax plain'));hot.drain(f);f.typed(native('syntax '+preset));hot.drain(f);pixels(data,caps,'setup-'+tag)
     cache,_=f.raw_cache();assert cache[0xdd68]==0xa5 and cache[0xdd69]==5
     stable,catalog=g.stable(),f.catalog();before=g.audit_begin();start=f.total_instructions;loads=f.get('se_overlay_loads',2);dc=f.get('se_reu_dma_calls',2);db=f.get('se_reu_dma_bytes',3);g.dll.hp_begin(f.get('se_e_draw_sequence',2));f.key(key);hot.drain(f);g.dll.hp_end();used=f.total_instructions-start;g.audit_end(before,tag)
     result=data[:84]+data[85:]if action=='BACK'else data[:85]+bytes((key,))+data[85:];assert f.merged()==result and g.stable()==stable and f.catalog()==catalog
     assert not any(f.get(n,1)for n in('se_e_job','se_e_error','se_f_owner','se_doc_read_locks','se_e_draw_busy','se_e_redraw'))
     if action=='CR':assert f.m.read(0x914a)!=0xa7
     else:assert f.m.read(0x914a)==0xa7
     h=pixels(result,caps,tag);item=dict(tag=tag,instructions=used,first=int(g.dll.hp_get(0,1)),loads=(f.get('se_overlay_loads',2)-loads)&65535,DMA_calls=(f.get('se_reu_dma_calls',2)-dc)&65535,DMA_bytes=(f.get('se_reu_dma_bytes',3)-db)&0xffffff,pixels=h,CV=f.read(0x9149,47).hex());cases.append(item);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n');print('PASS',tag,used,flush=True)
     f.command(16);hot.drain(f);assert f.merged()==data;pixels(data,caps,tag+'-undo')
  result=dict(status='PASS',identity=identity,cases=cases,scope=__doc__,guards='Actual packaged63, no executable replacements/manual import; independent bitmap/attrs/maps, canonical/history/clipboard/catalog/shim and whole16MiB outside exact checked DMA write masks. Explicit source-reset+ROM font/SEQ seams; no native timing.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close();font_fixture.ROOT=fontroot

def run_guards(out,fixture):
 identity=json.loads((fixture/'freeze.json').read_text());assert len(identity['names'])==63 and identity['names'][-1]=='paint'
 cpu=guards.observer.geos.grid.cpu_editor;old=cpu.startup;records=[];fontroot=font_fixture.ROOT;font_fixture.ROOT=fixture
 def startup(m,s,assets,banks=256):
  before=bytes(m.read(0xc600+i)for i in range(1024));imports=old(m,s,assets,banks)
  assert imports==identity['names']and set(assets)==set(imports)
  assert bytes(m.read(0xc600+i)for i in range(1024))==before
  assert m.read(s['se_overlay_ids']+62)==63 and m.read(s['image_slot']+62)&1==0
  assert s['se_overlay_capacity']==64 and sum(bool(m.read(s['se_overlay_ids']+i))for i in range(64))==63
  assert s['se_overlay_asset_count']==4 # exported constant is bank count, not occupied entries
  assert m.read(s['se_gf_state'])==0xa5 and not m.read(s['se_gf_state']+5)and not m.read(s['se_gf_state']+6)
  records.append(dict(imports=imports,overlay_count=63,shim_preserved=True,font_ready=165,scope='Actual cold filename decoder, startup loop and all63 real overlay_import operations. Host models ROM SEO/font transport only; no extra R63 import.'))
  return imports
 cpu.startup=startup
 text=inspect.getsource(guards.run)
 oldline="f=g.f;f.assets['geospage']=(link/'geospage.seo').read_bytes();f.assets['convergence']=(link/'convergence.seo').read_bytes();native=observer.geos.native_text"
 new="f=g.f;assert set(f.assets)==set(identity['names']);assert f.assets['paint']==(base/'build/overlays/paint.seo').read_bytes();native=observer.geos.native_text"
 assert text.count(oldline)==1;text=text.replace(oldline,new)
 oldhash="{n:hashlib.sha256((link/(n+'.seo')).read_bytes()).hexdigest()for n in('geospage','convergence')}";newhash="{n:hashlib.sha256((base/'build/overlays'/(n+'.seo')).read_bytes()).hexdigest()for n in('geospage','paint')}";assert text.count(oldhash)==1;text=text.replace(oldhash,newhash)
 ns=dict(guards.__dict__);exec(compile(text,str(Path(__file__))+':packaged-source-only','exec'),ns)
 try:result=ns['run'](out,fixture,fixture/'build/overlays')
 finally:cpu.startup=old;font_fixture.ROOT=fontroot
 assert len(records)==1 and len(result['cases'])==17
 result['cold_startup']=records;result['scope']='Real source-integrated packaged63 cold startup plus unchanged17 authority/lifetime groups, actual public source edits/Undo and independent pixels. No executable replacement or manual63rd import. CPU IEC/font transport seams only; no native/cycle claim.';(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS cold63 +17 guard/lifetime groups',flush=True)

def run_modal(base,out,expect_failure):
 out.mkdir();d=json.loads((base/'freeze.json').read_text());save=ob.geos.freeze;fontsroot=font_fixture.ROOT;ob.geos.freeze=lambda *_:(base,d);font_fixture.ROOT=base
 try:g=ob.Gate(out,base)
 finally:ob.geos.freeze=save
 f=g.f;fonts={n:(base/'fonts'/n).read_bytes()for n in ob.geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def modal(text):
  for c in bytes((0x88,))+native(text)+b'\r':
   f.key(c)
   for _ in range(100000):
    if not any(f.get(n,1)for n in('se_e_job','se_e_redraw','se_e_draw_busy','se_f_owner','se_doc_read_locks')):break
    f.tick()
   else:raise AssertionError(('modal pending',text,f.debug()))
   if f.get('se_e_error',1):return f.get('se_e_error',1)
  hot.drain(f);return 0
 def pixels(tag):
  mode=f.get('se_mode',1);caps=f.get('se_render_caps',1)
  if mode==3:bits,attrs,rows=plain.expected(f,data,fonts,caps)
  else:(bits,attrs),_,_,_=ob.geos.grid.expected(f,data);rows=None
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels/attrs')
  if rows:
   raw,_=f.raw_cache();assert(raw[0],raw[1])==(1,len(rows))
   for i,r in enumerate(rows):
    p=raw[0x200+0x800*i:0x220+0x800*i];assert tuple(int.from_bytes(p[j:j+3],'little')for j in(0,3,6))==(r.start,r.end,r.next)and(p[14],p[15])==(r.height,r.top)
   assert raw[0xdd68:0xdd6a]==bytes((0xa5,5));assert f.m.read(0x914b)==raw[1],(tag,'genuine collection before certification')
  ob.geos.png(bits,attrs,out/(tag+'.png'));return hashlib.sha256(bits+attrs).hexdigest()
 try:
  f.source(data,physical=256);assert modal('syntax full')==0 and modal('mode hires')==0
  stable,catalog=g.stable(),f.catalog();assets={n:hashlib.sha256(v).hexdigest()for n,v in f.assets.items()}
  sequence=['top']if expect_failure else['top','top','syntax markdown','top','syntax full','top','mode 80','mode hires','top','goto 2','top','mode 60','mode hires','top']
  for i,command in enumerate(sequence):
   tag=f'{i:02d}-'+command.replace(' ','-');before=g.audit_begin();start=f.total_instructions;loads=f.get('se_overlay_loads',2);error=modal(command);g.audit_end(before,tag)
   phase=f.read(0x9149,47);header=f.read(0x8500,64) # capture before checked document() borrows DOC buffer8500
   assert f.merged()==data and g.stable()==stable and f.catalog()==catalog
   if expect_failure:
    assert error==0xb1 and phase[1]==0xa6 and phase[2]==0 and header[1]==9
    (out/'reproduced-ram.bin').write_bytes(f.read(0,0xd000));case=dict(tag=tag,expected_real_failure=error,CV=phase.hex(),header=header.hex())
   else:
    assert error==0,(tag,error);h=pixels(tag);case=dict(tag=tag,instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,pixels_sha256=h,CV=f.read(0x9149,47).hex())
   cases.append(case);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n');print('PASS',base.name,tag,error,flush=True)
  assert assets=={n:hashlib.sha256(v).hexdigest()for n,v in f.assets.items()}
  result=dict(status='EXPECTED_B1_REPRODUCED'if expect_failure else'PASS',cases=cases,fixture=str(base),source_sha256=hashlib.sha256(data).hexdigest(),scope=__doc__,guards='Actual packaged assets unchanged, genuine prompt repaint/public commands, independent pixels/map and canonical/history/clip/settings/shim plus whole16MiB outside precise observed typedDMA writes; no host source/key/valid/PC seed.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close();font_fixture.ROOT=fontsroot

def run_stack(out,fixture,project):
 context=out.with_name(out.name+'-context');context.mkdir(parents=True);source=project/'src/cache/lexical-registration-probe/stack-run.py';spec=importlib.util.spec_from_file_location('paint63_stack',source);r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
 text=inspect.getsource(r.m.stage_proof);needle="59:['code','clex','type','grid','hotcold','fold','sema','inln','page','line','edit','tail','lex','ical','ctrl']";assert text.count(needle)==1
 tail=['code','clex','type','grid','hotcold','fold','sema','inln','page','line','edit','tail','lex','ical','ctrl','row','parse','xform','paint'];text=text.replace(needle,needle+',63:'+repr(tail));(context/'stage63-admission.py').write_text(text);ns=dict(r.m.__dict__);exec(compile(text,str(context/'stage63-admission.py'),'exec'),ns);r.m.stage_proof=ns['stage_proof']
 text=inspect.getsource(r.m.original.foreground_proof);old="[(0xb000,image[36:])],Ccall)";new="[(0xb000,image[36:])]+([(0xa000,images['geostail'][36:])]if name=='grid'else[]),Ccall)";assert text.count(old)==1;text=text.replace(old,new);(context/'foreground63.py').write_text(text);ns=dict(r.m.original.__dict__);exec(compile(text,str(context/'foreground63.py'),'exec'),ns);r.m.original.foreground_proof=ns['foreground_proof']
 result=r.run(out,fixture,project);assert result['foreground']['assets']==63
 names={x['name']for x in result['foreground']['results']};assert {'R:row','C:parse','R:xform','R:paint','C:geospage'}<=names
 result.pop('scope59',None);result['scope63']='Actual source-integrated cold63 resident/all63 images decoded, including R63 and changed C21. Original stack/nesting/unknown-edge rules retained. No native absolute SP claim.';(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print({k:result['foreground'][k]for k in('assets','R','C','foreground_beyond_entry_idle','relative_combined')},flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--gate',choices=('all','public','guards','modal','stack'),default='all');a=p.parse_args();f=a.fixture.resolve();out=a.out.resolve();out.mkdir(parents=True)
 for gate in ('public','guards','modal','stack'):
  if a.gate not in ('all',gate):continue
  if gate=='public':run_public(out/'public12',f)
  elif gate=='guards':run_guards(out/'guards17',f)
  elif gate=='modal':run_modal(f,out/'modal14',False)
  else:run_stack(out/'stack63',f,a.project.resolve())
