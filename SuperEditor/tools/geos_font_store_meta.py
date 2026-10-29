"""Trusted small runtime metadata from an existing genuine GFC1 font pack."""
from pathlib import Path
import argparse,binascii,hashlib,json

def build(pack,out):
 data=Path(pack).read_bytes();count=data[5]
 assert data[:5]==b'GFC1\x01' and data[6:10]==b'\x10\0\x20\0'
 assert int.from_bytes(data[10:13],'little')==32+count*16 and int.from_bytes(data[13:16],'little')==len(data) and data[16:32]==bytes(16)
 assert 1<=count<=64 and len(data)<=131072
 keys=[[],[],[],[]];crcs=[];info=[];maximum=0;previous=32+count*16
 for i in range(count):
  e=data[32+i*16:48+i*16];offset=int.from_bytes(e[8:11],'little');size=int.from_bytes(e[11:13],'little');raw=data[offset:offset+size]
  assert offset==previous and len(raw)==size and size>=10;previous=offset+size;maximum=max(maximum,size)
  baseline,stride,height,index,bits=raw[0],int.from_bytes(raw[1:3],'little'),raw[3],int.from_bytes(raw[4:6],'little'),int.from_bytes(raw[6:8],'little')
  offsets=[int.from_bytes(raw[p:p+2],'little') for p in range(index,bits,2)];widths=[b-a for a,b in zip(offsets,offsets[1:])]
  assert index==8 and baseline<height and len(raw)==bits+stride*height and e[4]==baseline and e[5]==height and int.from_bytes(e[6:8],'little')==stride
  assert len(widths)==e[13] and e[14]==32 and max(widths)==e[15]<128 and all(w>=0 for w in widths)
  for j in range(4):keys[j].append(e[j])
  crcs.append(binascii.crc_hqx(raw,65535));info.append(max(widths)|(128 if len(set(widths))==1 else 0))
 assert previous==len(data)
 def line(name,values):return name+': .byte '+','.join('$%02X'%v for v in values)+'\n'
 text='; GENERATED from immutable GFC1; no externalmedia regeneration.\n'
 text+='GF_PACK_BYTES=$%06X\nGF_PACK_CRC=$%04X\nGF_FACE_COUNT=%d\nGF_INDEX_END=%d\nGF_MAX_FONT=%d\n'%(len(data),binascii.crc_hqx(data,65535),count,32+count*16,maximum)
 bsw=[i for i in range(count) if tuple(k[i] for k in keys)==(2,255,255,9)]
 if len(bsw)==1:text+='GF_BSW9_CRC=$%04X\n'%crcs[bsw[0]]
 text+='.macro GF_IMPORT_METADATA\n'+line('gf_pack_header',data[:32])+'.endmacro\n'
 text+='.macro GF_RUNTIME_METADATA\n'
 for n,values in zip(('gf_origins','gf_family_lo','gf_family_hi','gf_points'),keys):text+=line(n,values)
 text+=line('gf_crc_lo',[v&255 for v in crcs])+line('gf_crc_hi',[v>>8 for v in crcs])+line('gf_face_info',info)+'.endmacro\n'
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text)
 return dict(pack_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),faces=count,max_font=maximum,pack_crc=binascii.crc_hqx(data,65535),runtime_metadata_bytes=count*7,include_sha256=hashlib.sha256(text.encode()).hexdigest())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--pack',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.pack,a.output),indent=2))
