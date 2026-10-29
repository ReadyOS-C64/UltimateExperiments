"""Editor64 actual cache/header/provider/DMA and unchanged generic capsules.

No editor build, disk, native VICE or physical ownership guesses. Generic
profiles retain exact bytes; editor stage remains5000 and catalogCA00 data-only.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,hashlib,json,re,subprocess,sys,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from overlays import wrap,HEADER
import test_editor_catalog32 as previous
DIGEST=bytes(range(16));BASELINE=ROOT/'agentsworking/evidence/M7/20261025T043317772867Z-geos-capacity-native/product-sources.zip'

def command(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def build(out,*,fixed=False,tail=False,capacity=15,fast=True,before=False):
 out.mkdir(parents=True,exist_ok=True);inc=out/'before/overlay'
 if before:
  inc.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(BASELINE) as archive:
   for n in ('cache.s','format.inc'):(inc/n).write_bytes(archive.read('src/overlay/'+n))
 src=inc/'cache.s' if before else ROOT/'src/overlay/cache.s'
 (out/'stub.s').write_text('''.setcpu "6502"
.export se_reu_banks,se_overlay_binding_digest
.segment "BSS"
se_reu_banks:.res2
.segment "RODATA"
se_overlay_binding_digest:.byte0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
'''.replace('.res2','.res 2').replace('.byte0','.byte 0'))
 catalog=0xCA00 if fixed else 0x7F40;extent=384 if fixed else 192
 (out/'probe.cfg').write_text(f'''MEMORY {{ Z:file="",start=$0002,size=$001A; C:file=%O,start=$1000,size=$3000; S:file="",start=$C000,size=$0600; T:file="",start=${catalog:04X},size=${extent:04X}; }}
SEGMENTS {{ ZEROPAGE:load=Z,type=zp; CODE:load=C,type=ro,define=yes; RODATA:load=C,type=ro,define=yes; CRC_TABLE:load=C,type=ro,align=$100,optional=yes; BSS:load=S,type=bss,define=yes; OVERLAY_CATALOG:load=T,type=bss,optional=yes,define=yes; }}''')
 flags=[f'OVL_LIMIT={capacity}',f'EDITOR_CATALOG_TAIL={int(tail)}',f'EDITOR_FIXED_ENTRY={int(fixed)}']
 if fast:flags+=['FAST_EDITOR_CRC=1']
 if fixed:flags+=['EDITOR_HALF_CRC=1']
 objects=[]
 for i,name in enumerate([src,ROOT/'src/overlay/header.s',ROOT/'src/reu/provider.s',ROOT/'src/reu/dma.s',ROOT/('src/overlay/crc_fast.s' if fast else 'src/overlay/crc.s'),out/'stub.s']):
  obj=out/f'{i}.o';args=['ca65','-g']
  for flag in flags:args+=['-D',flag]
  if before:args+=['-I',inc.parent]
  args+=['-I','src','-o',obj,name];command(*args);objects.append(obj)
 command('ld65','-C',out/'probe.cfg','-o',out/'probe.bin','-Ln',out/'probe.lbl','-m',out/'probe.map',*objects)
 labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'probe.lbl').read_text())}
 return labels
class Fixture(previous.Fixture):
 def __init__(self,out,s,banks=256,nonidentity=True):
  super().__init__(out,s,banks=banks,nonidentity=False)
  # Reset without touching the deterministic REU payload. Reserve odd physical
  # banks using foreign logical handles to force assets onto2/4/6/8.
  self.call('se_reu_provider_init')
  if nonidentity:
   for i,physical in enumerate((1,3,5,7)):self.call('se_reu_bind',4,200+i,physical)
  self.call('se_overlay_init')
  self.settings=bytes((i*29+53)&255 for i in range(64));self.m.load(0xCB80,self.settings)
 def imported(self,blob,error=None):
  self.m.load(self.s['se_overlay_header'],blob[:HEADER]);self.m.load(self.s.get('se_overlay_stage',0x5000),blob[HEADER:]);return self.call('se_overlay_import',error=error)
 def canonical(self):return self.read(self.s['se_overlay_ids'],384)+self.read(self.s['se_overlay_active'],4)+self.read(self.s['se_overlay_asset'],6)+self.ownership()+self.read(0xA000,8192)
 def safe(self):
  assert self.read(0x7F00,64)==self.visible_tail
  assert self.read(0x8000,len(self.unowned))==self.unowned
  assert self.read(0xC600,1024)==self.shim and self.read(0xCB80,64)==self.settings
 def handles(self):return list(self.read(self.s['se_overlay_asset'],4))
 def patch(self,handle,offset,value):
  self.put('se_reu_logical',handle);self.put('se_reu_offset',offset,2);self.put('se_reu_c64',0x7000,2);self.put('se_reu_length',1,2);self.m.write(0x7000,value);self.call('se_reu_copy')

def full(out,s):
 f=Fixture(out,s);cases=[];images=[]
 try:
  assert f.handles()==[1,0,0,0] and s['se_overlay_stage']==0x5000
  expected=bytearray(f.baseline)
  for index in range(64):
   identity=index+1 if index<60 else index+192
   image=f.image(identity,index&1);images.append(image)
   if index in (16,32,48):
    before=f.canonical();reu=f.reu();dma=f.get('se_reu_dma_calls',2)
    bad=bytearray(image);bad[0]=0;f.imported(bad,error=0x10)
    bad=bytearray(image);bad[HEADER+200]^=1;f.imported(bad,error=0x14)
    assert f.canonical()==before and f.reu()==reu and f.get('se_reu_dma_calls',2)==dma
    assert f.handles()[index//16]==0
   f.imported(image);physical=(index//16+1)*2;offset=(index&15)*4096
   expected[physical*65536+offset:physical*65536+offset+4096]=image[HEADER:]
   assert f.handles()==list(range(1,index//16+2))+[0]*(3-index//16)
  assert f.read(s['se_overlay_ids'],64)==bytes(list(range(1,61))+list(range(252,256)))
  assert f.handles()==[1,2,3,4] and [f.m.read(s['se_reu_map']+h) for h in f.handles()]==[2,4,6,8]
  assert f.reu()==expected;cases.append('64full4096images in fourlazy logical1..4 ->physical2/4/6/8')
  cases.append('invalidheader/payloadCRC at16/32/48 never allocates or publishes')
  before=f.canonical();dma=f.get('se_reu_dma_calls',2);f.imported(f.image(250,0),error=0x15)
  assert f.canonical()==before and f.get('se_reu_dma_calls',2)==dma;cases.append('65thimage refuses beforeDMA/allocation')
  for index in list(reversed(range(64)))+list(range(64)):
   identity=index+1 if index<60 else index+192
   if identity in (3,4):f.call('se_overlay_call',identity,index&1,error=0x19)
   else:assert f.call('se_overlay_call',identity,index&1)==(1 if identity==2 else identity)
   assert f.read(0xA000+(index&1)*4096,4096)==images[index][HEADER:]
  assert f.reu()==expected and f.read(s['se_overlay_busy'],2)==b'\0\0'
  cases.append('all64unsignedIDs eviction/hits/bothslots/CtoRnesting andsame-slot/RtoC refusal')
  # Runtime stage5000 must leave BOTH executable slots+active tags exact on
  # payload/binding faults in every bank, including the lastbyte of slot63.
  for index in (15,31,47,63):
   identity=index+1 if index<60 else index+192;handle=index//16+1;offset=(index&15)*4096
   other=index-2;other_id=other+1 if other<60 else other+192;f.call('se_overlay_call',other_id,1)
   for relative,error in [(4095,0x14),(0,0x11)]:
    f.patch(handle,offset+relative,images[index][HEADER+relative]^1)
    old=f.read(0xA000,8192)+f.read(s['se_overlay_active'],2);reu=f.reu();loads=f.get('se_overlay_loads',2)
    f.call('se_overlay_call',identity,1,error=error)
    assert f.read(0xA000,8192)+f.read(s['se_overlay_active'],2)==old and f.reu()==reu and f.get('se_overlay_loads',2)==loads
    f.patch(handle,offset+relative,images[index][HEADER+relative])
  assert f.reu()==expected;cases.append('CRC/bindingfaults all4banks preserveboth4096executable slots andactive tags')
  for handle in f.handles():
   f.call('se_overlay_call',1,0);f.m.write(s['se_reu_logical_owner']+handle,4);old=f.canonical();dma=f.get('se_reu_dma_calls',2)
   f.call('se_overlay_call',1,0,error=0x18);f.imported(f.image(251,1),error=0x18)
   assert f.canonical()==old and f.get('se_reu_dma_calls',2)==dma;f.m.write(s['se_reu_logical_owner']+handle,2)
  cases.append('all4logicalownership guards even cachehit in anotherbank')
  for index in (15,31,47,63):
   identity=index+1 if index<60 else index+192;physical=(index//16+1)*2
   other=index-2;f.call('se_overlay_call',other+1 if other<60 else other+192,1)
   f.m.write(s['se_reu_physical_owner']+physical,4);old=f.canonical();dma=f.get('se_reu_dma_calls',2)
   f.call('se_overlay_call',identity,1,error=4)
   assert f.canonical()==old and f.get('se_reu_dma_calls',2)==dma;f.m.write(s['se_reu_physical_owner']+physical,2)
  cases.append('selectedphysicalmapping/owner guards beforeactualDMA; unchangedhitcontract')
  old_handles=f.handles();f.call('se_reu_provider_init');old=f.canonical();dma=f.get('se_reu_dma_calls',2)
  f.call('se_overlay_call',1,0,error=0x18);assert f.canonical()==old and f.get('se_reu_dma_calls',2)==dma
  for handle in old_handles:f.call('se_reu_bind',4,handle,handle*2)
  f.call('se_overlay_init');assert f.handles()==[5,0,0,0] and f.read(s['se_overlay_ids'],64)==bytes(64) and f.read(s['se_overlay_active'],4)==bytes(4)
  ownership=f.ownership();f.call('se_overlay_init',error=0x18);assert f.ownership()==ownership
  assert f.reu()==expected;f.safe();cases.append('epoch reset/reinit preservesforeignhandles andall16MiB; repeatedinitrefuses')
  return cases
 finally:f.close()

def exhausted(out,s):
 cases=[]
 for boundary in (16,32,48):
  f=Fixture(out,s,banks=boundary//16+1,nonidentity=False)
  try:
   for index in range(boundary):f.imported(f.image(index+1,index&1))
   f.call('se_overlay_call',boundary,1);before=f.canonical();reu=f.reu();dma=f.get('se_reu_dma_calls',2);handles=f.handles()
   for _ in range(3):
    f.imported(f.image(boundary+1,0),error=1)
    assert f.canonical()==before and f.reu()==reu and f.get('se_reu_dma_calls',2)==dma and f.handles()==handles
   f.safe();cases.append('allocationexhaustion'+str(boundary)+' 3retries atomicallypreserveallhandles/catalog/active/source/REU')
  finally:f.close()
 return cases

def checker_gate(out):
 base=out/'checker';(base/'tools').mkdir(parents=True);(base/'build').mkdir()
 for name in ('check_build.py','bindings.py'):shutil.copy2(ROOT/'tools'/name,base/'tools'/name)
 (base/'build/editor.prg').write_bytes(b'\x01\x08'+bytes(32))
 def invoke(start=0xCA00,stop=0xCB7F,size=384,capacity=64,fixed=1,stage=0x5000,banks=4,settings=True,success=True):
  symbols=dict(se_entry=0x1000,se_diagnostics=0xC000,__BSS_RUN__=0xC000,__BSS_SIZE__=1533,se_overlay_capacity=capacity,se_overlay_fixed_entry=fixed,se_overlay_header_fixed_entry=fixed,se_overlay_stage=stage,se_overlay_asset_count=banks)
  (base/'build/editor.lbl').write_text(''.join(f'al {value:06X} .{name}\n' for name,value in symbols.items()))
  text=f'OVERLAY_CATALOG {start:06X} {stop:06X} {size:06X} 00001\n'
  if settings:text+='SETTINGS_STATE 00CB80 00CBBF 000040 00001\n'
  (base/'build/editor.map').write_text(text)
  proc=subprocess.run([sys.executable,str(base/'tools/check_build.py'),'--stem','editor'],capture_output=True,text=True)
  assert (proc.returncode==0)==success,(symbols,text,proc.stdout,proc.stderr)
  return proc.stderr
 invoke();invoke(start=0x7F40,stop=0x7FFF,size=192,capacity=24,fixed=0,banks=2,settings=False)
 rejects=[]
 for kw in [dict(start=0xCA01),dict(stop=0xCB80,size=385),dict(size=383),dict(stage=0xA000),dict(banks=2),dict(capacity=65,size=390),dict(start=0xC600,stop=0xC77F)]:
  rejects.append(dict(case=kw,diagnostics=invoke(**kw,success=False)))
 return dict(positive_profiles=2,rejected=rejects)

def main(out):
 previous.OUT=out/'runner';previous.DLL=previous.accelerator()
 identity=[]
 for tail,capacity in [(False,15),(True,24)]:
  for fast in (True,False):
   tag=('tail' if tail else 'generic')+('-fast' if fast else '-slow')
   old_s=build(out/(tag+'-before'),tail=tail,capacity=capacity,fast=fast,before=True)
   new_s=build(out/tag,tail=tail,capacity=capacity,fast=fast)
   assert (out/tag/'probe.bin').read_bytes()==(out/(tag+'-before')/'probe.bin').read_bytes()
   assert old_s['__BSS_SIZE__']==new_s['__BSS_SIZE__'];identity.append(dict(variant=tag,sha256=hashlib.sha256((out/tag/'probe.bin').read_bytes()).hexdigest()))
 old_editor=build(out/'editor32-before',fixed=True,tail=True,capacity=32,before=True)
 s=build(out/'editor64',fixed=True,tail=True,capacity=64)
 def object_segments(path):
  text=subprocess.run(['od65','--dump-segments',str(path)],capture_output=True,text=True,check=True).stdout
  return {name:int(size) for name,size in re.findall(r'Name:\s+"([A-Z_]+)".*?Size:\s+(\d+)',text,re.S)}
 old_bytes=object_segments(out/'editor32-before/0.o');new_bytes=object_segments(out/'editor64/0.o')
 assert new_bytes['CODE']-old_bytes['CODE']==-8 and new_bytes['BSS']-old_bytes['BSS']==2 and new_bytes['ZEROPAGE']==old_bytes['ZEROPAGE']
 rejected=[]
 for tail_,fixed_,capacity_ in [(1,1,65),(1,0,25),(0,0,17),(1,1,0)]:
  proc=subprocess.run(['ca65','-I','src','-D',f'EDITOR_CATALOG_TAIL={tail_}','-D',f'EDITOR_FIXED_ENTRY={fixed_}','-D',f'OVL_LIMIT={capacity_}','-o',str(out/'invalid.o'),'src/overlay/cache.s'],capture_output=True,text=True)
  assert proc.returncode;rejected.append(dict(tail=tail_,fixed=fixed_,capacity=capacity_,diagnostics=proc.stderr))
 assert s['se_overlay_asset_count']==4 and s['se_overlay_stage']==0x5000 and s['se_overlay_ids']==0xCA00 and s['__OVERLAY_CATALOG_SIZE__']==384
 assert [s[n] for n in ('se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')]==list(range(s['se_overlay_asset']+1,s['se_overlay_asset']+4))
 cases=full(out/'editor64',s);cases+=exhausted(out/'editor64',s);checker=checker_gate(out)
 result=dict(status='passed',capacity=64,catalog_bytes=384,catalog_address=0xCA00,stage=0x5000,lazy_logical_banks=4,new_BSS=2,new_ZP=0,code_delta=-8,generic_byte_identity=identity,object_segments=dict(before=old_bytes,after=new_bytes),invalid_configurations=rejected,cases=cases,check_build=checker,scope='Actualisolatededitor64cache/header/CRC/provider/DMA; rootproductintegration/native separate')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();a=p.parse_args();out=ROOT/'build/overlay-catalog64'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);main(out)
