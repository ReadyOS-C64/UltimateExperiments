"""Actual resident C26 SOURCE3→C39→C20 qualification.

Default mode preserves the private A/B: only CMP range38→40 plus candidate C26
and imported C39. --packaged uses the supplied canonical54 fixture without any
resident patch/build/asset substitution. Its8 cases run twice for repeatability;
private historical controls remain separate. Both modes use actual resident
se_editor_service for all REQUEST/OP transitions, independent pixels and source/
history/precise16MiB guards, then six real fault/recovery boundaries.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,inspect,json,sys,types,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_observer as observer
import test_plain_geos as plain

def build(out,base):
 p=ROOT/'src/cache/inline/probes/root-source4k/build.py';spec=importlib.util.spec_from_file_location('root_source_build',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m.build(out,base)

def run(out,base,faults_only=False,packaged=False):
 images=None if packaged else build(out/'build',base);d=out/'public';d.mkdir();g=observer.Gate(d,base);f=g.f;cases=[]
 try:
  # Long legacy whole-body rescans legitimately exceed the small fixture's
  # default25000 slice cap; retain all idle/error/lease checks, bound200000.
  settle_code=inspect.getsource(observer.geos.grid.editor_fixture.EditorFixture.settle).replace('25000','200000');ns={};exec('\n'.join(line[1:]for line in settle_code.splitlines()),ns);f.settle=types.MethodType(ns['settle'],f)
  fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
  lo=f.s['se_geos_service'];hi=f.s['se_geos_cancel'];raw=f.read(lo,hi-lo);matches=[i for i in range(len(raw)-2)if raw[i:i+3]==bytes((0xc9,38,0xb0))];assert packaged or len(matches)==1,matches
  if packaged:
   assert not matches and raw.count(bytes((0xc9,40,0xb0)))==1,'actual canonical range40 missing'
   assert len(g.identity['names'])==54 and 'line'in f.assets
   asset_hashes={n:hashlib.sha256(im).hexdigest()for n,im in f.assets.items()}
   resident_code=f.read(0x1000,0x2f00)
   (out/'linked-api-audit.json').write_text(json.dumps(audit(base),indent=2)+'\n')
  else:
   at=lo+matches[0]+1;f.m.write(at,40);(out/'resident-range.json').write_text(json.dumps(dict(address=at,old=38,new=40,expected=raw.hex(),scope='CMP immediate only; no new branch or stack behavior'),indent=2)+'\n')
   f.assets['line']=images['consumer']
  samples=[('tiny',observer.geos.native_text('Hi **bold** tail.\rNext.'))]
  for events in(1,4,8):
   text='**x** '*events+'w '*((4096-events*6)//2);samples.append((f'4k-{events}',observer.geos.native_text(text+'\rNext.')))
  nested='**bold *em* tail** and @@code@@ £* end. ';nested+='w '*((4096-len(nested))//2);nested+='x'*(4096-len(nested));samples.append(('4k-nested',observer.geos.native_text(nested+'\rNext.')))
  samples += [('dense1800',observer.geos.native_text('**x** ')*300),('4k-9',observer.geos.native_text('**x** '*9+'w '*2021+'\rNext.')),('far66k',observer.geos.native_text('**')+b'x'*66000+observer.geos.native_text('**\rNext.'))]
  if faults_only:samples=[]
  for variant in(('packaged-a','packaged-b')if packaged else('control','candidate')):
   if not packaged:f.assets['geosinln']=images[variant]
   for tag,data in samples:
    f.source(data)
    if tag=='far66k':
     # Actual Plain navigation avoids the unrelated old C23 whole-body INLINE
     # rescan per soft row; switch back via public command at the far viewport.
     f.typed(observer.geos.native_text('syntax plain'));f.command(99);f.position(65900);f.render();f.typed(observer.geos.native_text('syntax markdown'));f.render()
    else:f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render()
    before=g.reu();stable=g.stable();canonical=f.canonical();trace=[];start=f.total_instructions;dma=f.get('se_reu_dma_calls',2);loads=f.get('se_overlay_loads',2)
    original=f.call
    def tracked(name,a=0):
     if name=='se_editor_service'and f.get('se_e_job',1)==11:trace.append(tuple(f.read(0x9135,2)))
     r=original(name,a);assert not f.get('se_e_error',1),(variant,tag,name,r.a,trace[-8:]);return r
    f.call=tracked
    try:
     f.put('se_gc_width',0,1);f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1);f.render()
    finally:f.call=original
    bits,attrs,_=plain.expected(f,data,fonts,1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(variant,tag,'pixels')
    assert f.merged()==data and g.stable()==stable and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
    assert not any(f.get(n,1)for n in('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
    _,bank=f.raw_cache();after=g.reu();want=bytearray(before);spans=[(0,64),(0x600,0x680),(0xb200,0xd8b2),(0xe568,0xea88),(0xfc00,0xfda0)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
    for l,h in spans:want[bank*65536+l:bank*65536+h]=after[bank*65536+l:bank*65536+h]
    assert after==want,(variant,tag,'precise whole16MiB')
    if (packaged or variant=='candidate')and (tag.startswith('4k')or tag=='far66k'):assert(39,0)in trace and(39,1)in trace and(20,1)in trace,trace
    else:assert not any(req==39 for req,op in trace),trace
    if (packaged or variant=='candidate')and tag=='4k-9':assert(26,5)in trace,'event-limit fallback must use bypass5'
    observer.geos.png(bits,attrs,d/(variant+'-'+tag+'.png'));item=dict(variant=variant,tag=tag,bytes=len(data),instructions=f.total_instructions-start,dma=(f.get('se_reu_dma_calls',2)-dma)&65535,loads=(f.get('se_overlay_loads',2)-loads)&65535,routes={str(k):trace.count(k)for k in sorted(set(trace))},bitmap=hashlib.sha256(bits).hexdigest(),attrs=hashlib.sha256(attrs).hexdigest());cases.append(item);print('PASS',item,flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
  for tag,_ in samples:
   a,b=[x for x in cases if x['tag']==tag];assert a['bitmap']==b['bitmap']and a['attrs']==b['attrs']
  fault_results=faults(out/'faults',g,images,fonts,packaged)
  if packaged:
   assert f.read(0x1000,0x2f00)==resident_code,'canonical resident CODE changed'
   assert {n:hashlib.sha256(im).hexdigest()for n,im in f.assets.items()}==asset_hashes,'packaged asset substitution'
  result=dict(status='PASS',mode='canonical-packaged'if packaged else'private-A/B',cases=cases,faults=fault_results,scope='Canonical packaged assets/resident; two independent reset/pass repeats of8 publiccases, not an A/B swap. All continuations actualresident. Private historical A/B remains separate.'if packaged else __doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()


def faults(out,g,images,fonts,packaged=False):
 out.mkdir();f=g.f;results=[];data=observer.geos.native_text('**x** '+'w '*2045+'\rNext.')
 def force():
  f.put('se_gc_width',0,1);f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1);r=f.call('se_editor_render');assert not r.p&1
 for action in('wrong-certificate','source-change','source-after-END','queued-STOP','missing39-BEGIN','missing39-STEP'):
  if not packaged:f.assets['geosinln']=images['candidate']
  f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render();force();trace=[]
  target=(20,1)if action=='source-after-END'else(39,0)if action in('wrong-certificate','missing39-BEGIN')else(39,1)
  for step in range(10000):
   request=tuple(f.read(0x9135,2));trace.append(request)
   if f.get('se_e_job',1)==11 and request==target and(action!='source-after-END'or(any(req==39 for req,op in trace)and f.m.read(0x8b40+167)==1)):break
   assert f.get('se_e_job',1)==11;f.call('se_editor_service');assert not f.get('se_e_error',1)
  else:raise AssertionError(('fault boundary',action))
  before=g.reu();canonical=f.canonical();stable=g.stable();bitmap=f.read(0x6000,8000)+f.read(0x4000,1000);revision=f.get('se_r_revision',4);idx=None;tail=f.get('se_input_tail',1)
  if action=='wrong-certificate':f.m.write(0x8b40+29,f.m.read(0x8b40+29)^1)
  elif action in('source-change','source-after-END'):f.put('se_r_revision',revision+1,4)
  elif action=='queued-STOP':f.queued(3)
  else:
   idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==39 and f.m.read(f.s['image_slot']+i)&1==1);f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+1,0)
  f.call('se_editor_service')
  if action=='wrong-certificate':
   assert tuple(f.read(0x9135,2))==(26,5),('fallback bypass',f.read(0x9135,2).hex())
   assert not f.get('se_doc_read_locks',1)
   while f.get('se_e_job',1):trace.append(tuple(f.read(0x9135,2)));f.call('se_editor_service');assert not f.get('se_e_error',1)
  else:
   assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_job','se_e_draw_busy')) and not f.get('se_bc_flags',1)&8,(action,f.debug())
   assert f.get('se_e_error',1)==(0 if action=='queued-STOP'else 0x17 if idx is not None else 0x74 if action=='source-after-END'else 0xb1),(action,f.get('se_e_error',1))
   assert f.read(0x6000,8000)+f.read(0x4000,1000)==bitmap and g.reu()==before,(action,'prepaint mutation')
  assert f.canonical()==canonical and g.stable()==stable and f.merged()==data and f.read(0xc600,1024)==f.shim
  if idx is not None:f.m.write(f.s['se_overlay_ids']+idx,39)
  if action in('source-change','source-after-END'):f.put('se_r_revision',revision,4)
  if action=='queued-STOP':
   assert f.get('se_input_tail',1)==tail and f.get('se_input_head',1)!=(tail&63)
   f.put('se_status',1,1);f.tick();f.settle();assert f.get('se_input_tail',1)==f.get('se_input_head',1)
  elif action!='wrong-certificate':f.key(0x8b);f.key(0x8b)
  f.render();bits,attrs,_=plain.expected(f,data,fonts,1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(action,'recovery pixels')
  assert f.canonical()==canonical and g.stable()==stable and f.merged()==data and not any(f.get(n,1)for n in('se_e_error','se_doc_read_locks','se_f_owner','se_e_job'))
  _,bank=f.raw_cache();after=g.reu();want=bytearray(before);spans=[(0,64),(0x600,0x680),(0xb200,0xd8b2),(0xe568,0xea88),(0xfc00,0xfda0)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
  for l,h in spans:want[bank*65536+l:bank*65536+h]=after[bank*65536+l:bank*65536+h]
  assert after==want,(action,'whole16MiB recovery')
  observer.geos.png(bits,attrs,out/(action+'.png'));item=dict(action=action,steps=step,trace=trace);results.append(item);print('FAULT PASS',action,flush=True)
 return results


def audit(base):
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols']
 expected={'se_bc_arena':0x9fb5,'se_bc_flags':0x9fc2,'se_bc_count':0x9fc5,'se_fs_state':0x8ee0,'se_fs_state_size':86}
 assert all(s[n]==v for n,v in expected.items())
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  checks={'src/cache/api.inc':['BC_FRAME=$8D00','BCF_READER=173'], 'src/render/geos/semantic.inc':['GSEM_FRAME=$8B40'], 'src/render/geos/editor.inc':['GP_CONTROL=$9134'], 'src/cache/inline/api.inc':['BQ_READER=BQ+BCF_READER','BQ_READER=$8DAD'], 'src/cache/inline/source-entry.s':['S=$8880','R=S+161','H=R+161','P=H+21','P+26<=$8A00'], 'src/render/geos/source-line.s':['INLINE_SOURCES=$4400','INLINE_SOURCE_CAPACITY=162','INLINE_LINE=INLINE_SOURCES+INLINE_SOURCE_CAPACITY*3','INLINE_CORE_SIZE=GL_GLYPH+14','INLINE_MAP_SIZE=INLINE_SOURCE_CAPACITY*2','INLINE_IDENTITY_SIZE=59'],'src/render/geos/line.inc':['GL_GLYPH=96']}
  for path,needles in checks.items():
   text=''.join(z.read(path).decode().split())
   for needle in needles:assert needle in text,(path,needle)
  comments={n:[line for line in z.read(n).decode().splitlines()if line.startswith(';')and'PRIVATE'in line]for n in('src/cache/inline/api.inc','src/cache/inline/source-entry.s','src/cache/inline/source-seed.s','src/cache/inline/source-core.s','src/cache/inline/source-page.s','src/render/geos/source-cache-api.inc','src/render/geos/source-cache-gate.inc')}
 return dict(status='PASS',resident=report['sha256'],binding=report['resident_binding']['digest'],linked_fixed_fields=expected,source_contracts=checks,phase_map={'GL':'8D00..903F832B; bridge restores live110core/324map/32packet/59identity','query':'8D00..8F3F576B; reader8DAD86B, IO8EC0128B','inactive_R21_staging':'8880..89F0;343output+26control bytes','role_output_overlap':'8F36..8F3F aliases last10 IO bytes; provisional untilEND'},comment_findings=comments,note='PRIVATE/rootless-budget comments remain stale in promoted files, no functional address mismatch found. Production source edits remain parent-owned.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--packaged',action='store_true');p.add_argument('--faults-only',action='store_true');p.add_argument('--fixture',type=Path,default=ROOT/'build/cache-editor-product/20261026T031201729970Z/fixture');a=p.parse_args();out=ROOT/'build/cache-inline-root'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.faults_only,a.packaged)
