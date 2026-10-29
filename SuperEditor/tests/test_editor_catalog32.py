"""Optional32-entry editor catalog: real cache/header/CRC/provider/DMA, private CPU proof.
No shared build or production enable. Generic bytes/arbitrary entries remain valid.
"""
from pathlib import Path
import binascii,ctypes as C,hashlib,importlib.util,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
from overlays import HEADER,wrap
spec=importlib.util.spec_from_file_location('catalog_tail',ROOT/'tests/test_overlay_tail.py');tail=importlib.util.module_from_spec(spec);spec.loader.exec_module(tail)
OUT=ROOT/'build/editor-catalog32'
BASE=ROOT/'agentsworking/evidence/M5/20261025T004901311531Z-fold-editor-native'
DIGEST=bytes(range(16))
def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def freeze():
 out=OUT/'accepted800';out.mkdir(parents=True,exist_ok=True)
 names=['editor.prg','editor-report.json','editor.lbl','editor.map','editor-bindings.json','supereditor.d81','product-sources.zip']
 names += [p.name for p in sorted(BASE.glob('*.seo'))]
 manifest={}
 for name in names:
  p=BASE/name
  if p.exists():shutil.copy2(p,out/name);manifest[name]=sha(p)
 assert manifest['editor.prg']=='800ef98ec5ab478b1049b3f9bb13879056887ef7dee25a874083921b713625e5'
 entries={p.name:int.from_bytes(p.read_bytes()[10:12],'little') for p in out.glob('*.seo')}
 assert len(entries)==23 and set(entries.values())=={16}
 with zipfile.ZipFile(out/'product-sources.zip') as z:
  for n in z.namelist():
   if n.startswith('src/') and not n.endswith('/'):
    p=OUT/'baseline'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 tail.FROZEN=OUT/'baseline'
 (out/'freeze.json').write_text(json.dumps(dict(files=manifest,entries=entries),indent=2)+'\n');return manifest

def build(name,fixed=False,capacity=32,fast=True):
 # Reuse the previously proved isolated cache fixture; add only the new flag.
 tail.OUT=OUT
 original=tail.run
 def invoke(args,**kw):
  args=list(args)
  if str(args[0])=='ca65' and fixed:args[1:1]=['-D','EDITOR_FIXED_ENTRY=1']
  return original(args,**kw)
 tail.run=invoke
 try:return tail.compile_variant(name,tail=True,capacity=capacity,fast=fast)
 finally:tail.run=original

def accelerator():
 out=OUT/'runner';out.mkdir(parents=True,exist_ok=True);cpp=out/'runner.cpp'
 cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t c32_run(ZeroPagePeddle*m,uint64_t n){auto s=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<n;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-s;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void c32_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*p){for(uint32_t i=0;i<n;i++)p[i]=zeropage_peddle_read_reu(m,i);}
