"""Current48 reduced-REU pressure with retainedFC and real C33 witnesses.

The existing capacity_lifecycle workload/guards remain verbatim; one explicit
post-FC-preparation hook adds actual60/80 fast-root/pixel/typed-FE checks. All file
transport is the existing modeledKERNAL seam, not native IEC. No product edits.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,textwrap,zipfile
import test_capacity_lifecycle as parent
import test_geos_fold_editor as fold
ROOT=parent.ROOT

def extra(f,data,out,physical,checks):
 tree=fold.tree(data);tree,_=fold.action_model(tree,3,0,0,0,0)
 for width,mode in [(60,97),(80,98)]:
  f.command(mode);f.position(3);f.render();f.finish_style();f.command(2)
  canonical=f.canonical();before=f.reu();phase=f.read(0x8d00,1152);loads=f.get('se_overlay_loads',2);start=f.total_instructions;r=f.render();count=f.total_instructions-start
  assert not r.p&1 and r.a==0 and f.read(0x89c0,1)==b'\1',(physical,width,'actualTRY')
  assert f.canonical()==canonical and f.merged()==data and f.read(0x8d00,1152)==phase and f.read(0xc600,1024)==f.shim
  expected=fold.projection.expected(f,data,tree,f.get('se_v_top'));bits,attrs=expected[0]
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(physical,width,'independent fullpixels')
  h=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+h);assert h and bank and f.m.read(f.s['se_reu_logical_owner']+h)==f.m.read(f.s['se_reu_physical_owner']+bank)==0xfe
  at=bank*65536;now=f.reu();assert now[:at]==before[:at] and now[at+0x1600:]==before[at+0x1600:],(physical,width,'wholeactualREU outside exactrow/headercache')
  fold.geos.png(bits,attrs,out/f'{width}-with-retained-FC.png');item=dict(tag=f'{width}-actualC33-with-retainedFC',physical_banks=physical,instructions=count,loads=(f.get('se_overlay_loads',2)-loads)&65535,source_bytes=len(data),pixel_count=64000,attributes=1000);checks.append(item);print('PASS',item,flush=True)

source=textwrap.dedent(inspect.getsource(parent.run));needle="  # Real save and staged open coexist with the retained snapshot capability.\n";assert source.count(needle)==1;source=source.replace(needle,"  extra(f,data,out,physical,checks)\n"+needle);namespace=dict(parent.__dict__,extra=extra);exec(compile(source,__file__+'::existing-workload-plus-explicit-FE-hook','exec'),namespace)

def run(out,base,banks):
 identity=json.loads((base/'freeze.json').read_text());assert len(identity['names'])==48 and identity['names'][-1]=='grid'
 out.mkdir(parents=True);(out/'expanded-workload.py').write_text(source)
 with zipfile.ZipFile(out/'verifier-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 namespace['run'](out,base,banks)
 result=json.loads((out/'result.json').read_text());result['explicit_delta']=dict(wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),actual_C33_60_80=True,extra_native_claim=False,whole_REU_scope='Actual1/2MiB arrays; no16MiB claim');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--banks',type=int,choices=[16,32],required=True);a=p.parse_args();out=ROOT/'build/grid-capacity-current'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.banks)
