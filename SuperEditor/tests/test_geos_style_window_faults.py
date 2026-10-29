"""Actual bounded stylewindow authority, packet, cancellation and sourceguards."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json,argparse,zipfile,importlib.util
import test_geos_style_certificate_faults as old
import test_geos_style_certificate_candidate as certificate
ROOT=old.ROOT
BASE=ROOT/'build/geos-preflush-product/20261025T193429355750Z/fixture'
def run(out,base=BASE):
 certificate.D=ROOT/'src/render/geos/style-window-candidate'
 with zipfile.ZipFile(base/'product-sources.zip')as z:current='SC_CONSUME' in z.read('src/render/geos/page.s').decode()
 if current:
  spec=importlib.util.spec_from_file_location('window_fault_current_builder',ROOT/'src/render/geos/style-window-candidate/build-once.py');one=importlib.util.module_from_spec(spec);spec.loader.exec_module(one);certificate.install=one.install
 text=inspect.getsource(old.run)
 text=text.replace("f.read(0x458C,90)==plan[396:486]","f.read(0x4592,84)==plan[402:486]").replace("unowned90B ledger suffix","unowned84B ledger suffix")
 text=text.replace('want_plan[0]=0 #explicitBEGIN','want_plan[0]=0;want_plan[396]=0 #explicitBEGIN')
 text=text.replace('certificate=f.read(0x4400,396)','certificate=f.read(0x4400,402)').replace('f.read(0x4400,396)==certificate','f.read(0x4400,402)==certificate')
 extra="""   def window_ready():
    return f.m.read(0x9135)==20 and f.m.read(0x9136)==1 and not f.m.read(CONT) and f.m.read(0x912C)==1 and f.m.read(0x458C)==1 and int.from_bytes(f.read(0x8D00+38,3),'little')+32<=int.from_bytes(f.read(0x458D,3),'little')+f.m.read(0x4590)
   start(DATA);until(window_ready)
   scan=int.from_bytes(f.read(0x8D00+38,3),'little');buf=f.read(0x8300,160)+f.read(0x8F36,160);reu=whole();canonical=f.canonical()
   r=f.call('se_editor_service');assert not r.p&1 and f.m.read(0x9135)!=26
   assert f.read(0x8300,160)+f.read(0x8F36,160)==buf,'R14/measure changed retainedC26outputs'
   n=f.m.read(0x8D00+29);assert n<=32 and f.read(0x90EC,n)==DATA[scan:scan+n],'window changed actual32byte nativepacket'
   assert whole()==reu and f.canonical()==canonical
   stop('after-window-hit');faults.append('actualwindowhit retains320B outputs/nativepacket32/full16MiB')
   start(DATA);until(window_ready);canonical=f.canonical();f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
   r=f.call('se_editor_service');assert r.p&1 and f.get('se_e_error',1)in(0x74,0xB1)
   assert f.canonical()==canonical and not any(f.get(n,1)for n in('se_f_owner','se_fs_owned','se_doc_read_locks','se_e_job'))
   faults.append('windowhit originalR14 fullsourceguard rejects revisionchange')
   start(DATA);until(window_ready);assert not f.call('se_doc_read_acquire').p&1;stop('STOP-window',1);assert not f.call('se_doc_read_release').p&1
   faults.append('STOP held-windowlease preservesforeigncount')
   for address,value,label in((0x458C,2,'tag'),(0x4590,161,'count'),(0x458D,255,'query')):
    start(DATA);until(window_ready);f.m.write(address,value)
    r=f.call('se_editor_service');assert not r.p&1 and f.m.read(0x9135)==26 and f.m.read(0x9136)==3,(label,'window did notrefetch')
    f.settle();check(DATA,'window-'+label+'-fallback');faults.append('window '+label+' refusal/refetch exactpixels')
"""
 target=" (out/'generated-run.py').write_text(source)"
 assert text.count(target)==1
 text=text.replace(target," source=source.replace('   # The overwritten inactive40-column plan must never be used after mode return.',EXTRA+'   # The overwritten inactive40-column plan must never be used after mode return.')\n"+target)
 ns=dict(old.__dict__,EXTRA=extra);exec(text,ns);r=ns['run'](out,base)
 r['private_window_allowance']={'metadata':[0x458C,0x4592],'unowned_suffix':84,'output_buffers':'existing8300styles/8F36roles160; immutableuntilnextC26','roles_packet':'GS_OVERLAP9096 first32 dead betweenR14calls'}
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);a=p.parse_args()
 out=ROOT/'build/geos-style-window-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.base.resolve());print({'status':r['status'],'frames':len(r['frames']),'faults':len(r['faults'])},flush=True)
