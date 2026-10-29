"""Optional warm bitmap-tail catalog and lazy second logical asset bank.

Only build/overlay-tail is written. The old default object/source capsule was
frozen before production edits; no editor build, cfg enable or VICE is involved.
"""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from overlays import wrap,HEADER
OUT=ROOT/'build/overlay-tail'
FROZEN=OUT/'baseline'
DIGEST=bytes(range(16))
# Frozen before changing cache.s/format.inc; preserves a clean-build regression
# even when disposable build/overlay-tail/baseline has been removed.
EXPECTED_DEFAULT={
 'fast':'3c4cfd4c56586d5274972260617838b76297438e2c1d53a1f758915b8a19b75e',
 'slow':'6a7bef99c96cc5b5ecf6a4773ccd2844386e03dc5b04bd5286e6253f4076b730',
}
MODULES=['overlay/cache','overlay/header','reu/provider','reu/dma']
def run(args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def symbols(p):return {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',p.read_text())}
def compile_variant(name,*,tail=False,capacity=None,fast=True,frozen=False):
 out=OUT/name;out.mkdir(parents=True,exist_ok=True)
 src=FROZEN/'src' if frozen else ROOT/'src'
 assert src.exists(),('missing pre-edit identity capsule',src)
 (out/'stub.s').write_text('''.setcpu "6502"
.export se_reu_banks,se_overlay_binding_digest
.segment "BSS"
se_reu_banks:.res 2
.segment "RODATA"
se_overlay_binding_digest:.byte 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
''')
 (out/'probe.cfg').write_text('''MEMORY {
 Z:file="",start=$0002,size=$001A,type=rw;
 C:file=%O,start=$1000,size=$3000,type=rw;
 S:file="",start=$C000,size=$0600,type=rw;
 T:file="",start=$7F40,size=$00C0,type=rw;
}
SEGMENTS {
 ZEROPAGE:load=Z,type=zp; CODE:load=C,type=ro,define=yes;
 RODATA:load=C,type=ro,define=yes; CRC_TABLE:load=C,type=ro,align=$100,optional=yes;
 BSS:load=S,type=bss,define=yes;
 OVERLAY_CATALOG:load=T,type=bss,optional=yes,define=yes;
}
''')
 objects=[]
 for i,n in enumerate(MODULES+['overlay/crc_fast' if fast else 'overlay/crc']):
  p=out/f'{i}.o';args=['ca65','-g','-I',src,'-o',p]
  if fast:args+=['-D','FAST_EDITOR_CRC=1']
  if tail:args+=['-D','EDITOR_CATALOG_TAIL=1']
  elif not frozen:args+=['-D','EDITOR_CATALOG_TAIL=0']
  if capacity is not None:args+=['-D',f'OVL_LIMIT={capacity}']
  run(args+[src/(n+'.s')]);objects.append(p)
 p=out/'stub.o';run(['ca65','-g','-o',p,out/'stub.s']);objects.append(p)
 run(['ld65','-C',out/'probe.cfg','-o',out/'probe.bin','-Ln',out/'probe.lbl','-m',out/'probe.map',*objects])
 return out,symbols(out/'probe.lbl')

class Fixture:
 def __init__(self,out,s,banks=8,nonidentity=True):
  self.s=s;self.m=Machine();self.m.load(0x1000,(out/'probe.bin').read_bytes());self.banks=banks
  self.shim=bytes((i*73+29)&255 for i in range(1024));self.m.load(0xC600,self.shim)
  self.visible_tail=bytes((i*37+13)&255 for i in range(64));self.m.load(0x7F00,self.visible_tail)
  self.unowned=bytes((i*43+17)&255 for i in range(0x2000));self.m.load(0x8000,self.unowned)
  self.baseline=bytes(((i>>16)*17+(i&255)*31+11)&255 for i in range(banks*65536))
  for p in range(0,len(self.baseline),8192):
   data=self.baseline[p:p+8192];self.m.load(0x5000,data)
   for a,v in [(0xDF02,0),(0xDF03,0x50),(0xDF04,p&255),(0xDF05,(p>>8)&255),(0xDF06,p>>16),(0xDF07,0),(0xDF08,len(data)>>8),(0xDF0A,0),(0xDF01,0x90)]:self.m.write(a,v)
  self.put('se_reu_banks',banks,2);self.call('se_reu_provider_init')
  if nonidentity:
   self.call('se_reu_bind',4,200,1)
   self.call('se_reu_bind',4,201,3)
  self.call('se_overlay_init');assert self.get('se_overlay_asset_second')==0
 def close(self):self.m.close()
 def read(self,a,n):return bytes(self.m.read(a+i) for i in range(n))
 def get(self,n,w=1):return int.from_bytes(self.read(self.s[n],w),'little')
 def put(self,n,v,w=1):self.m.load(self.s[n],v.to_bytes(w,'little'))
 def call(self,n,a=0,x=0,y=0,error=None):
  r,_=self.m.call(self.s[n],a=a,x=x,y=y,limit=2000000)
  assert bool(r.p&1)==(error is not None),(n,r.a,error)
  if error is not None:assert r.a==error,(n,r.a,error)
  return r.a
 def image(self,identity,slot):
  if identity in [2,3,4]:
   target,childslot=(1,0) if identity==2 else (2,1)
   code=bytes([0xA9,target,0xA2,childslot,0x20,self.s['se_overlay_call']&255,self.s['se_overlay_call']>>8,0x60])
  else:code=bytes([0xA9,identity,0x18,0x60])
  payload=DIGEST+bytes((i*31+identity)&255 for i in range(16,4080))+code+bytes(16-len(code))
  return wrap(payload,slot,identity,4080,api=(self.s['se_overlay_call'],self.s['se_overlay_frame']),binding_digest=DIGEST)
 def imported(self,image,error=None):
  self.m.load(self.s['se_overlay_header'],image[:HEADER]);self.m.load(0x5000,image[HEADER:]);return self.call('se_overlay_import',error=error)
 def reu(self):return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,i) for i in range(self.banks*65536))
 def ownership(self):return self.read(self.s['se_reu_map'],256)+self.read(self.s['se_reu_logical_owner'],256)+self.read(self.s['se_reu_physical_owner'],256)
 def canonical(self):return self.read(0x7F40,192)+self.read(self.s['se_overlay_active'],4)+self.read(self.s['se_overlay_asset'],4)+self.ownership()+self.read(0xA000,8192)
 def safe(self):
  assert self.read(0x7F00,64)==self.visible_tail
  assert self.read(0x8000,len(self.unowned))==self.unowned
  assert self.read(0xC600,1024)==self.shim

