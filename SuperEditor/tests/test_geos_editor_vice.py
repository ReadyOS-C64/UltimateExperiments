"""Real D81/IRQ editor GEOS preview and80-column comparison; owned7700 only."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
import test_grid_editor_vice as grid
import test_geos_editor as geos
from test_fold_retention_vice import Captured
ROOT=grid.ROOT
sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,vice_plan
from vice_config import step
from png_pixels import read_png

class Plan(grid.GridPlan):
 def snapshot(self,ident,data,mode,ui=0):
  self.idle(ident,ui=ui,owner=1 if ui==3 else 0)
  self.memory(ident+'_actualmode','se_mode',mode)
  self.cases.append(dict(id=ident,source=data.hex(),mode=mode,ui=ui))
  captures=self.out/'captures';captures.mkdir(exist_ok=True)
  expected=[('se_e_ui',ui),('se_e_job',0),('se_e_redraw',0),('se_e_draw_busy',0),('se_doc_read_locks',0),('se_f_owner',1 if ui==3 else 0),('se_input_nmi_pending',0)]
  condition=' && '.join(f'(@cpu:${self.s[k]:04x} == ${v:02x})' for k,v in expected)
  condition+=f' && (@cpu:${self.s["se_input_head"]:04x} == @cpu:${self.s["se_input_tail"]:04x}) && (@cpu:$00c6 == $00)'
  stop=[f'break exec ${self.idle_pc:04x} if {condition}','x','delete']
  self.raw(ident+'_coherent',['delete',*stop,'step $10000',*stop,f'screenshot "{self.out}/native-{ident}.png" 2',f'bsave "{captures}/{ident}-ram.bin" 0 $0000 $cfff',f'bsave "{captures}/{ident}-colors.bin" 0 $d800 $dbe7'])
  self.steps.append(step(ident+'_reu','dump.reu',mode='full',stage_tag=ident+'_reu'))
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=7700;return p

def freeze():
 sourcezip=ROOT/'build/geos-native-product.zip'
 with zipfile.ZipFile(sourcezip,'w',zipfile.ZIP_DEFLATED) as z:
  for folder in ['src','cfg']:
   for p in (ROOT/folder).rglob('*'):
    if p.is_file():z.write(p,p.relative_to(ROOT))
  for p in ['Makefile','tests/test_geos_editor_vice.py']:z.write(ROOT/p,p)
 grid.NAMES=list(cpu_editor.NAMES);e=grid.freeze(ROOT/'build',sourcezip,wide_colors=True)
 target=ROOT/'agentsworking/evidence/M7'/(e.name.replace('-grid-editor-native','-geos-editor-native'));shutil.move(e,target);grid.package(target)
 for name in geos.GEOS_FONTS:shutil.copy2(ROOT/'assets/fonts/generated'/name,target/name)
 return target

def merged(f,reu):
 s=f.s
 def obj(identity,offset,length):
  result=bytearray()
  while length:
   n=min(length,65536-(offset&65535));handle=f.ram[s['object_extents']+identity*16+(offset>>16)];bank=f.ram[s['se_reu_map']+handle]
   result+=reu[bank*65536+(offset&65535):bank*65536+(offset&65535)+n];offset+=n;length-=n
  return bytes(result)
 source=bytearray()
 for i in range(f.get('se_doc_root_count',1)):
  root=f.read(s['se_doc_roots']+i*8,8);leaf=obj(f.get('se_doc_meta',1),root[0]*1024,root[1]*16)
  for j in range(root[1]):
   p=leaf[j*16:(j+1)*16];source+=obj(p[0],int.from_bytes(p[3:6],'little'),int.from_bytes(p[6:9],'little'))
 assert len(source)==f.get('se_doc_length')
 if f.get('se_hot_pending',1):
  base=f.get('se_hot_base');old=f.get('se_hot_old_length',2);left=f.get('se_hot_left',2);right=f.get('se_hot_right',2)
  raw=f.read(0x9200,left)+f.read(0x9200+right,2048-right)
  assert len(raw)==f.get('se_hot_length',2)
  source[base:base+old]=raw
 return bytes(source)

def evaluate(e):
 out=e/'editing';s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=grid.reu_images(out/'run');palette={};results=[]
 fonts={name:(e/name).read_bytes() for name in geos.GEOS_FONTS};fonts['native8.bin']=(e/'grid80.seo').read_bytes()[36+0xc00:36+0x1000]
 for c in cases:
  ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,e);data=bytes.fromhex(c['source'])
  assert merged(f,images[ident])==data,(ident,'mergedsource')
  assert ram[0xc600:0xca00]==bytes((i*73+29)&255 for i in range(1024)),(ident,'shim')
  assert all(f.get(n,1)==0 for n in ['se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks']),(ident,'idle')
  assert f.get('se_f_owner',1)==(1 if c['ui']==3 else 0),(ident,'owner')
  if c['mode']==3 and c['ui']==3:
   bits,attrs,lines=geos.body_model(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'))
   ui=grid.UI(grid.source40(data,f.get('se_v_top'),f.get('se_hot_caret')))
   listing=[f.read(s['se_fd_list_names']+i*16,f.read(s['se_fd_list_lengths']+i,1)[0]) for i in range(f.get('se_fd_list_count',1))]
   ui.file_dialog(f.get('se_f_device',1),f.read(s['se_f_name'],f.get('se_f_name_len',1)),listing,f.get('se_fd_list_index',1))
   bits,attrs=geos.with_chrome(bits,attrs,ui.matrix,ui.colors,fonts['native8.bin'],(1,4,38,19))
  elif c['mode']==3:bits,attrs,lines=geos.expected(f,data,fonts)
  else:
   rows=grid.anchors(data,f.get('se_v_top'),80);plan=grid.wide_semantics(data,rows,80);font=(e/'grid80.seo').read_bytes()[36+0x800:36+0xc00]
   bits,attrs,_=grid.body_model(data,f.get('se_v_top'),f.get('se_hot_caret'),80,False,0,font,plan)
   matrix,colors_,popup=geos.grid.logical_ui(f,data);bits,attrs=geos.with_chrome(bits,attrs,matrix,colors_,fonts['native8.bin'],popup)
  assert ram[0x6000:0x7f40]==bits,(ident,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x6000:0x7f40],bits)) if a!=b))
  assert ram[0x4000:0x43e8]==attrs,(ident,'attrs')
  w,h,pixels=read_png(out/f'native-{ident}.png');assert (w,h)==(384,272)
  for y in range(200):
   for x in range(320):
    at=(y//8)*40+x//8;ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attrs[at]>>4 if ink else attrs[at]&15;actual=pixels[(35+y)*w+32+x]
    assert actual==palette.setdefault(color,actual),(ident,'nativepixel',x,y)
  results.append(dict(id=ident,mode=c['mode'],source_bytes=len(data),pixels=64000))
 assert len(set(palette.values()))==len(palette),'native palette roles alias'
 assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'read-onlyscenariochangedD81'
 result=dict(status='passed',scope='Actual D81 editor source view/GEOS font preview; raw Markdown stillvisible; nofullGEOSfeatureclaim.',frames=results,pixels=len(results)*64000)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result

def run(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()));data=grid.fixture();n.boot();n.open('diverse',b'DIVERSE');n.mode_to(2);n.snapshot('source80',data,2)
 n.typed('geos','mode hires');n.snapshot('geos-diverse',data,3)
 n.send('actualtype',grid.native_text('Q'));n.snapshot('geos-typed',grid.native_text('Q')+data,3)
 n.typed('actualundo','undo');n.snapshot('geos-undo',data,3)
 n.send('help',bytes([0x8b]),ui=1);n.snapshot('geos-help',data,3,1)
 n.send('closehelp',bytes([0x8b]));n.snapshot('geos-restored',data,3)
 n.modal('geos-open-dialog','O');n.snapshot('geos-dialog',data,3,3)
 n.send('geos-cancel-dialog',bytes([3]),owner=0);n.snapshot('geos-dialog-restored',data,3)
 p=n.plan();(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n')
 project=grid.synchronous_project(n.out);vice_plan.PROJECT=project
 build=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
 print('NATIVE '+str(e),flush=True);vice_plan.run_plan(p,n.out);evaluate(e)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--verify',type=Path);a=ap.parse_args()
 if a.verify:evaluate(a.verify)
 elif a.run:run(freeze())
 else:print('Prepared; use --run for actualownedVICE.')
