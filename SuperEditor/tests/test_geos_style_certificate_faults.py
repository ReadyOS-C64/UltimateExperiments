"""Original inline bridge fault suite, exact additional396B output ownership."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json,argparse
import test_geos_style_certificate_candidate as candidate
import test_geos_inline_bridge as original
ROOT=candidate.ROOT

def run(out,base=candidate.BASE):
 fixture=candidate.install(out,base);gate=out/'gate';gate.mkdir();source=inspect.getsource(original.run)
 source=source.replace("assert len(identity['names'])==32","assert len(identity['names'])==48")
 old="assert f.read(0x4400,486)==plan[:486],'bridge overwrote reserved canonical anchors'"
 new="""assert f.read(0x458C,90)==plan[396:486],'certificate overwrote unowned90B ledger suffix'
  tag=f.m.read(0x4400)
  if tag in(1,2):
   count=f.m.read(0x443F);assert 0<count<=161
   assert all(v<4 for v in f.read(0x444A,count))and all(v<14 for v in f.read(0x44EB,count))
   if tag==2:assert f.read(0x4401,59)==f.read(0x9040+27,59),'completecertificate notcurrentC20identity'"""
 assert source.count(old)==1;source=source.replace(old,new)
 old="want_plan=bytearray(plan);want_plan[f.s['se_st_cp_valid']-0x4400]=0";assert source.count(old)==1;source=source.replace(old,old+";want_plan[0]=0 #explicitBEGIN certificate invalidation, no-lookahead path otherwiseunchanged")
 old="f.m.read(f.s['image_slot']+i)==slot";assert source.count(old)==1;source=source.replace(old,"f.catalog()[f.s['se_overlay_capacity']+i]==slot")
 # Exercise the new completed-C20 handoff itself, not only the old bridge.
 hook="   # The overwritten inactive40-column plan must never be used after mode return."
 extra="""   for stage in ('before-consume','after-consume'):
    start(DATA);until(lambda:f.m.read(0x9135)==20 and f.m.read(0x9136)==7)
    assert f.m.read(0x4400)==2 and not f.m.read(0x912D)
    if stage=='after-consume':
     r=f.call('se_editor_service');assert not r.p&1
    canonical=f.canonical();f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
    for tick in range(3):
     r=f.call('se_editor_service')
     if r.p&1:break
    assert r.p&1 and f.get('se_e_error',1)==0x74,(stage,f.debug())
    assert f.canonical()==canonical and not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job'])
    faults.append('certificate '+stage+' current-source guard rejects changedrevision before pixels')
   start(DATA);until(lambda:f.m.read(0x9135)==20 and f.m.read(0x9136)==7)
   assert not f.call('se_doc_read_acquire').p&1;stop('STOP-certificate',1);assert not f.call('se_doc_read_release').p&1
   faults.append('STOP completed-certificate handoff preservesforeignlease')
   for at,label in [(0x4401,'key'),(0x4440,'context'),(0x443F,'count')]:
    start(DATA);until(lambda:f.m.read(0x9135)==20 and f.m.read(0x9136)==7)
    f.m.write(at,0 if label=='count' else f.m.read(at)^1)
    r=f.call('se_editor_service');assert not r.p&1 and f.m.read(0x9135)==26 and f.m.read(0x9136)in(0,4),(label,f.debug())
    f.settle();check(DATA,'certificate-'+label+'-fallback');faults.append('certificate '+label+' mismatch usesoriginalC26')
   start(DATA);until(lambda:f.m.read(0x9135)==20 and f.m.read(0x9136)==7)
   for owner in(0,1,2,3,5,255):
    f.put('se_f_owner',owner,1);phase=f.read(0x8B40,0x640);certificate=f.read(0x4400,396);reu=whole()
    f.put('se_overlay_frame',7,1);r,n=f.fast_call(f.s['se_overlay_call'],a=20,x=1)
    assert r.p&1 and r.a==0xB2 and f.read(0x8B40,0x640)==phase and f.read(0x4400,396)==certificate and whole()==reu,(owner,'opaque consume refusal')
   f.put('se_f_owner',4,1);stop('opaque-certificate');faults.append('sixforeignowners op7 opaque entirephase/certificate/16MiB')
"""
 assert source.count(hook)==1;source=source.replace(hook,extra+hook)
 (out/'generated-run.py').write_text(source)
 ns=dict(original.__dict__);exec(source,ns);result=ns['run'](gate,fixture)
 result['private_certificate_allowance']={'bytes':396,'start':'4400','end':'458C','unowned_suffix_preserved':90,'all_other_guards':'unchanged; publishedmanagedslotbit onlynormalizedbyexistingcataloghelper'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=candidate.BASE);a=p.parse_args()
 out=ROOT/'build/geos-style-certificate-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.base.resolve());print({'status':r['status'],'frames':len(r['frames']),'faults':len(r['faults'])},flush=True)
