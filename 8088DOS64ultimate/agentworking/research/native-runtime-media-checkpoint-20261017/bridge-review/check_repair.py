from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P/'runtime';sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-counter-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists();os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import unittest,json,hashlib
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'runtime'))
from test_sequence_ui import *
t=unittest.TestCase();m,old,f=initial(t,admit=False)
try:
 enter(t,m);prepare(t,m,b'/usb1/Owned/NOTSTART.IMG')
 blob=(ROOT/'runtime/bridge/bridge.prg').read_bytes();base=int.from_bytes(blob[:2],'little');needle=bytes([0xa9,0,0xa2,8,0x9d])+AC['_ac_result'].to_bytes(2,'little')+bytes([0xca,0x10,0xfa]);assert blob.count(needle)==1;clear_pc=base+blob.index(needle)-2
 release_enter(t,m,clear_pc,40000000)
 m.put(AC['_ac_result'],bytes([2,0,6,0,1,1,0,1,0]))
 until(t,m,AC['ac_entry'],1000000);t.assertEqual(m.get(AC['_ac_result'],9),bytes(9))
 before=L.bulk_model_commands(m.m);ctx=m.get('dos64_files_state_start',25);m.p('hdb_active',1)
 r=L.dos64_run(m.m,BR['modal_wait'],20000000);t.assertEqual(r.status,2,(r.status,hex(r.regs.pc)));result=m.get(BE['br_last'],9);diag={'runtime':hashlib.sha256((ROOT/'runtime/work/build/dos64.prg').read_bytes()).hexdigest(),'bridge':hashlib.sha256((ROOT/'runtime/bridge/bridge.prg').read_bytes()).hexdigest(),'result':result.hex(),'bridge_success':m.g(BE['br_success']),'bridge_resume':m.g(BE['br_resume']),'native_diag':m.g('dos64_native_diag'),'UI_can_resume':m.g(UI['_mu_view']+258),'hdb_active':m.g('hdb_active'),'FILE_count_unchanged':L.bulk_model_commands(m.m)==before,'C25_unchanged':m.get('dos64_files_state_start',25)==ctx}
 t.assertEqual((diag['bridge_success'],diag['bridge_resume'],diag['UI_can_resume'],diag['hdb_active']),(0,0,0,1),diag)
 t.assertEqual(diag['native_diag'],0xe1);t.assertEqual(diag['result'],'00'*9);t.assertTrue(diag['FILE_count_unchanged']);t.assertTrue(diag['C25_unchanged'])
 rejected=m.call('modal_release',2000000);diag['actual_native_release_rejected']=bool(rejected.regs.p&1);t.assertTrue(diag['actual_native_release_rejected']);diag['scope']='actual CIA/private WAIT+controller pre-entry rejection+stale result seeded BEFORE actual bridge clear; rejected entry now E1/noResume; forced hdb_active fault, no guest escape; no worker operation began'
 (ROOT/'REPAIR_CHECK.json').write_text(json.dumps(diag,indent=2)+'\n')
finally:m.close()
