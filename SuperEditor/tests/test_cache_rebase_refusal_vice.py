"""Prepared current62 native EOF/capacity-refusal plans; root owns execution.

Actual ROM File/Open/IRQ setup. Measurements use the disclosed cold PC/SP
public input/command/render seam. The49 case also uses existing derived-cache
invalidation, never source/root/ref/count seeding. Default is offline only.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,re,shutil,socket,subprocess,sys,textwrap,zipfile
import test_cache_rebase_standalone_acceptance as acceptance
import test_cache_rebase_registered_vice as old
from closed_runtime_copy import run_with_closed_links
from d81_image import D81Image
from overlay_catalog_policy import catalog_identity
from cache_job_build import editor_pair_index
ROOT=old.ROOT;timing=old.timing;local=old.local
EOF_DATA=timing.native.live.grid.native_text('a')*70000+b'\r'+timing.native.live.grid.native_text('Z')
JOURNAL_DATA=old.DATA;AT=old.AT
SOURCE_SHA='303d61e2a5c455d66605b69c0650322ff1cb5641d01d52308ffc13815b658af0'
PORT=8500
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def measure_method(kind):
 s=inspect.getsource(timing.Plan.measure)
 needle="code=bytes((0x20,target&255,target>>8,0x4C,self.s['se_idle']&255,self.s['se_idle']>>8))";assert s.count(needle)==1
 if kind=='flush':new="command=self.s['se_editor_command'];code=bytes((0x20,target&255,target>>8,0xA9,77,0x20,command&255,command>>8,0x4C,self.s['se_idle']&255,self.s['se_idle']>>8))"
 elif kind=='flush-only':new="command=self.s['se_editor_command'];code=bytes((0xA9,77,0x20,command&255,command>>8,0x4C,self.s['se_idle']&255,self.s['se_idle']>>8))"
 else:new=needle
 s=s.replace(needle,new);needle="        commands += [\n            f'break exec ${self.idle_pc:04x}";assert s.count(needle)==1;s=s.replace(needle,"        commands += self.parser_traces\n"+needle)
 ns=dict(vars(timing));exec(compile(textwrap.dedent(s),str(Path(__file__))+'::'+kind,'exec'),ns);return ns['measure'],s
METHODS={n:measure_method(n)for n in('ordinary','flush','flush-only')}

class Plan(old.Plan):
 def measure(self,*a,operation='ordinary',**kw):
  METHODS[operation][0](self,*a,**kw);self.measurements[-1]['operation']=operation
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=PORT;p['global_defaults']['monitor_port_span']=1;p['global_defaults']['timeouts']['step_s']=900
  assert not p['steps'][0]['params']['kill_stale'];return p

def make_plan(e,phase):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=False
 names=json.loads((e/'freeze.json').read_text())['catalog'];n.parser_points=[]
 def runtime_index(name):
  image=(e/(name+'.seo')).read_bytes()
  return editor_pair_index(image[5],image[6]) if 'catalog_index' in n.s else names.index(name)
 for name,ident in(('parse',41),('geossema',24),('geoslex',25)):
  syms=old.labels(e/(name+'.lbl'))
  for fn in('entry','se_sm_feed','se_sl_feed','request'):
   if fn in syms:n.parser_points.append(dict(name=name+':'+fn,pc=syms[fn],slot=runtime_index(name)+1,id=ident))
 n.parser_traces=[f'trace exec ${p["pc"]:04x} if @cpu:${n.s["se_overlay_active"]+1:04x} == ${p["slot"]:02x}'for p in n.parser_points]
 n.boot();n.open('open_'+phase,b'LARGE70'if phase=='eof'else b'JOURNAL8')
 n.typed('markdown_initial','syntax markdown');n.typed('enter_geos','mode hires');n.typed('nowrap','wrap off');n.typed('full_actual','syntax full');n.memory('actual_caps','se_render_caps',3)
 if phase=='eof':
  n.memory('actual_loaded70k','se_doc_length',len(EOF_DATA),3);n.typed('public_bottom','bottom');n.memory('actual_EOF','se_hot_caret',len(EOF_DATA),3)
  n.measure('eof-before',EOF_DATA,3,full=True,category='genuine70002B-EOF');n.measurements[-1].update(expected_caret=70002,expected_pending=0,expected_node=1,phase=phase)
  n.measure('eof-Q',EOF_DATA+timing.native.live.grid.native_text('Q'),3,key=timing.native.live.grid.native_text('Q')[0],full=True,category='public-Q-after-checkedBASE1');n.measurements[-1].update(expected_caret=70003,expected_pending=1,expected_node=1,phase=phase)
  n.measure('eof-Undo',EOF_DATA,3,key=0x1a,full=True,category='actualUndo-after-EOFQ');n.measurements[-1].update(expected_caret=70002,expected_pending=0,expected_node=1,phase=phase)
 else:
  n.typed('target_line','goto 5');n.send('target_column',b'\x1d'*10);n.memory('actual_target', 'se_hot_caret',AT,3);n.memory('initial_queue0','se_bc_count',0)
  data=JOURNAL_DATA
  for k in range(24):
   data=data[:AT+k]+timing.native.live.grid.native_text('Q')+data[AT+k:];tag='cow-'+str(k+1)
   n.measure(tag,data,3,key=timing.native.live.grid.native_text('Q')[0],operation='flush',category='genuine-public-input-WRAP_OFF-COW')
   n.measurements[-1].update(expected_caret=AT+k+1,expected_pending=0,expected_node=k+2,expected_journal=(k+1)*2,expected_queue=0,phase=phase)
   n.memory(tag+'_retired','se_bc_count',0)
  data=data[:AT+24]+timing.native.live.grid.native_text('Q')+data[AT+24:]
  n.measure('full48-plus1',data,3,key=timing.native.live.grid.native_text('Q')[0],full=True,category='one-pending49-forced-derived-miss')
  n.measurements[-1].update(expected_caret=AT+25,expected_pending=1,expected_node=25,expected_journal=48,expected_queue=1,phase=phase)
  n.memory('one_unretired','se_bc_count',1)
  n.measure('full48-plus2',data,3,full=True,operation='flush-only',category='actual-public-WRAP_OFF-REKEY50')
  n.measurements[-1].update(expected_caret=AT+25,expected_pending=0,expected_node=26,expected_journal=48,expected_queue=2,phase=phase)
  n.memory('two_unretired','se_bc_count',2)
 return n

def prepare(base,out,port):
 global PORT
 PORT=port;out.mkdir(parents=True)
 original=json.loads((base/'freeze.json').read_text());assert len(original['names'])==62
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  assert hashlib.sha256(z.read('src/cache/edit-rebase-integration/worker.s')).hexdigest()==SOURCE_SHA,'Only qualified combined variant2 is admitted'
 assert len((base/'build/overlays/parse.seo').read_bytes())-36==4068
 phases={}
 for phase,data,name in(('eof',EOF_DATA,'large70'),('journal',JOURNAL_DATA,'journal8')):
  e=acceptance.freeze(base,out/phase)
  for mod in('parse','geossema','geoslex'):
   import test_cache_rebase_registered as reg
   meta=reg.metadata(base,mod);assert meta.with_suffix('.bin').read_bytes()==(e/(mod+'.seo')).read_bytes()[36:];shutil.copy2(meta.with_suffix('.lbl'),e/(mod+'.lbl'))
  payload=e/(name+'.seq');payload.write_bytes(data);p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(payload),name+',s'],capture_output=True,text=True);(e/'regression-package.log').write_text(p.stdout+p.stderr);assert not p.returncode
  assert D81Image((e/'working.d81').read_bytes()).read(name.upper().encode(),kind=1).data==data;shutil.copy2(e/'working.d81',e/'regression-initial.d81')
  n=make_plan(e,phase);plan=n.plan();assert len({x['id']for x in plan['steps']})==len(plan['steps'])
  (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'parser-points.json').write_text(json.dumps(n.parser_points,indent=2)+'\n')
  (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
  for kind,(_,source)in METHODS.items():(n.out/('measure-'+kind+'.py')).write_text(source)
  dependencies={}
  with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
   for module in list(sys.modules.values()):
    path=Path(getattr(module,'__file__','')or'/').resolve()
    if not path.is_file()or path.suffix!='.py'or not path.is_relative_to(ROOT):continue
    name=str(path.relative_to(ROOT))
    if name in dependencies:continue
    raw=path.read_bytes();dependencies[name]=hashlib.sha256(raw).hexdigest();z.writestr(name,raw)
  (e/'phase.json').write_text(json.dumps(dict(phase=phase,source_fixture=str(base),port=port,source_sha256=sha(Path(__file__)),dependencies=dependencies),indent=2)+'\n')
  phases[phase]=dict(path=str(e),steps=len(plan['steps']),frames=len(n.measurements),IRQbytes=n.keys,expected_raw_REU_bytes=len(n.measurements)*16777216,plan_sha256=sha(n.out/'plan.yaml'))
 receipt=dict(status='PREPARED_NOT_NATIVE',fixture=str(base),phases=phases,scope=__doc__,source_sha256=sha(Path(__file__)),native_scope='First-class ROMFileOpen+IRQ setup; measured service uses disclosed publicPC/SP probe. No source/root/count seeding.49 derived invalidation explicit. Root must run/inspect; no acceptance claimed.')
 (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PREPARED_REFUSAL_NATIVE',out,json.dumps(phases),flush=True);return receipt

def loaded(e):
 n=local.presentation.scenario_loaded(e);n.__class__=Plan;n.cost_profile=False;n.parser_points=json.loads((n.out/'parser-points.json').read_text());return n

def evaluate(e):
 n=loaded(e);phase=json.loads((e/'phase.json').read_text())['phase'];old_expected,old_catalog=timing.semantic.expected,timing.FontCatalog
 timing.semantic.expected=local.presentation.expected_geos;timing.FontCatalog=lambda p,native:local.preview.pack_catalog((e/'font-pack.bin').read_bytes(),native)
 try:result=timing.evaluate(n)
 finally:timing.semantic.expected,timing.FontCatalog=old_expected,old_catalog
 reus=timing.native.live.grid.reu_images(n.out/'run');pack=(e/'font-pack.bin').read_bytes();rows=[];old53=None
 for m in result['measurements']:
  tag=m['id'];ram=(n.out/'captures'/(tag+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(tag+'-colors.bin')).read_bytes();f=local.Captured(n.s,ram,colors,e);reu=reus[tag]
  assert len(reu)==16777216 and f.get('se_mode',1)==3 and f.get('se_render_caps',1)==3
  assert f.get('se_hot_caret')==m['expected_caret']and f.get('se_hot_pending',1)==m['expected_pending']and f.get('se_h_current',4)==m['expected_node']and f.get('se_h_saved',4)==1
  assert f.get('se_clip_length')==0 and f.get('se_sel_mark',1)==0 and not f.get('se_fs_owned',1)
  assert f.read(n.s['se_editor_settings'],64)==(e/'editor-defaults.bin').read_bytes()and f.read(n.s['se_f_current_name'],f.get('se_f_current_len',1))==(b'LARGE70'if phase=='eof'else b'JOURNAL8')
  for i,h in enumerate(f.read(n.s['se_gf_state']+1,2)):
   b=ram[n.s['se_reu_map']+h];assert h and b and ram[n.s['se_reu_logical_owner']+h]==ram[n.s['se_reu_physical_owner']+b]==0xfd
   raw=pack[i*65536:(i+1)*65536];assert reu[b*65536:b*65536+len(raw)]==raw
  token=f.read(n.s['se_bc_arena'],5);h=ram[n.s['object_extents']+token[0]*16];b=ram[n.s['se_reu_map']+h];assert ram[n.s['object_owner']+token[0]]==ram[n.s['se_reu_logical_owner']+h]==ram[n.s['se_reu_physical_owner']+b]==0x53
  raw=reu[b*65536:(b+1)*65536];selected=old.splice.roots(raw)[2]
  if phase=='eof':
   assert selected[31]==1
   for k in('se_doc_original','se_doc_append'):assert ram[n.s['object_banks']+f.get(k,1)]*65536>=70003,'realFileOpen must provide sufficient actual quota'
   assert old53 is None or raw==old53,'EOFfallback must preserve whole53';old53=raw
  else:
   assert selected[31]==5 and selected[30]==m['expected_journal']and f.get('se_bc_count',1)==m['expected_queue']
   if tag=='cow-24':old53=raw
   if tag.startswith('full48-'):assert old53==raw,'fulljournal fallback altered old53'
  text=(n.out/('stopwatch-'+tag+'.log')).read_text(encoding='utf-8-sig');counts={p['name']:len(re.findall(r'(?mi)^\.C:'+format(p['pc'],'04x')+r'\s',text))for p in n.parser_points}
  request=next(p['pc']for p in n.parser_points if p['name']=='parse:request')
  handoffs=len(re.findall(r'(?mi)^\.C:'+format(request,'04x')+r'\s[^\r\n]*?A:15 X:01',text))
  if phase=='journal'and tag.startswith('cow-'):assert counts.get('parse:se_sm_feed',0)>0 and counts.get('geossema:se_sm_feed',0)==counts.get('geoslex:se_sl_feed',0)==0
  if tag in('eof-Q','full48-plus1','full48-plus2'):assert handoffs>0 and counts.get('geossema:se_sm_feed',0)>0,'genuine C41 decline plus fallback parser required'
  rows.append(dict(id=tag,cycles=m['emulated_cycles'],loads=m['counter_deltas']['se_overlay_loads'],journal_count=selected[30],root_flags=selected[31],queued=f.get('se_bc_count',1),C41_to_C21=handoffs,counts=counts))
 assert(e/'working.d81').read_bytes()==(e/'regression-initial.d81').read_bytes(),'read-only scenarios changed disk'
 result.update(regression_rows=rows,scope=__doc__,limits='Mutable source/history intervals are not wholeREU read-only. All62assetpayloads/FDfontpack/shim/lower64stack/coldprobe/current source/pixels are independently checked; old53 entirebank exact across refusal frames. CPU gates prove exact per-write FE/COW spans. Not physical-key latency/ReadyOS proof.')
 (n.out/'refusal-native-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def execute(e):
 global PORT
 info=json.loads((e/'phase.json').read_text());PORT=info['port'];assert info['source_sha256']==sha(Path(__file__)),'prepared verifier changed; reprepare'
 for name,digest in info['dependencies'].items():assert sha(ROOT/name)==digest,('prepared verifier dependency changed; reprepare',name)
 for port in(PORT,*range(PORT+100,PORT+140)):
  with socket.socket()as s:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',port))
 n=loaded(e);project=timing.native.live.grid.synchronous_project(n.out);local.vice_plan.PROJECT=project
 p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert not p.returncode
 plan=json.loads((n.out/'plan.yaml').read_text());run_with_closed_links(local.capacity.run_owned_plan,plan,n.out,timeout=3600);return evaluate(e)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--run',type=Path);p.add_argument('--verify',type=Path);p.add_argument('--fixture',type=Path);p.add_argument('--out',type=Path);p.add_argument('--port',type=int,default=8500);a=p.parse_args()
 if a.run:execute(a.run.resolve())
 elif a.verify:evaluate(a.verify.resolve())
 elif a.prepare:
  assert a.fixture and a.out;prepare(a.fixture.resolve(),a.out.resolve(),a.port)
 else:print('Offline preparation only. Root controls explicit --run and native port assignment.')
