"""Canonical D81 styled-navigation timing and pixels on owned8100/text8200.

IRQ setup and actual File/Open supply the source. Timing retains the documented
public-input PC/SP seam; a conditional read-only trace records real job12
requests. No product patches, host source/viewport seed, or physical-key claim.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil, socket, subprocess, zipfile
from test_lifecycle_cache_current import cache_frame
from test_cache_presentation_vice import presentation, timing, capacity, Captured
from d81_image import D81Image
import vice_plan
ROOT=timing.ROOT
DATA=timing.native.live.grid.native_text('**'+'x'*4092+'**\rNext.')

class Plan(presentation.Plan):
 def __init__(self,e,report):
  super().__init__(e,report,1,0);self.cost_profile=True
  raw=(e/'editor.prg').read_bytes();load=int.from_bytes(raw[:2],'little')
  start=self.s['se_geos_service']-load+2
  # AD operation / STA frame / AD request / PHA is the real dispatcher.
  prefix=raw[start:start+10]
  assert prefix[0]==0xad and prefix[3]==0x8d and prefix[6]==0xad and prefix[9]==0x48
  assert int.from_bytes(prefix[7:9],'little')==0x9135
  self.nav_trace=self.s['se_geos_service']+9
 def measure(self,*args,**kwargs):
  super().measure(*args,**kwargs)
  ident=args[0];p=self.out/(ident+'_timed_coherent.mon')
  text=p.read_text();assert text.count('stopwatch reset')==1
  trace=f'trace exec ${self.nav_trace:04x} if @cpu:${self.s["se_e_job"]:04x} == $0c\n'
  p.write_text(text.replace('stopwatch reset',trace+'stopwatch reset'))

def prepare(base):
 for port in(8100,*range(8200,8240)):
  with socket.socket()as s:
   s.settimeout(.05);assert s.connect_ex(('127.0.0.1',port))!=0,('owned port busy',port)
 e=timing.freeze(base,'pal');target=e.with_name(e.name.replace('display-timing-pal','cache-navigation-native'));e.rename(target);e=target
 source=e/'navdoc.bin';source.write_bytes(DATA)
 p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(source),'navdoc,s'],capture_output=True,text=True)
 (e/'navigation-package.log').write_text(p.stdout+p.stderr);assert not p.returncode
 assert D81Image((e/'working.d81').read_bytes()).read(b'NAVDOC',kind=1).data==DATA
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
 n=Plan(e,json.loads((e/'editor-report.json').read_text()));n.boot();n.open('open_navdoc',b'NAVDOC')
 n.typed('markdown','syntax markdown');n.typed('enter_geos','mode hires')
 n.memory('baseline_armed','se_bc_flags',17)
 def command(tag,text,caps):
  n.send(tag+'_prompt',b'\x88'+timing.native.live.grid.native_text(text),ui=2)
  n.measure(tag,DATA,3,key=13,category='public-command-'+text)
  n.measurements[-1]['caps']=caps
 command('styled-bottom','bottom',1)
 n.typed('plain','syntax plain');n.typed('plain_top_prepare','top')
 command('plain-bottom','bottom',0)
 n.typed('markdown_again','syntax markdown')
 command('styled-top','top',1)
 (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 (n.out/'plan-metadata.json').write_text(json.dumps(dict(nav_trace=n.nav_trace,cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in('tests','tools'):
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 return e,n

def evaluate(n):
 old=timing.semantic.expected;timing.semantic.expected=presentation.expected_geos
 try:result=timing.evaluate(n)
 finally:timing.semantic.expected=old
 images=timing.native.live.grid.reu_images(n.out/'run')
 arenas={};allocation=None;derived=set();payload=None
 for item in n.measurements:
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();s=n.s
  current,body=cache_frame(s,ram,images[ident],n.e)
  assert current['merged_length']==len(DATA) and current['root_ticket']==0
  assert ram[s['se_bc_flags']]in(1,17,33,49) and ram[s['se_bc_count']]==0
  oid=int(current['token'][:2],16)
  assert [i for i in range(8)if ram[s['object_owner']+i]==0x53]==[oid]
  logical=list(ram[s['object_extents']+oid*16:s['object_extents']+oid*16+current['banks']])
  physical=[ram[s['se_reu_map']+b]for b in logical]
  assert len(set(logical))==len(set(physical))==current['banks']
  assert sorted(physical)==[b for b in range(256)if ram[s['se_reu_physical_owner']+b]==0x53]
  current.update(logical_banks=logical,physical_banks=physical)
  if allocation is None:allocation=current;payload=body
  assert current==allocation and body==payload,(ident,'retained typed53 arena changed')
  arenas[ident]=current
  derived.update(b for b in range(256)if ram[s['se_reu_physical_owner']+b]==0xfe)
 assert not set(allocation['physical_banks'])&derived
 outside=None;stable=None;traces={}
 for item in n.measurements:
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(n.s,ram,colors,n.e)
  assert f.get('se_render_caps',1)==item['caps'] and not f.get('se_hot_pending',1)
  assert f.get('se_hot_caret')==(0 if ident=='styled-top'else len(DATA))
  assert f.get('se_v_top')==(0 if ident=='styled-top'else DATA.rfind(b'\r')+1)
  assert f.read(n.s['se_f_current_name'],f.get('se_f_current_len',1))==b'NAVDOC'
  canonical=f.read(n.s['se_doc_roots'],512)+b''.join(f.read(n.s[k],w)for k,w in[('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)])
  if stable is None:stable=canonical
  assert canonical==stable,(ident,'source/history/clipboard')
  assert f.read(n.s['se_editor_settings'],64)==(n.e/'editor-defaults.bin').read_bytes()
  masked=bytearray(images[ident])
  for bank in derived:
   assert ram[n.s['se_reu_physical_owner']+bank]in(0,0xfe)
   masked[bank*65536:(bank+1)*65536]=bytes(65536)
  digest=hashlib.sha256(masked).hexdigest()
  if outside is None:outside=digest
  assert digest==outside,(ident,'whole16MiB outside checkedFE')
  log=(n.out/('stopwatch-'+ident+'.log')).read_text(errors='replace')
  requests=[]
  for pc,a in re.findall(r'(?m)^\.C:([0-9a-f]{4}).*?A:([0-9a-f]{2})',log,re.I):
   if int(pc,16)==n.nav_trace:requests.append(int(a,16))
  assert 23 in requests,(ident,'actual job12 dispatcher absent')
  if item['caps']==0:assert not set(requests)&{24,25,26,34,35,37,39},requests
  traces[ident]={str(v):requests.count(v)for v in sorted(set(requests))}
 assert (n.e/'working.d81').read_bytes()==(n.e/'initial-fixtures.d81').read_bytes()
 result.update(nav_requests=traces,arena_allocation=allocation,arena_records=arenas,source_bytes=len(DATA),scope=__doc__)
 (n.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--verify',type=Path);p.add_argument('--run',action='store_true');a=p.parse_args()
 if a.verify:
  e=a.verify.resolve();n=presentation.scenario_loaded(e);n.nav_trace=json.loads((n.out/'plan-metadata.json').read_text())['nav_trace'];result=evaluate(n);print('PASS',e,flush=True)
  for item in result['measurements']:print(json.dumps(dict(id=item['id'],cycles=item['emulated_cycles'],loads=item['counter_deltas']['se_overlay_loads'])),flush=True)
  raise SystemExit
 assert a.fixture;e,n=prepare(a.fixture.resolve());plan=n.plan()
 (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');print('PREPARED',e,flush=True)
 if a.run:
  project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
  b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
  manifest=capacity.run_owned_plan(plan,n.out,timeout=1200);(n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  result=evaluate(n);print('PASS',e,flush=True)
  for item in result['measurements']:print(json.dumps(dict(id=item['id'],cycles=item['emulated_cycles'],loads=item['counter_deltas']['se_overlay_loads'])),flush=True)
