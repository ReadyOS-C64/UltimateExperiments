"""CPU fixture seam: bypass IEC only, executing actual FD provider and DMA."""
from pathlib import Path
import hashlib,binascii
ROOT=Path(__file__).resolve().parents[1]
PACK_SHA='5a980ffdeb34cec91469414768a273aa0f842fe16c8fd4ccc89215459c617975'

def install_font_pack(f,pack=None):
 """Install immutable genuine pack after fixture startup/source provider reset.

 f supplies m (Peddle Machine), s symbol map, call(name,a), read(address,count).
 Source/history/clipboard/catalog and native4800 remain untouched; CPU bounce
 5000..5FFF, actual provider/DMA request scratch and descriptorCBC0 are allowed.
 Existing same-epoch FD capabilities are reused, never blindly forgotten.
 """
 payload=(Path(pack) if pack else ROOT/'build/geos-font-catalog/font-pack.bin').read_bytes()
 assert len(payload)==74432 and hashlib.sha256(payload).hexdigest()==PACK_SHA
 assert binascii.crc_hqx(payload,65535)==0x8B6A
 s,m=f.s,f.m;base=s.get('se_gf_state',0xCBC0)
 assert base==0xCBC0
 def read(a,n):return bytes(m.read(a+i) for i in range(n))
 def put(n,v,w=2):m.load(s[n],v.to_bytes(w,'little'))
 epoch=read(s['se_reu_epoch'],2);old=read(base,64)
 def owned(h):
  return h and m.read(s['se_reu_logical_owner']+h)==0xFD and m.read(s['se_reu_physical_owner']+m.read(s['se_reu_map']+h))==0xFD
 if old[3:5]==epoch and any(owned(h) for h in old[1:3]):
  assert old[0]==0xA5 and old[5]==0 and len(set(old[1:3]))==2 and all(owned(h) for h in old[1:3]),'refuse overwriting live/incomplete font capability'
  return tuple(old[1:3])
 # No old FD capability remains: a source-reset descriptor may hold stale
 # handles now owned by document/overlays. Never free those replacement owners.
 handles=[]
 try:
  for _ in range(2):
   r=f.call('se_reu_alloc',0xFD);assert not r.p&1,('font-pack allocation',r.a)
   handles.append(r.a)
  for offset in range(0,len(payload),4096):
   data=payload[offset:offset+min(4096,65536-(offset&65535))]
   m.load(0x5000,data);put('se_reu_logical',handles[offset>>16],1)
   put('se_reu_offset',offset&65535);put('se_reu_length',len(data));put('se_reu_c64',0x5000)
   r=f.call('se_reu_copy',0);assert not r.p&1,('font-pack DMA',offset,r.a)
 except BaseException:
  for h in handles:m.call(s['se_reu_free'],x=h)
  raise
 descriptor=bytearray(64);descriptor[1:3]=bytes(handles);descriptor[3:5]=epoch
 descriptor[9:12]=len(payload).to_bytes(3,'little');descriptor[14:16]=(0x8B6A).to_bytes(2,'little')
 m.load(base,descriptor);m.write(base,0xA5)
 return tuple(handles)
