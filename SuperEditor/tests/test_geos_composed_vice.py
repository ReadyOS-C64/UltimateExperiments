"""Actual line+strip GEOS native display/layout probe; never an editable mode.

Private PRG/D81/ports7700+7800 only. Independent canonical line/bitmap/tile model,
actual CPU preflight, real VICE captures and full pixel checks.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
from redraw_model import native_text
from test_geos_glyphs import native
from test_geos_line import oracle as line_oracle
from test_geos_row import Fixture as RowModel,PALETTE
from vice_config import step
from vice_plan import run_plan
from png_pixels import read_png
from d81_image import D81Image
OUT=ROOT/'build/geos-composed'
SOURCES=['src/probes/geos-composed.s','src/probes/geos-composed-alias.s','src/render/geos/line.s','src/render/geos/row.s','src/render/geos/measure.s','src/render/geos/glyph.s','src/render/geos/assets.s','src/render/narrow/cell8.s','src/tui/header40.s','src/tui/text40.s','src/tui/petscii.s','src/tui/box40.s','src/tui/cell40.s']
FOOTER='GEOS display/layout PROBE - F6 Help'
HELP=[(6,5,'GEOS composition probe',7),(8,5,'Real line and strip services.',1),(9,5,'Packed font + native mono code.',1),(11,5,'Static display validation.',1),(12,5,'This is not an editable mode.',1),(15,5,'F6 closes this help window.',3)]
def run(a,**kw):return subprocess.run(list(map(str,a)),cwd=ROOT,check=True,**kw)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fixture():
 entries=[('# GEOS row + line primitives',1,2,1,0),('Mixed lower / UPPER: Wim. gjpqy keep their real proportional widths.',0,0,0,0),('Bold and italic combine; packet seams preserve word-wrap anchors.',0,0,0,0),('- Bullets and 1. numbers remain native source.',0,1,0,0),('1. Proportional text wraps at spaces; long words break safely.',0,0,0,0),('W'*60,0,0,0,0),('## BASIC and assembler use native8',1,2,1,0),('10 PRINT "MiXeD":REM Native8 code',0,0,0,1),('20 FOR I=1 TO 3:PRINT I:NEXT I',0,0,0,1),('entry: LDA #$2A  ; native8 mono',0,0,0,1),('       STA $D020 : RTS',0,0,0,1),('Native symbols: ',0,0,0,0),('Selection + caret invert once.',0,0,0,0)]
 data=bytearray();styles=bytearray();roles=bytearray();flags=bytearray();kinds=bytearray()
 for i,(text,style,role,flag,kind) in enumerate(entries):
  raw=native_text(text)+(bytes([0x5C,0x5E,0xA1,0xFF]) if i==11 else b'')
  st=bytearray([style])*len(raw);ro=bytearray([role])*len(raw);fl=bytearray([flag])*len(raw)
  if i==2:
   for a,b,s in [(0,4,1),(9,15,2),(16,23,3)]:st[a:b]=bytes([s])*(b-a)
  if kind:
   # Static fixture token roles, no claim of running the editor lexer here.
   for j,c in enumerate(raw):ro[j]=8 if 48<=c<=57 else 2 if c in [0xD0,0xCC,0xD3] else 0
  if i==12:
   fl[0:18]=bytes([2])*18;fl[12]|=4
  data+=raw+b'\r';styles+=st+b'\0';roles+=ro+b'\0';flags+=fl+b'\0';kinds+=bytes([kind])*(len(raw)+1)
 return dict(data=bytes(data),styles=bytes(styles),roles=bytes(roles),flags=bytes(flags),kinds=bytes(kinds))
def build():
 OUT.mkdir(parents=True,exist_ok=True);f=fixture();inc=[]
 for name,key in [('source','data'),('source_styles','styles'),('source_roles','roles'),('source_flags','flags'),('source_kinds','kinds')]:
  raw=f[key]+(b'\0' if key=='kinds' else b'');inc.append(name+':')
  for i in range(0,len(raw),24):inc.append('.byte '+','.join('$%02X'%v for v in raw[i:i+24]))
 inc+=['source_size='+str(len(f['data'])),'source_advances: .res 32,8'];(OUT/'geos-composed-fixture.inc').write_text('\n'.join(inc)+'\n');objs=[]
 for n in SOURCES:
  q=OUT/(Path(n).stem+'.o');run(['ca65','-g','-I',OUT,'-I','src','-I','src/probes','-o',q,n]);objs.append(q)
 run(['ld65','-C','src/probes/geos-composed.cfg','-o',OUT/'geos-composed.prg','-m',OUT/'geos-composed.map','-Ln',OUT/'geos-composed.lbl',*objs]);s={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(OUT/'geos-composed.lbl').read_text())};assert 0x801+len((OUT/'geos-composed.prg').read_bytes())-2<=0x4000
 (OUT/'fixture.json').write_text(json.dumps({k:v.hex() for k,v in f.items()},indent=2)+'\n');return s,f

def model(f,help_=False):
 data=f['data'];widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();adv=[8 if k else widths[native(v)]+(s&1)+(s&2) for v,s,k in zip(data,f['styles'],f['kinds'])];meta=[];start=0;y=16
 while True:
  kind=f['kinds'][start] if start<len(data) else 0
  if kind:y=(y+7)&~7
  w=line_oracle(data,adv,start,320 if kind else 316,0,0,-1,0);count=w['end']-start;assert count<=128
  meta.append([start,w['end'],w['next'],count,y,kind]);y+=8 if kind else 9;assert y<=192,(meta,y)
  if w['reason']==2:break
  start=w['next']
 out=bytearray(65536);out[0x4000:0x43E8]=b'\x16'*1000
 mock=object.__new__(RowModel);mock.font=(ROOT/'assets/fonts/generated/bsw9.bin').read_bytes();mock.widths=widths
 for row in range(2,24):
  runs=[]
  for start,end,next_,count,y,kind in meta:
   if not kind and y<row*8+8 and y+9>row*8:runs.append((data[start:end],f['styles'][start:end],f['roles'][start:end],f['flags'][start:end],2,y-row*8))
  assert len(runs)<=2
  out,_,_,_=mock.oracle(runs,row,(0,320,0,8),out)
 font=(ROOT/'assets/fonts/generated/native8.bin').read_bytes()
 def cell(row,col,code,color):
  out[0x6000+row*320+col*8:0x6000+row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in font[(code&127)*8:(code&127)*8+8]);out[0x4000+row*40+col]=(color<<4)|6
 for start,end,next_,count,y,kind in meta:
  if kind:
   for col,at in enumerate(range(start,end)):
    code=native(data[at]);flag=f['flags'][at];code^=128 if flag&1 else 0;code^=128 if flag&6 else 0;cell(y//8,col,code,PALETTE[f['roles'][at]])
 header=[0x5D if c=='|' else native(native_text(c)[0]) for c in '|File |Edit |View |Navigate|Block |Help|']
 rule=[0x6D if i==0 else 0x7D if i==39 else 0x71 if i in [6,12,18,27,34] else 0x40 for i in range(40)]
 for row,line in enumerate([header,rule]):
  for col,code in enumerate(line):cell(row,col,code,7 if row or col in [0,6,12,18,27,34,39] else 1)
 for col in range(40):cell(24,col,32,15)
 for col,value in enumerate(native_text(FOOTER),1):cell(24,col,native(value),15)
 if help_:
  for row in range(5,19):
   for col in range(3,37):
    ry=row-5;rx=col-3;code=32;color=1
    if ry==0:code=0x70 if rx==0 else 0x6E if rx==33 else 0x40;color=14
    elif ry==13:code=0x6D if rx==0 else 0x7D if rx==33 else 0x40;color=14
    elif rx in [0,33]:code=0x5D;color=14
    cell(row,col,code,color)
  for row,col,text,color in HELP:
   for i,value in enumerate(native_text(text)):cell(row,col+i,native(value),color)
 return bytes(out[0x6000:0x7F40]),bytes(out[0x4000:0x43E8]),meta

def cpu(s,f):
 cpp=OUT/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t gc_until(ZeroPagePeddle*m,uint16_t pc,uint64_t limit){for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==pc)return i+1;zeropage_peddle_step_instruction(m);}return 0;}
''');ext='.dylib' if sys.platform=='darwin' else '.so';p=OUT/('runner'+ext);run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',p]);lib=C.CDLL(str(p));lib.gc_until.argtypes=[C.c_void_p,C.c_uint16,C.c_uint64];lib.gc_until.restype=C.c_uint64;m=Machine();shim=bytes((i*73+29)&255 for i in range(1024));tail=bytes((i*31+7)&255 for i in range(192))
 try:
  m.load(0x801,(OUT/'geos-composed.prg').read_bytes()[2:]);m.load(0xC600,shim);m.load(0x7F40,tail);m.lib.zeropage_peddle_set_pc(m.handle,0x1000);m.lib.zeropage_peddle_set_sp(m.handle,0xFD);m.lib.zeropage_peddle_set_p(m.handle,0x24);used=lib.gc_until(m.handle,s['idle'],20_000_000);assert used,('cpu nonreturn',hex(m.regs().pc));read=lambda a,n:bytes(m.read(a+i) for i in range(n));assert read(s['probe_error'],1)==b'\0',('probe error',read(s['probe_error'],1),'line',read(0x8D00,80).hex(),'row',read(0x8880,20).hex(),'meta',read(0x8000,192).hex())
  bits,attrs,meta=model(f);actualmeta=read(0x8000,len(meta)*9);expected=b''.join(a.to_bytes(2,'little')+b.to_bytes(2,'little')+c.to_bytes(2,'little')+bytes([d,e,g]) for a,b,c,d,e,g in meta);assert actualmeta==expected,('metadata',actualmeta.hex(),expected.hex());assert read(0x6000,8000)==bits,('cpu bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(read(0x6000,8000),bits)) if a!=b));assert read(0x4000,1000)==attrs,('cpu attrs',next((i,a,b) for i,(a,b) in enumerate(zip(read(0x4000,1000),attrs)) if a!=b));assert read(0xC600,1024)==shim and read(0x7F40,192)==tail
  (OUT/'expected-body-bitmap.bin').write_bytes(bits);(OUT/'expected-body-attributes.bin').write_bytes(attrs);bits,attrs,_=model(f,True);(OUT/'expected-help-bitmap.bin').write_bytes(bits);(OUT/'expected-help-attributes.bin').write_bytes(attrs);(OUT/'expected-meta.bin').write_bytes(expected)
  m.write(s['probe_help'],1);m.lib.zeropage_peddle_set_pc(m.handle,s['paint']);m.lib.zeropage_peddle_set_sp(m.handle,0xFD);m.write(0x1FE,0xFE);m.write(0x1FF,2);assert lib.gc_until(m.handle,0x2FF,20_000_000)
  assert read(0x6000,8000)==bits and read(0x4000,1000)==attrs,('CPU help mismatch',next(((i,a,b) for i,(a,b) in enumerate(zip(read(0x4000,1000),attrs)) if a!=b),None))
  assert read(0xC600,1024)==shim and read(0x7F40,192)==tail
  assert read(0x801,len((OUT/'geos-composed.prg').read_bytes())-2)==(OUT/'geos-composed.prg').read_bytes()[2:],'immutable probe/source/font changed'
  return dict(instructions=used,lines=len(meta),source_bytes=len(f['data']),fullscreens=2,pixels=128000)
 finally:m.close()

def native_run(s,f):
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M7'/(stamp+'-geos-composed-native');e.mkdir(parents=True);shutil.copytree(OUT,e/'build');disk=e/'working.d81';p=e/'build/geos-composed.prg';r=run(['c1541','-format','geos primitives,gp','d81',disk,'-attach',disk,'-write',p,'geosprobe,p','-list'],capture_output=True,text=True);(e/'package.log').write_text(r.stdout+r.stderr);assert D81Image(disk.read_bytes()).read(b'GEOSPROBE',kind=2).data==p.read_bytes()
 shim=bytes((i*73+29)&255 for i in range(1024));tail=bytes((i*31+7)&255 for i in range(192));steps=[step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),step('shim','memory.write',start=0xC600,bytes_hex=shim.hex(' ')),step('tail','memory.write',start=0x7F40,bytes_hex=tail.hex(' ')),step('warp','monitor.command',command='raw: warp'),step('reu_before','dump.reu',mode='full',stage_tag='reu_before'),step('boot','input.sequence',keys=list(b'LOAD"GEOSPROBE",8,1\rRUN\r'),inter_key_delay_s=0.04)]
 def memory(n,at,data):
  data=data if isinstance(data,bytes) else bytes([data]);a=step(n,'assert.memory',start=at,end=at+len(data)-1,equals_hex=data.hex(' '));a['retry']=dict(max_attempts=1200,backoff_ms=50,jitter=False);steps.append(a)
 def capture(name,seq,help_):
  memory(name+'_ready',s['probe_ready'],1);memory(name+'_error',s['probe_error'],0);memory(name+'_seq',s['probe_sequence'],seq);memory(name+'_help',s['probe_help'],help_)
  steps.append(step(name+'_png','monitor.command',command=f'raw: screenshot "{e}/native-{name}.png" 2'));steps.append(step(name+'_ram','dump.memory_ranges',ranges=[dict(label='bitmap',start=0x6000,end=0x7F3F),dict(label='attributes',start=0x4000,end=0x43E7),dict(label='meta',start=0x8000,end=0x8000+len((OUT/'expected-meta.bin').read_bytes())-1),dict(label='fallback',start=0x4800,end=0x4BFF),dict(label='native8',start=0xA000,end=0xA3FF),dict(label='shim',start=0xC600,end=0xC9FF),dict(label='tail',start=0x7F40,end=0x7FFF)]))
 capture('geos-primitives',1,0);steps.append(step('show_help','input.sequence',keys=[0x8B],post_delay_s=0.12));capture('geos-help',2,1);steps.append(step('close_help','input.sequence',keys=[0x8B],post_delay_s=0.12));capture('geos-return',3,0);memory('shim_final',0xC600,shim);memory('tail_final',0x7F40,tail);steps.append(step('reu_after','dump.reu',mode='full',stage_tag='reu_after'))
 plan=dict(version=1,kind='vice_task_plan',plan_id='geos-composed-'+stamp,run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=7700,monitor_port_span=1,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=90,read_s=2),artifact_policy=dict(capture_screen=False,capture_state=False,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
 print('EVIDENCE '+str(e),flush=True);artifacts,manifest=run_plan(plan,e);return e

def verify(e,f):
 total=0;nativefont=(ROOT/'assets/fonts/generated/native8.bin').read_bytes()
 for name,kind in [('geos-primitives','body'),('geos-help','help'),('geos-return','body')]:
  stage=e/'run/stages'/(name+'_ram');bits=(stage/'bitmap.bin').read_bytes();attrs=(stage/'attributes.bin').read_bytes();assert bits==(e/f'build/expected-{kind}-bitmap.bin').read_bytes(),(name,'native bitmap');assert attrs==(e/f'build/expected-{kind}-attributes.bin').read_bytes(),(name,'native attrs');assert (stage/'meta.bin').read_bytes()==(e/'build/expected-meta.bin').read_bytes();assert (stage/'fallback.bin').read_bytes()==nativefont and (stage/'native8.bin').read_bytes()==nativefont
  assert (stage/'shim.bin').read_bytes()==bytes((i*73+29)&255 for i in range(1024)) and (stage/'tail.bin').read_bytes()==bytes((i*31+7)&255 for i in range(192))
  w,h,pixels=read_png(e/f'native-{name}.png');assert (w,h)==(384,272);rgb={}
  for y in range(200):
   for x in range(320):
    a=attrs[(y//8)*40+x//8];bit=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x&7));code=a>>4 if bit else a&15;color=pixels[(35+y)*w+32+x];assert color==rgb.setdefault(code,color),(name,x,y,'VIC');total+=1
  assert rgb[6]==pixels[0] and rgb[6][2]>max(rgb[6][:2]);assert min(rgb[1])>220 and min(rgb[7][:2])>220 and rgb[7][2]<128
 before=(e/'run/stages/reu_before/reu_reu_before_full.img').read_bytes();after=(e/'run/stages/reu_after/reu_reu_after_full.img').read_bytes();assert before==after
 review=e/'visual-review.json';reviewed=False
 if review.exists():
  reviewed=json.loads(review.read_text())['screenshots']=={n:sha(e/n) for n in ['native-geos-primitives.png','native-geos-help.png','native-geos-return.png']}
 result=dict(status='passed' if reviewed else 'passed-awaiting-direct-visual-review',evidence=str(e),prg_sha256=sha(e/'build/geos-composed.prg'),prg_bytes=(e/'build/geos-composed.prg').stat().st_size,source_bytes=len(f['data']),native_screens=3,native_REU_bytes_unchanged=len(before),direct_visual_review=reviewed,pixels_checked=total,attributes_checked=3000,shim_bytes=1024,catalog_tail_bytes=192,ports=dict(binary=7700,text_start=7800,text_end=7839),scope='Static actual line+strip composition native display/layout probe; no GEOS editing/mode/source-adapter/physical-key claim')
 (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result

def main():
 a=argparse.ArgumentParser();a.add_argument('--cpu-only',action='store_true');a.add_argument('--verify',type=Path);args=a.parse_args()
 if args.verify:return verify(args.verify,{k:bytes.fromhex(v) for k,v in json.loads((args.verify/'build/fixture.json').read_text()).items()})
 s,f=build();c=cpu(s,f);(OUT/'cpu.json').write_text(json.dumps(c,indent=2)+'\n');print('CPU '+json.dumps(c),flush=True)
 if not args.cpu_only:e=native_run(s,f);verify(e,f)
if __name__=='__main__':main()
