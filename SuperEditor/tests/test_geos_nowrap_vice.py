"""Native no-wrap gallery: four modes, clipped GEOS prose/code and pending pan.

Only private7900/text8000; initial source enters via actual ROM D81 File/Open.
Prepare until the parent grants the stable clipped-renderer build/window.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,zipfile
import test_geos_nowrap_editor as nowrap
import test_geos_semantic_io_vice as io
from test_fold_retention_vice import Captured
from d81_image import D81Image
from png_pixels import read_png
import vice_plan
live=io.live;ROOT=live.ROOT
FIXTURE=live.grid.native_text('# GEOS clipping\r**'+('Wim'*48)+'** prose end.\r*'+('mimW'*28)+'* italic end.\riWW\r'
    ':::basic\r10 PRINT "'+('ABCD '*17)+'":REM color clipping\r20 DATA 1,2,"x:y":PRINT 42\r:::\r'
    ':::asm\rlabel: .byte "'+('Wim'*26)+'",$FF ; clipping\rL:\r:::\rTail.')


def freeze(source):
 source=Path(source).resolve();flat=io.previous.freeze(source)
 e=ROOT/'agentsworking/evidence/M7'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-geos-nowrap-native');e.mkdir(parents=True)
 for p in flat.iterdir():
  if p.is_file():shutil.copy2(p,e/p.name)
 shutil.copy2(source/'fonts/chargen.bin',e/'chargen.bin');(e/'nowrap.bin').write_bytes(FIXTURE)
 p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'nowrap.bin'),'nowrap,s'],capture_output=True,text=True)
 (e/'nowrap-package.log').write_text(p.stdout+p.stderr);assert p.returncode==0
 assert D81Image((e/'working.d81').read_bytes()).read(b'NOWRAP',kind=1).data==FIXTURE
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81');print('FROZEN '+str(e),flush=True);return e


def scenario(e):
 n=io.Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');data=FIXTURE;caret=0
 def capture(ident,mode,pan=None,ui=0,mark=False,anchor=0,group='unchanged',pending=False):
  n.memory(ident+'_caret','se_hot_caret',caret,3);n.memory(ident+'_mark','se_sel_mark',int(mark));n.memory(ident+'_pending','se_hot_pending',int(pending))
  if mark:n.memory(ident+'_anchor','se_sel_anchor',anchor,3)
  if pan is not None:n.memory(ident+'_pan','se_l_pan',pan,3)
  if mode<3 and ui==0:n.memory(ident+'_style','se_st_valid',1);n.memory(ident+'_styledone','se_st_request',0)
  if mode==3:n.memory(ident+'_vertical_seen','se_v_seen',1)
  n.snapshot(ident,data,mode,ui);n.cases[-1].update(caret=caret,pan=pan,mark=mark,anchor=anchor,group=group,pending=pending)
 def position(ident,p):
  nonlocal caret
  line=data[:p].count(b'\r')+1;column=p-(data.rfind(b'\r',0,p)+1);n.typed(ident+'_goto','goto '+str(line))
  if column:n.send(ident+'_right',bytes([0x1D])*column)
  caret=p
 n.boot();n.open('open_nowrap',b'NOWRAP');start=data.index(b'\r')+1
 for mode in (0,1,2,3):
  if mode<3:n.mode_to(mode)
  else:n.typed('enter_geos','mode hires')
  n.typed('wrap_reset_'+str(mode),'wrap on');n.typed('nowrap_'+str(mode),'wrap off');position('focus_'+str(mode),start)
  capture('mode'+str(mode)+'-pan0',mode,0)
  n.send('View_right_'+str(mode),bytes([0x85,0x56,0x52]));capture('mode'+str(mode)+'-pan20',mode,20)
  n.typed('right_again_'+str(mode),'pan right');capture('mode'+str(mode)+'-pan40',mode,40)
 code_start=data.index(live.grid.native_text('label:'))
 position('code_focus',code_start);n.typed('code_reset','wrap on');n.typed('code_nowrap','wrap off')
 n.typed('code_pan20','pan right');capture('GEOS-code20',3,20)
 n.typed('code_pan40','pan right');capture('GEOS-code40',3,40)
 for label,short,focus in [('prose',live.grid.native_text('iWW'),start),('code',live.grid.native_text('L:'),code_start)]:
  anchor=data.index(short)+len(short)+1;position('anchor_'+label,anchor);n.send('mark_'+label,bytes([0x89]));position('select_focus_'+label,focus)
  n.typed('select_reset_'+label,'wrap on');n.typed('select_nowrap_'+label,'wrap off');n.typed('select_pan_'+label,'pan right')
  capture('partial-'+label+'-selected-CR',3,20,mark=True,anchor=anchor);n.send('unmark_'+label,bytes([3]))
 n.send('help_key',bytes([0x8B]),ui=1);capture('help',3,ui=1)
 n.send('help_close',bytes([0x8B]));n.send('File_key',bytes([0x85,0x46]),ui=1);capture('File-menu',3,ui=1)
 n.send('File_close',bytes([3]));capture('restored',3)
 n.typed('pending_reset','wrap on');n.typed('pending_nowrap','wrap off');position('pending_focus',start+3);n.send('pending_Q',live.grid.native_text('Q'));data=data[:caret]+live.grid.native_text('Q')+data[caret:];caret+=1
 # The View menu path must preserve the live pending gap, not secretly flush
 # through C8's old source-window reload route.
 n.send('pending_View_right',bytes([0x85,0x56,0x52]));capture('pending-pan20',3,20,group=None,pending=True)
 n.typed('pending_again','pan right');capture('pending-pan40',3,40,group=None,pending=True)
 n.send('undo_pending',bytes([0x1A]));data=FIXTURE;caret-=1;capture('pending-undo',3,group=None)
 return n


def evaluate(e):
 out=e/'gallery';s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run');fonts={name:(e/name).read_bytes() for name in live.geos.GEOS_FONTS};fonts['native8.bin']=(e/'grid80.seo').read_bytes()[36+0xC00:36+0x1000];font40=(e/'chargen.bin').read_bytes()[0x800:]
 palette={};catalog=None;state=None;full_banks=set();union=None;precise=None;whole_intervals=0;precise_intervals=0;observed=[]
 for c in cases:
  if c['group']:
   ram=(out/'captures'/(c['id']+'-ram.bin')).read_bytes();handle=ram[s['se_gc_handle']]
   if handle:
    physical=ram[s['se_reu_map']+handle];assert physical and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+physical]==0xFE;full_banks.add(physical)
 for c in cases:
  ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
  assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret'] and bool(f.get('se_sel_mark',1))==c['mark'] and bool(f.get('se_hot_pending',1))==c['pending'],(ident,'canonical source/caret/selection/pending')
  if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
  if c['pan'] is not None:assert f.get('se_l_pan')==c['pan']
  assert f.get('se_l_mode',1)==1 and f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
  assert all(f.get(k,1)==0 for k in ('se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_f_owner','se_e_error'))
  cat=f.read(s['se_overlay_ids'],192)
  if catalog is None:catalog=cat
  assert cat==catalog
  if c['mode']==3:
   assert f.get('se_v_seen',1)==1
   bits,attrs,rows,sem,advances=nowrap.nowrap_expected(f,data,fonts)
   handle=f.get('se_gc_handle',1);bank=ram[s['se_reu_map']+handle];cache=reu[bank*65536:(bank+1)*65536]
   assert cache[0]==1 and cache[1]==len(rows)
   for i,row in enumerate(rows):
    prefix_=cache[0x200+i*0x800:0x220+i*0x800];pan=f.get('se_l_pan');member=row.start<=c['caret']<row.end or c['caret']==row.end and row.reason in (1,2)
    x=sum(advances[row.start:c['caret']])-pan if member else 0;valid=member and 0<=x<320
    assert bool(prefix_[26])==member and bool(prefix_[18])==valid and int.from_bytes(prefix_[19:21],'little')==(x if valid else 0),(ident,'native signedcaret/membership',i)
  else:
   (a,b),_,_,_=live.geos.grid.expected(f,data)
   if c['mode']==0:
    assert f.read(0x4000,1000)==a and bytes(v&15 for v in colors)==b and f.read(0x4800,2048)==font40
    bits=bytearray(8000);attrs=bytearray(1000)
    for row in range(25):
     for col in range(40):
      at=row*40+col;code=a[at];bits[row*320+col*8:row*320+col*8+8]=font40[code*8:code*8+8];attrs[at]=(b[at]<<4)|6
   else:bits,attrs=a,b
  if c['mode']:
   assert ram[0x6000:0x7F40]==bits,(ident,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x6000:0x7F40],bits)) if a!=b))
   assert ram[0x4000:0x43E8]==attrs,(ident,'attributes',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x4000:0x43E8],attrs)) if a!=b))
  w,h,pixels=read_png(out/('native-'+ident+'.png'));assert (w,h)==(384,272)
  for y in range(200):
   for x in range(320):
    attr=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attr>>4 if ink else attr&15;actual=pixels[(35+y)*w+32+x]
    assert actual==palette.setdefault(color,actual),(ident,'actualVICpixel',x,y)
  if c['group']:
   now=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],n) for k,n in (('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)))
   if state is None:state=now
   assert now==state,(ident,'viewonlychangedcanonical/history')
   assert len(reu)==16*1024*1024;masked=bytearray(reu)
   for cache_bank in full_banks:masked[cache_bank*65536:(cache_bank+1)*65536]=bytes(65536)
   digest=hashlib.sha256(masked).hexdigest()
   if union is None:union=digest
   else:whole_intervals+=1
   assert union==digest,(ident,'otherREUacrossallmodes')
   if c['mode']==3:
    masked=bytearray(reu);start=bank*65536;masked[start:start+64]=bytes(64)
    for i in range(22):a=start+0x200+i*0x800;masked[a:a+0x800]=bytes(0x800)
    digest=hashlib.sha256(masked).hexdigest()
    if precise is None:precise=digest
    else:precise_intervals+=1
    assert precise==digest,(ident,'preciseGEOSFEprefix/tail/otherREU')
  observed.append(dict(id=ident,mode=c['mode'],pan=f.get('se_l_pan'),caret=c['caret'],pending=c['pending']))
 assert len(set(palette.values()))==len(palette)
 assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'read-onlyscenariochangedD81'
 result=dict(status='passed',identity=json.loads((e/'freeze.json').read_text()),frames=observed,screenshots=len(cases),native_pixels=len(cases)*64000,native_attributes=len(cases)*1000,whole16MiB_mode_intervals=whole_intervals,precise_FE_header_slots_intervals=precise_intervals,scope='ActualD81FileOpen/IRQnative fourmode-nowrap0/20/40, GEOSunalignedcode/partialCR/selection/pendingpreservation/UI. No physicalkeyboard/timingclaim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def execute(e):
 n=scenario(e);plan=n.plan();assert len({x['id'] for x in plan['steps']})==len(plan['steps'])
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for module in (__file__,nowrap.__file__,nowrap.semantic.__file__,io.__file__,live.__file__,io.native.__file__,nowrap.geos.__file__,ROOT/'tests/geos_packet.py',ROOT/'tools/supermark_model.py'):
   p=Path(module);z.write(p,p.relative_to(ROOT))
 project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0
 print('NATIVE '+str(e)+' steps='+str(len(n.steps))+' IRQbytes='+str(n.keys)+' screenshots='+str(len(n.cases)),flush=True)
 vice_plan.run_plan(plan,n.out);return evaluate(e)


def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--source-freeze',type=Path);p.add_argument('--verify',type=Path);args=p.parse_args()
 if args.verify:return evaluate(args.verify.resolve())
 if args.run:
  assert args.fixture or args.source_freeze,'Explicit frozen CPU fixture/nativefreeze required'
  return execute((args.fixture or freeze(args.source_freeze)).resolve())
 print('Prepared only; await stable no-wrapbuild and exclusive7900/text8000 before --run.')


if __name__=='__main__':main()
