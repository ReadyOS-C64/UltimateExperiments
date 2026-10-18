"""Original CC0 3x7 ASCII in 4x8 cells; CP437 fallback from licensed Unscii8."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/native-text'
# Seven rows, three bits, at left of 4-pixel cell; final column separates text.
upper={
'A':'2575555','B':'6565656','C':'3444443','D':'6555556','E':'7446447','F':'7446444','G':'3447553','H':'5557555','I':'7222227','J':'1111552','K':'5564655','L':'4444447','M':'5775555','N':'5577555','O':'2555552','P':'6556444','Q':'2555573','R':'6556655','S':'3442116','T':'7222222','U':'5555557','V':'5555552','W':'5555775','X':'5552555','Y':'5552222','Z':'7112447',
'0':'7555557','1':'2622227','2':'6112447','3':'6112116','4':'5557111','5':'7446116','6':'3446552','7':'7112222','8':'2552552','9':'2553116'}
lower={
'a':'0035357','b':'4446556','c':'0034443','d':'1113553','e':'0025743','f':'1227222','g':'0035531','h':'4446555','i':'2002222','j':'1001111','k':'4445655','l':'6222223','m':'0057755','n':'0065555','o':'0025552','p':'0065556','q':'0035553','r':'0065444','s':'0034216','t':'2227223','u':'0055553','v':'0055552','w':'0055575','x':'0055255','y':'0055531','z':'0071247'}
punc={' ':'0000000','!':'2222202','"':'5500000','#':'5757575','$':'2372632','%':'5012405','&':'2526553',"'":'2200000','(':'1222221',')':'4222224','*':'0527250','+':'0027200',',':'0000024','-':'0007000','.':'0000002','/':'0012440',':':'0020020',';':'0020024','<':'0124210','=':'0007070','>':'0421240','?':'2512202','@':'2577543','[':'3222223','\\':'0042110',']':'6222226','^':'2500000','_':'0000007','`':'4200000','{':'1224221','|':'2222222','}':'4221224','~':'0052000'}
full=(ROOT/'assets/native-text/cp437-unscii8.bin').read_bytes()
def half(v):return sum(1<<(3-i) for i in range(4) if v&(3<<(6-i*2)))
rows=[[half(full[c*8+y]) for y in range(8)] for c in range(256)]
original={}
for chars in (upper,lower,punc):
 for c,pattern in chars.items():
  r=[int(d,8)<<1 for d in pattern]+[0]
  if c in 'gpqy':r[7]=4 if c in 'pq' else 6
  if c=='j':r[7]=6
  rows[ord(c)]=r;original[str(ord(c))]=r
assert len(original)==95
# Original narrow single-line box glyphs, reaching every required cell edge.
box={179:[4]*8,196:[0,0,0,15,0,0,0,0],218:[0,0,0,7,4,4,4,4],191:[0,0,0,12,4,4,4,4],192:[4,4,4,7,0,0,0,0],217:[4,4,4,12,0,0,0,0],195:[4,4,4,7,4,4,4,4],180:[4,4,4,12,4,4,4,4],194:[0,0,0,15,4,4,4,4],193:[4,4,4,15,0,0,0,0],197:[4,4,4,15,4,4,4,4],219:[15]*8,220:[0]*4+[15]*4,223:[15]*4+[0]*4,221:[12]*8,222:[3]*8}
for c,r in box.items():rows[c]=r;original[str(c)]=r
rows[0]=[0]*8;original['0']=rows[0]
packed=bytes((r[y]<<4)|r[y+1] for r in rows for y in range(0,8,2));assert len(packed)==1024
outputs={'cp437-narrow4x8.bin':packed,'cp437-narrow4x8-rows.json':(json.dumps(rows)+'\n').encode()}
outputs['narrow-provenance.json']=(json.dumps({'license':'Original ASCII and listed line/block glyphs dedicated CC0-1.0 by this project; remaining glyphs OR reduced from pinned CC0 Unscii-derived full font','original_glyph_rows':original,'fallback_source':'assets/native-text/cp437-unscii8.bin','fallback_sha256':hashlib.sha256(full).hexdigest(),'source_generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'packed_sha256':hashlib.sha256(packed).hexdigest(),'packing':'character*4 + row/2; even row high nibble, odd row low nibble; bit3 left','original_count':len(original)},indent=2)+'\n').encode()
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 for name,data in outputs.items():
  path=OUT/name
  if args.check:
   if path.read_bytes()!=data:raise ValueError('Narrow font/source provenance differs: '+name)
  else:path.write_bytes(data)
 print(hashlib.sha256(packed).hexdigest())
