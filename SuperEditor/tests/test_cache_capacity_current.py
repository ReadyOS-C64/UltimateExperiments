"""Bounded current54 large-source/reduced-REU acceptance, CPU only.

70,002 canonical bytes, including one70,000-byte logical line; actual two-bank
quota in16 physical banks. Public40/60/80/GEOS render/navigation/edit/Undo.
The initial source import is the released fixture seam, not native File/Open.
No shared build, overlay replacement or emitted layout in expected pixels.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,zipfile
import test_plain_geos as plain
import test_lifecycle_cache_current as cache
geos=plain.geos;ROOT=geos.ROOT
BASE=ROOT/'build/cache-editor-product/20261026T035310363807Z/fixture'


class Fixture(geos.Fixture):
 def __init__(self,*args):self.service_costs={};super().__init__(*args)
 def call(self,name,a=0):
  key=None
  if name=='se_editor_service':
   job=self.get('se_e_job',1);key=(job,self.m.read(0x9135)if job==11 else 0)
  start=self.total_instructions;regs=super().call(name,a)
  if key:self.service_costs[key]=self.service_costs.get(key,0)+self.total_instructions-start
  return regs


def run(out,base,physical=16):
 out.mkdir(parents=True);frozen,identity=geos.freeze(out,base)
 assert len(identity['names'])==54 and identity['names'][-1]=='line'
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True)
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 original=geos.native_text('a')*70000+b'\r'+geos.native_text('Z');assert len(original)==70002
 data=original;cases=[];timings=[];baseline=None
 def reu():return f.reu()[:physical*65536]
 def clean():
  assert not any(f.get(n,1)for n in('se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_e_draw_busy'))
  assert f.read(0xc600,1024)==f.shim
 def measured(tag,operation):
  start=f.total_instructions;operation();used=f.total_instructions-start
  timings.append(dict(tag=tag,instructions=used,max_service=f.max_service));print('COST',timings[-1],flush=True)
 def frame(tag):
  nonlocal baseline
  prior_costs=dict(f.service_costs)
  canonical=f.canonical();catalog=f.catalog();before=reu();owners=f.read(f.s['se_reu_physical_owner'],physical);start=f.total_instructions
  f.render();render_used=f.total_instructions-start
  costs={str(job)+':'+str(request):used-prior_costs.get((job,request),0)for (job,request),used in f.service_costs.items()if used!=prior_costs.get((job,request),0)}
  baseline_used=costs.get('11:34',0)
  clean();guard_start=f.total_instructions
  assert f.merged()==data and f.canonical()==canonical and f.catalog()==catalog
  source_guard_used=f.total_instructions-guard_start
  mode=f.get('se_mode',1)
  if mode==3:
   bits,attrs,rows=plain.expected(f,data,fonts,f.get('se_render_caps',1))
   assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent GEOS pixels')
   raw,_=f.raw_cache();assert raw[0]==1 and raw[1]==len(rows)
   for i,row in enumerate(rows):
    p=raw[0x200+i*0x800:0x220+i*0x800]
    assert tuple(int.from_bytes(p[j:j+3],'little')for j in(0,3,6))==(row.start,row.end,row.next),(tag,'24bit row anchors',i)
   assert f.get('se_v_bottom')==rows[-1].next
   geos.png(bits,attrs,out/(tag+'.png'))
  else:
   (bits,attrs),anchors,_,_=geos.grid.expected(f,data)
   assert f.read(0x4000 if mode==0 else 0x6000,len(bits))==bits,(tag,'independent grid pixels')
   assert (bytes(v&15 for v in f.read(0xd800,1000))if mode==0 else f.read(0x4000,1000))==attrs,(tag,'independent grid attrs')
   assert tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little')for i in range(22))==tuple(anchors[:22])
   assert f.get('se_v_bottom')==anchors[-1]
  after=reu();wanted=bytearray(before);spans=[]
  h=f.get('se_gc_handle',1)
  if h:
   b=f.m.read(f.s['se_reu_map']+h);assert b<physical and f.m.read(f.s['se_reu_physical_owner']+b)==f.m.read(f.s['se_reu_logical_owner']+h)==0xfe
   if mode==3:
    ranges=[(0,64),(0x600,0x680),(0xb200,0xd568),(0xe568,0xea88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
   else:ranges=[(0,22*240)]
   for lo,hi in ranges:
    lo+=b*65536;hi+=b*65536;wanted[lo:hi]=after[lo:hi];spans.append((lo,hi))
  # Only initial typed53 allocation may write its new payload. No existing53
  # allowance exists: every later readonlyrender must preserve it exactly.
  for b in range(physical):
   now=f.m.read(f.s['se_reu_physical_owner']+b)
   if owners[b]==0 and now==0x53:
    proof,payload=cache.cache_frame(f.s,f.read(0,65536),f.reu(),frozen/'build/overlays')
    assert proof['merged_length']==len(data);baseline=proof
    wanted[b*65536:(b+1)*65536]=after[b*65536:(b+1)*65536]
  assert after==wanted,(tag,'actual REU outside precise FE/newtyped53 spans')
  case=dict(tag=tag,mode=mode,source_bytes=len(data),caret=f.get('se_hot_caret'),top=f.get('se_v_top'),bottom=f.get('se_v_bottom'),render_instructions=render_used,baseline_C34_service_instructions=baseline_used,other_render_instructions=render_used-baseline_used,actual_service_request_costs=costs,source_verification_instructions=source_guard_used,physical_banks=physical,allocated_bank_checkpoint=sum(2<=v<255 for v in f.read(f.s['se_reu_physical_owner'],physical)),live_object_checkpoint=sum(bool(v)for v in f.read(f.s['object_owner'],8)),readonly_spans=spans)
  cases.append(case);print('PASS',case,flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
 try:
  measured('initial-source-import-cold40',lambda:f.source(data,banks=2,physical=physical));assert f.get('se_doc_length')==70002
  # Render all source geometries atBOF. The huge paragraph has no inline/code
  # markers, but baseline must retain exact24bit CR boundaries rather than wrap.
  for command in(96,97,98,99):
   measured('mode-'+str(command),lambda c=command:f.command(c));frame('BOF-mode'+str(command-96))
  assert baseline and baseline['merged_length']==70002 and baseline['records']>=2
  # Public BOTTOM performs real navigation; no host TOP/caret/FE seeding.
  measured('return40-before-far-nav',lambda:f.command(96))
  measured('public-BOTTOM',lambda:f.command(35));assert f.get('se_hot_caret')==70002
  frame('far-40')
  for command in(97,98,99):
   measured('far-mode-'+str(command),lambda c=command:f.command(c));frame('far-mode'+str(command-96))
  q=geos.native_text('Q');at=f.get('se_hot_caret');assert at==70002
  measured('far-public-Q-input',lambda:f.key(q[0]));data=data+q;assert f.merged()==data;frame('far-pending-Q')
  measured('far-public-Undo',lambda:f.command(16));data=original;assert f.merged()==data;frame('far-Undo')
  result=dict(status='passed',identity=identity,physical_banks=physical,actual_REU_bytes=physical*65536,document_quota=131072,source_bytes=70002,longest_logical_body=70000,baseline=baseline,cases=cases,cost_intervals=timings,scope=__doc__,verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except Exception as exc:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(exc),cases=cases,cost_intervals=timings,job=f.get('se_e_job',1),state=f.debug()),indent=2)+'\n');(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(reu());raise
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--banks',type=int,choices=[16,32],default=16);a=p.parse_args()
 out=ROOT/'build/cache-capacity-current'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.banks)
