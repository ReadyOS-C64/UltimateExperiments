"""Private early-wrap R28 PAL native10+10, owned8500/text8600.

Reuse released public-input timing and independent source/VIC/file/font/REU
oracles. Only reviewed build cardinality, feature-path and strict FE tail deltas.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,shutil
import test_geos_heading_body_candidate_vice as original
ROOT=original.ROOT
BASE=ROOT/'build/geos-row-backup/20261025T172445081632Z/fixture'
CANDIDATE=ROOT/'build/geos-wrap-refusal/20261025T174122951015Z/fixture'
SHA='ce4ec3c3bb365229817201d680fd6629b88ebd065717a03958ffa318d8eeb32d'
changes=[]

class Plan(original.Plan):
 def boot(self):
  # Current released profile superclass already records natural idle.
  return original.profile.Plan.boot(self)
original.Plan=Plan

def adapted(function,replacements):
 text=inspect.getsource(function)
 for old,new in replacements:
  assert text.count(old)==1,(function.__name__,old)
  text=text.replace(old,new);changes.append(dict(function=function.__name__,old=old,new=new))
 ns=dict(vars(original));ns['SOURCE_SHA']=SHA;exec(compile(text,str(Path(__file__))+'::'+function.__name__,'exec'),ns);return ns[function.__name__]

original.freeze=adapted(original.freeze,[
 ("len(ident['catalog'])==47","len(ident['catalog'])==48"),
 ("==4096","==4095"),("==4051","==3928"),
 ("'-heading-body-'+tag+'-native'","'-wrap-refusal-'+tag+'-native'")])
original.scenario=adapted(original.scenario,[("expected=2 if variant=='candidate'and fast else 0","expected=2 if fast else 0")])
old_extra=original.extra
candidate_extra=adapted(original.extra,[("[(0,64),(0x200,0xe568)]","[(0,64),(0x200,0xd568)]")])
def extra(n,result):
 # Both released3928 and early4095 exclude all removed backups from writes.
 return (candidate_extra if len((n.e/'geosdelta.seo').read_bytes())-36 in (3928,4095) else old_extra)(n,result)
original.extra=extra

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--baseline',type=Path,default=BASE);p.add_argument('--candidate',type=Path,default=CANDIDATE);a=p.parse_args()
 if not a.run:print('Prepared combined48 PAL heading10+10 on owned8500/text8600.');return
 out=ROOT/'build/geos-wrap-refusal-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 (out/'adaptations.json').write_text(json.dumps(dict(original_sha256=hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),changes=changes,scope=__doc__),indent=2)+'\n');shutil.copy2(Path(__file__),out/Path(__file__).name)
 b,br=original.execute(a.baseline.resolve(),'baseline');c,cr=original.execute(a.candidate.resolve(),'candidate');cases=[]
 for x,y in zip(br['measurements'],cr['measurements']):
  assert x['id']==y['id'];bp=b/'timing'/('native-'+x['id']+'.png');cp=c/'timing'/('native-'+y['id']+'.png');assert bp.read_bytes()==cp.read_bytes(),(x['id'],'A/B PNGbytes differ')
  cases.append(dict(id=x['id'],baseline_cycles=x['emulated_cycles'],candidate_cycles=y['emulated_cycles'],baseline_first=x['first_publish_cycles'],candidate_first=y['first_publish_cycles'],baseline_loads=x['counter_deltas']['se_overlay_loads'],candidate_loads=y['counter_deltas']['se_overlay_loads'],PNG_byte_identical=True))
 result=dict(status='passed',baseline=str(b),candidate=str(c),cases=cases,whole16MiB_paired_intervals=br['extra']['whole16MiB_paired_intervals']+cr['extra']['whole16MiB_paired_intervals'],native_pixels=(len(br['measurements'])+len(cr['measurements']))*64000,VICE_closed=True,ports=[8500,8600],scope=__doc__)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('DONE',out,json.dumps(result),flush=True)
if __name__=='__main__':main()
