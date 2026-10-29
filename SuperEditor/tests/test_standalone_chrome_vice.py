"""Current47-asset final chrome all-mode acceptance wrapper; own8700/text8800 only.

Uses the existing43-capture scenario and exact independent source/pixel/file/
history/font oracles. Only port/lifetime configuration and frozen declared FE
cache extents differ from the historical39-asset engine. No product edits.
"""
from pathlib import Path
import argparse,hashlib,inspect,json,shutil,zipfile,socket
import test_standalone_acceptance_vice as engine
from overlay_catalog_policy import catalog_identity
ROOT=engine.ROOT
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T135058303696Z/fixture'
PRG='4e64d113b50f425bba3368edc9604da05c37daa91b4b5892a08225549c941fed'
DISK='46b1375681695db647f2ffdee3490eed036575cd4d481a2e722dd52f89f709bf'

class Plan(engine.Plan):
 def plan(self):
  p=super().plan();g=p['global_defaults'];g['monitor_port_start']=8700;g['monitor_port_span']=1
  assert not g.get('kill_stale',False)
  return p


def patch_engine():
 # Narrow explicit extents only, never a blanket derived-bank exception.
 # Existingsource rows/header and B200..D527 sourcebackup remain; add the
 # frozen R28transaction, typingfont and previewheader contracts independently.
 text=inspect.getsource(engine.evaluate)
 old="[(0,64),(0x200,0xb200),(0xb200,0xd528)]"
 new="[(0,64),(0x200,0xb200),(0xb200,0xd528),(0xd528,0xe568),(0xe568,0xea88),(0xea88,0xeb69),(0xeb69,0xfba9)]"
 assert text.count(old)==1,'historical guard changed; inspect before adapting'
 text=text.replace(old,new)
 old_catalog="  current=f.read(s['se_overlay_ids'],6*64)"
 assert text.count(old_catalog)==1
 text=text.replace(old_catalog,"  current=catalog_identity(f.read(s['se_overlay_ids'],6*64),s)")
 engine.__dict__['catalog_identity']=catalog_identity
 exec(compile(text,str(Path(__file__).resolve())+'::adapted-evaluate','exec'),engine.__dict__)
 engine.Plan=Plan
 original=engine.capacity.run_owned_plan
 engine.capacity.run_owned_plan=lambda plan,out:original(plan,out,timeout=1800)
 return text


def freeze(source):
 # Originalfreeze verifies every immutable D81 catalog payload and seal;
 # it has no stale hard-coded39assetcount restriction.
 e=engine.folds.freeze(source,PRG,DISK)
 target=ROOT/'agentsworking/evidence/M8'/e.name.replace('-geos-fold-native','-standalone47-chrome-native')
 target.parent.mkdir(parents=True,exist_ok=True);shutil.move(e,target)
 identity=json.loads((target/'freeze.json').read_text());assert len(identity['catalog'])==47
 with zipfile.ZipFile(target/'product-sources.zip')as z:
  contracts={n:z.read(n).decode()for n in ('src/render/geos/edit-cache.inc','src/render/geos/typing-font-cache.inc','src/render/geos/preview-cache.inc','src/render/geos/preview-glyph-cache.inc')}
 assert 'GEX_OLD_HEADER=$D528' in contracts['src/render/geos/edit-cache.inc']and'GEX_TAIL_END=$E568'in contracts['src/render/geos/edit-cache.inc']
 assert 'GTF_DATA=$E568'in contracts['src/render/geos/typing-font-cache.inc']and'GTF_META=$EA68'in contracts['src/render/geos/typing-font-cache.inc']
 assert 'PPC_META_REU=$EA88'in contracts['src/render/geos/preview-cache.inc']and'PPC_SIZE=225'in contracts['src/render/geos/preview-cache.inc']
 assert all(v in contracts['src/render/geos/preview-glyph-cache.inc']for v in ('PGC_VERSION=3','PGC_BASE=$EB69','PGC_END=$FBA9','PGC_BYTES=4160'))
 assert len((target/'geosfontrow.seo').read_bytes())-36==4095,'PGC enabled only for exact declaredR23 revision'
 return target


def pgc_contract(target):
 # This gate also runs for offline verification of an alreadyfrozen capture.
 with zipfile.ZipFile(target/'product-sources.zip')as z:
  contract=z.read('src/render/geos/preview-glyph-cache.inc').decode()
 assert all(v in contract for v in ('PGC_VERSION=3','PGC_BASE=$EB69','PGC_END=$FBA9','PGC_BYTES=4160'))
 assert len((target/'geosfontrow.seo').read_bytes())-36==4095
 identity=json.loads((target/'freeze.json').read_text())
 assert len(identity['catalog'])==47 and identity['prg_sha256']==PRG and identity['disk_sha256']==DISK


def free_ports():
 for port in [8700,*range(8800,8840)]:
  with socket.socket()as s:
   try:s.bind(('127.0.0.1',port))
   except OSError as exc:raise AssertionError(f'owned port{port} is busy')from exc


