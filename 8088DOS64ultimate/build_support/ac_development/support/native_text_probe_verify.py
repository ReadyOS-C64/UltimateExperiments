"""Offline independent raw RAM verifier for the presentation-only DTP1 probe.

Does not claim DOS execution, VIC timing or physical visual readability.
Requires -g ca65 labels and ld65 map, retaining all self-modified operands.
"""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def expected(mode,font):
 if mode not in (0,3) or len(font)!=2048:raise ValueError('Unsupported fixture mode/font')
 cols=40 if mode==0 else 80
 cells=bytearray(b' '*(cols*25))
 lines=[f'DOS64 NATIVE TEXT FIXTURE {cols} COLUMNS','A>VER','MS-DOS Version 3.30 (sample text)','A>DIR','PRESENTATION ONLY - NO DOS EXECUTION']
 for row,line in enumerate(lines):cells[row*cols:row*cols+len(line)]=line.encode('ascii')
 cells[5*cols:6*cols]=b'\xda'+b'\xc4'*(cols-2)+b'\xbf'
 cells[6*cols:7*cols]=b'\xb3'+b' CP437 GLYPHS BELOW; CURSOR HIDDEN'+b' '*(cols-36)+b'\xb3'
 cells[7*cols:8*cols]=b'\xc0'+b'\xc4'*(cols-2)+b'\xd9'
 cells[10*cols:10*cols+256]=bytes(range(256))
 def half(v):return sum(1<<(3-i) for i in range(4) if v&(3<<(6-i*2)))
 bitmap=bytearray(8000)
 for row in range(25):
  for cell in range(40):
   ci=row*cols+cell*(1 if cols==40 else 2)
   for y in range(8):
    l=font[cells[ci]*8+y]
    bitmap[row*320+cell*8+y]=l if cols==40 else half(l)*16+half(font[cells[ci+1]*8+y])
 return bytes(bitmap),b'\xf0'*1000

def verify_capture(ram,prg,labels,map_text,mode,font):
 if len(ram)!=65536 or prg[:2]!=b'\x01\x08':raise ValueError('Need complete RAM and 0801 PRG')
 symbols={b[2].lstrip('.'):int(b[1],16) for line in labels.splitlines() if len(b:=line.split())==3 and b[0]=='al'}
 m=symbols['dos64_text_probe_mailbox']
 bitmap,matrix=expected(mode,font)
 if ram[0x6000:0x7f40]!=bitmap:raise ValueError('Bitmap mismatch')
 if ram[0x4000:0x43e8]!=matrix:raise ValueError('Matrix mismatch')
 if ram[0x4800:0x5000]!=font:raise ValueError('Font mismatch')
 record=b'DTP1'+bytes([1,mode,0xa5,0])+b''.join((sum(data)&65535).to_bytes(2,'little') for data in (bitmap,matrix,font))
 if ram[m:m+14]!=record:raise ValueError('Mailbox mismatch')
 mutable={symbols[name]+o for name in ['np_text','np_scan','rt_matrix','rt_bitmap','rt_font_left','rt_font_right'] for o in (1,2)}
 verified=0
 for segment in ['BASIC','BOOT','CODE','DISPLAYCODE','RENDERCODE']:
  line=re.search(r'^'+segment+r'\s+([0-9A-F]+)\s+([0-9A-F]+)\s+([0-9A-F]+)',map_text,re.M)
  if not line:raise ValueError('Missing executable segment '+segment)
  start,end=int(line[1],16),int(line[2],16)
  for address in range(start,end+1):
   if address in mutable:continue
   offset=address-0x801+2
   if offset>=len(prg) or ram[address]!=prg[offset]:raise ValueError(f'Executable mismatch at {address:04x}')
   verified+=1
 sha=lambda b:hashlib.sha256(b).hexdigest()
 return {'accepted':True,'kind':'presentation-only','mode':mode,'columns':40 if mode==0 else 80,'mailbox_hex':record.hex(),'ram_sha256':sha(ram),'prg_sha256':sha(prg),'bitmap_sha256':sha(bitmap),'matrix_sha256':sha(matrix),'font_sha256':sha(font),'verified_immutable_code_bytes':verified,'excluded_self_modified_operand_bytes':12,'limitations':['No DOS execution','No raster/DMA/timing model','Physical visual readability requires screenshot and inspection','VIC/CIA settings need independent register capture']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ram',type=Path,required=True);p.add_argument('--prg',type=Path,required=True);p.add_argument('--labels',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--mode',type=int,choices=[0,3],required=True);p.add_argument('--font',type=Path,default=ROOT/'assets/native-text/cp437-unscii8.bin');a=p.parse_args();print(json.dumps(verify_capture(a.ram.read_bytes(),a.prg.read_bytes(),a.labels.read_text(),a.map.read_text(),a.mode,a.font.read_bytes()),indent=2))
