from pathlib import Path
import ctypes as C,json
from config_fixture import F,L,Regs
P=Path.cwd();rows=[]
for home,expected in [(b'/Home',4),(b'/Moved installation',7)]:
 f=F(auto=False)
 try:
  L.dir_model_path(f.m,b'/');L.dir_model_path(f.m,home)
  L.dir_model_row(f.m,b'/',16,home[1:],len(home)-1)
  originals={p.name:p.read_bytes() for p in (P/'generated').iterdir() if p.is_file()}
  for name,data in originals.items():L.bulk_model_seed(f.m,home+b'/'+name.encode(),data,len(data))
  assert originals['DOS64.CFG'][8:136].split(b'\0')[0]==b'/Home'
  guard=f.guard;first=bytearray(guard)
  a=f.labels['__CONFIG_HIGH_RUN__'];n=f.labels['__CONFIG_HIGH_TOTAL__'];first[a:a+n]=b'\1'*n
  def run(target,g):
   L.dos64_clear_writes(f.m);r=L.dos64_run(f.m,target,100000000)
   assert (r.status,r.regs.pc,r.regs.sp)==(2,target,0xfd),(r.status,hex(r.regs.pc),r.regs.sp)
   assert r.stack<120 and L.browser_bad_write(f.m,g)==65536
   assert f.read('sp',2)==b'\xff\xcf'
  L.dos64_poke(f.m,0,0x2f);L.dos64_poke(f.m,1,0x37)
  L.dos64_set_regs(f.m,Regs(0x080d,0xfd,0x71,0x82,0x93,0x2c,0,0))
  run(f.labels['config_poll_return'],bytes(first))
  def poll():
   L.dos64_cia_clock_advance(f.m,1024)
   run(f.labels['config_poll_loop'],guard);run(f.labels['config_poll_return'],guard)
  def ready():
   for _ in range(4000):
    poll();state=f.read('_cg_result',8)[0]
    if state not in [1,3] and not(state==2 and f.read('_db_result',1)==b'\1'):return state
   raise AssertionError('bounded actual native UI')
  def key(row,col):
   keys=bytearray(8);keys[row]|=1<<col;L.dos64_host_input_model_keys(f.m,bytes(keys));poll()
   L.dos64_host_input_model_keys(f.m,bytes(8));poll();return ready()
  assert ready()==2
  assert key(0,1)==2
  result=key(0,4);assert result==expected,(home,result)
  assert f.read('_rm_result',1)==b'\0' and f.read('_cp_result',1)==b'\0'
  assert f.call('_cg_closed_quiet')==1
  commands=f.commands();assert commands.count(b'\1\3')==2
  assert not any(t==2 and op in [2,0x22] for t,op in commands)
  for name,data in originals.items():
   out=C.create_string_buffer(len(data));assert L.bulk_model_read(f.m,home+b'/'+name.encode(),out,len(data)) and out.raw==data
  if home!=b'/Home':
   assert f.read('_ri_result',8)[1]==5 and f.read('_cg_result',8)[1:3]==b'\4\5'
   assert f.call('_cg_get')==0
   assert L.bulk_model_size(f.m,b'/Home/DOS64.CFG')==0xffffffff
  rows.append({'selected_home':home.decode(),'saved_home':'/Home','CG':list(f.read('_cg_result',8)),'RI':list(f.read('_ri_result',8)),'firmware_commands':[list(c)for c in commands],'original_files_unchanged':True,'native_entry':'SYS $080d from bank37','native_input':'CIA matrix Return then F1','mode':'model'} )
 finally:f.close()
(P.parent/'RESULT.json').write_text(json.dumps({'status':'REPRODUCED_V1_RELOCATION_GAP','groups':rows,'current_CONFIG_sha256':'3deb783d9d94848b7595310d174e6ce3490bcc19b2e4510d1852f901f048635d','actual_SET_UP_CFG_unmodified':True,'physical':False,'fixed':False,'scope':'Same generated SETUP files at original and moved directory; actual CONFIG SYS and CIA UI; moved case refuses before media or publication.'},indent=2)+'\n')
