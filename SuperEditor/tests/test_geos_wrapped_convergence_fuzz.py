"""Actual private48asset logical-line convergence versus forcedfull and host pixels."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,json,sys,random
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_checkpoint_refresh_hook as hook
c=hook.c
DEFAULT=ROOT/'build/geos-wrapped-convergence/20261025T212053359253Z/project'
BASE=ROOT/'build/geos-convergent-line-editor/20261025T211148922415Z/fixture'

def outside(f,before,tag):
 after=f.reu();_,bank=f.raw_cache();allowed=[(0,64),(0x600,0x680),(0xb200,0xd568),(0xe568,0xea88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)];cursor=0
 for a,b in sorted((bank*65536+a,bank*65536+b)for a,b in allowed):assert after[cursor:a]==before[cursor:a],(tag,'foreignREU',cursor,a);cursor=b
 assert after[cursor:]==before[cursor:],(tag,'foreignREUtail')

def run(out,project,smoke=False,start=0):
 frozen,identity=hook.freeze_project(out,project);c.geos.grid.editor_fixture.ROOT=c.geos.grid.cpu_editor.ROOT=frozen;c.geos.grid.editor_fixture.NAMES=c.geos.grid.cpu_editor.NAMES=identity['names'];dll=c.geos.grid.runner(out);f=c.Fixture(out,frozen,dll,True);g=c.Fixture(out,frozen,dll,True);h=c.Fixture(out,frozen,dll,True);h.assets={n:(BASE/'build/overlays'/(n+'.seo')).read_bytes()for n in identity['names']};fonts={n:(frozen/'fonts'/n).read_bytes()for n in c.geos.GEOS_FONTS+('native8.bin',)};cases=[];data=b''
 def profile(x):
  idx=next(i for i in range(x.s['se_overlay_capacity'])if x.m.read(x.s['se_overlay_ids']+i)==21 and x.m.read(x.s['image_slot']+i)&127==0);dll.gm_profile(x.s['se_overlay_active'],idx+1,0,0xa035,0,0,0)
 def clean(x):assert x.read(0xc600,1024)==x.shim and not any(x.get(n,1)for n in ['se_e_error','se_e_job','se_f_owner','se_fs_owned','se_doc_read_locks','se_e_draw_busy']),x.debug()
 def setup(raw,at):
  nonlocal data
  data=c.geos.native_text(raw)if isinstance(raw,str)else raw
  for x in(f,g,h):
   x.source(data);x.command(99)
   if at>65535:
    logical=data.rfind(bytes([13]),0,at)+1;x.position(logical);x.render()
   x.position(at);x.render();clean(x)
  cache,_=f.raw_cache();records=[]
  for i in range(cache[1]):
   r=cache[0x700+i*0x800:0x740+i*0x800]
   if r[0]==0x43 and r[3]==1:assert binascii.crc_hqx(r[:62],65535)==int.from_bytes(r[62:64],'little');records.append((i,r.hex()))
  assert records,('no-real-producer-certificates',cache[0x700:0x740].hex());return records
 def check(tag,key,want_dirty=None):
  nonlocal data
  at=f.get('se_hot_caret');assert g.get('se_hot_caret')==at
  data=data[:at-1]+data[at:]if key==0x14 else data[:at]+bytes([key])+data[at:]
  for x in(f,g,h):x.key(key)
  pre_admission=dict(GEC=f.m.read(0xcfe8),GCC=f.m.read(0xcf90),pending=f.get('se_hot_pending',1),phase=f.get('se_hot_phase',1),TOP=f.get('se_v_top'),caret=f.get('se_hot_caret'))
  results=[]
  for x,forced in[(f,False),(g,True),(h,False)]:
   canonical=x.canonical();catalog=x.catalog();before=x.reu();start=x.total_instructions
   if forced:x.m.write(0xcfe8,0);x.m.write(0xcf90,0)
   profile(x);x.events=[];x.trace=True;x.render();x.trace=False;calls=dll.gm_metric(0);used=x.total_instructions-start;fast=x.m.read(0x9134+20)
   assert x.canonical()==canonical and x.catalog()==catalog and x.merged()==data,(tag,'source/catalog');clean(x);outside(x,before,tag);bits,attrs,rows=c.exact_pixels(x,data,fonts,tag+('-forced'if forced else''));results.append((used,calls,rows,x.events,fast))
  assert f.read(0x6000,8000)==g.read(0x6000,8000)and f.read(0x4000,1000)==g.read(0x4000,1000),(tag,'fullrendererAB')
  dirty=results[0][4]==2
  assert not dirty or results[0][1]<results[1][1],(tag,"dirtystripcalls")
  if want_dirty is not None:assert dirty==want_dirty,(tag,'dirty',dirty,want_dirty,results[0][:2],results[1][:2],results[0][3][:3]+results[0][3][-3:])
  c.geos.png(f.read(0x6000,8000),f.read(0x4000,1000),out/(tag+'.png'));entry=dict(tag=tag,pre_admission=pre_admission,source_bytes=len(data),dirty=dirty,instructions=results[0][0],forced_full_instructions=results[1][0],row_calls=results[0][1],forced_full_row_calls=results[1][1],packaged_baseline_instructions=results[2][0],packaged_baseline_row_calls=results[2][1],queries=results[0][3][:3]+results[0][3][-3:]);cases.append(entry);print('PASS',{k:v for k,v in entry.items()if k!='queries'},flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
 try:
  rng=random.Random(0x6510)
  words=['wide','words','alpha','iiii','MMMM','state','*bold*','**strong**','@code@']
  for i in range(24):
   body=' '.join(rng.choice(words)for _ in range(28+rng.randrange(20)))
   prefix=('#'*(i%6+1)+' Heading ')if i%3==0 else 'Prose '
   raw=prefix+body+'\rNext untouched.\rFinal untouched.\rTail.'
   at=20+rng.randrange(min(110,len(raw)-40))
   if i<start:continue
   setup(raw,at)
   # This changes one ordinary letter, preserving grammar delimiters/carry.
   old=c.semantic.global_rows(data,fonts['bsw9-widths.bin']);new=data[:at]+c.geos.native_text('Q')+data[at:];nextrows=c.semantic.global_rows(new,fonts['bsw9-widths.bin'])
   same=len(old)==len(nextrows)
   check('seeded-'+str(i)+'-insert',c.geos.native_text('Q')[0],None)
   if same:
    last=cases[-1];assert last['dirty']or(last['row_calls']==last['packaged_baseline_row_calls']==0),('expectedwholeparagraphreuse',i,last)
   check('seeded-'+str(i)+'-BACK',0x14,None)
   if same:
    last=cases[-1];assert last['dirty']or(last['row_calls']==last['packaged_baseline_row_calls']==0),('expectedwholeparagraphreuseBACK',i,last)

  result=dict(status='passed',identity=identity,cases=cases,scope='Actualpublickey/render coherent48asset privatecandidate; forcedfullsamecandidate+independentcanonicalpixels/allanchors/bottom, full16MiB outside exactownedspans, nohostworker calls/SEOsubstitutions. CPUinstructions only.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close();g.close();h.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=DEFAULT);p.add_argument('--smoke',action='store_true');p.add_argument('--start',type=int,default=0);a=p.parse_args();out=ROOT/'build/geos-wrapped-convergence-fuzz'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.project.resolve(),a.smoke,a.start);print('RESULT',r['status'],len(r['cases']))
