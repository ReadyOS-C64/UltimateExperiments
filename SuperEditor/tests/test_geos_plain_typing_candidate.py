"""Private Plain R30/C32 public edits, forcedfull/pixels/precise REU refusals.
No canonical changes. Negative FE writes are explicit debugger fault seams.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_geos_plain_typing_probe as profile
geos=profile.geos;preview=profile.preview
import test_geos_semantic_editor as semantic
DEFAULT=ROOT/'build/geos-plain-typing-candidate/first/fixture'
def run(out,base):
 out.mkdir(parents=True);i=json.loads((base/'freeze.json').read_text());geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=profile.font_fixture.ROOT=base;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=i['names']
 dll=profile.profile_runner(out);f=preview.Fixture(out,base,dll,True);g=preview.Fixture(out,base,dll,True);fonts={n:(base/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};frames=[];data=b'';caps=0
 def setup(text,at,preset='plain'):
  nonlocal data,caps
  data=geos.native_text(text);caps={'plain':0,'markdown':1,'full':3}[preset]
  assert 0<=at<len(data)
  for x in(f,g):
   x.source(data);x.typed(geos.native_text('syntax '+preset));x.command(99)
   for _ in range(at):x.key(0x1d)
   x.render()
 def check(tag,fast=None,gtc=None):
  if gtc is not None:assert f.m.read(0x9149)==gtc,(tag,'producer',f.m.read(0x9149),gtc)
  before=f.canonical();reu=f.reu();cat=f.catalog();started=f.total_instructions;loads=f.get('se_overlay_loads',2)
  indices=[q+1 for q in range(64)if f.m.read(f.s['se_overlay_ids']+q)in(30,31)and f.m.read(f.s['image_slot']+q)&0x7f==0];assert len(indices)==2
  dll.gm_profile(f.s['se_overlay_active'],*indices,f.s['se_er_published'],0,f.s['se_er_published'],0);dll.pt_start(f.s['se_overlay_active'],f.s['se_overlay_ids']);f.render();used=f.total_instructions-started
  direct=bool(dll.gm_metric(0));window=f.m.read(f.s['se_gf_state']+21);calls={q:int(dll.pt_calls(q))for q in range(64)if dll.pt_calls(q)};staged=int(dll.pt_calls(255));styledstage=int(dll.pt_calls(254));dll.pt_start(0,0);dll.gm_profile(0,0,0,0,0,0,0)
  if fast is not None:assert direct==fast,(tag,'path',direct,calls)
  startg=g.total_instructions;g.m.write(0xcfe8,0);g.m.write(0xcf90,0);g.render();forced=g.total_instructions-startg
  actual,forceddata=f.merged(),g.merged()
  assert actual==forceddata==data,(tag,'source',actual,forceddata,data)
  assert f.canonical()==before,(tag,'render changed canonical state')
  assert f.catalog()==cat,(tag,'render changed catalog identity')
  if caps==0:
   bits,attrs,_=geos.body_model(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor')if f.get('se_sel_mark',1)else None);matrix,colors,rect=geos.grid.logical_ui(f,data);bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],rect)
   assert not set(calls)&{14,15,17,18,19,24,25,26,31}and staged==0,(tag,'Plain parser/lexer work',calls,staged)
  else:bits,attrs,_,_=semantic.expected(f,data,fonts)
  assert f.read(0x6000,8000)==bits==g.read(0x6000,8000),(tag,'independent/full pixels')
  assert f.read(0x4000,1000)==attrs==g.read(0x4000,1000),(tag,'independent/full attrs')
  assert f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error'))
  h=f.get('se_gc_handle',1);p=f.m.read(f.s['se_reu_map']+h);assert h and p and f.m.read(f.s['se_reu_logical_owner']+h)==f.m.read(f.s['se_reu_physical_owner']+p)==0xfe
  cursor=0;after=f.reu();b=p*65536
  for lo,hi in[(0,64),(0x200,0xe568)]:assert reu[cursor:b+lo]==after[cursor:b+lo],(tag,'outside exactFEspan');cursor=b+hi
  assert reu[cursor:]==after[cursor:],(tag,'FEfont/tail/otherREU')
  rec=dict(tag=tag,caps=caps,direct=direct,postrender_window=window,instructions=used,forced_instructions=forced,loads=(f.get('se_overlay_loads',2)-loads)&65535,source_bytes=len(data),C_calls=calls,C31_stage_entries=staged,C32_stage_entries=styledstage,bitmap_sha256=hashlib.sha256(bits).hexdigest());frames.append(rec);(out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n');print('PASS',rec,flush=True)
 def edit(tag,key,fast=None,gtc=None):
  nonlocal data
  at=f.get('se_hot_caret');assert at==g.get('se_hot_caret');start=f.total_instructions
  marked=f.get('se_sel_mark',1);assert marked==g.get('se_sel_mark',1)
  anchor=f.get('se_sel_anchor')if marked else at
  if marked:assert anchor==g.get('se_sel_anchor')
  lo,hi=sorted((anchor,at))
  if lo!=hi:data=data[:lo]+(b''if key==0x14 else bytes([key]))+data[hi:]
  elif key==0x14:data=data[:at-1]+data[at:]
  else:data=data[:at]+bytes([key])+data[at:]
  dll.pt_start(f.s['se_overlay_active'],f.s['se_overlay_ids']);f.key(key);inputcalls={q:int(dll.pt_calls(q))for q in range(64)if dll.pt_calls(q)};inputstage=int(dll.pt_calls(255));dll.pt_start(0,0);inputused=f.total_instructions-start;g.key(key)
  if caps==0:assert not set(inputcalls)&{14,15,17,18,19,24,25,26,31}and inputstage==0
  check(tag,fast,gtc);frames[-1].update(input_instructions=inputused,end_to_end_instructions=inputused+frames[-1]['instructions'],input_C_calls=inputcalls)
 def damage(offset,value):
  # Actual checked FE write. No positive source/key/certificate is fabricated.
  raw,_=f.raw_cache();row=raw[42];h=f.get('se_gc_handle',1);before=f.canonical();f.call('se_doc_invalidate');f.m.load(0x8000,bytes([value]))
  for n,v,w in [('se_reu_logical',h,1),('se_reu_offset',0x200+row*0x800+offset,2),('se_reu_length',1,2),('se_reu_c64',0x8000,2)]:f.put(n,v,w)
  assert not f.call('se_reu_copy',0).p&1 and f.canonical()==before
 try:
  text='Ordinary text here.\rSecond source row.\rThird source row.\rLast.'
  for preset in ('plain','markdown','full'):
   setup(text,5,preset)
   for k in range(4):edit(preset+'-repeat'+str(k),geos.native_text('Q')[0]if k%2==0 else 0x14,True,2)
   for x in(f,g):x.command(16)
   data=f.merged();check(preset+'-undo')
   for x in(f,g):x.command(17)
   data=f.merged();check(preset+'-redo')
  for preset in ('markdown','full'):
   setup('Ordinary **boldwords** here.\rSecond source row.\rLast.',13,preset)
   edit(preset+'-styled-insert',geos.native_text('Q')[0],True,2)
   edit(preset+'-styled-back',0x14,True,2)
  # Keep the first styled row's shared tile neighbours ordinary; the existing
  # strict seam guard intentionally refuses a directly adjacent fence band.
  mixed='Ordinary **boldwords** here.\rSecond ordinary row.\rThird ordinary row.\r:::basic\r10 PRINT "HELLO":REM KEEP\r:::\rTail.'
  setup(mixed,13,'full');edit('namespace42-prime',geos.native_text('Q')[0],True,2)
  assert frames[-1]['C32_stage_entries']>0
  for x in(f,g):
   x.typed(geos.native_text('goto 5'))
   for _ in range(len(geos.native_text('10 PRINT "HE'))):x.key(0x1d)
   x.render()
  edit('namespace41-code-insert',geos.native_text('X')[0],True)
  assert frames[-1]['C31_stage_entries']>0
  edit('namespace41-code-back',0x14,True)
  assert frames[-1]['C31_stage_entries']>0
  for x in(f,g):
   x.typed(geos.native_text('goto 1'))
   for _ in range(13):x.key(0x1d)
   x.render()
  edit('namespace42-reload',geos.native_text('Q')[0],True,2)
  assert frames[-1]['C32_stage_entries']>0
  setup('Ordinary **literal** and @@source@@ text.\rSecond row.\rLast.',12);edit('plain-literal-markup',geos.native_text('Q')[0],True,2)
  for name,line,at in [('punctuation-prefix','# heading remains literal',5),('digit-prefix','10 PRINT remains literal',5),('softwrap','Ordinary '+('W'*80),5)]:
   setup(line+'\rFollowing row.\rTail.',at);edit(name,geos.native_text('Q')[0],False,0)
  setup(text,5);edit('CR-fallback',13,False,0)
  setup(text,0);edit('first-column-fallback',geos.native_text('Q')[0],False,0)
  setup('Ordinary row.\r\rTail.',len(geos.native_text('Ordinary row.\r')));edit('empty-row-fallback',geos.native_text('Q')[0],False,0)
  setup(text,5)
  for x in(f,g):x.command(68);x.key(0x1d);x.key(0x1d)
  assert f.get('se_sel_mark',1)==g.get('se_sel_mark',1)==1
  edit('selection-fallback',geos.native_text('Q')[0],False,0)
  setup('# Parent\rOrdinary body here.\r# Next\rTail.',12,'full')
  caps=0
  for x in(f,g):
   x.command(115);x.render();assert x.get('se_ef_valid',1)==1
   x.typed(geos.native_text('syntax plain'));x.render();assert x.get('se_ef_valid',1)==1
   x.typed(geos.native_text('goto 2'))
   for _ in range(5):x.key(0x1d)
   x.render()
  edit('stored-foldmap-fallback',geos.native_text('Q')[0],False,0)
  setup(text,5)
  for x in(f,g):x.command(76) #alreadywrapped policy publication still revokes
  for x in(f,g):x.render();x.command(77);x.render()
  edit('nowrap-fallback',geos.native_text('Q')[0],False,0)
  for name,offset,value in [('raw-style-nonzero',194,1),('raw-inline-nonzero',23,1),('wrong-encoding',16,9),('wrong-role',356,2),('wrong-height',14,8)]:
   setup(text,5);damage(offset,value);edit('fault-'+name,geos.native_text('Q')[0],False)
  # Actual public preset publication revokes every old edit/GCC certificate
  # before rebuilding, including opposite-direction styled→raw→styled.
  setup('Ordinary **boldwords** here.\rSecond row.\rThird row.',13,'full')
  for preset in ('plain','full','markdown','plain'):
   caps={'plain':0,'full':3,'markdown':1}[preset]
   for x in(f,g):
    x.typed(geos.native_text('syntax '+preset));assert x.m.read(0xcfe8)==x.m.read(0xcf90)==x.m.read(0x9149)==x.get('se_gc_width',1)==0
   check('public-transition-'+preset,False)
  # Invalid capabilities/foreign ownership preserve phase and source; these
  # are explicit host faults at the R30 API, not positive product input.
  setup(text,5);edit('prime-api-probe',geos.native_text('Q')[0],True)
  for owner in(1,2,3,4,255):
   original=f.canonical();phase=f.read(0x8800,2432);f.put('se_f_owner',owner,1);f.put('se_overlay_frame',3,1);r=f.call('se_overlay_call',30);assert not r.p&1 and r.a==2 and f.get('se_f_owner',1)==owner and f.read(0x8800,2432)==phase and f.canonical()==original
  f.put('se_f_owner',0,1)
  for value in(2,4,255):
   original=f.canonical();phase=f.read(0x8800,2432);f.put('se_render_caps',value,1);f.put('se_overlay_frame',3,1);r=f.call('se_overlay_call',30);assert not r.p&1 and r.a==2 and f.read(0x8800,2432)==phase and f.canonical()==original
  f.put('se_render_caps',0,1)
 finally:f.close();g.close()
 result=dict(status='PASS',fixture=str(base),frames=frames,API_faults=8,scope='Private actual public R30/C32, Plain zero-parser, Full/Markdown controls, realcheckedFE negative faults, forcedfull+independentrawfont pixels, exactsource/history/shim and whole16MiB outside declared FE. CPU not native.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args();out=ROOT/'build/geos-plain-typing-matrix'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve())
