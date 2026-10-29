"""Actual native161-glyph ABI2 capacity through D81 and public IRQ input.

Own binary8100/text8200 only; isolated disk/PID. No map, pan, caret or PC seeding.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,zipfile
import test_geos_semantic_io_vice as io
import test_geos_nowrap_editor as nowrap
from test_fold_retention_vice import Captured
from geos_packet import raw_layout,rows as decode_rows,normalize_legacy,LegacyCapacityError
from d81_image import D81Image
from png_pixels import read_png
import vice_plan
live=io.live;ROOT=live.ROOT
DEFAULT=ROOT/'build/geos-rendered-editor/20261025T042922386544Z/fixture'
DATA=b'.'*200+b'\rTail.'
class Plan(io.Plan):
 def plan(self):
  plan=super().plan();plan['global_defaults']['monitor_port_start']=8100;plan['global_defaults']['monitor_port_span']=1
  assert plan['global_defaults']['vice']['headless'] and not plan['steps'][0]['params']['kill_stale']
  return plan

def freeze(source):
 source=Path(source).resolve();flat=io.previous.freeze(source)
 e=ROOT/'agentsworking/evidence/M7'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-geos-capacity-native');e.mkdir(parents=True)
 for p in flat.iterdir():
  if p.is_file():shutil.copy2(p,e/p.name)
 shutil.copy2(source/'fonts/chargen.bin',e/'chargen.bin');(e/'capacity.bin').write_bytes(DATA)
 p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'capacity.bin'),'capacity,s'],capture_output=True,text=True)
 (e/'capacity-package.log').write_text(p.stdout+p.stderr);assert p.returncode==0
 assert D81Image((e/'working.d81').read_bytes()).read(b'CAPACITY',kind=1).data==DATA
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
 assert json.loads((e/'freeze.json').read_text())['prg_sha256']=='01bef7a4e52a5c111be879d3e7d8555f054f0127283b83995e56e3c0ecf764d8'
 print('FROZEN '+str(e),flush=True);return e

def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),'editing')
 def capture(ident,data,caret,mode=3,pan=None,mark=False,anchor=0,pending=False,group=None):
  for name,value,width in [('se_hot_caret',caret,3),('se_sel_mark',int(mark),1),('se_hot_pending',int(pending),1)]:n.memory(ident+'_'+name,name,value,width)
  if pan is not None:n.memory(ident+'_pan','se_l_pan',pan,3)
  if mark:n.memory(ident+'_anchor','se_sel_anchor',anchor,3)
  if mode<3:n.memory(ident+'_style','se_st_valid',1);n.memory(ident+'_styledone','se_st_request',0)
  n.snapshot(ident,data,mode);n.cases[-1].update(caret=caret,pan=pan,mark=mark,anchor=anchor,pending=pending,group=group)
 n.boot();n.open('open_capacity',b'CAPACITY');n.typed('GEOS','mode hires');n.typed('nowrap','wrap off')
 for i in range(4):n.typed('jump40_'+str(i),'jump +40')
 capture('capacity161',DATA,160,pan=1,group='clean')
 n.send('mark',b'\x89');n.send('selection_RIGHT',b'\x1D')
 capture('selection-pan3',DATA,161,pan=3,mark=True,anchor=160,group='clean')
 n.send('unmark',b'\x03');n.send('insert_position_LEFT',b'\x9D');n.send('pending_insert',b'.')
 capture('pending',DATA[:160]+b'.'+DATA[160:],161,pan=3,pending=True)
 n.send('undo_pending',b'\x1A');capture('undo',DATA,160,pan=3,group='after-undo')
 n.mode_to(2);capture('source80',DATA,160,mode=2,group='after-undo')
 n.typed('return_GE0S','mode hires');capture('GEOS-return',DATA,160,pan=1,group='after-undo')
 return n

def evaluate(e):
 out=e/'editing';s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run')
 fonts={name:(e/name).read_bytes() for name in live.geos.GEOS_FONTS};fonts['native8.bin']=(e/'grid80.seo').read_bytes()[36+0xC00:36+0x1000]
 assert fonts['bsw9-widths.bin'][live.geos.native(ord('.'))]==2
 palette={};catalog=None;groups={};observed=[];intervals=0
 for c in cases:
  ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
  assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret'] and bool(f.get('se_hot_pending',1))==c['pending'] and bool(f.get('se_sel_mark',1))==c['mark']
  if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
  assert all(f.get(n,1)==0 for n in ('se_e_job','se_e_redraw','se_e_draw_busy','se_f_owner','se_doc_read_locks','se_e_error'))
  assert f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
  cat=f.read(s['se_overlay_ids'],192)
  if catalog is None:catalog=cat
  assert cat==catalog
  assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==b'CAPACITY' and f.get('se_f_current_device',1)==8
  handle=f.get('se_gc_handle',1);bank=ram[s['se_reu_map']+handle]
  assert handle and bank and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)
  assert ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xFE
  first=None
  if c['mode']==3:
   assert f.get('se_l_mode',1)==1 and f.get('se_l_pan')==c['pan'] and f.get('se_l_manual',1)==0 and f.get('se_v_seen',1)==1
   bits,attrs,rows,semantic,advances=nowrap.nowrap_expected(f,data,fonts)
   cache=reu[bank*65536:(bank+1)*65536];assert cache[0]==1 and raw_layout(cache).version in (2,3)
   decoded=decode_rows(cache);assert len(decoded)==len(rows)
   for row_index,(actual,row) in enumerate(zip(decoded,rows)):
    advance=advances[row.start:row.end];x=0;indices=[];xs=[];closed=False
    for index,a in enumerate(advance,row.start):
     if x+a>c['pan'] and not closed:
      if not indices:xs.append(max(0,min(320,x-c['pan'])))
      indices.append(index);xs.append(max(0,min(320,x+a-c['pan'])));closed=x+a>=c['pan']+320
     x+=a
    if indices:boundaries=tuple(indices+[indices[-1]+1]);first_origin=sum(advances[row.start:indices[0]])-c['pan']
    else:boundaries=(row.end,);xs=[max(0,min(320,x-c['pan']))];first_origin=0
    assert actual['count']==len(indices) and actual['chars']==bytes(data[p] for p in indices)
    assert actual['styles']==bytes(semantic.styles[p] for p in indices) and actual['roles']==bytes(semantic.roles[p] for p in indices)
    assert actual['x']==tuple(xs) and actual['left']==actual['right']==boundaries,(ident,'rawABI2canonicalmaps',row_index)
    assert (actual['start'],actual['end'],actual['next'])==(row.start,row.end,row.next)
    assert actual['raster_x']==first_origin
   first=decoded[0];assert first['count']==161 and first['raster_x']==-1
   if ident=='capacity161':
    assert first['chars']==b'.'*161 and first['x']==tuple(max(0,min(320,i*2-1)) for i in range(162))
    assert first['left']==first['right']==tuple(range(162)) and first['caret_valid']==1 and first['caret_x']==319
   if ident=='selection-pan3':assert first['left']==tuple(range(1,163)) and first['caret_x']==319
   try:normalize_legacy(cache)
   except LegacyCapacityError:pass
   else:raise AssertionError('raw161record silently accepted by160-glyph legacy adapter')
   (out/(ident+'-raw-cache.bin')).write_bytes(cache)
  else:(bits,attrs),_,_,_=live.geos.grid.expected(f,data)
  assert ram[0x6000:0x7F40]==bits,(ident,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x6000:0x7F40],bits)) if a!=b))
  assert ram[0x4000:0x43E8]==attrs,(ident,'attributes',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x4000:0x43E8],attrs)) if a!=b))
  w,h,pixels=read_png(out/('native-'+ident+'.png'));assert (w,h)==(384,272)
  for y in range(200):
   for x in range(320):
    attr=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attr>>4 if ink else attr&15;actual=pixels[(35+y)*w+32+x]
    assert actual==palette.setdefault(color,actual),(ident,'actualVICpixel',x,y)
  if c['group']:
   state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[n],size) for n,size in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
   assert len(reu)==16*1024*1024;masked=bytearray(reu);masked[bank*65536:(bank+1)*65536]=bytes(65536)
   value=state,hashlib.sha256(masked).hexdigest()
   if c['group'] in groups:intervals+=1
   assert groups.setdefault(c['group'],value)==value,(ident,'canonical/history/full16MiB outsideauthenticatedFE')
  observed.append(dict(id=ident,mode=c['mode'],caret=c['caret'],pan=f.get('se_l_pan'),glyphs=first['count'] if first else None,pending=c['pending']))
 assert len(set(palette.values()))==len(palette)
 assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'read-only native scenario changedD81'
 result=dict(status='passed',identity=json.loads((e/'freeze.json').read_text()),frames=observed,screenshots=len(cases),native_pixels=64000*len(cases),attributes=1000*len(cases),whole16MiB_readonly_intervals=intervals,scope='ActualROMD81FileOpen/IRQ-native jump+40×4/E47pan1/rawABI2count161/selectionRIGHTpan3/pendinginsertundo/80modeGEOSreturn; no hostmaps/viewseeding orphysicalchord claim')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result

def execute(e):
 n=scenario(e);plan=n.plan();assert len({x['id'] for x in plan['steps']})==len(plan['steps'])
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for source in (__file__,nowrap.__file__,nowrap.semantic.__file__,io.__file__,live.__file__,io.native.__file__,live.grid.__file__,live.geos.__file__,ROOT/'tests/geos_packet.py',ROOT/'tests/test_fold_retention_vice.py',ROOT/'tools/supermark_model.py',ROOT/'tools/vice_plan.py',ROOT/'tools/vice_config.py'):
   p=Path(source);z.write(p,p.relative_to(ROOT))
 project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0
 print('NATIVE '+str(e)+' steps='+str(len(n.steps))+' IRQbytes='+str(n.keys)+' screenshots='+str(len(n.cases))+' binary8100/text8200',flush=True)
 vice_plan.run_plan(plan,n.out);return evaluate(e)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--cpu-fixture',type=Path,default=DEFAULT);p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:evaluate(a.verify.resolve())
 elif a.run:execute((a.fixture or freeze(a.cpu_fixture)).resolve())
 else:print('Prepared only; explicitnative8100/text8200 grant required')
