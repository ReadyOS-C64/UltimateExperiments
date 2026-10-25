"""Private bounded C20 stylelookahead, released certificate controlunchanged."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,inspect,zipfile,importlib.util
import test_geos_style_certificate_candidate as certificate
ROOT=certificate.ROOT
BASE=ROOT/'build/geos-preflush-product/20261025T193429355750Z/fixture'
def run(out,base,suite='fit',control=False):
 certificate.D=ROOT/('src/render/geos/source-style-window-candidate'if control else'src/render/geos/style-window-candidate')
 with zipfile.ZipFile(base/'product-sources.zip')as z:current='SC_CONSUME' in z.read('src/render/geos/page.s').decode()
 if current:
  spec=importlib.util.spec_from_file_location('window_current_builder',ROOT/'src/render/geos/style-window-candidate/build-once.py');one=importlib.util.module_from_spec(spec);spec.loader.exec_module(one)
  if suite=='fit':return one.build(out/'link',base,control)[1]
  fixture=one.install(out,base,control)
 else:
  if suite=='fit':return certificate.build(out/'link',base)
  fixture=certificate.install(out,base)
 target=out/'gate';target.mkdir()
 if suite in('profile','small'):
  import test_geos_inline_query_profile as gate
  if suite=='profile':
   result=gate.run(target,fixture)
   if not control:
    for row in result['records']:
     for event in row['events']:
      if event['id']==26 and event['operation']==3:assert 0<event['count']<=160 and event['start']<=event['query'] and event['query']+event['count']<=event['end']<=row['source_bytes'],('stylewindow outside actual logical event',event)
      if event['id']==14 and event['rootrequest']==20:assert 0<event['count']<=32,('rawC20read enlarged',event)
    result['actual_window_bounds_checked']=True;(target/'result.json').write_text(json.dumps(result,indent=2)+'\n')
   return result
  cases=[('short',b'Plain **bold** tail.'),('tiny',b'**x**'),('heading',b'# **Title**\rnext.'),('one-row',b'**'+b'W'*20+b'**'),('wide200',b'***'+b'W'*200+b'***\rTail.'),('shortwrap',b'**'+(b'W '*100)+b'**\rTail.'),('long-plain',b'x'*300+b'\rTail.'),('empty',b''),('cr',b'\r'),('prefix',b'- ***Item*** and @@code@@.\r'),('exact320-cr',b'**'+b'.'*48+b'**'+b'.'*76+b'\rTail.'),('exact320-eof',b'**'+b'.'*48+b'**'+b'.'*76)]
  src=inspect.getsource(gate.run);line=next(l for l in src.splitlines()if l.startswith('  for tag,data in '));src=src.replace(line,'  for tag,data in CASES:');ns=dict(gate.__dict__,CASES=cases);exec(src,ns);result=ns['run'](target,fixture)
  if not control:
   for row in result['records']:
    for event in row['events']:
     if event['id']==26 and event['operation']==3:assert 0<event['count']<=160 and event['query']+event['count']<=event['end'],event
   result['actual_window_bounds_checked']=True;(target/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  return result
 if suite=='inline':
  import test_geos_semantic_editor as gate
  return gate.run(target,fixture,inline_case=True)
 if suite=='fold':
  import test_geos_fold_editor as gate
  r=gate.run(target,fixture);return r or json.loads((target/'result.json').read_text())
 if suite=='incremental':
  import test_geos_incremental_editor as gate
  r=gate.run(target,fixture);return r or json.loads((target/'result.json').read_text())
 if suite=='capacity':
  import test_geos_inline161_candidate as gate
  return gate.public(target,fixture)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--suite',choices=['fit','profile','inline','capacity','small','fold','incremental'],default='fit');p.add_argument('--base',type=Path,default=BASE);p.add_argument('--control',action='store_true');a=p.parse_args()
 out=ROOT/'build/geos-style-window'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.suite+('-control'if a.control else''));out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.base.resolve(),a.suite,a.control);print(r if a.suite=='fit'else{'status':r['status']},flush=True)