def f8_supplement(source):
 # Freshownedboot of the same savedD81; never rerun/mutate completed phases.
 stamp=engine.datetime.now(engine.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 target=ROOT/'agentsworking/evidence/M8'/(stamp+'-standalone47-f8-native');target.mkdir()
 for p in source.iterdir():
  if p.is_file()and p.name not in ('result.json','visual-comparison.json'):
   shutil.copy2(p,target/p.name)
 pgc_contract(target);before=(target/'working.d81').read_bytes()
 def scenario(e,phase):
  n=Plan(e,json.loads((e/'editor-report.json').read_text()),phase);data=engine.live.grid.native_text('Q')+engine.live.grid.fixture();name=engine.NAMES[3]
  n.boot();n.open('f8_saved_open',name);n.switch('f8_start_geos',3)
  n.shot('f8-initial-geos',data,3,current=name)
  for mode in [0,1,2,3]:
   n.send('actual_F8_'+str(mode),b'\x8C');n.memory('F8_published_mode_'+str(mode),'se_mode',mode)
   n.shot('f8-mode-'+str(mode),data,mode,current=name)
  return n
 engine.scenario=scenario;free_ports();result=engine.execute(target,'restart');free_ports()
 result['scope']='Freshownedcoldboot/reopenFINALGEOS423B; actualIRQF8cycle3→0→1→2→3; no additionalfileopens or physicalchords claimed.'
 (target/'restart/result.json').write_text(json.dumps(result,indent=2)+'\n')
 assert(target/'working.d81').read_bytes()==before,'read-onlyF8D81changed'
 # Different displaycachelayouts deliberately own the exact FEprefix union.
 # Everybyte outside[0,FBA9), includingFEunusedtail and allother16MiB, exact.
 images=engine.live.grid.reu_images(target/'restart/run');symbols=json.loads((target/'editor-report.json').read_text())['symbols'];reference=None;binding=None
 for c in json.loads((target/'restart/cases.json').read_text()):
  ram=(target/'restart/captures'/(c['id']+'-ram.bin')).read_bytes();h=ram[symbols['se_gc_handle']];bank=ram[symbols['se_reu_map']+h]
  assert h and bank and ram[symbols['se_reu_logical_owner']+h]==ram[symbols['se_reu_physical_owner']+bank]==0xfe
  assert binding in(None,(h,bank));binding=(h,bank);data=bytearray(images[c['id']]);data[bank*65536:bank*65536+0xfba9]=bytes(0xfba9)
  digest=hashlib.sha256(data).hexdigest();assert reference in(None,digest),(c['id'],'full16MiBoutsideexactFEunion');reference=digest
 (target/'f8-result.json').write_text(json.dumps(dict(status='passed',identity=json.loads((target/'freeze.json').read_text()),frames=5,actual_F8_events=4,mode_sequence=[3,0,1,2,3],whole16MiB_intervals=4,FE_allowed_union=[0,0xfba9],D81_byte_unchanged=True,scope='RealIRQnativeF8bytes; exactsource/history/catalog/fontpack/allpixels/shim; notphysicalchords.'),indent=2)+'\n')
 print('F8DONE',target,flush=True)


def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--f8-from',type=Path);p.add_argument('--cpu-fixture',type=Path,default=DEFAULT);p.add_argument('--fixture',type=Path);p.add_argument('--verify',type=Path);p.add_argument('--phase',choices=['editing','restart','fold','both'],default='both');a=p.parse_args()
 patched=patch_engine()
 if a.f8_from:
  f8_supplement(a.f8_from.resolve());return
 if not a.run and not a.verify:print('Prepared47assets,43captures,private8700/text8800; --run uses frozen135058 managed product.');return
 e=a.verify.resolve()if a.verify else a.fixture.resolve()if a.fixture else freeze(a.cpu_fixture.resolve())
 pgc_contract(e)
 (e/'current-wrapper-evaluate.py').write_text(patched)
 (e/'current-wrapper.json').write_text(json.dumps(dict(test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),binary_port=8700,text_ports=[8800,8839],expected_assets=47,expected_prg=PRG,expected_disk=DISK,scope='Existing43capture all-mode/file-restart scenario; exactsource/history/font/pixels. Current wrapper extends only documented authenticatedFE spans. Exact frozenPGCv3FE[EB69,FBA9)4160B also permitted; all other16MiB exact. Only declared published catalog bit7 normalized via tools/overlay_catalog_policy; raw fields/sealed assets remain exact. IRQevents are not physicalchords; no lifecycle/timingclaim.'),indent=2)+'\n')
 results=[]
 for phase in (('editing','restart','fold')if a.phase=='both'else(a.phase,)):
  if not a.verify:free_ports()
  results.append(engine.evaluate(e,phase)if a.verify else engine.execute(e,phase))
  if not a.verify:free_ports()
 (e/'result.json').write_text(json.dumps(dict(status='passed',identity=json.loads((e/'freeze.json').read_text()),phases=[dict(phase=r['phase'],frames=len(r['frames']),pixels=r['pixels'],attributes=r['attributes'],readonly_intervals=r['whole16MiB_readonly_intervals'])for r in results],limits='No physical keyboard, hardware timing, ReadyOS suspend/resume or staged-renderer claim.'),indent=2)+'\n')
 print('DONE',e,flush=True)
if __name__=='__main__':main()
