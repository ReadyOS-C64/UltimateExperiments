"""Isolated actual R27 native8 CELL/STATUS helpers; fullRAM/REU oracle.

No shared build, renderer callbacks, font substitution, or native-cycle claim.
The real shared status micromodule and resident print/hex services are linked;
expected glyphs/status are independently reconstructed from canonical inputs.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,random,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from peddle import Machine
import test_geos_row as row
from test_editor_chrome import oracle as chrome_oracle,settings as chrome_settings
from redraw_model import native_text


def build(out):
 frozen=out/'fixture';frozen.mkdir();files=['src/render/geos/caret-ui.s','src/render/geos/caret-ui.inc','src/render/geos/caret-cache.inc','src/render/narrow/api8.inc','src/tui/editor-chrome40.s','src/tui/header40.s','src/editor/geometry.inc','src/platform.inc','src/tui/theme.inc','build/editor.prg','build/editor-report.json','cfg/overlay-r.cfg']
 hashes={}
 for name in files:
  p=frozen/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p);hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
 report=json.loads((frozen/'build/editor-report.json').read_text());assert hashes['build/editor.prg']==report['sha256']
 s=report['symbols'];(frozen/'build/editor-api.inc').write_text('; Minimal imports resolved by private immutable resident bindings.\n')
 names=['se_f_owner','se_overlay_frame','text_ptr','screen_ptr','se_print','se_hex_byte','se_ink_reverse','se_e_ui','se_e_error','se_e_text','se_e_text_length','se_hot_caret','se_hot_pending','se_h_dirty','se_h_fault','se_h_trimmed','se_sel_mark','se_v_col','se_v_cell']
 bindings=''.join(('.exportzp ' if n in ('text_ptr','screen_ptr') else '.export ')+n+'\n'+n+f'=${s[n]:04X}\n' for n in names)
 (out/'bindings.s').write_text(bindings);objects=[]
 for name,source in [('ui',frozen/'src/render/geos/caret-ui.s'),('chrome',frozen/'src/tui/editor-chrome40.s'),('header',frozen/'src/tui/header40.s'),('bindings',out/'bindings.s')]:
  o=out/(name+'.o');subprocess.run(['ca65','-g','-I',str(frozen/'src'),'-I',str(frozen/'build'),'-o',str(o),str(source)],check=True);objects.append(o)
 subprocess.run(['ld65','-C',str(frozen/'cfg/overlay-r.cfg'),'-o',str(out/'ui.bin'),'-Ln',str(out/'ui.lbl'),'-m',str(out/'ui.map'),*map(str,objects)],check=True)
 symbols={n:int(a,16)for a,n in re.findall(r'al ([0-9a-fA-F]+) \.(\w+)',(out/'ui.lbl').read_text())};s.update(symbols)
 dump=subprocess.check_output(['od65','--dump-segments',str(out/'ui.o')],text=True)
 sizes={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',dump,re.S)}
 assert not any(sizes.get(n,0)for n in ('BSS','ZEROPAGE','DATA')) and sizes['CODE']<=350
 font=(ROOT/'assets/fonts/generated/native8.bin').read_bytes();assert len(font)==1024
 (frozen/'native8.bin').write_bytes(font);hashes['native8.bin']=hashlib.sha256(font).hexdigest()
 (out/'sources.json').write_text(json.dumps(hashes,indent=2)+'\n');return s,sizes,hashes,font


def run(out,smoke=False):
 out.mkdir(parents=True);s,sizes,hashes,font=build(out);row.OUT=out;dll=row.runner();m=Machine()
 m.load(0,bytes((i*73+19)&255 for i in range(65536)))
 prg=(out/'fixture/build/editor.prg').read_bytes();m.load(int.from_bytes(prg[:2],'little'),prg[2:]);m.load(0xa000,(out/'ui.bin').read_bytes())
 m.load(0x4800,font);m.load(0xac00,bytes(v^0xA5 for v in font)) #prove actual4800,notdeclaredAC00
 frame=0x8880;column=0xcfe2;calls=peak=valid=invalid=foreign=status_calls=0
 codes=set();colors=set();coordinates=set()
 def read(a,n):
  b=C.create_string_buffer(n);dll.gr_read(m.handle,a,n,b);return b.raw
 def reu():
  b=C.create_string_buffer(16*1024*1024);dll.gr_reu(m.handle,len(b),b);return b.raw
 def invoke(entry,wanted,allow=(),a=0):
  nonlocal calls,peak
  m.write(0x1fe,0xfe);m.write(0x1ff,2);before=read(0,65536)
  for n,v in [('pc',s[entry]),('sp',0xfd),('p',0x24),('a',a),('x',0xa5),('y',0x5a)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
  n=dll.gr_run(m.handle,20000);assert n,('nonreturn',entry,hex(m.regs().pc));peak=max(peak,n);calls+=1
  after=read(0,65536);expected=bytearray(before)
  for address,values in wanted.items():expected[address:address+len(values)]=values
  for address in allow:expected[address]=after[address]
  assert after==expected,('fullRAM',entry,calls,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,expected))if a!=b))
  return m.regs()
 def bc(row_,col,code,fg,bg):return bytes([row_,col,code,fg,bg,0,0xac,0,0x60,0,0x40])
 def cell(row_,col,code,fg,bg,owner=0,change=None):
  nonlocal valid,invalid,foreign
  data=bytearray(bc(row_,col,code,fg,bg))
  if change is not None:data[change[0]]=change[1]
  m.load(frame,data);m.load(s['se_overlay_frame']+1,frame.to_bytes(2,'little'));m.write(s['se_f_owner'],owner)
  okay=owner<2 and data[0]<25 and data[1]<40 and data[3]<16 and data[4]<16 and data[5:]==bytes.fromhex('00ac00600040')
  want={};allow=()
  if owner>=2:foreign+=1;error=0xb2
  elif not okay:
   invalid+=1;error=0x90;want[s['text_ptr']]=frame.to_bytes(2,'little')
  else:
   valid+=1;error=0;codes.add(data[2]);colors.add((data[3],data[4]));coordinates.add((data[0],data[1]));at=data[0]*40+data[1];gp=0x4800+(data[2]&127)*8;bp=0x6000+at*8
   want={0x4000+at:bytes([(data[3]<<4)|data[4]]),bp:bytes(v^(255 if data[2]&128 else 0)for v in font[(data[2]&127)*8:(data[2]&127)*8+8]),s['text_ptr']:gp.to_bytes(2,'little'),s['screen_ptr']:bp.to_bytes(2,'little'),0x1fd:bytes([gp&255]),0x1fc:bytes([gp>>8])}
  r=invoke('se_gcc_cell',want,allow);assert r.a==error and bool(r.p&1)==bool(error),(r.a,r.p,data.hex(),owner)
 normal=dict(ui=0,error=0,caret=0,pending=0,dirty=0,mark=0,fault=0,trimmed=0,text=b'')
 def status(state,owner=4):
  nonlocal status_calls,foreign
  chrome_settings(m,s,state);m.write(s['se_ink_reverse'],0);m.write(s['se_f_owner'],owner)
  if owner!=4:
   r=invoke('se_gcc_status',{});assert r.a==0xb2 and r.p&1;foreign+=1;return
  matrix,colors=chrome_oracle(state);matrix=matrix[80:120];colors=colors[80:120]
  want={0x43c0:bytes((c<<4)|6 for c in colors),0xdbc0:colors,column:bytes([40])}
  want[0x7e00]=b''.join(bytes(v^(255 if code&128 else 0)for v in font[(code&127)*8:(code&127)*8+8])for code in matrix)
  allow=list(range(0x100,0x200))+[s[n]+i for n,w in [('text_ptr',2),('screen_ptr',2),('se_v_col',1),('se_v_cell',1)]for i in range(w)]
  r=invoke('se_gcc_status',want,allow);assert not r.p&1 and r.a==0;status_calls+=1
 try:
  old_reu=reu()
  for code in (0,32,65,127,128,160,255):cell(24,39,code,15,6)
  status(normal);print('FIRST8 PASS',flush=True)
  if not smoke:
   # All256raw/inverse bytes; each glyph crosses everyforeground/background.
   for code in range(256):
    for fg in range(16):cell((code+fg)%25,(code*13+fg)%40,code,fg,(code+fg)&15,owner=fg&1)
   # Everyphysicaltile, bothinverse forms; includes lasttile7F38..7F3F.
   for r in range(25):
    for c in range(40):
     for inv in (0,128):cell(r,c,((r*40+c)&127)|inv,(r+c)&15,(r*3+c)&15)
   for field,values in [(0,range(25,256)),(1,range(40,256)),(3,range(16,256)),(4,range(16,256)),(5,range(1,256)),(6,[v for v in range(256)if v!=0xac]),(7,range(1,256)),(8,[v for v in range(256)if v!=0x60]),(9,range(1,256)),(10,[v for v in range(256)if v!=0x40])]:
    for value in values:cell(24,39,255,15,6,owner=value&1,change=(field,value))
   for owner in range(2,256):cell(255,255,255,255,255,owner)
   states=[]
   for caret in (0,1,255,256,65535,65536,0xabcdef,0xffffff):
    for dirty,pending,mark in [(0,0,0),(1,0,0),(0,1,1),(1,1,1)]:states.append(normal|dict(caret=caret,dirty=dirty,pending=pending,mark=mark))
   for error in range(256):states.append(normal|dict(error=error))
   for fault,trimmed in [(1,0),(0,1),(0,256),(1,65535)]:states.append(normal|dict(fault=fault,trimmed=trimmed))
   for length in range(32):states.append(normal|dict(ui=2,text=(native_text('Mixed CASE 0123456789 ££ ')+b'\xff\xa0')[:length].ljust(length,b'Q')))
   for state in states:status(state)
   for owner in range(256):
    if owner!=4:status(normal,owner)
  assert reu()==old_reu,'whole16MiB REU changed'
  if not smoke:assert (len(codes),len(colors),len(coordinates))==(256,256,1000)
  result=dict(status='passed',calls=calls,valid_cells=valid,invalid_cells=invalid,foreignowners=foreign,status_cases=status_calls,coverage=dict(raw_codes=len(codes),color_pairs=len(colors),tile_coordinates=len(coordinates)),REU_sha256=hashlib.sha256(old_reu).hexdigest(),helper_code_bytes=sizes['CODE'],new_BSS=0,new_ZP=0,linked_helper_chrome_header_bytes=(out/'ui.bin').stat().st_size,peak_instructions=peak,source_sha256=hashes,guard='Full64KiBRAM every call; exactcellglyph/attr/frame/pointer/2stackbytes. STATUS allowsonly actualstatusoutput+existingpointer/Vcol/Vcell+CPUstack; header/body/catalog/shim/source exact. Whole16MiBREU unchanged.',scope='Isolatedactualassembler helper and real sharedstatus/residentprint; noeditor/native/timingclaim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:m.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args();run(a.out or ROOT/'build/geos-caret-ui'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),a.smoke)
