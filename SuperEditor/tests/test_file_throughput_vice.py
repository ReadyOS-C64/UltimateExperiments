"""End-to-end Open/Save settled-cost qualification; private8500/text8600, no sharedmake.

Explicit PC/SP public-input seam accepts RETURN from ui3/owner1, never the
F7 command dispatcher. Real bounded job9 and foreground rendering complete.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,socket,subprocess,zipfile
import test_display_timing_vice as timing
import test_reu_capacity_vice as capacity
from test_fold_retention_vice import Captured
from test_geos_navigation_vice import object_bytes
from d81_image import D81Image
import vice_plan
ROOT=timing.ROOT
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T140326098391Z/fixture'
OUTNAME=b'IOOUT'

class Plan(timing.Plan):
 modal_return=False
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8500;p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False)
  return p
 def condition(self,ui):
  # Parent timing's RETURN specialcase is F7ui2. Here only the actual File
  # dialog3/owner1 is legal before accepting a filename.
  if self.modal_return and ui==2:ui=3
  text=super().condition(ui)
  if ui==3:
   old=f'(@cpu:${self.s["se_f_owner"]:04x} == $00)';assert text.count(old)==1;text=text.replace(old,old.replace('$00','$01'))
   # Backgroundstyling is intentionally deferred whileFILE owns the union.
   deferred=f' && (@cpu:${self.s["se_st_request"]:04x} == $00)';assert text.count(deferred)==1;text=text.replace(deferred,'')
  return text
 def calibrate(self):
  p=timing.PROBE;assert p>=self.cold_end and p+8<0x1000
  self.raw('stopwatch_calibration',['delete',f'break exec ${self.idle_pc:04x} if {self.condition(0)}','x','delete',f'> {p:04x} '+bytes([0xea]*8).hex(' '),f'logname "{self.out}/calibration.log"','log on',f'registers PC=${p:04x}, SP=$ff, FL=$24','stopwatch reset',f'until ${p+8:04x}','stopwatch','registers','log off',f'registers PC=${self.s["se_idle"]:04x}, SP=$ff, FL=$20','x'])
 def filename(self,ident,action,name):
  self.modal(ident+'_dialog',action)
  self.send(ident+'_filename',b'\x14'*16+name,ui=3,owner=1)
  self.memory(ident+'_modal','se_e_ui',3);self.memory(ident+'_fileowner','se_f_owner',1)
  self.memory(ident+'_requested_length','se_f_name_len',len(name));self.memory(ident+'_requested_name','se_f_name',name)
 def measure_file(self,ident,data,*,current,node,saved,caret):
  self.modal_return=True
  try:super().measure(ident,data,0,key=13,ui=0,category='actual-modal-file-'+ident)
  finally:self.modal_return=False
  self.measurements[-1].update(before_ui=3,before_owner=1,current=current.decode(),node=node,saved=saved,caret_expected=caret)
  for n,v,w in [('se_hot_pending',0,1),('se_h_current',node,4),('se_h_saved',saved,4),('se_hot_caret',caret,3)]:self.memory(ident+'_verified_'+n,n,v,w)


def unpack_catalog(e):
 # Host reference only, reconstructed from this immutable D81's actual pack.
 pack=(e/'font-pack.bin').read_bytes();root=e/'genuine';root.mkdir();faces=[]
 timing.native.previous.pack_catalog(pack,(e/'native8.bin').read_bytes())
 for i in range(pack[5]):
  row=pack[32+i*16:48+i*16];at=int.from_bytes(row[8:11],'little');length=int.from_bytes(row[11:13],'little');raw=pack[at:at+length]
  p=root/f'face-{i:02d}.bin';p.write_bytes(raw);faces.append(dict(namespace='GEOS-system-source'if row[0]==2 else'GEOS-font-file',point_size=row[3],native_family_id=int.from_bytes(row[1:3],'little'),files={'font.bin':p.name},raw_sha256=hashlib.sha256(raw).hexdigest()))
 (root/'catalog.json').write_text(json.dumps(dict(faces=faces),indent=2)+'\n')


def freeze(base):
 e=timing.native.freeze(base);out=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-file-throughput-native');shutil.move(e,out);unpack_catalog(out);return out


def scenario(e,reopen=False):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.boot();n.calibrate();data=timing.native.live.grid.fixture();edited=timing.native.live.grid.native_text('Q')+data
 if reopen:
  n.filename('reopen','O',OUTNAME);n.measure_file('reopen423',edited,current=OUTNAME,node=1,saved=1,caret=0)
 else:
  n.filename('open','O',b'DIVERSE');n.measure_file('open422',data,current=b'DIVERSE',node=1,saved=1,caret=0)
  n.send('type_Q',timing.native.live.grid.native_text('Q'));n.memory('pending_Q','se_hot_pending',1)
  n.filename('saveas','A',OUTNAME);n.memory('saveas_pending_flushed','se_hot_pending',0)
  n.measure_file('saveas423',edited,current=OUTNAME,node=2,saved=2,caret=1)
 return n


def extra(n,result):
 e=n.e;s=n.s;images=timing.native.live.grid.reu_images(n.out/'run');pack=(e/'font-pack.bin').read_bytes();details=[]
 calibration=(n.out/'calibration.log').read_text(encoding='utf-8-sig');clocks=[int(v)for v in re.findall(r'Stopwatch:\s*(\d+)',calibration,re.I)];assert len(clocks)==1 and 16<=clocks[0]<=64,clocks
 assert re.search(r'\.C:0f08',calibration,re.I),'exact calibration stop'
 for item,measured in zip(n.measurements,result['measurements']):
  ident=item['id'];log=(n.out/('stopwatch-'+ident+'.log')).read_text(encoding='utf-8-sig');registers=re.findall(r'(?m)^\.;([0-9a-f]{4})\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+([0-9a-f]{2})\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+([01]{8})',log,re.I)
  assert len(registers)==2 and int(registers[0][0],16)==timing.PROBE and registers[0][1].lower()=='ff' and int(registers[0][2],2)==0x20
  assert int(registers[-1][0],16)==n.idle_pc and registers[-1][1].lower()=='ff' and not(int(registers[-1][2],2)&4),(ident,'exact IRQenabled settledstop')
  ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();before=(n.out/'captures'/(ident+'-before-ram.bin')).read_bytes();f=Captured(s,ram,colors,e);reu=images[ident]
  assert len(reu)==16*1024*1024 and f.get('se_reu_banks',2)==256
  assert before[s['se_e_ui']]==3 and before[s['se_f_owner']]==1,(ident,'real file modal before public input')
  assert f.get('se_e_ui',1)==0 and f.get('se_mode',1)==0 and f.get('se_hot_pending',1)==0
  assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==item['current'].encode()
  assert [f.get('se_h_current',4),f.get('se_h_saved',4),f.get('se_hot_caret')]==[item['node'],item['saved'],item['caret_expected']]
  assert f.get('se_h_dirty',1)==0 and f.get('se_h_end',2)==(75 if item['node']==2 else 0)
  assert not any(f.get(k,1)for k in ['se_e_error','se_f_owner','se_doc_read_locks','se_fs_owned','se_n_owned','se_doc_busy'])and ram[0x98]==0
  assert f.read(0xcb80,64)==(e/'editor-defaults.bin').read_bytes()
  for i,h in enumerate(f.read(0xcbc1,2)):
   bank=ram[s['se_reu_map']+h];assert h and bank and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+bank]==0xfd
   part=pack[i*65536:(i+1)*65536];assert reu[bank*65536:bank*65536+len(part)]==part
  if item['node']==2:
   journal=object_bytes(f,reu,f.read(s['se_h_token'],5),75);assert journal[:6]==b'SEH1\1\1'and journal[64:67]==bytes([2,1,0]);(n.out/'saved-journal.bin').write_bytes(journal)
  details.append(dict(id=ident,bytes=len(bytes.fromhex(item['source'])),cycles=measured['emulated_cycles'],cycles_per_byte=measured['emulated_cycles']/len(bytes.fromhex(item['source'])),counter_deltas=measured['counter_deltas'],source_sha256=hashlib.sha256(bytes.fromhex(item['source'])).hexdigest(),current=item['current']))
 baseline=D81Image((e/'initial-fixtures.d81').read_bytes());disk=D81Image((e/'working.d81').read_bytes());expected=timing.native.live.grid.native_text('Q')+timing.native.live.grid.fixture()
 assert disk.read(OUTNAME,kind=1).data==expected
 for entry in baseline.entries():
  a,b=baseline.read(entry.name),disk.read(entry.name);assert a.data==b.data and a.sectors==b.sectors,(entry.name,'preexisting file bytes/sectors changed')
 assert {v.name for v in disk.entries()}=={v.name for v in baseline.entries()}|{OUTNAME}
 text=(n.out/'resources.log').read_text(encoding='utf-8-sig');assert re.search(r'Drive8TrueEmulation[^\r\n]*\b0\b',text)and'Warp mode is on.'in text
 launch=(n.out/'run/vice_stdout.log').read_text(encoding='utf-8-sig');assert' -trapdevice8 'in launch and' +drive8truedrive 'in launch
 result=dict(status='passed',identity=result['identity'],measurements=details,calibration_cycles=clocks[0],calibration_stop_pc='0f08',video='PAL VICIIModel0',irq_enabled_for_IO=True,warp=True,IEC_traps=True,true_drive=False,saved_bytes=423,source_mode=0,modal_before=dict(ui=3,owner=1),complete=dict(ui=0,owner=0),scope='Emulated cycles from explicit PC0F00/SPFF/FL20 JSRpublicinput RETURN through realmodaldispatch/job9/render/idle. Includes frontend/CRC/REU/IRQ/VIC; excludes filename entry, keyboard delivery and physical drive latency. Cycles/byte is end-to-end service work, not rawIEC bandwidth. No worstcase bound.')
 (n.out/'throughput-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def free_ports():
 for p in [8500,*range(8600,8640)]:
  with socket.socket()as sock:sock.bind(('127.0.0.1',p))


def execute(e,reopen=False):
 free_ports();n=scenario(e,reopen);plan=n.plan();(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ['tests','tools']:
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 print('NATIVE',e,'steps',len(n.steps),'IRQ',n.keys,'captures',len(n.measurements),flush=True);capacity.run_owned_plan(plan,n.out,timeout=1800);free_ports();return extra(n,timing.evaluate(n))


def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args()
 if not a.run:print('Prepared actualmodal load/save/reopen PAL cycles; own8500/text8600.');return
 e=freeze(a.fixture.resolve());first=execute(e);fresh=e/'fresh-reopen';fresh.mkdir()
 for p in e.iterdir():
  if p.is_file():shutil.copy2(p,fresh/p.name)
 shutil.copytree(e/'genuine',fresh/'genuine');before=(fresh/'working.d81').read_bytes();second=execute(fresh,True);assert(fresh/'working.d81').read_bytes()==before,'read-only freshreopen modifieddisk'
 summary=dict(status='passed',identity=json.loads((e/'freeze.json').read_text()),initial=first,fresh_reopen=second,VICE_closed=True,ports=[8500,8600],no_product_build_or_edits=True)
 (e/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print('DONE',e,flush=True)
 for d in first['measurements']+second['measurements']:print(json.dumps(d),flush=True)
if __name__=='__main__':main()