def full(out,s):
 f=Fixture(out,s);cases=[]
 try:
  expected=bytearray(f.baseline);images=[];first=f.get('se_overlay_asset')
  assert first==1 and f.m.read(s['se_reu_map']+first)==2
  for i in range(16):
   image=f.image(i+1,i&1);images.append(image);f.imported(image)
   assert f.get('se_overlay_asset_second')==0
   expected[2*65536+i*4096:2*65536+(i+1)*4096]=image[HEADER:]
  assert f.reu()==expected;cases.append('16full4096 slots use first bank only')
  # Header/payload faults cannot cause lazy allocation even at the boundary.
  before=f.canonical();dma=f.get('se_reu_dma_calls',2)
  bad=bytearray(f.image(17,0));bad[0]=0;f.imported(bad,error=0x10)
  bad=bytearray(f.image(17,0));bad[HEADER+200]^=1;f.imported(bad,error=0x14)
  assert f.canonical()==before and f.get('se_reu_dma_calls',2)==dma and f.reu()==expected
  cases.append('header and payload CRC precede second allocation')
  for i in range(16,24):
   image=f.image(i+1,i&1);images.append(image);f.imported(image)
   second=f.get('se_overlay_asset_second');assert second==2 and f.m.read(s['se_reu_map']+second)==4
   expected[4*65536+(i-16)*4096:4*65536+(i-15)*4096]=image[HEADER:]
  assert f.read(s['se_overlay_ids'],24)==bytes(range(1,25))
  assert f.reu()==expected;cases.append('24fullslots / logical1->physical2 and logical2->physical4')
  before=f.canonical();dma=f.get('se_reu_dma_calls',2);f.imported(f.image(200,0),error=0x15)
  assert f.canonical()==before and f.get('se_reu_dma_calls',2)==dma
  cases.append('25th image refused before DMA or allocation')
  for i in list(reversed(range(24)))+list(range(24)):
   identity=i+1
   if identity in (3,4):f.call('se_overlay_call',identity,i&1,error=0x19)
   else:assert f.call('se_overlay_call',identity,i&1)==(1 if identity==2 else identity)
   assert f.read(0xA000+(i&1)*4096,4096)==images[i][HEADER:]
  assert f.read(s['se_overlay_busy'],2)==b'\0\0' and f.reu()==expected
  cases.append('both bank calls/hits and unchanged C->R / R->C / same-slot nesting')
  # Corrupt last second-bank slot, force a reload, retain prior executable.
  second=f.get('se_overlay_asset_second');offset=7*4096+4095
  f.put('se_reu_logical',second);f.put('se_reu_c64',0x7000,2);f.put('se_reu_offset',offset,2);f.put('se_reu_length',1,2)
  f.m.write(0x7000,images[-1][-1]^1);f.call('se_reu_copy')
  expected[4*65536+offset]^=1
  f.call('se_overlay_call',22,1);active=f.read(s['se_overlay_active'],2);code=f.read(0xB000,4096)
  f.call('se_overlay_call',24,1,error=0x14)
  assert f.read(s['se_overlay_active'],2)==active and f.read(0xB000,4096)==code and f.reu()==expected
  cases.append('corrupt last second-bank slot preserves executable and active tags')
  # Owning a stale second logical handle revokes the complete cache, even a hit
  # in bank1; no allocation or DMA can acquire a foreign mapping.
  f.m.write(s['se_reu_logical_owner']+second,4);before=f.canonical();dma=f.get('se_reu_dma_calls',2)
  f.call('se_overlay_call',22,1,error=0x18);f.imported(f.image(201,0),error=0x18)
  assert f.canonical()==before and f.get('se_reu_dma_calls',2)==dma
  f.m.write(s['se_reu_logical_owner']+second,2)
  # Mapping ownership is also checked by the real DMA path before staging.
  f.call('se_overlay_call',21,0) # force slot23 through the checked DMA path
  f.m.write(s['se_reu_physical_owner']+4,4);dma=f.get('se_reu_dma_calls',2)
  f.call('se_overlay_call',23,0,error=4);assert f.get('se_reu_dma_calls',2)==dma
  f.m.write(s['se_reu_physical_owner']+4,2);cases.append('stale second logical/physical owner refuses before DMA')
  # Reset provider, preserve foreign bindings occupying both old handles, then
  # re-init one first bank and leave second lazy. No REU data is cleared.
  f.call('se_reu_provider_init');dma=f.get('se_reu_dma_calls',2)
  f.call('se_overlay_call',1,0,error=0x18)
  assert f.get('se_reu_dma_calls',2)==dma
  f.call('se_reu_bind',4,first,2);f.call('se_reu_bind',4,second,4)
  f.call('se_overlay_init');assert f.get('se_overlay_asset')==3 and f.get('se_overlay_asset_second')==0
  assert f.read(s['se_overlay_ids'],24)==bytes(24) and f.read(s['se_overlay_active'],4)==bytes(4)
  ownership=f.ownership();f.call('se_overlay_init',error=0x18);assert f.ownership()==ownership
  assert f.m.read(s['se_reu_logical_owner']+first)==4 and f.m.read(s['se_reu_logical_owner']+second)==4
  assert f.reu()==expected;f.safe();cases.append('provider reset invalidates both / re-init preserves foreign banks')
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
  f.safe();return 'lazy allocation exhaustion3retries leaves no handle/map/catalog/source mutation'
 finally:f.close()

