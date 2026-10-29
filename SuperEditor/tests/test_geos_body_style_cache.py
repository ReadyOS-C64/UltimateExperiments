"""Private cross-row actual-C26 style cache; C20/R24 substitution only."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,inspect
import test_geos_inline_query_profile as profile
ROOT=profile.ROOT;BASE=ROOT/'build/geos-incremental-editor/20261025T204511293143Z/fixture'
def builder():
 p=ROOT/'src/render/geos/body-style-cache-candidate/build-once.py';s=importlib.util.spec_from_file_location('body_cache_builder',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def run(out,base,suite='profile'):
 fixture=builder().install(out,base);gate=out/'gate';gate.mkdir()
 if suite=='profile':return profile.run(gate,fixture)
 if suite in ('small','small-cold'):
  cases=[('short',b'Plain **bold** tail.'),('tiny',b'**x**'),('heading',b'# **Title**\rnext.'),('one-row',b'**'+b'W'*20+b'**'),('wide200',b'***'+b'W'*200+b'***\rTail.'),('shortwrap',b'**'+(b'W '*100)+b'**\rTail.'),('long-plain',b'x'*300+b'\rTail.'),('empty',b''),('cr',b'\r'),('prefix',b'- ***Item*** and @@code@@.\r'),('exact320-cr',b'**'+b'.'*48+b'**'+b'.'*76+b'\rTail.'),('exact320-eof',b'**'+b'.'*48+b'**'+b'.'*76)]
  src=inspect.getsource(profile.run);line=next(l for l in src.splitlines()if l.startswith('  for tag,data in '));src=src.replace(line,'  for tag,data in CASES:')
  if suite=='small-cold':
   needle="   for n in['se_r_valid','se_gc_valid','se_gc_width']:"
   assert src.count(needle)==1
   src=src.replace(needle,"   f.put('se_f_owner',4,1);f.put('se_overlay_frame',6,1);r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=0);assert not r.p&1;f.put('se_f_owner',0,1) #explicit checkedderivedcache revoke fixture before cold measurement\n"+needle)
  ns=dict(profile.__dict__,CASES=cases);exec(src,ns);return ns['run'](gate,fixture)
 if suite=='inline':
  import test_geos_semantic_editor as g
  src=inspect.getsource(g.run);old="(0xEA88 if 'gfont' in f.assets else 0xE568 if 'geosdelta' in f.assets else 0xD528))]):";assert src.count(old)==1
  src=src.replace(old,"(0xEA88 if 'gfont' in f.assets else 0xE568 if 'geosdelta' in f.assets else 0xD528))]+[(start+0xFC00,start+0xFDA0)]):")
  ns=dict(g.__dict__);exec(src,ns);return ns['run'](gate,fixture,inline_case=True)
 if suite=='capacity':
  import test_geos_inline161_candidate as g
  src=inspect.getsource(g.public);old='(start+0xB200,start+0xEA88)]';assert src.count(old)==1
  src=src.replace(old,'(start+0xB200,start+0xEA88),(start+0xFC00,start+0xFDA0)]');ns=dict(g.__dict__);exec(src,ns);return ns['public'](gate,fixture)
 if suite=='boundaries':
  import test_geos_style_window_boundaries as g
  text=inspect.getsource(g.run);line=next(l for l in text.splitlines()if l.startswith(' candidate.certificate.D='));text=text.replace(line," fixture=FIXTURE;target=out/'boundaries';target.mkdir()")
  needle=" ns=dict(existing.__dict__);exec(text,ns);";assert text.count(needle)==1
  text=text.replace(needle," text=text.replace('(start+0xB200,start+0xEA88)]','(start+0xB200,start+0xEA88),(start+0xFC00,start+0xFDA0)]')\n"+needle)
  ns=dict(g.__dict__,FIXTURE=fixture);exec(text,ns);return ns['run'](gate)
 if suite=='fold':
  import test_geos_fold_editor as g;return g.run(gate,fixture)
 if suite=='incremental':
  import test_geos_incremental_editor as g
  text=inspect.getsource(g.run);old='[(base,base+64),(base+0x200,base+0xE568)]';assert text.count(old)==1
  text=text.replace(old,'[(base,base+64),(base+0x200,base+0xE568),(base+0xFC00,base+0xFDA0)]');ns=dict(g.__dict__);exec(text,ns);return ns['run'](gate,fixture)
 raise ValueError(suite)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--suite',choices=['profile','small','small-cold','inline','capacity','boundaries','fold','incremental'],default='profile');a=p.parse_args();out=ROOT/'build/geos-body-style-cache'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.suite);out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.base.resolve(),a.suite);print(r and r.get('status'),flush=True)
