"""Actual sealed R21 small negative horizontal origins, independent signed pixels.

Private build/catalog only. FixedABF3/AEDB fonts; no shared make/native claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,zipfile
import test_geos_editor as geos
import test_geos_row as model
import test_geos_row_leaf as leaf
ROOT=geos.ROOT;F=0x8880;SIZE=704
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T033116850492Z/fixture'
class Fixture(leaf.Fixture):
 def setup(self,runs,row=0,clip=(0,320,0,8),reset=True):
  encoded=[(*r[:4],r[4]&65535,r[5]) for r in runs]
  return super().setup(encoded,row,clip,reset)
 def check(self,runs,row=0,clip=(0,320,0,8),reset=True,hist=None):
  frame,records=self.setup(runs,row,clip,reset);r,before,after=self.invoke();wanted,weights,maps,dones=model.Fixture.oracle(self,runs,row,clip,before,hist)
  assert not r.p&1 and r.a==0,(row,clip,r.a,r.p)
  assert after[F:F+20]==frame and after[F+20]==1
  assert after[F+98:F+658]==bytes(v for tile in weights for v in tile)
  for index,(at,n,arrays) in enumerate(records):
   expected=b''.join((v&65535).to_bytes(2,'little') for v in maps[index])
   assert after[at:at+len(expected)]==expected,('signed boundaries',maps[index],after[at:at+len(expected)].hex())
   assert after[at+len(expected):at+2*(n+1)]==b'\xA7'*(2*(n+1)-len(expected))
   desc=0x8D00+index*17+14;assert after[desc:desc+3]==bytes([dones[index]])+(maps[index][-1]&65535).to_bytes(2,'little')
   wanted[at:at+len(expected)]=expected;wanted[desc:desc+3]=after[desc:desc+3]
  wanted[F+20:F+SIZE]=after[F+20:F+SIZE];self.loader_expected(wanted,before,after)
  for n in ['text_ptr','screen_ptr']:at=self.s[n];wanted[at:at+2]=after[at:at+2]
  assert after==wanted,('fullRAM/signedpixels/attrs/source/shim/catalog',row,clip,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
  return weights,maps,dones

def run(out,previous=DEFAULT):
 frozen,identity=geos.freeze(out,previous)
 leaf.resident.cpu_editor.ROOT=leaf.resident.editor_fixture.ROOT=frozen
 leaf.resident.cpu_editor.NAMES=leaf.resident.editor_fixture.NAMES=identity['names']
 ls,payload,image=leaf.build(out,frozen);f=Fixture(out,ls,payload,image);rows=0;invalid=0
 def rec(chars,x,y=0,style=0,flag=0,role=2):
  n=len(chars);return chars,bytes([style])*n,bytes([role])*n,bytes([flag])*n,x,y
 try:
  reu=f.reu()
  for x in range(-15,0):
   for style in range(4):
    for flag in range(8):
     f.check([rec(b'Wim. gjpq Lower/UPPER',x,style=style,flag=flag,role=(style+flag)%14)],row=(x+style+flag)%25);rows+=1
  for x in [-15,-8,-4,-1]:
   for clip in [(0,0,0,8),(0,320,0,8),(5,37,1,7),(0,320,3,5),(319,320,0,8)]:
    f.check([rec(b'gjpq Wim.',x,-8,3,6),rec(b'Next line',x,1,2,3,3)],row=24,clip=clip);rows+=1
  hist,_,_=f.check([rec(b'Wim.',-4)],row=2);rows+=1
  f.check([rec(b'gjpq',-1,-8,3,6,3)],row=2,reset=False,hist=hist);rows+=1
  for x in [320,1000,0x8000,0xFFF0]:
   _,maps,dones=f.check([rec(b'Offright',x)],row=4);assert maps==[[x]] and dones==[0];rows+=1
  # Actual immutable packet rendering remains lease-neutral under counted
  # foreign leases, regardless of a signed clipping origin.
  for leases in [1,7]:
   for _ in range(leases):assert not f.call('se_doc_read_acquire').p&1
   f.check([rec(bytes([0x5C,0x7F,0xA1,0xFF]),-3,style=3,flag=6)],row=3);rows+=1
   assert f.get('se_doc_read_locks',1)==leases
   for _ in range(leases):assert not f.call('se_doc_read_release').p&1
  for owner in [0,1,2,3,5,255]:
   f.setup([rec(b'Negative frame opaque',-4)])
   for op in [0,1,255]:f.refuse(0xB2,op=op,ctx=0xC600,owner=owner);invalid+=1
  for field,value in [('style',4),('role',14),('flag',8)]:
   _,records=f.setup([rec(b'Negative invalid',-4)])
   f.m.write(records[0][2][{'style':1,'role':2,'flag':3}[field]],value);f.refuse(frame=True);invalid+=1
  assert f.reu()==reu
  result=dict(status='passed',identity=identity,payload_bytes=len(payload),spare_bytes=4096-len(payload),packed_font=ls['se_geos_packed'],widths=ls['se_geos_widths'],rows=rows,pixels_checked=rows*2560,invalid_frames=invalid,full_RAM_guard_bytes=65536,whole_REU_unchanged=16777216,new_BSS=0,new_ZP=0,horizontal_negative_range=[-15,-1],source_boundary_encoding='two-complement16 until nonnegative; otherunsignedoffright retained',scope='PrivateactualsealedR21 catalog, signedclip/inkmajority/selectioncaretunion/maps/resetappend/lease/fault guards; no native/editorintegration claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  archive=ROOT/'agentsworking/evidence/M7'/(out.name+'-geos-row-signed');archive.mkdir(parents=True)
  for name in ['result.json','build.json','geosrow.bin','geosrow.seo','geosrow.lbl','geosrow.map','aliases.s']:shutil.copy2(out/name,archive/name)
  for name in ['freeze.json','product-sources.zip']:shutil.copy2(frozen/name,archive/name)
  with zipfile.ZipFile(archive/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
   for p in ['src/render/geos/row.s','src/render/geos/row.inc','tests/test_geos_row_signed.py','tests/test_geos_row.py']:z.write(ROOT/p,p)
  pointer=dict(status='passed',evidence=str(archive.relative_to(ROOT)),payload_bytes=len(payload),rows=rows,invalid_frames=invalid,packed_font=hex(ls['se_geos_packed']),widths=hex(ls['se_geos_widths']))
  (ROOT/'agentsworking/evidence/M7/geos-row-signed-checkpoint.json').write_text(json.dumps(pointer,indent=2)+'\n');print(json.dumps(pointer,indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args();out=ROOT/'build/geos-row-signed'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.fixture)
