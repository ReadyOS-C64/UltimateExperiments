"""Bytepaint actualC27 private reassembly/A-B; no production/shared edits."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,random,shutil,subprocess,sys,zipfile
import test_geos_editor as geos
import test_geos_preview_editor as public
from overlays import wrap
ROOT=geos.ROOT
BASE=ROOT/'build/geos-incremental-editor/20261025T115828132288Z/fixture'
PRIVATE=ROOT/'src/render/geos/preview-byte-paint-candidate'


def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 assert not p.returncode,(args,p.stdout,p.stderr)


def build(out,base):
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];inc=out/'includes';inc.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith('src/') and name.endswith(('.inc','.s')):
    p=inc/name[4:];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
  source=z.read('src/render/geos/preview.s').decode();cfg=z.read('cfg/geos-editor-page.cfg')
 a=source.index('paint:\n');b=source.index('complete:\n',a)
 replacement=(PRIVATE/'paint.inc').read_text()
 candidate=source[:a]+replacement+'\n'+source[b:]
 assert candidate.count('masks: .byte $80,$40,$20,$10,8,4,2,1')==1
 candidate=candidate.replace('masks: .byte $80,$40,$20,$10,8,4,2,1','masks: .byte $80,$40,$20,$10,8,4,2,1\nclip_masks: .byte $FF,$80,$C0,$E0,$F0,$F8,$FC,$FE')
 images={};sizes={}
 for variant,text in [('control',source),('candidate',candidate)]:
  d=out/variant;d.mkdir();(d/'preview.s').write_text(text);(d/'cfg').write_bytes(cfg)
  command(sys.executable,'tools/overlay_api.py','--all-public','--symbols','text_ptr','screen_ptr','--report',base/'build/editor-report.json','--output',d/'editor-api.inc')
  command('ca65','-g','-I',d,'-I',inc,'-o',d/'preview.o',d/'preview.s')
  command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'binding.s',d/'preview.o')
  command('ca65','-o',d/'binding.o',d/'binding.s')
  command('ld65','-C',d/'cfg','-o',d/'preview.bin','-Ln',d/'preview.lbl','-m',d/'preview.map',d/'preview.o',d/'binding.o')
  raw=(d/'preview.bin').read_bytes();sizes[variant]=len(raw)
  if variant=='control':assert raw==(base/'build/overlays/geospreview.seo').read_bytes()[36:]
  images[variant]=wrap(raw,1,27,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))
  print('LINK',variant,len(raw),flush=True)
 return images,sizes


def run_public(out,base,variant,image):
 base_class=public.Fixture
 measurements=[]
 class PrivateFixture(base_class):
  def __init__(self,*a,**kw):
   super().__init__(*a,**kw)
   self.assets['geospreview']=image
  def render(self):
   preview=bool(self.get('se_r_presentation',1));before=self.total_instructions;loads=self.get('se_overlay_loads',2)
   result=super().render()
   if preview:measurements.append(dict(instructions=self.total_instructions-before,loads=(self.get('se_overlay_loads',2)-loads)&65535))
   return result
 public.Fixture=PrivateFixture
 try:public.run(out,base)
 finally:public.Fixture=base_class
 r=json.loads((out/'result.json').read_text())
 assert len(measurements)==len(r['frames']),(len(measurements),len(r['frames']))
 for frame,cost in zip(r['frames'],measurements):frame['CPU_render']=cost
 r['private_C27_replacement']=dict(variant=variant,sha256=hashlib.sha256(image).hexdigest(),scope='Only actualC27 private SEO differs; actualpubliccommands/root/provider and canonical/fontoracles unchanged.')
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r


def micro(out,base,images):
 from test_geos_catalog_byte_candidate import symbols
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=base
 names=json.loads((base/'freeze.json').read_text())['names'];geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=names
 (out/'runner').mkdir();dll=geos.grid.runner(out/'runner');fixtures={};labels={}
 for name in images:
  fixtures[name]=public.Fixture(out,base,dll,True);fixtures[name].source(b'');fixtures[name].m.load(0xb000,images[name][36:])
  fixtures[name].m.write(fixtures[name].s['se_f_owner'],4)
  labels[name]=symbols(out/name/'preview.lbl')['paint']
 rng=random.Random(0x651027);cases=[]
 for phase in range(8):
  for advance in range(28):
   for height in (1,9,24):cases.append((phase,advance,height))
 for i in range(256):cases.append((rng.randrange(8),rng.randrange(28),rng.randrange(1,25)))
 costs=[];baselines={k:f.reu()for k,f in fixtures.items()}
 try:
  for index,(phase,advance,height)in enumerate(cases):
   possible=[x for x in range(321-advance)if x%8==phase]
   if not possible:continue
   x=rng.choice(possible);offset=rng.randrange(33-height);top=rng.choice(range(16,161,8));baseline=rng.randrange(height)
   role=rng.randrange(14);fg=rng.randrange(16);bg=rng.randrange(16)
   ink=bytes([255])*96 if index%3==0 else rng.randbytes(96)if hasattr(rng,'randbytes')else bytes(rng.randrange(256)for _ in range(96))
   bitmap=bytes(rng.randrange(256)for _ in range(8000));attrs=bytes(rng.randrange(256)for _ in range(1000));flags=bytes(rng.choice((0,0,1))for _ in range(160))
   expected=bytearray(bitmap);colors=bytearray(attrs);ef=bytearray(flags)
   color=(fg if role<7 else {7:7,8:13,9:5,10:15,11:7,12:3,13:1}[role])*16+bg
   for y in range(height):
    py=top+offset+y
    for col in range(advance):
     if ink[y*4+col//8]&(128>>(col%8)):
      px=x+col;tile=(py//8)*40+px//8;address=(py//8)*320+(px//8)*8+(py%8)
      expected[address]|=128>>(px%8)
      local=((py-top)//8)*40+px//8
      if not ef[local]:ef[local]=1;colors[tile]=color
   entry=dict(index=index,phase=phase,advance=advance,height=height)
   for name,f in fixtures.items():
    f.m.load(0x6000,bitmap);f.m.load(0x4000,attrs);f.m.load(0xcd00,flags)
    f.m.load(0xcc0a,x.to_bytes(2,'little'));f.m.write(0xcc0c,top);f.m.write(0xcc36,baseline+offset)
    f.m.write(0xcc12+4,fg);f.m.write(0xcc19+5,bg);f.m.write(0xcc21,role)
    f.m.write(0x8811,advance);f.m.write(0x8812,height);f.m.write(0x8813,baseline);f.m.load(0x8814,ink)
    before=f.read(0,65536);r,used=f.fast_call(labels[name]) #internal paint has no carry return contract
    after=f.read(0,65536);want=bytearray(before)
    allowed=[(0x100,0x200),(0x4000,0x43e8),(0x6000,0x7f40),(0xcd00,0xcda0),(0xcc25,0xcc30),(0xcc33,0xcc36),(0xcc38,0xcc39),(f.s['text_ptr'],f.s['text_ptr']+2),(f.s['screen_ptr'],f.s['screen_ptr']+2)]
    for a,b in allowed:want[a:b]=after[a:b]
    assert after==want,(index,name,'fullRAM',next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
    assert f.read(0x6000,8000)==expected and f.read(0x4000,1000)==colors and f.read(0xcd00,160)==ef,(index,name,'independentpixels/attrs/firstink')
    entry[name+'_instructions']=used
   costs.append(entry)
  for name,f in fixtures.items():assert f.reu()==baselines[name],name+' all16MiB'
  result=dict(status='PASS',cases=costs,body_pixel_composites=len(costs),whole16MiB_unchanged=True,scope='IsolatedactualC27internalpaint underdeclaredalignedband geometry; randomink clippedtoadvance, all8phases/0..27advance/1..24height, firstinkattrflags andfullRAM oracle. Notpublicinput/nativecycles.')
  (out/'micro-result.json').write_text(json.dumps(result,indent=2)+'\n')
  print('MICRO',len(costs),sum(x['control_instructions']for x in costs),sum(x['candidate_instructions']for x in costs),flush=True)
 finally:
  for f in fixtures.values():f.close()


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--micro',action='store_true');p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--variant',choices=['control','candidate'],default='candidate');a=p.parse_args()
 out=ROOT/'build/geos-preview-byte-paint-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 images,sizes=build(out,a.fixture.resolve());(out/'budget.json').write_text(json.dumps(sizes,indent=2)+'\n')
 if a.micro:micro(out,a.fixture.resolve(),images)
 if a.run:run_public(out,a.fixture.resolve(),a.variant,images[a.variant])
