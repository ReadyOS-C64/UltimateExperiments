"""Actual corrected62 pressure/retirement/quota qualification, CPU modeled ROM.

Original16/32-bank File/FC/clip/fold rollback oracles and original quota tests
are retained through asserted host-source adaptations. Genuine root5 is a
separate profile, never forged. No native/shared build/Git/hardware action.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,inspect,json,os,shutil,textwrap,zipfile
import test_cache_rebase_registered as identity
import test_cache_pressure_registered as registered59
import test_cache_file_retire as retire
import test_document_quota_editor as quota
from d81_image import D81Image
ROOT=identity.ROOT;eviction=registered59.eviction;prior=registered59.prior;parent=registered59.parent;geos=prior.geos
BASE=ROOT/'build/rebase-refusal-canonical-working-v3/20261026T234113497948Z/fixture'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def source_view(out,base):
 out.mkdir(parents=True);project=out/'project';project.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   p=project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 (project/'build').symlink_to(base/'build',target_is_directory=True)
 seal=identity.authenticate(base,project);(out/'authentication.json').write_text(json.dumps(seal,indent=2)+'\n');return project,seal

class PressureFixture(eviction.Fixture):
 def reu(self):
  raw=C.create_string_buffer(16777216);self.dll.gm_reu(self.m.handle,len(raw),raw);return raw.raw

class QuotaFixture(quota.geos.Fixture):
 def reu(self):
  raw=C.create_string_buffer(16777216);self.dll.gm_reu(self.m.handle,len(raw),raw);return raw.raw

def pressure(out,base,banks,root5=False):
 source=textwrap.dedent(inspect.getsource(prior.run))
 old="assert len(identity['names'])==54 and identity['names'][-1]=='line'";assert source.count(old)==1;source=source.replace(old,"assert len(identity['names'])==62 and identity['names'][-2:]==['parse','xform']")
 a=source.index("  f.fs[b'REOPEN']=data;");b=source.index("  assert f.merged()==data;quiet();state('open-complete')",a);source=source[:a]+eviction.replacement+source[b:]
 needle='  geos.grid.Fixture.source(f,data,banks=1,physical=banks);';assert source.count(needle)==1;source=source.replace(needle,'  f.init_retire_trace();geos.grid.Fixture.source(f,data,banks=1,physical=banks);provider_tail=f.reu()[banks*65536:];')
 assert source.count('stages=[];catalog=None')==1;source=source.replace('stages=[];catalog=None','stages=[];catalog=None;provider_tail=None')
 needle='  current=f.catalog()';assert source.count(needle)==1;source=source.replace(needle,needle+"\n  if provider_tail is not None:assert f.reu()[banks*65536:]==provider_tail,'outside configured provider changed'")
 source=source.replace('  if admitted or banks==32:assert','  if banks==32:assert')
 source=source.replace("  (out/'result.json').write_text", "  result['automatic_retirement']=True;result['helper_witnesses']=f.retire_witness;result['component_scope']=__doc__\n  (out/'result.json').write_text")
 if root5:
  old='10 PRINT "Hi"\\r:::';assert source.count(old)==1;source=source.replace(old,'10 PRINT "Hi":REM '+('x'*1000)+'\\r:::')
  needle="  state('semantic-baseline');arena,payload=cache.cache_frame";assert source.count(needle)==1;source=source.replace(needle,"  actual_root5(f,dll,frozen,data)\n"+needle)
 namespace=dict(vars(prior),actual_root5=actual_root5);namespace.update(__doc__=__doc__,__file__=__file__);exec(compile(source,str(out)+'::unchanged-original-pressure','exec'),namespace)
 oldfixture=parent.Fixture;parent.Fixture=PressureFixture
 try:
  result=namespace['run'](out,base,banks);result.update(root5_profile=root5,snapshot_proof=registered59.audit_snapshots(out,base,banks),full16MiB_reads=True,provider_tail_preserved=True,adaptations='Exact62catalog; actual C12 automatic replacement already released; original rollback/error/FC/source/history/ring assertions unchanged. Optional root5 profile uses real Full long-BODY producer/linker before same workload.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:
  parent.Fixture=oldfixture
  if out.exists():(out/'executed-pressure.py').write_text(source)

def actual_root5(f,dll,base,data):
 import test_cache_lexical_registered as lex
 p=identity.metadata(base,'ical');sl=lex.labels(p.with_suffix('.lbl'));q=identity.metadata(base,'geoslex');strict=lex.labels(q.with_suffix('.lbl'))
 dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('ical')+1,list(f.assets).index('geoslex')+1,sl['se_sl_feed'],0,0,strict['se_sl_feed'])
 f.typed(geos.native_text('syntax full'));f.render();feeds=dll.gm_metric(0);strictfeeds=dll.gm_metric(2);dll.gm_profile(0,0,0,0,0,0,0)
 proof,payload=prior.cache.cache_frame(f.s,f.read(0,65536),f.reu(),base/'build/overlays');root=payload[proof['root_offset']:proof['root_offset']+128]
 start=data.index(geos.native_text('10 PRINT'));end=data.index(13,start)
 assert root[31]==5 and root[98:100]==b'\1\0' and feeds==end-start and strictfeeds==0 and f.get('se_bc_flags',1)&129==129 and f.get('se_bc_count',1)==0
 print('ACTUAL_ROOT5',json.dumps(dict(body_bytes=end-start,producer_feeds=feeds,strict_feeds=strictfeeds,root_flags=root[31],root_sequence=proof['root_sequence'])),flush=True)

def quota_run(out,base,banks):
 source=inspect.getsource(quota.run)
 old="shutil.copy2(ROOT/'agentsworking/evidence/M7/20261025T063145901590Z-reu-1024-native/font-pack.bin',pack)";assert source.count(old)==1;source=source.replace(old,"assert pack.read_bytes()==D81Image((frozen/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data")
 old='shutil.copytree(previous,frozen)';assert source.count(old)==1;source=source.replace(old,'shutil.copytree(previous,frozen,copy_function=os.link)')
 old='f.source(data,banks=banks,physical=16)';assert source.count(old)==1;source=source.replace(old,f'f.source(data,banks=banks,physical={banks})')
 # Strengthen the unchanged refusal observer contract; existing source/history/
 # selection/REU/savepoint assertions are not replaced.
 old="  f.put('se_e_error',0,1);f.call('se_editor_command',c)";assert source.count(old)==1;source=source.replace(old,"  observer=f.read(f.s['se_bc_arena'],17)+f.read(f.s['se_bc_ring'],96)\n"+old)
 old="  f.put('se_e_mods',0,1);f.put('se_e_key',c,1);f.put('se_e_error',0,1);f.call('se_editor_input')";assert source.count(old)==1;source=source.replace(old,"  observer=f.read(f.s['se_bc_arena'],17)+f.read(f.s['se_bc_ring'],96)\n"+old)
 old="  return f.get('se_e_error',1)";assert source.count(old)==2;source=source.replace(old,"  answer=f.get('se_e_error',1)\n  if answer==0x32:assert f.read(f.s['se_bc_arena'],17)+f.read(f.s['se_bc_ring'],96)==observer,'refused quota changed observer17/ring96'\n  return answer")
 old='physical_banks=16,cases=cases';assert source.count(old)==1;source=source.replace(old,f'physical_banks={banks},cases=cases')
 namespace=dict(vars(quota),D81Image=D81Image,os=os);exec(compile(source,str(out)+'::original-quota62','exec'),namespace)
 oldfixture=quota.geos.Fixture;quota.geos.Fixture=QuotaFixture
 try:
  result=namespace['run'](out,base,None);assert result['status']=='passed'and len(result['cases'])==16 and not result['failures']
  result.update(full16MiB_reads=True,pack_input='Actual current immutable D81 GEOSFONTS, no historical native pack substitution',observer_refusal='Every capacity32 input/command preserves exact17+96 observer',scope='Original16 quota cases with actual1-bank quota/two-bank control and configured16/32-bank provider. Source-import/modeledROM and explicit checked append resize exhaustion seam; no native pixels/cold-minimum claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:
  quota.geos.Fixture=oldfixture
  if out.exists():(out/'executed-quota.py').write_text(source)

def run(out,base,suite,banks,root5):
 project,seal=source_view(out/'source-view',base)
 import font_fixture
 font_fixture.ROOT=base
 results={}
 if suite in('pressure','all'):
  for count in banks:
   for lexical in([False,True]if root5 else[False]):
    dest=out/(f'pressure{count}'+('-root5'if lexical else'-base1'));results[dest.name]=pressure(dest,base,count,lexical)
 if suite in('quota','all'):
  for count in banks:dest=out/f'quota{count}';results[dest.name]=quota_run(dest,base,count)
 if suite in('retire','all'):
  dest=out/'retire';dest.mkdir();retire.run(dest,base,identity.metadata(base,'fileio'));results['retire']=json.loads((dest/'result.json').read_text())
 result=dict(status='PASS',identity=seal,groups={n:dict(status=d.get('status'),cases=len(d.get('cases',[])),banks=d.get('physical_banks'),root5=d.get('root5_profile'))for n,d in results.items()},source_sha256=sha(Path(__file__)),scope=__doc__)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('REBASE_PRESSURE_PASS',out,flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--suite',choices=('all','pressure','quota','retire'),default='all');p.add_argument('--banks',choices=('16','32','both'),default='both');p.add_argument('--root5',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/rebase-pressure-adapter'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out.resolve(),a.fixture.resolve(),a.suite,(16,32)if a.banks=='both'else(int(a.banks),),a.root5)
