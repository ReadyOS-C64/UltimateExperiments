"""Current46-asset all-mode acceptance wrapper; own8700/text8800 only.

Uses the existing43-capture scenario and exact independent source/pixel/file/
history/font oracles. Only port/lifetime configuration and frozen declared FE
cache extents differ from the historical39-asset engine. No product edits.
"""
from pathlib import Path
import argparse,hashlib,inspect,json,shutil,zipfile,socket
import test_standalone_acceptance_vice as engine
from overlay_catalog_policy import catalog_identity
ROOT=engine.ROOT
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T112646631270Z/fixture'
PRG='bdef9dd027940c0eb52afe0ab7d41cf6448f88a7b20fca07646b544698f4d2c6'
DISK='b3813f5d4fae6bf81e33524692b7aa62a70259b82bde856897b825f8a5b3fced'

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
 new="[(0,64),(0x200,0xb200),(0xb200,0xd528),(0xd528,0xe568),(0xe568,0xea88),(0xea88,0xeb69)]"
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
 target=ROOT/'agentsworking/evidence/M8'/e.name.replace('-geos-fold-native','-standalone46-native')
 target.parent.mkdir(parents=True,exist_ok=True);shutil.move(e,target)
 identity=json.loads((target/'freeze.json').read_text());assert len(identity['catalog'])==46
 with zipfile.ZipFile(target/'product-sources.zip')as z:
  contracts={n:z.read(n).decode()for n in ('src/render/geos/edit-cache.inc','src/render/geos/typing-font-cache.inc','src/render/geos/preview-cache.inc')}
 assert 'GEX_OLD_HEADER=$D528' in contracts['src/render/geos/edit-cache.inc']and'GEX_TAIL_END=$E568'in contracts['src/render/geos/edit-cache.inc']
 assert 'GTF_DATA=$E568'in contracts['src/render/geos/typing-font-cache.inc']and'GTF_META=$EA68'in contracts['src/render/geos/typing-font-cache.inc']
 assert 'PPC_META_REU=$EA88'in contracts['src/render/geos/preview-cache.inc']and'PPC_SIZE=225'in contracts['src/render/geos/preview-cache.inc']
 return target


def free_ports():
 for port in [8700,*range(8800,8840)]:
  with socket.socket()as s:
   try:s.bind(('127.0.0.1',port))
   except OSError as exc:raise AssertionError(f'owned port{port} is busy')from exc


def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--cpu-fixture',type=Path,default=DEFAULT);p.add_argument('--fixture',type=Path);p.add_argument('--verify',type=Path);p.add_argument('--phase',choices=['editing','restart','fold','both'],default='both');a=p.parse_args()
 patched=patch_engine()
 if not a.run and not a.verify:print('Prepared46assets,43captures,private8700/text8800; --run uses frozen112646 managed product.');return
 e=a.verify.resolve()if a.verify else a.fixture.resolve()if a.fixture else freeze(a.cpu_fixture.resolve())
 (e/'current-wrapper-evaluate.py').write_text(patched)
 (e/'current-wrapper.json').write_text(json.dumps(dict(test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),binary_port=8700,text_ports=[8800,8839],expected_assets=46,expected_prg=PRG,expected_disk=DISK,scope='Existing43capture all-mode/file-restart scenario; exactsource/history/font/pixels. Current wrapper extends only documented authenticatedFE spans. Only declared published catalog bit7 normalized via tools/overlay_catalog_policy; raw fields/sealed assets remain exact. IRQevents are not physicalchords; no lifecycle/timingclaim.'),indent=2)+'\n')
 results=[]
 for phase in (('editing','restart','fold')if a.phase=='both'else(a.phase,)):
  if not a.verify:free_ports()
  results.append(engine.evaluate(e,phase)if a.verify else engine.execute(e,phase))
  if not a.verify:free_ports()
 (e/'result.json').write_text(json.dumps(dict(status='passed',identity=json.loads((e/'freeze.json').read_text()),phases=[dict(phase=r['phase'],frames=len(r['frames']),pixels=r['pixels'],attributes=r['attributes'],readonly_intervals=r['whole16MiB_readonly_intervals'])for r in results],limits='No physical keyboard, hardware timing, ReadyOS suspend/resume or staged-renderer claim.'),indent=2)+'\n')
 print('DONE',e,flush=True)
if __name__=='__main__':main()
