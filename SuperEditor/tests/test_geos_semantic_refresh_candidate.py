"""Private late-refresh authority proof. No resident publication hook installed."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_consumer as c
from test_geos_semantic_refresh_profile import F
D=ROOT/'src/render/geos/semantic-refresh-candidate'

def run(out,base,smoke=False,aux=False):
 spec=importlib.util.spec_from_file_location('rekey_build',D/('build-aux.py' if aux else 'build.py'));b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budget=b.build(out/'link',base)
 spec=importlib.util.spec_from_file_location('consumer_build',c.D/'build.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);copy=out/'consumer-input';shutil.copytree(c.D,copy);pub=(copy/'publish.inc').read_text();needle='@invalidate_previous:\n lda #0\n jsr gsc_valid_write';assert needle in pub;pub=pub.replace(needle,'@invalidate_previous:\n lda se_v_top\n ora se_v_top+1\n ora se_v_top+2\n bne @skip\n lda #0\n jsr gsc_valid_write');(copy/'publish.inc').write_text(pub);p.D=copy;budget['consumer']=p.build(out/'consumer-link',base)
 frozen,identity=c.geos.freeze(out,base);c.geos.grid.editor_fixture.ROOT=c.geos.grid.cpu_editor.ROOT=frozen;c.geos.grid.editor_fixture.NAMES=c.geos.grid.cpu_editor.NAMES=identity['names'];dll=c.geos.grid.runner(out);f=c.Fixture(out,frozen,dll,True);f.assets['aux' if aux else 'viewsource']=(out/'link/helper'/('aux.seo' if aux else 'viewsource.seo')).read_bytes();f.assets['geossema']=(out/'consumer-link/seed/geossema.seo').read_bytes();f.assets['geospage']=(out/'consumer-link/producer/geospage.seo').read_bytes();fonts={n:(frozen/'fonts'/n).read_bytes()for n in c.geos.GEOS_FONTS+('native8.bin',)};cases=[];data=b''
 def refresh(want=True):
  before=f.reu();canonical=f.canonical();catalog=f.catalog();cache,bank=f.raw_cache();f.m.write(f.s['se_overlay_frame'],6);r,n=f.fast_call(f.s['se_overlay_call'],a=13 if aux else 14,x=1 if aux else 0);assert not r.p&1 and bool(r.a)==want,('refresh',r.a,want,hex(f.m.regs().pc));after=f.reu();start=bank*65536+0x600;assert before[:start]==after[:start]and before[start+128:]==after[start+128:]and f.canonical()==canonical and f.catalog()==catalog and f.read(0xc600,1024)==f.shim
  assert not any(f.get(x,1)for x in ['se_f_owner','se_doc_read_locks','se_fs_owned'])
  aftercache,_=f.raw_cache()
  if want:
   for offset in([0x600,0x640]if f.get('se_v_top')else[0x600]):
    old=cache[offset:offset+64];new=aftercache[offset:offset+64];assert old[:24]==new[:24]and old[31:62]==new[31:62],('immutable-anchor/carry/TOP',offset)
    assert int.from_bytes(new[24:28],'little')==f.get('se_r_revision',4)and int.from_bytes(new[28:31],'little')==len(data)
  else:assert before==after
  return n
 def setup(far,row):
  nonlocal data
  pre=c.geos.native_text('prefix\r')*(9400 if far else 0);suffix=c.geos.native_text('# Heading words.\rSecond plain row.\rThird plain row.\rTail.');data=pre+suffix;top=len(pre);at=top+[5,22,40][row];f.source(data);f.command(99);f.position(top);f.render();f.position(at);f.render();assert f.get('se_v_top')==top
 try:
  for far in([False]if smoke else[False,True]):
   for row in([1]if smoke else[0,1,2]):
    setup(far,row)
    for serial,key in enumerate([c.geos.native_text('Q')[0],c.geos.native_text('R')[0],0x14,0x14,13]):
     at=f.get('se_hot_caret');data=data[:at-1]+data[at:]if key==0x14 else data[:at]+bytes([key])+data[at:];f.key(key);canonical=f.canonical();before=f.reu();f.events=[];f.trace=True;start=f.total_instructions;f.render();f.trace=False;used=f.total_instructions-start;c.exact_pixels(f,data,fonts,'refresh');assert f.merged()==data and f.canonical()==canonical;c.outside_cache(f,before,'refresh');extra=refresh();entry=dict(far=far,row=row,serial=serial,key=key,render_instructions=used,refresh_instructions=extra,max_READS=max([e['READS']for e in f.events]or[0]),hit=any(e['op']==3 and e['proof']in(1,2)for e in f.events));cases.append(entry);print('PASS',entry,flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
  result=dict(status='passed',variant='AUX'if aux else'R14-oversized',budget=budget,identity=identity,cases=cases,scope='Actualpublicedit/render then explicitlyseparate checked R14op6; no residenthook, not integratednativeperf. Allsource/pixels/anchors and full16MiB guarded; anchors/carry/TOP unchanged. Placement records exact compiledbudget; standaloneR14variant overflowscombinedSP2, AUXvariantusesexistingC13andactualnestedR14begin. No publicationhookinstalled.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=c.BASE);p.add_argument('--smoke',action='store_true');p.add_argument('--aux',action='store_true');a=p.parse_args();out=ROOT/'build/geos-semantic-refresh-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture.resolve(),a.smoke,a.aux);print('RESULT',r['status'],'cases',len(r['cases']))
