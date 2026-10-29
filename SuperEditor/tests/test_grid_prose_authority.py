"""Actual private C14-derived SP1 publication and C33 retained prose edits."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,importlib.util,binascii
import test_geos_fold_editor as fold
import test_grid_modes as grid
from supermark_model import blocks
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
def run(out,base=BASE):
 frozen=out/'fixture';shutil.copytree(base,frozen);spec=importlib.util.spec_from_file_location('prosebuild',ROOT/'src/render/grid/prose-authority-candidate/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf',frozen);identity=json.load(open(frozen/'freeze.json'))
 for n,seo in seos.items():(frozen/'build/overlays'/(n+'.seo')).write_bytes(seo);identity['assets'][n]=hashlib.sha256(seo).hexdigest()
 (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];f=fold.Fixture(out,frozen,dll,True)
 old=json.load(open(base/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=old['names'];g=fold.Fixture(out,base,dll,True);cases=[]
 def ready(x):x.render();x.finish_style()
 def certificate(x):
  handle=x.get('se_gc_handle',1);bank=x.m.read(x.s['se_reu_map']+handle);raw=x.reu()[bank*65536+0x1600:bank*65536+0x1680];return raw,bank
 def check_certificate(tag):
  raw,bank=certificate(f);assert raw[:4]==b'SP\1\xa5',(tag,'SP1 published',raw.hex());assert binascii.crc_hqx(raw[:126],65535)==int.from_bytes(raw[126:],'little'),tag
  assert raw[4:37]==f.read(f.s['se_st_descriptor'],33) and raw[37:39]==f.read(f.s['se_doc_epoch'],2)and raw[39:41]==f.read(f.s['se_st_generation'],2)
  rows=f.read(f.s['se_v_rows'],66)+f.read(f.s['se_v_bottom'],3);assert raw[42:111]==rows,(tag,'exactcapturedviewport')
  starts=[int.from_bytes(rows[i:i+3],'little')for i in range(0,66,3)];prose={q['start']for q in blocks(f.merged())if q['kind']==0};wanted=sum(1<<i for i,p in enumerate(starts)if p in prose)
  assert int.from_bytes(raw[111:114],'little')==wanted,(tag,'genuine whole-source block oracle',bin(int.from_bytes(raw[111:114],'little')),bin(wanted));return bank
 def setup(raw,width,at):
  for x in(f,g):x.source(raw);x.command(97 if width==60 else 98);x.position(at);ready(x)
  check_certificate('setup')
 def edit(tag,key):
  for x in(f,g):x.key(key)
  before=f.canonical();reu=f.reu();phase=f.read(0x8d00,1152);start=f.total_instructions;loads=f.get('se_overlay_loads',2);f.render();instructions=f.total_instructions-start
  assert f.m.read(0x89ff)==1,(tag,'actual typingbranch')
  # Full reference follows its ordinary parser/plan publication route.
  g.put('se_gc_valid',0,1);ready(g);want,attrs=grid.expected(f,f.merged())[0]
  assert f.read(0x6000,8000)==want==g.read(0x6000,8000),(tag,'allpixels')
  assert f.read(0x4000,1000)==attrs==g.read(0x4000,1000),(tag,'allattrs')
  assert f.canonical()==before and f.read(0x8d00,1152)==phase and f.read(0xc600,1024)==f.shim,(tag,'canonical/history/phase/shim')
  bank=check_certificate(tag);now=f.reu();a=bank*65536;assert now[:a]==reu[:a] and now[a+65536:]==reu[a+65536:],(tag,'allforeign16MiB')
  expected=bytearray(reu[a:a+65536]);row=f.get('se_v_caret_row',1)
  for p,z in [(row*240,(row+1)*240),(0x1500,0x1600),(0x1600,0x1680)]:expected[p:z]=now[a+p:a+z]
  assert bytes(expected)==now[a:a+65536],(tag,'onlyownedpacket/header/SP1')
  cases.append(dict(tag=tag,instructions=instructions,loads=(f.get('se_overlay_loads',2)-loads)&65535));print('PASS',cases[-1],flush=True)
 try:
  raw=grid.native_text('# Heading\r:::basic\r10 PRINT "x"\r:::\r:::asm\rlda #1\r:::\r:::region Closed\rregion body\r:::end\rAlpha paragraph having ample room.\rTail.')
  at=raw.index(grid.native_text('having'))+2
  for width in(60,80):
   setup(raw,width,at)
   for i,key in enumerate([81,82,20,20]):edit(str(width)+'-after-closed-fences-region-'+str(i),key)
  # More than64KiB of parser prefix: authoritative event START is24-bit,
  # and a leading closed fence far before the viewport must not be inferred.
  high=grid.native_text(':::basic\r')+b'X'*65540+grid.native_text('\r:::\rAlpha paragraph having ample room.\rTail.')
  at=high.index(grid.native_text('having'))+2
  setup(high,80,at);edit('80-above64KiB-insert',81);edit('80-above64KiB-delete',20)
  # Fold publications remain an explicit optional miss, not a false claim of
  # canonical row-locality through collapsed intervals.
  faults=[]
  def miss(tag,text='Alpha paragraph having ample room.\rTail.',at=12,key=81,mutate=None):
   setup(grid.native_text(text),80,at);f.key(key)
   if mutate:mutate()
   before=f.canonical();reu=f.reu();phase=f.read(0x8d00,1152);pixels=f.read(0x6000,8000)+f.read(0x4000,1000);f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
   assert r.a==2 and not r.p&1,(tag,'optional readonly miss',r.a,r.p)
   assert before==f.canonical()and reu==f.reu()and phase==f.read(0x8d00,1152)and pixels==f.read(0x6000,8000)+f.read(0x4000,1000),(tag,'refusal before writes')
   faults.append(dict(tag=tag,instructions=n));print('MISS',tag,n,flush=True)
  for tag,text,at,key in [('ASM-keyword',':::asm\rla\r:::',8,grid.native_text('d')[0]),('BASIC-keyword',':::basic\rPRNT\r:::',11,grid.native_text('I')[0]),('activate-basic',':::basc\rTail.',6,grid.native_text('i')[0]),('activate-region',':::regin\rTail.',7,grid.native_text('o')[0]),('heading','#Heading\rTail.',1,32),('list','*word\rTail.',1,32),('unclosed-code-after-prefix',':::asm\rxyz\rAlpha paragraph having room.',25,81),('inline','Alpha **bold** words.\rTail.',10,81),('softwrap','A'*100,12,81),('CR','Alpha paragraph.\rTail.',8,13)]:miss(tag,text,at,key)
  def corrupt(offset,value=None,recrc=False):
   raw,bank=certificate(f);raw=bytearray(raw);raw[offset]=raw[offset]^1 if value is None else value
   if recrc:raw[126:]=binascii.crc_hqx(raw[:126],65535).to_bytes(2,'little')
   # Explicit host fault-injection via existing real REU DMA, never seeded
   # successful parser authority in an accepted frame.
   f.m.load(0x8b00,raw);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',0x1600,2);f.put('se_reu_c64',0x8b00,2);f.put('se_reu_length',128,2);assert not f.call('se_reu_copy',0).p&1
  for tag,offset,value,recrc in [('CRC',126,None,False),('magic',0,0,True),('version',2,2,True),('unpublished',3,0,True),('source-token',4,None,True),('doc-epoch',37,None,True),('style-generation',39,None,True),('width',41,60,True),('row-anchor',42,None,True),('not-prose',111,0,True)]:miss('SP1-'+tag,mutate=lambda o=offset,v=value,c=recrc:corrupt(o,v,c))
  for name,size,value in [('se_f_owner',1,1),('se_f_owner',1,2),('se_f_owner',1,3),('se_sel_mark',1,1),('se_ef_valid',1,1),('se_reu_retired',1,1),('se_st_valid',1,0),('se_st_request',1,1)]:miss(name,mutate=lambda n=name,z=size,v=value:f.put(n,v,z))
  for tag,mutate in [('FE-logical-owner',lambda:f.m.write(f.s['se_reu_logical_owner']+f.get('se_gc_handle',1),253)),('FE-physical-owner',lambda:f.m.write(f.s['se_reu_physical_owner']+f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1)),253)),('FE-map',lambda:f.m.write(f.s['se_reu_map']+f.get('se_gc_handle',1),0)),('FE-epoch',lambda:f.put('se_gc_epoch',f.get('se_gc_epoch',2)^1,2))]:miss(tag,mutate=mutate)
  # Real history replay changes canonical identity. Actual reparse must publish
  # a fresh certificate before another row-local edit can be admitted.
  normal=grid.native_text(':::asm\rlda #1\r:::\rAlpha paragraph having ample room.\rTail.')
  at=normal.index(grid.native_text('having'))+2;setup(normal,80,at);edit('history-insert',81)
  for command in(16,17):
   for x in(f,g):x.command(command);ready(x)
   assert f.merged()==g.merged()and f.read(0x6000,8000)==g.read(0x6000,8000)and f.read(0x4000,1000)==g.read(0x4000,1000)
   check_certificate('history-'+str(command))
  edit('post-replay-insert',82)
  # A real earlier grammar transition must reclassify later visible prose;
  # fresh certificates cannot inherit a former role0/plain witness.
  carry_cases=[]
  for tag,text,edit_at,key,target in [('activate-earlier-basic',':::basc\r10 PRINT 1\rAlpha paragraph having ample room.\rTail.',6,grid.native_text('i')[0],'having'),('close-earlier-basic',':::basic\r10 PRINT 1\r::\rAlpha paragraph having ample room.\rTail.',22,ord(':'),'having')]:
   raw=grid.native_text(text);at=raw.index(grid.native_text(target))+2;setup(raw,80,at)
   for x in(f,g):
    x.position(edit_at);x.key(key);ready(x);at=x.merged().index(grid.native_text(target))+2;line=x.merged()[:at].count(b'\r')+1;column=at-(x.merged().rfind(b'\r',0,at)+1)
    x.typed(grid.native_text('goto '+str(line)))
    for _ in range(column):x.key(0x1d)
    ready(x)
   check_certificate(tag);assert f.merged()==g.merged()and f.read(0x6000,8000)==g.read(0x6000,8000)and f.read(0x4000,1000)==g.read(0x4000,1000)
   carry_cases.append(dict(tag=tag,source=f.merged().hex()))
  # New R14 producer operations are strictly owner2; opaque foreign phases and
  # source/provider/REU remain exact. These are actual public overlay calls.
  opacity=[]
  for owner in(0,1,3,4):
   for operation in(3,4,5):
    f.put('se_f_owner',owner,1);f.put('se_overlay_frame',operation,1);phase=f.read(0x8d00,1152);scratch=f.read(0x89c0,64)+f.read(0x8a00,128);reu=f.reu();before=f.canonical();r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0)
    assert r.p&1 and r.a==2,(owner,operation,'opaque refusal')
    assert phase==f.read(0x8d00,1152)and scratch==f.read(0x89c0,64)+f.read(0x8a00,128)and reu==f.reu()and before==f.canonical(),(owner,operation,'phase/source/REU opacity')
    opacity.append(dict(owner=owner,operation=operation,instructions=n))
  f.put('se_f_owner',0,1)
  result=dict(status='passed',budget=budget,cases=cases,faults=faults,producer_wrong_owner=opacity,carry_transitions=carry_cases,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close();g.close()
if __name__=='__main__':
 out=ROOT/'build/grid-prose-authority'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
