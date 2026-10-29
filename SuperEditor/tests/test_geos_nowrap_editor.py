"""Actual frozen public GEOS no-wrap/pan reproduction, independent signed-X pixels.

Records known failures rather than weakening the oracle. No product changes,
shared build, native VICE or editable no-wrap completion claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,shutil,zipfile
import test_geos_editor as geos
import test_geos_semantic_editor as semantic
ROOT=geos.ROOT
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T033116850492Z/fixture'

def run(out,previous=DEFAULT):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
 records=[];f=None
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def state():
  d={n:f.get(n,w) for n,w in [('se_mode',1),('se_l_mode',1),('se_l_pan',3),('se_l_manual',1),('se_hot_caret',3),('se_v_top',3),('se_v_seen',1),('se_v_caret_row',1),('se_f_owner',1),('se_e_job',1),('se_e_error',1),('se_doc_read_locks',1),('se_fs_owned',1)]}
  d.update(request=f.m.read(0x9135),operation=f.m.read(0x9136),parent_phase=f.m.read(0x9134),GS_active=f.m.read(0x912C),GS_context_valid=f.m.read(0x912D));return d
 def safe_reu(before,after):
  handle=f.get('se_gc_handle',1)
  if not handle:assert before==after;return
  assert f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)
  assert f.m.read(f.s['se_reu_logical_owner']+handle)==0xFE
  bank=f.m.read(f.s['se_reu_map']+handle);assert f.m.read(f.s['se_reu_physical_owner']+bank)==0xFE
  start=bank*65536;pos=0
  for a,b in [(start,start+64)]+[(start+0x200+i*0x800,start+0x200+(i+1)*0x800) for i in range(22)]:
   assert after[pos:a]==before[pos:a],('foreign REU changed',pos,a);pos=b
  assert after[pos:]==before[pos:],'REU tail changed'
 def expected(data):
  s=semantic.classify(data);pan=f.get('se_l_pan');nowrap=bool(f.get('se_l_mode',1))
  bits,attrs,rows=semantic.raster(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor') if f.get('se_sel_mark',1) else None,
      styles=s.styles,roles=s.roles,reverse=s.reverse,code=s.code,nowrap=nowrap,pan=pan)
  matrix,colors,popup=geos.grid.logical_ui(f,data);bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
  return bits,attrs,rows,s
 def compare(data,tag):
  before,catalog,reu=f.canonical(),f.catalog(),whole();error=None
  try:f.render()
  except AssertionError as exc:error=str(exc)
  assert f.canonical()==before and f.catalog()==catalog and f.read(0xC600,1024)==f.shim
  safe_reu(reu,whole())
  rec=dict(tag=tag,source_hex=data.hex(),state=state(),exception=error)
  (out/(tag+'-ram.bin')).write_bytes(f.read(0,65536))
  if error:
   rec['status']='error-or-timeout';records.append(rec);return False
  assert f.merged()==data
  bits,attrs,rows,s=expected(data);actual=f.read(0x6000,8000);actual_attrs=f.read(0x4000,1000)
  diffs=[i for i,(a,b) in enumerate(zip(actual,bits)) if a!=b]
  pixel_count=sum(bin(a^b).count('1') for a,b in zip(actual,bits))
  # Code uses an existing aligned native8 cell writer whose attribute contract
  # differs from ink voting. This gate compares its bitmap, not an invented
  # attribute policy for a newly clipped/nonaligned native tile.
  prose_rows=set(y//8 for row in rows if row.height==9 for y in range(row.top,min(192,row.top+9)))
  code_rows=set(y//8 for row in rows if row.height==8 for y in range(row.top,min(192,row.top+8)))
  attrdiff=[i for i,(a,b) in enumerate(zip(actual_attrs,attrs)) if a!=b and i//40 in prose_rows-code_rows]
  witnesses=[];pan=f.get('se_l_pan')
  for row in rows:
   x=0
   for at in range(row.start,row.end):
    advance=8 if row.height==8 else fonts['bsw9-widths.bin'][geos.native(data[at])]+(s.styles[at]&1)+(s.styles[at]&2)
    if x+advance>pan:
     witnesses.append(dict(start=row.start,top=row.top,height=row.height,first_source=at,glyph_origin=x-pan,advance=advance,style=s.styles[at],role=s.roles[at]));break
    x+=advance
  rec.update(status='mismatch' if diffs or attrdiff else 'passed',bitmap_byte_differences=len(diffs),pixel_differences=pixel_count,prose_attribute_differences=len(attrdiff),first_bitmap_difference=(dict(offset=diffs[0],x=(diffs[0]%320//8)*8,y=(diffs[0]//320)*8+diffs[0]%8,actual=actual[diffs[0]],expected=bits[diffs[0]]) if diffs else None),first_intersecting_glyphs=witnesses)
  rec['code_bitmap_differences']=sum(1 for i in diffs if ((i//320)*8+i%8)//8 in code_rows)
  cache,bank=f.cache();rec['cache_prefixes']=[cache[0x200+i*0x800:0x220+i*0x800].hex() for i in range(cache[1])]
  advances=[8 if s.code[i] else fonts['bsw9-widths.bin'][geos.native(v)]+(s.styles[i]&1)+(s.styles[i]&2) for i,v in enumerate(data)]
  maps=[];caret_mismatches=[]
  for i,row in enumerate(rows):
   if i>=cache[1]:break
   raw=cache[0x200+i*0x800:0xA00+i*0x800];prefix_=raw[:32]
   want=geos.line_break(data,advances,row.start,320,int(bool(f.get('se_l_mode',1))),pan if f.get('se_l_mode',1) else 0,f.get('se_hot_caret'),0)
   count=int.from_bytes(prefix_[12:14],'little');actual_maps=[int.from_bytes(raw[512+j*2:514+j*2],'little') for j in range(count+1)]
   actual_first=int.from_bytes(prefix_[9:12],'little')
   match=actual_maps==want['maps'] and actual_first==want['first']
   left=[int.from_bytes(raw[834+j*3:837+j*3],'little') for j in range(count+1)]
   right=[int.from_bytes(raw[1317+j*3:1320+j*3],'little') for j in range(count+1)]
   assert match and left==right==list(range(want['first'],want['first']+count+1)),('canonical clipped maps',tag,i,actual_maps,want)
   maps.append(dict(start=row.start,first=actual_first,count=count,boundaries=actual_maps,canonical_affinities_exact=True))
   caret=f.get('se_hot_caret');member=row.start<=caret<row.end or caret==row.end and row.reason in (1,2)
   x=sum(advances[row.start:caret])-(pan if f.get('se_l_mode',1) else 0) if member else None
   valid=member and 0<=x<320
   actual_valid=prefix_[18];actual_x=int.from_bytes(prefix_[19:21],'little')
   if bool(actual_valid)!=valid or valid and actual_x!=x:
    caret_mismatches.append(dict(start=row.start,expected_valid=valid,expected_viewport_x=x if valid else None,actual_valid=actual_valid,actual_x=actual_x))
  rec['source_maps']=maps;rec['caret_mismatches']=caret_mismatches
  if caret_mismatches:rec['status']='mismatch'
  for suffix,raw in [('actual-bitmap',actual),('expected-bitmap',bits),('actual-attrs',actual_attrs),('expected-attrs',attrs)]:
   (out/(tag+'-'+suffix+'.bin')).write_bytes(raw)
  geos.png(actual,actual_attrs,out/(tag+'-actual-cpu.png'));geos.png(bits,attrs,out/(tag+'-expected-cpu.png'))
  records.append(rec);(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');return True
 scenarios=[('plain',geos.native_text('W'*60+'\rTail.'),0,False),
 ('bold',geos.native_text('**'+'W'*60+'**\rTail.'),5,False),
 ('italic',geos.native_text('*'+'mimW'*20+'*\rTail.'),5,False),
 ('selected',geos.native_text('**'+'Wim'*25+'**\rTail.'),2,True),
 ('basic',geos.native_text(':::basic\r10 PRINT "'+'W'*55+'"\r:::\rTail.'),0,False),
 ('asm',geos.native_text(':::asm\rlabel: .byte "'+'W'*55+'"\r:::\rTail.'),0,False)]
 try:
  for tag,data,caret,selected in scenarios:
   if f:f.close()
   f=geos.Fixture(out,frozen,dll,True);f.source(data)
   if caret:f.position(caret)
   f.command(99);assert compare(data,tag+'-wrap')
   # Actual F4 key toggles wrap; command75 is the same command as View/R.
   try:
    f.key(0x8A)
    assert f.get('se_l_mode',1)==1
   except AssertionError as exc:
    records.append(dict(tag=tag+'-F4',status='command-error-or-timeout',state=state(),exception=str(exc)));continue
   if not compare(data,tag+'-nowrap0'):continue
   if selected:
    f.command(68)
    for _ in range(7):f.command(2)
    compare(data,tag+'-marked')
   try:
    if tag=='plain':f.key(0x85);f.key(0x56);f.key(ord('R')) #actual File/View menu path
    else:f.command(75)
   except AssertionError as exc:
    records.append(dict(tag=tag+'-pan-right',status='command-error-or-timeout',state=state(),exception=str(exc)));continue
   assert f.get('se_l_mode',1)==1 and f.get('se_l_pan')>0
   if not compare(data,tag+'-pan20'):continue
   if tag in ('plain','selected'):
    try:f.command(75);compare(data,tag+'-pan40');f.command(74);compare(data,tag+'-pan-left20')
    except AssertionError as exc:records.append(dict(tag=tag+'-pan-repeat',status='command-error-or-timeout',state=state(),exception=str(exc)))
  result=dict(status='reproduced' if any(r['status']!='passed' for r in records) else 'passed',identity=identity,cases=records,full_REU_guard_bytes=16*1024*1024,scope='Read-only actual public GEOS wrap/pan/caret/selection reproduction; independent signed-left bitmap model; no native/editable-no-wrap completion claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  archive=ROOT/'agentsworking/evidence/M7'/(out.name+'-geos-nowrap-repro');archive.mkdir(parents=True)
  for path in out.iterdir():
   if path.is_file():shutil.copy2(path,archive/path.name)
  for n in ['freeze.json','product-sources.zip']:shutil.copy2(frozen/n,archive/n)
  shutil.copy2(Path(__file__),archive/Path(__file__).name)
  pointer=dict(status=result['status'],evidence=str(archive.relative_to(ROOT)),prg_sha256=identity['prg_sha256'],disk_sha256=identity['disk_sha256'],cases=len(records),failures=[dict(tag=r['tag'],status=r['status'],pixels=r.get('pixel_differences'),state=r['state']) for r in records if r['status']!='passed'])
  (ROOT/'agentsworking/evidence/M7/geos-nowrap-repro-checkpoint.json').write_text(json.dumps(pointer,indent=2)+'\n');print(json.dumps(pointer,indent=2));return result
 finally:
  if f:f.close()
def legacy_main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args();out=ROOT/'build/geos-nowrap-repro'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.fixture)


def nowrap_expected(f,data,fonts):
 """Whole logical rows at signed raster origins; no product maps consumed."""
 semantic_=semantic.classify(data);pan=f.get('se_l_pan') if f.get('se_l_mode',1) else 0
 caret=f.get('se_hot_caret');anchor=f.get('se_sel_anchor') if f.get('se_sel_mark',1) else None
 bits,attrs,rows=semantic.raster(data,fonts,top=f.get('se_v_top'),caret=caret,anchor=anchor,
     styles=semantic_.styles,roles=semantic_.roles,reverse=semantic_.reverse,code=semantic_.code,
     nowrap=bool(f.get('se_l_mode',1)),pan=pan)
 advances=[8 if semantic_.code[i] else fonts['bsw9-widths.bin'][geos.native(v)]+(semantic_.styles[i]&1)+(semantic_.styles[i]&2) for i,v in enumerate(data)]
 bits=bytearray(bits);attrs=bytearray(attrs);lo,hi=sorted((caret,anchor)) if anchor is not None else (0,0)
 for row in rows:
  # A manually panned caret is visible only when its boundary is in0..319.
  # Selection endpoints remain canonical even when that caret is hidden.
  member=row.start<=caret<row.end or caret==row.end and row.reason in (1,2)
  if member:
   x=sum(advances[row.start:caret])-pan
   if not 0<=x<320 and not lo<=caret<hi:
    width=advances[caret] if caret<row.end else 8 if row.height==8 else fonts['bsw9-widths.bin'][geos.native(32)]
    for y in range(row.top,min(192,row.top+row.height)):
     for px in range(max(0,x),min(320,x+width)):
      bits[(y//8)*320+(px//8)*8+y%8]^=128>>(px&7)
  # Aligned native8 cells retain direct foreground, including blank glyphs.
  # Unaligned/clipped native code uses per-tile ink votes with R21 priorities.
  if row.height==8 and pan%8==0:
   for at in range(row.start,row.end):
    x=(at-row.start)*8-pan
    if 0<=x<320:attrs[(row.top//8)*40+x//8]=(semantic.PALETTE[semantic_.roles[at]]<<4)|6
 matrix,colors,popup=geos.grid.logical_ui(f,data)
 bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
 return bits,attrs,rows,semantic_,advances


def exact_width_text(width,widths):
 """Canonical prose with exact reference width for partial selectedCR tests."""
 alphabet=geos.native_text(' ilWm.');found={0:b''}
 for n in range(width+1):
  if n not in found:continue
  for value in alphabet:
   end=n+widths[geos.native(value)]
   if end<=width and end not in found:found[end]=found[n]+bytes([value])
 assert width in found;return found[width]


def run_accept(out,previous):
 frozen,identity=geos.freeze(out,previous)
 paths=[Path(__file__),Path(semantic.__file__),Path(geos.__file__),ROOT/'tools/supermark_model.py',ROOT/'tests/test_geos_line.py']
 verification={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for path in paths:z.write(path,path.relative_to(ROOT))
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
 records=[];f=None;reu_intervals=0
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def guard(before,after):
  nonlocal reu_intervals
  handle=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+handle)
  assert handle and bank and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)
  assert f.m.read(f.s['se_reu_logical_owner']+handle)==f.m.read(f.s['se_reu_physical_owner']+bank)==0xFE
  start=bank*65536;cursor=0
  for a,b in [(start,start+64)]+[(start+0x200+i*0x800,start+0x200+(i+1)*0x800) for i in range(22)]:
   assert before[cursor:a]==after[cursor:a],('otherREU/unusedFEprefix',cursor,a);cursor=b
  assert before[cursor:]==after[cursor:],'otherREU/unusedFEtail';reu_intervals+=1
 def check(data,tag):
  canonical,catalog,reu=f.canonical(),f.catalog(),whole();top=f.get('se_v_top')
  f.render();assert f.canonical()==canonical and f.catalog()==catalog and f.get('se_v_top')==top,(tag,'viewchangedcanonical/catalog/top')
  assert f.merged()==data and f.read(0xC600,1024)==f.shim
  assert all(f.get(n,1)==0 for n in ('se_e_job','se_e_error','se_f_owner','se_doc_read_locks','se_fs_owned'))
  guard(reu,whole());bits,attrs,rows,sem,advances=nowrap_expected(f,data,fonts)
  actual,actual_attrs=f.read(0x6000,8000),f.read(0x4000,1000)
  for suffix,raw in [('actual-bitmap',actual),('expected-bitmap',bits),('actual-attrs',actual_attrs),('expected-attrs',attrs),('source',data)]:
   (out/(tag+'-'+suffix+'.bin')).write_bytes(raw)
  geos.png(actual,actual_attrs,out/(tag+'-actual-cpu.png'))
  assert actual==bits,(tag,'exactbitmap',next((i,a,b) for i,(a,b) in enumerate(zip(actual,bits)) if a!=b))
  assert actual_attrs==attrs,(tag,'allattributesincludingnative8arbitration',next((i,a,b) for i,(a,b) in enumerate(zip(actual_attrs,attrs)) if a!=b))
  cache,bank=f.cache();assert cache[0]==1 and cache[1]==len(rows)
  pan=f.get('se_l_pan') if f.get('se_l_mode',1) else 0;caret=f.get('se_hot_caret');members=[];horizontal=[];metadata=[]
  for i,row in enumerate(rows):
   raw=cache[0x200+i*0x800:0xA00+i*0x800];prefix_=raw[:32]
   want=geos.line_break(data,advances,row.start,320,int(bool(f.get('se_l_mode',1))),pan,caret,0)
   assert tuple(int.from_bytes(prefix_[a:a+3],'little') for a in (0,3,6))==(row.start,row.end,row.next),(tag,'canonicalrowanchors',i)
   count=int.from_bytes(prefix_[12:14],'little');first=int.from_bytes(prefix_[9:12],'little')
   assert count==len(want['maps'])-1 and first==want['first'],(tag,'clippedfirst/count',i)
   maps=[int.from_bytes(raw[512+j*2:514+j*2],'little') for j in range(count+1)]
   left=[int.from_bytes(raw[834+j*3:837+j*3],'little') for j in range(count+1)]
   right=[int.from_bytes(raw[1317+j*3:1320+j*3],'little') for j in range(count+1)]
   assert maps==want['maps'] and left==right==list(range(first,first+count+1)),(tag,'exactsourceaffinities',i)
   assert raw[32:32+count]==data[first:first+count] and raw[192:192+count]==sem.styles[first:first+count] and raw[352:352+count]==sem.roles[first:first+count],(tag,'clippedglyphs/styles/roles',i)
   raster=sum(advances[row.start:first])-pan if count else 0
   actual_raster=int.from_bytes(prefix_[24:26],'little',signed=True)
   assert actual_raster==raster,(tag,'signedfirstglyphorigin',i,raster,actual_raster)
   member=row.start<=caret<row.end or caret==row.end and row.reason in (1,2)
   x=sum(advances[row.start:caret])-pan if member else 0;valid=member and 0<=x<320
   assert bool(prefix_[26])==member and bool(prefix_[18])==valid,(tag,'independentvertical/horizontalcaret',i,member,valid,prefix_.hex())
   assert int.from_bytes(prefix_[19:21],'little')==(x if valid else 0),(tag,'caretxzeroifhidden',i)
   members.append(member);horizontal.append(valid);tailx=sum(advances[row.start:row.end])-pan
   space=8 if row.height==8 else fonts['bsw9-widths.bin'][geos.native(32)]
   tailvalid=tailx<320 and tailx+space>0 #geometry only; painting separately gates CR/EOF
   assert bool(prefix_[27])==tailvalid,(tag,'partialcanonicaltailvalid',i,tailx,space,prefix_.hex())
   if tailvalid:assert int.from_bytes(prefix_[28:30],'little',signed=True)==tailx,(tag,'signedtailx',i)
   metadata.append(dict(start=row.start,end=row.end,first=first,count=count,raster_x=raster,member=member,caret_valid=valid,caret_x=x if valid else None,tail_valid=tailvalid,tail_x=tailx if tailvalid else None))
  assert bool(cache[41])==bool(f.get('se_v_seen',1))==any(members),(tag,'SEENverticalevenhiddenhorizontal')
  assert bool(cache[45])==any(horizontal),(tag,'GPHhorizontalcaret-witness')
  records.append(dict(tag=tag,pan=pan,nowrap=f.get('se_l_mode',1),caret=caret,pending=f.get('se_hot_pending',1),rows=metadata));(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n')
 def view(command):
  before=f.canonical();top=f.get('se_v_top');f.command(command)
  assert f.canonical()==before and f.get('se_v_top')==top,('panmustnotWLOAD/flush/mutate',command)
 def position(data,p):
  line=data[:p].count(b'\r')+1;column=p-(data.rfind(b'\r',0,p)+1)
  f.typed(geos.native_text('goto '+str(line)))
  for _ in range(column):f.command(2)
  assert f.get('se_hot_caret')==p
 def new(data):
  nonlocal f
  if f:f.close()
  f=geos.Fixture(out,frozen,dll,True);f.source(data);f.command(99)
 try:
  scenarios=[('plain',geos.native_text('W'*75+'\rTail.')),
   ('bold',geos.native_text('**'+'Wim'*30+'**\rTail.')),
   ('italic',geos.native_text('*'+'mimW'*25+'*\rTail.')),
   ('basic',geos.native_text(':::basic\r10 PRINT "'+'W'*65+'":REM longer comment\r:::\rTail.')),
   ('asm',geos.native_text(':::asm\rlabel: .byte "'+'W'*65+'",$FF ; comment\r:::\rTail.'))]
  for name,data in scenarios:
   new(data);check(data,name+'-wrap');f.key(0x8A);assert f.get('se_l_mode',1)==1;check(data,name+'-nowrap0')
   # Pan on the long row, not a short fence opener, so the bound is meaningful
   # under either current-line or document-maximum policy.
   if name in ('basic','asm'):position(data,data.index(b'\r')+1)
   view(75);assert f.get('se_l_pan')==20 and f.get('se_l_mode',1)==1;check(data,name+'-pan20')
   view(75);assert f.get('se_l_pan')==40;check(data,name+'-pan40')
   view(74);assert f.get('se_l_pan')==20;check(data,name+'-left20')
   view(74);view(74);assert f.get('se_l_pan')==0;check(data,name+'-left-clamp0')
  # Auto-enable no-wrap, real menu pan route, and upper bound clamping.
  data=geos.native_text('W'*75+'i\rTail.');new(data);check(data,'auto-wrap-start')
  f.key(0x85);f.key(0x56);f.key(ord('R'));assert f.get('se_l_mode',1)==1 and f.get('se_l_pan')==20;check(data,'menu-auto-nowrap20')
  width=sum(fonts['bsw9-widths.bin'][geos.native(v)] for v in data.split(b'\r')[0]);maximum=max(0,width-320)
  for _ in range((maximum+19)//20+2):view(75)
  assert f.get('se_l_pan')==maximum;check(data,'right-clamp-maximum')
  # COUNT0 but a partially intersecting selected canonical CR tail.
  for name,code in [('prose',False),('code',True)]:
   short=b'L:' if code else exact_width_text(18,fonts['bsw9-widths.bin'])
   data=(geos.native_text(':::asm\r') if code else b'')+b'W'*75+b'\r'+short+b'\r'+(b':::\rTail.' if code else b'Tail.')
   new(data);first=len(geos.native_text(':::asm\r')) if code else 0;end=data.index(b'\r',first)+1+len(short)
   position(data,end+1);f.command(68);position(data,first);view(75);assert f.get('se_l_pan')==20
   check(data,'blank-left-selected-'+name+'-CR')
  # A real pending gap survives pan; hidden horizontal caret must not trigger
  # the unrelated canonical flush/reveal route.
  data=geos.native_text('**'+'Wim'*30+'**\rTail.');new(data);position(data,3);f.key(geos.native_text('Q')[0]);data=data[:3]+geos.native_text('Q')+data[3:]
  assert f.get('se_hot_pending',1);view(75);check(data,'pending-pan20');assert f.get('se_hot_pending',1)
  view(75);check(data,'pending-pan40');assert f.get('se_hot_pending',1)
  f.command(16);data=geos.native_text('**'+'Wim'*30+'**\rTail.');check(data,'pending-pan-undo')
  result=dict(status='passed',identity=identity,verification_sha256=verification,cases=records,screenshots=len(records),pixels=len(records)*64000,attributes=len(records)*1000,whole_REU_guard_bytes=16*1024*1024,whole_REU_intervals=reu_intervals,scope='ActualpublicGEOSnowrap/pan: allpixels/allattrs/signedorigins/canonicalaffinities/horizontalcaret/verticalmembership/partialtails/pendingpreservation. CPUonly; no native/timingclaim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:
  if f:f.close()


def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--accept',action='store_true');a=p.parse_args()
 folder='geos-nowrap-editor' if a.accept else 'geos-nowrap-repro';out=ROOT/'build'/folder/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 print('RUN '+str(out),flush=True)
 try:return run_accept(out,a.fixture) if a.accept else run(out,a.fixture or DEFAULT)
 except BaseException as error:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(error)),indent=2)+'\n');raise

if __name__=='__main__':main()