def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').unlink(missing_ok=True)
 default=[]
 for fast in [True,False]:
  tag='fast' if fast else 'slow'
  new,ns=compile_variant('default-'+tag,fast=fast)
  assert sha(new/'probe.bin')==EXPECTED_DEFAULT[tag]
  if (FROZEN/'src').exists():
   old,os=compile_variant('old-'+tag,fast=fast,frozen=True)
   assert (old/'probe.bin').read_bytes()==(new/'probe.bin').read_bytes()
   assert os['__BSS_SIZE__']==ns['__BSS_SIZE__']
  default.append(dict(crc=tag,sha256=sha(new/'probe.bin'),code_bytes=ns['__CODE_SIZE__'],bss=ns['__BSS_SIZE__']))
 tail,s=compile_variant('tail24',tail=True,capacity=24)
 assert s['se_overlay_ids']==0x7F40 and s['__OVERLAY_CATALOG_SIZE__']==192
 cases=full(tail,s);cases.append(exhausted(tail,s))
 slow,ss=compile_variant('tail24-slow',tail=True,capacity=24,fast=False)
 slowcases=full(slow,ss);assert slowcases==cases[:-1]
 # Additional accepted/rejected constant overrides prove the default <=16 and
 # optional <=24 domains without changing or copying format.inc constants.
 compile_variant('override16',capacity=16)
 for tailflag,capacity in [(False,17),(True,25),(True,0)]:
  args=['ca65','-I',str(ROOT/'src'),'-D',f'EDITOR_CATALOG_TAIL={int(tailflag)}','-D',f'OVL_LIMIT={capacity}','-o',str(OUT/'bad.o'),str(ROOT/'src/overlay/cache.s')]
  bad=subprocess.run(args,capture_output=True,text=True);assert bad.returncode
 base_code=default[0]['code_bytes'];delta=s['__CODE_SIZE__']-base_code
 assert delta<=34,(base_code,s['__CODE_SIZE__'],delta)
 result=dict(status='passed',default_byte_identity=default,tail_capacity=24,tail_catalog_start=s['se_overlay_ids'],tail_catalog_bytes=s['__OVERLAY_CATALOG_SIZE__'],tail_code_bytes=s['__CODE_SIZE__'],tail_slow_code_bytes=ss['__CODE_SIZE__'],both_crc_engines_exercised=True,core_code_delta=delta,default_bss=default[0]['bss'],tail_bss=s['__BSS_SIZE__'],additional_handle_bytes=1,zero_page_added=0,cases=cases,checked_reu_bytes=8*65536,shim_bytes=1024,
  source_sha256={n:sha(ROOT/n) for n in ['src/overlay/cache.s','src/overlay/format.inc','tests/test_overlay_tail.py']},
  scope='Optional actual cache/header/CRC/provider/DMA CPU proof; default bytes preserved against pre-edit capsule; no editor enable, shared build or native/bitmap integration')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
