"""Private no-new-asset C33/R25 factoring and short-row typing capsule.
Actual sealed images; no canonical/shared products are modified.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,shutil
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
def run(out,base):
 frozen=out/'fixture';shutil.copytree(base,frozen)
 spec=importlib.util.spec_from_file_location('gridtypingbuild',ROOT/'src/render/grid/typing-candidate/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf',frozen)
 identity=json.loads((frozen/'freeze.json').read_text());names=identity['names']
 for name,seo in seos.items():
  assert name in names; (frozen/'build/overlays'/(name+'.seo')).write_bytes(seo);identity['assets'][name]=hashlib.sha256(seo).hexdigest()
 (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=names;f=fold.Fixture(out,frozen,dll,True)
 old=json.loads((base/'freeze.json').read_text());grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=old['names'];g=fold.Fixture(out,base,dll,True);cases=[]
 def ready(x):x.render();x.finish_style()
 try:
  for width in (60,80):
   raw=grid.native_text('# Heading\rPlain paragraph having ample room.\rSecond untouched source row.\rTail.')
   for x in(f,g):x.source(raw);x.command(97 if width==60 else 98);x.position(16);ready(x)
   for key in (81,20):
    for x in(f,g):x.key(key)
    before=f.canonical();phase=f.read(0x8d00,1152);ram=f.read(0,65536);reu=f.reu();start=f.total_instructions;cycles=f.m.regs().cycles;loads=f.get('se_overlay_loads',2);r=f.render();n=f.total_instructions-start;cycles=f.m.regs().cycles-cycles
    # The reference explicitly drops only the disposable row-cache validbits.
    g.put('se_gc_valid',0,1);g.render();g.finish_style()
    want,attrs=grid.expected(f,f.merged())[0]
    assert not r.p&1 and r.a==0,(width,key,'result',r.a,r.p)
    assert f.m.read(0x89ff)==1,(width,key,'typing admitted',f.read(0x89c0,64).hex())
    assert f.read(0x6000,8000)==want==g.read(0x6000,8000),(width,key,'typing pixels',next((i for i,(a,b)in enumerate(zip(f.read(0x6000,8000),want))if a!=b),None))
    assert f.read(0x4000,1000)==attrs==g.read(0x4000,1000),(width,key,'typing attrs')
    assert f.canonical()==before and f.read(0x8d00,1152)==phase and f.read(0xc600,1024)==f.shim
    bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));offset=bank*65536;now=f.reu();assert now[:offset]==reu[:offset] and now[offset+65536:]==reu[offset+65536:],'all foreign16MiB exact'
    expected=bytearray(reu[offset:offset+65536]);row=f.get('se_v_caret_row',1)
    for a,z in [(row*240,(row+1)*240),(0x1500,0x1600)]:expected[a:z]=now[offset+a:offset+z]
    assert bytes(expected)==now[offset:offset+65536],'ownedFE only one packet+NCheader'
    after=f.read(0,65536);expected=bytearray(ram)
    for a,z in [(2,0x1c),(0x100,0x200),(0x4000,0x43e8),(0x5000,0x8c00),(0x8c00,0x8d00),(0xa000,0xc600),(0xca00,0xd000),(0xd000,0xe000)]:expected[a:z]=after[a:z]
    for name,size in [('read_budget',2),('se_object_id',5),('validate_index',3)]:
     a=f.s[name];expected[a:a+size]=after[a:a+size]
    assert bytes(expected)==after,('all64KiB guard',[(hex(i),a,b)for i,(a,b)in enumerate(zip(expected,after))if a!=b][:20])
    fold.geos.png(want,attrs,out/(str(width)+'-'+str(key)+'.png'))
    cases.append(dict(width=width,key=key,typing=True,instructions=n,loads=(f.get('se_overlay_loads',2)-loads)&65535));print('PASS',cases[-1],flush=True)
   for key in (2,1,2):
    for x in(f,g):x.command(key)
    before=f.canonical();phase=f.read(0x8d00,1152);start=f.total_instructions;r=f.render();n=f.total_instructions-start;g.render();g.finish_style()
    assert not r.p&1 and r.a==0,(width,key,r.a,r.p)
    want,attrs=grid.expected(f,f.merged())[0]
    assert f.read(0x6000,8000)==want==g.read(0x6000,8000),(width,key,'pixels')
    assert f.read(0x4000,1000)==attrs==g.read(0x4000,1000),(width,key,'attrs')
    assert f.canonical()==before and f.read(0x8d00,1152)==phase and f.read(0xc600,1024)==f.shim
    cases.append(dict(width=width,key=key,instructions=n));print('PASS',cases[-1],flush=True)
  # Actual optional TRY refusal must not alter pixels, any REU byte, phase or
  # source/history. Mutations below are declared fault-injection seams only.
  faults=[]
  def setup(text='Alpha paragraph having ample room.\rTail.',at=12,width=80):
   for x in(f,g):x.source(grid.native_text(text));x.command(97 if width==60 else 98);x.position(at);ready(x)
  def miss(tag,mutate=lambda:None,key=81):
   f.key(key);mutate();before=f.canonical();reu=f.reu();phase=f.read(0x8d00,1152);pixels=f.read(0x6000,8000)+f.read(0x4000,1000);f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
   assert r.a==2 and not r.p&1,(tag,'optional miss',r.a,r.p)
   assert f.canonical()==before and f.reu()==reu and f.read(0x8d00,1152)==phase and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels,(tag,'readonly refusal')
   faults.append(dict(tag=tag,instructions=n));print('MISS',tag,n,flush=True)
  for tag,text,at,key in [('heading','# Heading\rTail.',4,81),('inline','Alpha **bold** words.\rTail.',10,81),('bullet','- Bullet words.\rTail.',7,81),('softwrap','A'*100,12,81),('CRinsert','Alpha paragraph.\rTail.',8,13),('spaceinsert','Alpha paragraph.\rTail.',8,32),('firstbyte','Alpha paragraph.\rTail.',0,81),('ASM-keyword',':::asm\rla\r:::',8,grid.native_text('d')[0]),('BASIC-keyword',':::basic\rPRNT\r:::',11,grid.native_text('I')[0]),('activate-basic-fence',':::basc\rTail.',6,grid.native_text('i')[0]),('activate-region-fence',':::regin\rTail.',7,grid.native_text('o')[0]),('malformed-heading','#Heading\rTail.',1,32),('malformed-list','*word\rTail.',1,32),('prior-closed-code',':::text\rclosed\r:::\rAlpha paragraph.\rTail.',28,81),('long-prefix','X'*130+'\rAlpha paragraph.\rTail.',140,81)]:
   setup(text,at);miss(tag,key=key)
  for name,width,value in [('se_f_owner',1,1),('se_f_owner',1,2),('se_f_owner',1,3),('se_sel_mark',1,1),('se_l_pan',3,1),('se_reu_retired',1,1),('se_st_valid',1,0),('se_st_request',1,1),('se_e_ui',1,1),('se_gc_valid',1,254),('se_hot_delete',1,1)]:
   setup();miss(name,lambda name=name,width=width,value=value:f.put(name,value,width))
  # A new C33 must safely decline an old, same-resident-binding R25 image.
  setup();oldtail=(base/'build/overlays/geostail.seo').read_bytes()
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==25 and f.m.read(f.s['image_slot']+i)&1==0:f.m.write(f.s['se_overlay_ids']+i,0)
  f.m.write(f.s['se_overlay_active'],0);f.m.load(f.s['se_overlay_header'],oldtail[:36]);f.m.load(0x5000,oldtail[36:]);assert not f.call('se_overlay_import').p&1
  miss('mixed-generation-old-R25')
  # Old C33 must remain compatible with expanded R25, including its legacy
  # GEOS tail op0/op1. Reinstall old C33 via the real typed catalog importer.
  oldgrid=(base/'build/overlays/grid.seo').read_bytes()
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==33 and f.m.read(f.s['image_slot']+i)&1==1:f.m.write(f.s['se_overlay_ids']+i,0)
  f.m.write(f.s['se_overlay_active']+1,0);f.m.load(f.s['se_overlay_header'],oldgrid[:36]);f.m.load(0x5000,oldgrid[36:]);assert not f.call('se_overlay_import').p&1
  f.assets['grid']=oldgrid
  compatibility=[]
  for mode in (97,98,99):
   raw=grid.native_text('First row\rSecond row\rTail.')
   for x in(f,g):
    x.source(raw);x.command(mode);x.position(3);x.render()
    if mode!=99:x.finish_style()
   for x in(f,g):x.command(2);x.render()
   assert f.read(0x6000,8000)==g.read(0x6000,8000) and f.read(0x4000,1000)==g.read(0x4000,1000) and f.merged()==raw and f.read(0xc600,1024)==f.shim
   # Selection includes a genuine CR, exercising virtual GEOS tail selection.
   for x in(f,g):x.command(68);x.position(15);x.render()
   assert f.read(0x6000,8000)==g.read(0x6000,8000) and f.read(0x4000,1000)==g.read(0x4000,1000)
   compatibility.append(dict(mode=mode,oldC33newR25=True,selection_CR=True))
  result=dict(status='passed',budget=budget,cases=cases,faults=faults,compatibility=compatibility);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/grid-typing-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base)
