"""Public GEOS presentation/pixel/navigation gate; no emitted classes in oracle.

Plain uses independent literal9 geometry; Markdown keeps host-derived block/
inline formatting and uniform role4 code. Parser-entry counters across all four
views are independently owned by test_presentation_bypass.py.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,sys,zipfile
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_editor as sem
import test_geos_semantic_consumer as old
import test_geos_convergent_line as previous
geos=sem.geos
SOURCE=geos.native_text(
 '# Heading **strong** and *emphasis*\r'
 'Ordinary interior prose with **bold** and @@code@@ plus a late close.\r'
 '- Bullet words\r:::basic\r10 PRINT "Hello":REM tail\r20 DATA 1,2,3\r:::\r'
 ':::asm\rstart: lda #$2A ; native comment\r .byte "ab",$FF\r:::\r'
 'Last prose line.\r')

class Fixture(old.Fixture):
 def __init__(self,*args,**kwargs):self.layout_revocations=[];super().__init__(*args,**kwargs)
 def call(self,name,a=0):
  before=self.get('se_e_command',1)if 'se_e_command'in self.s else -1
  regs=super().call(name,a)
  # Observe the actual C8 publication return before its ensuing C23 reveal
  # claims/repurposes the phase. No test instruction or productfield is replaced.
  if name in('se_editor_command','se_editor_service')and(before in(73,76,77)or name=='se_editor_command'and a in(73,76,77))and self.get('se_e_command',1)==47:
   assert self.get('se_gc_width',1)==self.m.read(0xcf90)==self.m.read(0xcfe8)==self.m.read(0x9149)==0,'layout publication retained derived authority'
   self.layout_revocations.append(dict(command=a if name=='se_editor_command'else before,sequence=self.get('se_e_draw_sequence',2)))
  return regs

def expected(f,data,fonts,caps):
 kwargs=dict(top=f.get('se_v_top'),caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor')if f.get('se_sel_mark',1)else None,nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
 if caps==0:bits,attrs,rows=geos.body_model(data,fonts,**kwargs)
 else:
  parsed=sem.classify(data);roles=bytes(4 if parsed.code[i]and caps==1 else r for i,r in enumerate(parsed.roles))
  bits,attrs,rows=sem.raster(data,fonts,styles=parsed.styles,roles=roles,reverse=parsed.reverse,code=parsed.code,**kwargs)
  attrs=bytearray(attrs)
  # Aligned native8 code sets its real source tiles even for blank glyphs.
  for row in rows:
   if row.height!=8:continue
   x=-kwargs['pan']if kwargs['nowrap']else 0
   for at in range(row.start,row.end):
    if x%8==0 and 0<=x<320:attrs[(row.top//8)*40+x//8]=(sem.PALETTE[roles[at]]<<4)|6
    x+=8
  attrs=bytes(attrs)
 matrix,colors,rect=geos.grid.logical_ui(f,data)
 bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],rect)
 return bits,attrs,rows

def raw_target(data,widths,caret,command,preferred=None,nowrap=False):
 # Full-document metric walk; source_lines() deliberately clips to one page.
 advances=[widths[geos.native(v)]for v in data];rows=[];start=0
 while True:
  part=geos.line_break(data,advances,start,320,int(nowrap),0,-1,0)
  rows.append(SimpleNamespace(start=start,end=part['end'],next=part['next'],reason=part['reason']))
  if part['reason']==2:break
  assert part['next']>start;start=part['next']
 def member(row):return row.start<=caret and(caret<=row.end if row.reason in(1,2)else caret<row.next)
 current=next(i for i,row in enumerate(rows)if member(row));row=rows[current]
 if preferred is None:preferred=sum(widths[geos.native(v)]for v in data[row.start:caret])
 target=max(0,min(len(rows)-1,current+(-19 if command==38 else 19 if command==39 else -1 if command==36 else 1)))
 row=rows[target];positions=[0]
 for v in data[row.start:row.end]:positions.append(positions[-1]+widths[geos.native(v)])
 boundary=min(range(len(positions)),key=lambda i:(abs(positions[i]-preferred),-i));at=row.start+boundary
 if row.reason not in(1,2):at=min(at,row.end-1)
 return at,preferred

def run(out,fixture=None,smoke=False):
 paths={Path(__file__).resolve()}|{Path(m.__file__).resolve()for m in list(sys.modules.values())if getattr(m,'__file__',None)and Path(m.__file__).resolve().is_relative_to(ROOT)and Path(m.__file__).suffix=='.py'}
 with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as archive:
  for path in sorted(paths):archive.write(path,path.relative_to(ROOT))
 verification={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in sorted(paths)}
 frozen,identity=geos.freeze(out,fixture);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};frames=[];data=SOURCE
 assert {'se_render_caps','se_ef_visible'}<=f.s.keys()
 def clean():
  # FS8EE0/retained GS_FS9040 are dead phase aliases after rastering. The live
  # lease proof is resident lockcount/owner and C20's two persistent controlflags.
  assert not any(f.get(n,1)for n in['se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_e_draw_busy'])and f.read(0x912c,2)==b'\0\0'and f.read(0xc600,1024)==f.shim,f.debug()
 def check(tag):
  before=f.reu();canonical=f.canonical();catalog=f.catalog();start=f.total_instructions;f.render();caps=f.get('se_render_caps',1)
  assert f.merged()==data and f.canonical()==canonical and f.catalog()==catalog;clean();previous.outside(f,before,tag)
  bits,attrs,rows=expected(f,data,fonts,caps)
  assert f.read(0x6000,8000)==bits,(tag,'bitmap',next((i,a,b)for i,(a,b)in enumerate(zip(f.read(0x6000,8000),bits))if a!=b))
  assert f.read(0x4000,1000)==attrs,(tag,'attributes')
  cache,_=f.raw_cache();assert cache[0]==1 and cache[1]==len(rows)
  for i,row in enumerate(rows):
   p=cache[0x200+i*0x800:0x220+i*0x800];assert tuple(int.from_bytes(p[j:j+3],'little')for j in(0,3,6))==(row.start,row.end,row.next)and(p[14],p[15])==(row.height,row.top),(tag,'geometry',i,row,p.hex())
   if caps==0:assert p[16]==p[22]==p[23]==p[30]==0 and p[31]==255,(tag,'explicitrawprefix',i,p.hex())
  anchors=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little')for i in range(len(rows)))
  assert anchors==tuple(r.start for r in rows)and f.get('se_v_bottom')==rows[-1].next,(tag,'VIEWanchors')
  geos.png(bits,attrs,out/(tag+'.png'));entry=dict(tag=tag,caps=caps,source_bytes=len(data),TOP=f.get('se_v_top'),caret=f.get('se_hot_caret'),instructions=f.total_instructions-start,rows=len(rows));frames.append(entry);print('PASS',entry,flush=True);(out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
 def preset(name,want):
  f.typed(geos.native_text('syntax '+name));assert f.get('se_render_caps',1)==want,(name,f.get('se_render_caps',1));check('preset-'+name+'-'+str(len(frames)))
 try:
  f.source(data);f.put('se_status',1,1);f.command(99);preset('plain',0)
  original=data;at=f.get('se_hot_caret');q=geos.native_text('Q');f.key(q[0]);data=data[:at]+q+data[at:];check('plain-pending-insert')
  preferred=None
  for cmd in (37,36):
   target,preferred=raw_target(data,fonts['bsw9-widths.bin'],f.get('se_hot_caret'),cmd,preferred);f.command(cmd);assert f.get('se_hot_caret')==target;check('plain-pending-nav-'+str(cmd))
  assert f.get('se_hot_caret')==at+1
  f.key(0x14);data=original;check('plain-pending-BACK')
  preset('markdown',1);preset('full',3)
  if not smoke:
   preset('off',0);f.command(34);check('plain-TOP')
   preferred=None
   for i,cmd in enumerate([37,37,37,36,39,38,37]):
    target,preferred=raw_target(data,fonts['bsw9-widths.bin'],f.get('se_hot_caret'),cmd,preferred,bool(f.get('se_l_mode',1)));f.command(cmd);assert f.get('se_hot_caret')==target,('rawnav',cmd,target,f.get('se_hot_caret'));check('plain-nav-'+str(i))
   for line in [1,5,10]:
    at=0 if line==1 else [i+1 for i,v in enumerate(data)if v==13][line-2]
    f.typed(geos.native_text('goto '+str(line)));assert f.get('se_hot_caret')==at;check('plain-goto-'+str(line))
   f.command(35);assert f.get('se_hot_caret')==len(data);check('plain-BOTTOM')
   f.command(34);f.command(68);f.command(37);check('plain-selection');f.command(69);lo,hi=sorted((f.get('se_sel_anchor'),f.get('se_hot_caret')));assert f.get('se_clip_length')==hi-lo;f.command(50);check('plain-selection-clear')
   preset('markdown',1);preset('on',3);preset('plain',0)
   f.key(0x8b);check('plain-help');f.key(0x8b);check('plain-help-close');f.key(0x85);check('plain-menu');f.key(3);check('plain-menu-close')
   for label,raw in [('empty',b''),('CR-empty',b'\r\r'),('long-markers',geos.native_text('i'*200+' **closed** @@code@@\rTail.'))]:
    data=raw;f.source(data);f.command(99);preset('plain',0);check('raw-'+label)
    if data:
     f.command(77);check('raw-'+label+'-nowrap');f.command(75);check('raw-'+label+'-pan20');f.command(74);check('raw-'+label+'-panleft');f.command(76);check('raw-'+label+'-wrap')
   # Initial far viewport is an explicit fixture seed; subsequent vertical
   # commands, typedgoto and all rendering use the actual public services.
   prefix=geos.native_text('small\r')*11000;data=prefix+geos.native_text('Far mixedCase **literal**\rTail.')
   f.source(data);f.command(99);f.typed(geos.native_text('syntax plain'));f.position(len(prefix)+4);f.put('se_v_top',len(prefix));check('raw-24bit-start')
   preferred=None
   for cmd in (37,36,36):
    target,preferred=raw_target(data,fonts['bsw9-widths.bin'],f.get('se_hot_caret'),cmd,preferred);f.command(cmd);assert f.get('se_hot_caret')==target;check('raw-24bit-nav-'+str(len(frames)))
  result=dict(status='passed',identity=identity,frames=frames,layout_revocations=f.layout_revocations,verification=verification,scope='Actual public source/presentationcommands/render/jobs; independent literal9/Markdown/Full pixels, attributes, source/geometry/anchors/history/catalog/shim/full16MiB exactownedspans. No parser counters claimed here; independent allviewcountergate owns those. CPUonly.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--smoke',action='store_true');a=p.parse_args()
 if not a.run:print('Prepared actualGEOSraw9/Markdownpixel/publicnavigation gate; --run freezes product.');raise SystemExit
 out=ROOT/'build/plain-geos'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture,a.smoke);print('RESULT',r['status'],len(r['frames']))
