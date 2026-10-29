"""Same actual root recovery gate, strict memo-slot policy and dead-span poison."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_row_backup_candidate as candidate
import test_geos_incremental_recovery as original

def run(out,fixture):
 # The archived old recovery verifier predates managed catalog bit7. Normalize
 # only the slot equality test, exactly as the published catalog identity ABI.
 text=inspect.getsource(original.run)
 old="f.m.read(f.s['image_slot']+i)==slot";new="(f.m.read(f.s['image_slot']+i)&1)==slot"
 assert text.count(old)==1
 old_data="Ordinary text here.\\rSecond source line.\\rThird source line.\\rLast."
 new_data="# Heading words.\\rSecond source line.\\rThird source line.\\rLast."
 assert text.count(old_data)==1
 text=text.replace(old_data,new_data) # current R27 deliberately bypasses R28 for plain prose
 original.fold.Fixture=type('PoisonRecovery',(candidate.PoisonMixin,original.fold.Fixture),{})
 ns=dict(vars(original));exec(compile(text.replace(old,new),str(Path(__file__))+'::managed-slot','exec'),ns)
 (out/'verifier-adaptation.json').write_text(json.dumps(dict(original_sha256=hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),old=old,new=new,scope='Slot dispatch equality only; original catalog identity, independent pixels/canonical/full16MiB/exactFE guard unchanged.'),indent=2)+'\n')
 ns['run'](out,fixture)
 result=json.loads((out/'result.json').read_text());result['backup_poison']=list(candidate.observations)
 result['extra']=extra(out/'extra',fixture)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

def extra(out,fixture):
 out.mkdir();geos=original.geos;frozen,identity=geos.freeze(out,fixture)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=original.fold.retention.runner(out);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 raw=geos.native_text('# Heading words.\rSecond source line.\rThird source line.\rLast.');cases=[]
 def verify(f,data,tag):
  before=f.reu();canonical=f.canonical();f.render();assert f.canonical()==canonical and f.merged()==data
  eb,ea,_,_=original.semantic.expected(f,data,fonts)
  assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'independentpixels')
  actual=f.reu();_,bank=f.raw_cache();cursor=0
  for a,b in [(bank*65536,bank*65536+64),(bank*65536+0x200,bank*65536+0xd568)]:
   assert actual[cursor:a]==before[cursor:a],(tag,'strict16MiB',cursor,a);cursor=b
  assert actual[cursor:]==before[cursor:],(tag,'backups/font/foreign')
  assert f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job','se_e_draw_busy'])
  geos.png(eb,ea,out/(tag+'.png'))
 for action,error in [('source-revision',0x74),('cache-epoch',0x18),('cache-map',0x18),('cache-owner',0x18)]:
  f=original.fold.Fixture(out,frozen,dll,True)
  try:
   f.source(raw);f.command(99);f.position(5);f.render();f.key(geos.native_text('Q')[0]);changed=raw[:5]+geos.native_text('Q')+raw[5:];canonical=f.canonical()
   f.call('se_editor_render')
   for count in range(10000):
    assert f.get('se_e_job',1)==11,(action,'ended')
    if f.m.read(0x9134)==12 and f.m.read(0x9135)==21:break
    f.call('se_editor_service')
   else:raise AssertionError('no rebase')
   handle=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+handle)
   if action=='source-revision':at=f.s['se_r_revision']
   elif action=='cache-epoch':at=f.s['se_gc_epoch']
   elif action=='cache-map':at=f.s['se_reu_map']+handle
   else:at=f.s['se_reu_logical_owner']+handle
   old=f.m.read(at);f.m.write(at,old^1);reu=f.reu()
   f.call('se_editor_service');f.settle(error=error)
   assert f.reu()==reu and f.canonical()==canonical and f.merged()==changed,(action,'failedcheckedstep wrote canonical/REU')
   assert not any(f.get(n,1)for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job','se_e_draw_busy'])
   f.m.write(at,old);f.put('se_e_error',0,1);verify(f,changed,action)
   f.command(16);verify(f,raw,action+'-undo');f.command(17);verify(f,changed,action+'-redo')
   cases.append(dict(tag=action,error=error,source_bytes=len(changed),frames=3));print('EXTRA PASS',cases[-1],flush=True)
  except BaseException:
   (out/(action+'-failure-ram.bin')).write_bytes(f.read(0,65536));(out/(action+'-failure-reu.bin')).write_bytes(f.reu());raise
  finally:f.close()
 return cases

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/geos-row-backup-recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 run(out,a.fixture.resolve())
