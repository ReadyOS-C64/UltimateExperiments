"""Actual R1 styles/cache/context gate against frozen resident; no shared make.

Builds only build/style-render and imports its newly assembled R1 through the
real overlay cache. The resident/root is frozen old code: no background job or
native screenshot claim. Synthetic valid plans deliberately style CR/EOF too,
proving the renderer's blank paths independently ignore them.
"""
from pathlib import Path
import hashlib,json,random,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from cpu_editor import startup
import cpu_editor,editor_fixture
from redraw_model import source40,screen_code,Screen,verify_screen,native_text
from overlays import wrap,HEADER
OUT=ROOT/'build/style-render'
FROZEN=ROOT/'agentsworking/evidence/M5/20261024T220215181032Z-header-cpu'
NAMES=['eedit','eplay','window','text40','menu40','engine','navigate','search','block','layout','fileio','aux']
STYLE_SYMBOLS=dict(se_st_descriptor=0x8CC9,se_st_generation=0x8CEA,se_st_valid=0x8CEC,se_st_request=0x8CED,
 se_st_cache_generation=0x8CC6,se_st_cache_valid=0x8CC8,se_st_cp_valid=0x47E3,se_st_cp_damage=0x47E4,se_st_cp_dirty=0x47E7)

def build():
 OUT.mkdir(parents=True,exist_ok=True)
 report=json.loads((FROZEN/'build/editor-report.json').read_text())
 assert report['sha256']=='33bf5e57d915d9a5763c52dd0fa78a012738f8e3df8cee41a3b8b41b5328d876'
 extra=['text_ptr','screen_ptr','tui_putc40','tui_color','box_rx','box_ry','tui_box_x','tui_box_y','tui_box_w','tui_box_h']
 symbols={n:v for n,v in report['symbols'].items() if n.startswith('se_') or n in extra};symbols.update(STYLE_SYMBOLS)
 api='\n'.join(f'{n} = ${v:04X}' for n,v in sorted(symbols.items()))+'\n.macro OVL_BINDING\n.byte '+','.join('$'+b for b in [report['resident_binding']['digest'][i:i+2] for i in range(0,32,2)])+'\n.endmacro\n'
 (OUT/'editor-api.inc').write_text(api)
 for name,src in [('renderer','src/overlays/editor40.s'),('header','src/tui/header40.s')]:
  args=['ca65','-g','-I',OUT,'-I',ROOT/'src','-o',OUT/(name+'.o')]
  if name=='header':args+=['-D','EDITOR_OVERLAY=1']
  subprocess.run(list(map(str,args+[ROOT/src])),check=True)
 subprocess.run(list(map(str,['ld65','-C',ROOT/'cfg/overlay-r.cfg','-o',OUT/'renderer.bin','-m',OUT/'renderer.map','-Ln',OUT/'renderer.lbl',OUT/'renderer.o',OUT/'header.o'])),check=True)
 payload=(OUT/'renderer.bin').read_bytes();assert len(payload)<=4096
 image=wrap(payload,0,1,api=(report['symbols']['se_overlay_call'],report['symbols']['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))
 (OUT/'text40.seo').write_bytes(image);return report,image

class Fixture(editor_fixture.EditorFixture):
 def __init__(self,report,image):
  self.report=report;self.s={**report['symbols'],**STYLE_SYMBOLS};self.m=Machine()
  self.assets={n:(FROZEN/f'build/overlays/{n}.seo').read_bytes() for n in NAMES};self.assets['text40']=image
  self.max_service=0;self.total_instructions=0
  self.shim=bytes((i*73+29)&255 for i in range(1024));self.m.load(0xC600,self.shim)
  startup(self.m,self.s,self.assets);self.settle()
 def keybytes(self):
  return self.read(self.s['se_doc_meta'],15)+self.read(self.s['se_doc_generation'],2)+self.read(self.s['se_r_revision'],4)+self.read(self.s['se_v_length'],3)+self.read(self.s['se_v_top'],3)+self.read(self.s['se_l_pan'],3)+self.read(self.s['se_reu_epoch'],2)+self.read(self.s['se_l_mode'],1)
 def publish(self,plan,generation=None):
  assert len(plan)==880;self.m.load(0x4400,plan);self.m.load(self.s['se_st_descriptor'],self.keybytes())
  self.put('se_st_generation',generation if generation is not None else (self.get('se_st_generation',2)+1)&65535,2)
  self.put('se_st_valid',1,1);self.put('se_st_request',0,1)
 def reu(self):return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,i) for i in range(32*65536))

def expected(f,data,plan=None):
 top=f.get('se_v_top');caret=f.get('se_hot_caret');marked=bool(f.get('se_sel_mark',1));anchor=f.get('se_sel_anchor')
 base=source40(data,top,caret,marked=marked,anchor=anchor,pending=bool(f.get('se_hot_pending',1)),dirty=bool(f.get('se_h_dirty',1)),error=f.get('se_e_error',1))
 matrix,colors=bytearray(base.matrix),bytearray(base.colors);matrix[80:960]=bytes([32])*880;colors[80:960]=bytes([1])*880
 lo,hi=sorted((anchor,caret)) if marked else (caret,caret);pos=top;rows=[];seen=None
 for row in range(22):
  rows.append(pos)
  end=data.find(b'\r',pos) if f.get('se_l_mode',1) else -1
  if end<0:end=len(data)
  for col in range(40):
   p=pos+f.get('se_l_pan')+col if f.get('se_l_mode',1) else pos
   if p>end:continue
   eof=p==len(data);cr=not eof and data[p]==13
   glyph=32 if eof or cr else screen_code(data[p]);ink=1
   if plan is not None and not eof and not cr:
    style=plan[row*40+col];glyph^=style&128;ink=style&15
   original=glyph
   if marked and lo<=p<hi:glyph^=128;ink=3
   if p==caret and seen is None:glyph=original^128;ink=7 if marked else 3;seen=(row,col)
   at=(row+2)*40+col;matrix[at]=glyph;colors[at]=ink
   if not f.get('se_l_mode',1):
    if eof:break
    pos+=1
    if cr:break
  if f.get('se_l_mode',1):pos=end+1 if end<len(data) else len(data)
 rows.append(pos)
 return Screen(bytes(matrix),bytes(colors),tuple(rows),seen)

def main():
 report,image=build();(OUT/'result.json').unlink(missing_ok=True)
 cpu_editor.ROOT=editor_fixture.ROOT=FROZEN;cpu_editor.NAMES=editor_fixture.NAMES=NAMES
 f=Fixture(report,image);frames=0;cases=[]
 rng=random.Random(0xC014A1);plan=bytes(rng.choice([1,0x13,0x27,0x3A,0x4E,0x87,0x93,0xA7,0xBA,0xCE]) for _ in range(880))
 def check(data,styled=False,tag='frame'):
  nonlocal frames
  f.render();want=expected(f,data,plan if styled else None)
  verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),want,tag=tag);frames+=1
  assert f.read(0xC600,1024)==f.shim
 try:
  data=native_text('# Styled heading')+b'\r'+native_text('Source **strong**, *emphasis*, @@code@@ and graphics ')+bytes([0xA1,0xFF])+b'\r\r'+native_text('Last line')
  f.source(data,banks=2,physical=32);check(data,tag='plain-request')
  assert not f.get('se_st_valid',1) and f.get('se_st_request',1)==1
  f.publish(plan);check(data,True,'published-full');assert f.get('se_r_path',1)==0
  before=f.reu();gap=f.read(0x9200,2048);history=f.read(f.s['se_h_current'],12)
  for _ in range(12):
   f.key(0x1D);check(data,True,'styled-caret-move');assert f.get('se_r_path',1)==1
  f.key(0x89)
  for _ in range(7):f.key(0x1D);check(data,True,'styled-selection-caret')
  f.key(3);check(data,True,'unmark-restores-styled-underlay')
  assert f.reu()==before,'navigation changed REU'
  assert f.read(f.s['se_h_current'],12)==history,'navigation changed history'
  assert f.document()==data,'navigation changed source'
  cases.append('full880 style bytes / caret and selection union / sourceREU invariant')
  # Full key coverage: every one of33 bytes independently makes a valid plan stale.
  for offset in range(33):
   f.publish(plan);check(data,True,f'key-{offset}-ready')
   at=f.s['se_st_descriptor']+offset;f.m.write(at,f.m.read(at)^1)
   check(data,False,f'key-{offset}-refused')
   assert not f.get('se_st_valid',1) and f.get('se_st_request',1)==1 and f.get('se_r_path',1)==0
   assert f.read(f.s['se_st_descriptor'],33)==f.keybytes()
  cases.append('all33 source/context key bytes reject stale color/caret caches')
  # Missing C14 cannot read its phase key to bind a failure: R1 already bound
  # the exact source key when it requested optional work on the preceding draw.
  f.put('se_st_valid',0,1);f.put('se_st_request',0,1)
  f.m.load(f.s['se_st_descriptor'],bytes(33))
  check(data,False,'initial-admission-key-bound');assert f.read(f.s['se_st_descriptor'],33)==f.keybytes()
  f.put('se_st_request',0x80,1)
  check(data,False,'missing-C14-exact-context-held');assert f.get('se_st_request',1)==0x80
  cases.append('R1 binds request context before initial missing C14 failure')
  # A failed matching context remains quiet until a real key mismatch.
  f.m.load(f.s['se_st_descriptor'],f.keybytes());f.put('se_st_valid',0,1);f.put('se_st_request',0x80,1)
  for _ in range(3):check(data,False,'failed-context-no-retry');assert f.get('se_st_request',1)==0x80
  f.m.write(f.s['se_st_descriptor']+24,f.m.read(f.s['se_st_descriptor']+24)^1)
  check(data,False,'failure-context-changed');assert f.get('se_st_request',1)==1
  cases.append('matching failure80 does not retry; changed context requests1')
  # Same validity but a new plan generation must repaint cached caret colors.
  f.publish(plan);check(data,True,'old-generation');old=f.get('se_st_generation',2)
  plan=bytes((v&0xF0)|((v+2)&15) for v in plan)
  f.publish(plan,(old+1)&65535);check(data,True,'new-generation-full');assert f.get('se_r_path',1)==0
  cases.append('generation publication forces full repaint before caret restore')
  # Poison phase union: R1 must use only descriptor/plan and leave it untouched.
  union=f.read(0x8D00,1152);poison=bytes((i*43+7)&255 for i in range(1152));f.m.load(0x8D00,poison)
  nav=f.read(0x9180,128);diag=f.read(0x8800,128);check(data,True,'no-phase-union-dependence')
  assert f.read(0x8D00,1152)==poison and f.read(0x9180,128)==nav and f.read(0x8800,128)==diag
  f.m.load(0x8D00,union);cases.append('phase union poison / NAV / diagnostic prefix preserved')
  # Nonwrap CR and EOF explicitly ignore even synthetic reverse/color entries.
  f.command(77);check(data,False,'nowrap-request');f.publish(plan);check(data,True,'nowrap-styled')
  f.command(75);check(data,False,'pan-request');f.publish(plan);check(data,True,'pan-styled')
  cases.append('logical-line mode/pan and explicit plainCR/EOF routes')
  # Real pending edit captures proof before R1 clears damage; cursor-only redraw
  # retains the proof while a style job remains pending for the older descriptor.
  f.source(data,banks=2,physical=32);f.publish(plan);check(data,True,'before-real-edit')
  f.put('se_st_cp_valid',1,1);f.put('se_st_cp_dirty',0,1);f.key(native_text('X')[0]);data=native_text('X')+data
  check(data,False,'pending-edit-plain')
  assert f.get('se_hot_pending',1) and f.get('se_st_cp_dirty',1) and f.get('se_st_cp_damage')==0
  assert not f.get('se_r_damage_valid',1)
  f.key(0x1D);check(data,False,'cursor-retains-prefix-proof');assert f.get('se_st_cp_valid',1) and f.get('se_st_cp_dirty',1)
  f.put('se_r_revision',(f.get('se_r_revision',4)+1)&0xFFFFFFFF,4);f.put('se_r_damage_valid',0,1)
  check(data,False,'unknown-revision-invalidates-checkpoint');assert not f.get('se_st_cp_valid',1)
  cases.append('actual pending edit / damage retained past R1 cache clear / unknown revision invalidates')
  result=dict(status='passed',frozen_resident_sha256=report['sha256'],frozen_binding=report['resident_binding']['digest'],r1_payload_bytes=len(image)-HEADER,r1_free=4096-(len(image)-HEADER),view_state_suffix_bytes=3,descriptor_bytes=37,frames=frames,full_cells_checked=frames*1000,key_bytes_individually_checked=33,cases=cases,shim_bytes=1024,
   source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['src/overlays/editor40.s','src/overlays/render-cache.s','src/overlays/render-nowrap.s','src/overlays/render-style.s','src/style/api.inc','src/style/state.s','src/style/render-state.s','tests/test_style_render.py']},
   scope='Actual imported R1 plus frozen33bf resident, independent1000glyph/color oracle; no production root/style provider scheduling or native screenshot proof')
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()
