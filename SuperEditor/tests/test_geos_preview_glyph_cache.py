"""Complete privateR23 glyphcache: realFD+FEproviders, CRCrecords, optionalmiss."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,sys,shutil,argparse,zipfile
import test_geos_preview_only as reference
old=reference.old;ORIGINAL_BUILD=old.build;ROOT=old.ROOT;D=ROOT/'src/render/geos/preview-glyph-cache-candidate';BASE=reference.DEFAULT
def build_control(out,base):
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  if 'src/render/geos/catalog-ink-preview.s' in z.namelist():
   source=out/'control-source';source.mkdir(parents=True,exist_ok=True);(source/'catalog-preview.s').write_bytes(z.read('src/render/geos/catalog-ink-preview.s'));(source/'preview-row-entry.s').write_bytes(z.read('src/render/geos/preview-row-entry.s'));result=ORIGINAL_BUILD(out,base,True,source)
  else:result=ORIGINAL_BUILD(out,base,False)
 assert(out/'r23.bin').read_bytes()==(base/'build/overlays/geosfontrow.seo').read_bytes()[36:],'exactactualcontrol'
 return result

class Fixture(reference.Fixture):
 def __init__(self,*a):
  super().__init__(*a);r=self.call('se_reu_alloc',0xfe);assert not r.p&1;self.put('se_gc_handle',r.a,1);self.put('se_gc_epoch',self.get('se_reu_epoch',2),2)
 def glyph(self,entry,value,style,inverse,clip=None,encoding=0,native=False):
  ctx=0x8800
  if clip is None:
   profile=bytes((0,1,0,8,1,6,0))if native else bytes((0,0,0,9,1,6,0))if entry[0]==2 else bytes((1,entry[1],entry[2],entry[3],1,6,0));self.m.load(0xcc12,profile);self.m.write(0xcc22,value);self.m.write(0xcc20,style);self.m.write(0xcc41,inverse);self.m.write(0xcc21,0);self.m.write(0xcc23,0);target=self.symbols['entry'];x=y=0
  else:
   if not native:self.m.load(0xcbd0,entry[:4]);assert not self.fast_call(self.symbols['se_gf_fetch_preview'])[0].p&1
   fp=0 if native else 0x5000;length=0 if native else int.from_bytes(entry[11:13],'little');inputs=fp.to_bytes(2,'little')+length.to_bytes(2,'little')+bytes((0,0x48,value,encoding,style,inverse,*clip));self.m.load(ctx,inputs+bytes([0xa7])*226);target=self.symbols['se_geos_catalog_ink_preview'];x=0;y=0x88
  before=self.read(0,65536);self.last_before=before;r,n=self.fast_call(target,x=x,y=y);after=self.read(0,65536);want=bytearray(before)
  for a,z in[(0x100,0x200),(0x5000,0x6072),(0x8800,0x88f0),(0x8a00,0x8ab0),(0xcbc0,0xcc00),(0xdf00,0xdf0b),(self.s['text_ptr'],self.s['text_ptr']+2),(self.s['screen_ptr'],self.s['screen_ptr']+2),(self.s['se_reu_c64'],self.s['dma_physical']+1),(self.s['se_crc_value'],self.s['se_crc_value']+2)]:want[a:z]=after[a:z]
  assert after==want,('fullRAM',next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b));return r,self.read(ctx,240),n

def run(out,base,smoke):
 frozen,identity=old.geos.freeze(out,base);old.geos.grid.editor_fixture.ROOT=old.geos.grid.cpu_editor.ROOT=frozen;old.geos.grid.editor_fixture.NAMES=old.geos.grid.cpu_editor.NAMES=identity['names'];build_control(out/'control',frozen)
 spec=importlib.util.spec_from_file_location('cachebuild',D/'build-cache.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);budget=m.build(out/'candidate',frozen)
 for ext in('bin','lbl'):shutil.copy2(out/'candidate'/('cache.'+ext),out/'candidate'/('r23.'+ext))
 dll=old.geos.grid.runner(out);a=Fixture(out,frozen,dll,out/'control');b=Fixture(out,frozen,dll,out/'candidate');pack=(out/'control/font-pack.bin').read_bytes();entries=[pack[32+i*16:48+i*16]for i in range(43)];fallback=(frozen/'fonts/native8.bin').read_bytes();cases=[]
 try:
  baseline=b.reu();bank=b.m.read(b.s['se_reu_map']+b.get('se_gc_handle',1));left=bank*65536+0xeb69;right=left+4160
  for face,e in enumerate(entries[-1:]if smoke else entries):
   offset=int.from_bytes(e[8:11],'little');raw=pack[offset:offset+int.from_bytes(e[11:13],'little')]
   for value,style,inverse in([(0x41,0,0),(0x47,7,1),(0xc1,3,0)]if smoke else[(v,v&7,(v>>3)&1)for v in range(256)]):
    ar,af,na=a.glyph(e,value,style,inverse);br,bf,nb=b.glyph(e,value,style,inverse);assert not(ar.p&1 or br.p&1),(face,value,ar.a,br.a)
    met,ink,cov=old.oracle(raw,fallback,value,0,style,inverse,(0,32,0,24));h=bf[18];assert bf[14:20]==af[14:20]==met and bf[20:20+h*4]==af[20:20+h*4]==ink[:h*4],('cold',face,value)
    cr,cf,nc=b.glyph(e,value,style,inverse);assert not cr.p&1 and cf[:20]==bf[:20] and cf[20:20+h*4]==bf[20:20+h*4],('hit',face,value,cr.a)
    cases.append(dict(face=face,value=value,style=style,inverse=inverse,control=na,cold=nb,warm=nc));print('CASE',cases[-1],flush=smoke)
   now=b.reu();assert now[:left]==baseline[:left] and now[right:]==baseline[right:],'whole16MiBoutside4160FE'
  result=dict(status='passed',budget=budget,cases=cases,scope='CompleteprivateR23/cache optional; actualFD+typedFE/RAM+16MiBguard. Notproduction/native.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True);return result
 finally:a.close();b.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--fixture',type=Path,default=BASE);x=p.parse_args();out=ROOT/'build/geos-preview-glyph-cache'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,x.fixture.resolve(),x.smoke)