''')
 ext='.dylib' if sys.platform=='darwin' else '.so';Machine().close();p=out/('runner'+ext)
 run('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',p)
 dll=C.CDLL(str(p));dll.c32_run.argtypes=[C.c_void_p,C.c_uint64];dll.c32_run.restype=C.c_uint64;dll.c32_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return dll
DLL=None
class Fixture(tail.Fixture):
 def __init__(self,*args,**kw):super().__init__(*args,**kw);self.m.call=self.fast
 def fast(self,address,a=0,x=0,y=0,limit=2000000):
  for n,v in [('pc',address),('sp',0xFD),('p',0x24),('a',a),('x',x),('y',y)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=DLL.c32_run(self.m.handle,limit);assert used,('nonreturn',hex(address),hex(self.m.regs().pc));return self.m.regs(),used
 def reu(self):
  p=C.create_string_buffer(self.banks*65536);DLL.c32_reu(self.m.handle,len(p),p);return p.raw
 def image(self,identity,slot,entry=16):
  if identity in [2,3,4]:
   child,cs=(1,0) if identity==2 else (2,1)
   code=bytes([0xA9,child,0xA2,cs,0x20,self.s['se_overlay_call']&255,self.s['se_overlay_call']>>8,0x60])
  else:code=bytes([0xA9,identity,0x18,0x60])
  payload=DIGEST+bytes((i*31+identity)&255 for i in range(16,entry))+code
  payload+=bytes((i*31+identity)&255 for i in range(len(payload),4096))
  return wrap(payload,slot,identity,entry,api=(self.s['se_overlay_call'],self.s['se_overlay_frame']),binding_digest=DIGEST)

def reseal(data):
 data=bytearray(data);data[14:16]=binascii.crc_hqx(data[:14]+data[16:36],0xffff).to_bytes(2,'little');return data

def full(out,s,banks=256):
 f=Fixture(out,s,banks=banks);cases=[]
 try:
  expected=bytearray(f.baseline);images=[]
  first=f.get('se_overlay_asset');assert first==1 and f.m.read(s['se_reu_map']+first)==2
  # Every incorrect entry, including otherwise-valid arbitrary entries, fails
  # before CRC staging/allocation/DMA. Reseal isolates grammar from header CRC.
  before=f.canonical();dma=f.get('se_reu_dma_calls',2)
  for entry in [0,1,15,17,255,256,4080,4095,4096,65535]:
   bad=bytearray(f.image(100,0));bad[10:12]=entry.to_bytes(2,'little');f.imported(reseal(bad),error=0x13)
   assert f.canonical()==before and f.get('se_reu_dma_calls',2)==dma
  # A16-byte payload cannot contain its required entry.
  bad=bytearray(f.image(100,0));bad[8:10]=(16).to_bytes(2,'little');f.imported(reseal(bad),error=0x13)
  cases.append('fixed entry grammar rejects10bad offsets and empty entry before DMA')
  for i in range(32):
   if i==16:
    before=f.canonical();dma=f.get('se_reu_dma_calls',2)
    bad=bytearray(f.image(17,0));bad[0]=0;f.imported(bad,error=0x10)
    bad=bytearray(f.image(17,0));bad[HEADER+200]^=1;f.imported(bad,error=0x14)
    assert f.canonical()==before and f.get('se_reu_dma_calls',2)==dma and f.get('se_overlay_asset_second')==0
   image=f.image(i+1,i&1);images.append(image);f.imported(image)
   bank=2 if i<16 else 4;offset=(i&15)*4096
   expected[bank*65536+offset:bank*65536+offset+4096]=image[HEADER:]
   if i<16:assert f.get('se_overlay_asset_second')==0
  assert f.get('se_overlay_asset_second')==2 and f.m.read(s['se_reu_map']+2)==4
  assert f.read(s['se_overlay_ids'],32)==bytes(range(1,33)) and f.reu()==expected
  cases.append('32full4096images occupy two logical banks on nonidentity physical2/4')
  before=f.canonical();dma=f.get('se_reu_dma_calls',2);f.imported(f.image(200,0),error=0x15)
  assert f.canonical()==before and f.get('se_reu_dma_calls',2)==dma
  cases.append('33rd image refuses before DMA/allocation/canonical mutation')
  for i in list(reversed(range(32)))+list(range(32)):
   identity=i+1
   if identity in (3,4):f.call('se_overlay_call',identity,i&1,error=0x19)
   else:assert f.call('se_overlay_call',identity,i&1)==(1 if identity==2 else identity)
   assert f.read(0xA000+(i&1)*4096,4096)==images[i][HEADER:]
  assert f.read(s['se_overlay_busy'],2)==b'\0\0' and f.reu()==expected
  cases.append('late IDs and both slots survive eviction/hits and C-to-R nesting restrictions')
  # Last byte of last bank image is CRC-covered before executable publication.
  second=f.get('se_overlay_asset_second');offset=65535
  for n,v,w in [('se_reu_logical',second,1),('se_reu_c64',0x7000,2),('se_reu_offset',offset,2),('se_reu_length',1,2)]:f.put(n,v,w)
  f.m.write(0x7000,images[-1][-1]^1);f.call('se_reu_copy');expected[4*65536+offset]^=1
  f.call('se_overlay_call',30,1);before=f.read(s['se_overlay_active'],2)+f.read(0xB000,4096)
  f.call('se_overlay_call',32,1,error=0x14)
  assert f.read(s['se_overlay_active'],2)+f.read(0xB000,4096)==before and f.reu()==expected
  cases.append('corrupt32nd image preserves active tags/executable')
  f.m.write(s['se_reu_logical_owner']+second,4);before=f.canonical();dma=f.get('se_reu_dma_calls',2)
  f.call('se_overlay_call',30,1,error=0x18);f.imported(f.image(201,0),error=0x18)
  assert f.canonical()==before and f.get('se_reu_dma_calls',2)==dma
  f.m.write(s['se_reu_logical_owner']+second,2);f.call('se_overlay_call',29,0)
  f.m.write(s['se_reu_physical_owner']+4,4);dma=f.get('se_reu_dma_calls',2)
  f.call('se_overlay_call',31,0,error=4);assert f.get('se_reu_dma_calls',2)==dma
  f.m.write(s['se_reu_physical_owner']+4,2)
  cases.append('stale second logical/physical owner refuses before DMA')
  f.call('se_reu_provider_init');f.call('se_overlay_call',1,0,error=0x18)
  f.call('se_reu_bind',4,first,2);f.call('se_reu_bind',4,second,4);f.call('se_overlay_init')
  assert f.get('se_overlay_asset')==3 and f.get('se_overlay_asset_second')==0
  assert f.read(s['se_overlay_ids'],32)==bytes(32) and f.read(s['se_overlay_active'],4)==bytes(4)
  ownership=f.ownership();f.call('se_overlay_init',error=0x18);assert f.ownership()==ownership
  assert f.reu()==expected;f.safe();cases.append('provider reset revokes catalog without clearing16MiB or foreign ownership')
  return cases
 finally:f.close()

def exhausted(out,s):
 f=Fixture(out,s,banks=2,nonidentity=False)
 try:
  for i in range(16):f.imported(f.image(i+1,i&1))
  f.call('se_overlay_call',16,1)
  before=f.canonical();reu=f.reu();dma=f.get('se_reu_dma_calls',2)
  for _ in range(3):
   f.imported(f.image(17,0),error=1)
   assert f.get('se_overlay_asset_second')==0 and f.canonical()==before and f.reu()==reu and f.get('se_reu_dma_calls',2)==dma
  f.safe();return 'lazy allocation exhaustion3retries preserves handles/maps/catalog/active/source'
 finally:f.close()

def real_headers(out,s):
 f=Fixture(out,s);count=0
 try:
  # Rebind only the resident seal/API to this private CPU capsule. Real payload
  # bytes after the16-byte binding are retained, imported and never executed.
  for p in sorted((OUT/'accepted800').glob('*.seo')):
   b=p.read_bytes();payload=DIGEST+b[HEADER+16:]
   image=wrap(payload,b[5],b[6],16,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=DIGEST)
   f.imported(image);count+=1
  # Actual old23 images plus9more occupy every catalog tag. Late unsigned IDs
  # and arbitrary slot assignment remain independent of the catalog ordinal.
  for i in range(9):
   identity=247+i;slot=i&1;f.imported(f.image(identity,slot))
  assert f.read(s['se_overlay_ids'],32)[23:]==bytes(range(247,256))
  reu=f.reu()
  for i in range(9):assert f.call('se_overlay_call',247+i,i&1)==247+i
  assert f.reu()==reu;f.safe();return count
 finally:f.close()

def generic(out,s):
 f=Fixture(out,s)
 try:
  f.imported(f.image(90,0,4080));assert f.call('se_overlay_call',90,0)==90
  # Header validation remains a pure operation over arbitrary legal offsets.
  checks=0
  for length in [17,18,255,256,257,4095,4096]:
   for entry in [0,15,16,17,255,256,4080,4095,4096,65535]:
    b=bytearray(f.image(91,0));b[8:10]=length.to_bytes(2,'little');b[10:12]=entry.to_bytes(2,'little');b=reseal(b)
    f.m.load(s['se_overlay_header'],b[:HEADER]);f.call('se_overlay_validate',error=None if 16<=entry<length else 0x13);checks+=1
  return checks
 finally:f.close()

def main():
 global DLL
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').unlink(missing_ok=True);frozen=freeze();DLL=accelerator();tail.OUT=OUT
 defaults=[]
 for fast in [True,False]:
  tag='fast' if fast else 'slow';d,s=tail.compile_variant('default-'+tag,fast=fast)
  old,old_s=tail.compile_variant('accepted800-default-'+tag,fast=fast,frozen=True)
  assert (d/'probe.bin').read_bytes()==(old/'probe.bin').read_bytes()
  assert s['__BSS_SIZE__']==old_s['__BSS_SIZE__']
  defaults.append(dict(crc=tag,sha256=sha(d/'probe.bin'),code=s['__CODE_SIZE__'],bss=s['__BSS_SIZE__']))
 generic_out,gs=build('generic24',capacity=24);checks=generic(generic_out,gs)
 out,s=build('fixed32',True);assert s['se_overlay_capacity']==32 and s['se_overlay_fixed_entry']==1
 assert s['__OVERLAY_CATALOG_SIZE__']==192 and s['se_overlay_ids']==0x7F40
 assert s['__BSS_SIZE__']==gs['__BSS_SIZE__']
 assert re.search(r'ZEROPAGE\s+\w+\s+\w+\s+(\w+)',(out/'probe.map').read_text()).group(1)==re.search(r'ZEROPAGE\s+\w+\s+\w+\s+(\w+)',(generic_out/'probe.map').read_text()).group(1)
 cases=full(out,s);cases.append(exhausted(out,s));real_count=real_headers(out,s)
 slow,ss=build('fixed32-slow',True,fast=False);assert full(slow,ss,banks=8)==cases[:-1]
 # Explicit feature-domain guards: generic24, fixed32 accepted;33 never fits.
 rejected=[]
 for fixed,limit in [(False,25),(True,33),(True,0)]:
  p=subprocess.run(['ca65','-I',str(ROOT/'src'),'-D','EDITOR_CATALOG_TAIL=1','-D',f'EDITOR_FIXED_ENTRY={int(fixed)}','-D',f'OVL_LIMIT={limit}','-o',str(OUT/'bad.o'),str(ROOT/'src/overlay/cache.s')],capture_output=True,text=True)
  assert p.returncode;rejected.append([fixed,limit])
 result=dict(status='passed',scope='Optional fixed-entry actualCPU cache proof; production enable/native integration remains parent-owned',accepted800_freeze=frozen,default_byte_identity=defaults,actual23_headers_imported=real_count,generic_header_cases=checks,generic_arbitrary_entry=4080,capacity=32,catalog_bytes=192,bss_added=0,zp_added=0,code_delta_vs_tail24=s['__CODE_SIZE__']-gs['__CODE_SIZE__'],fixed_code=s['__CODE_SIZE__'],generic_code=gs['__CODE_SIZE__'],checked_reu_bytes=16*1024*1024,slow_crc_checked_reu_bytes=8*65536,cases=cases,rejected_configurations=rejected,source_sha256={n:sha(ROOT/n) for n in ['src/overlay/cache.s','src/overlay/header.s','src/overlay/format.inc','tools/check_build.py','tests/test_editor_catalog32.py']})
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
