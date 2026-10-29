"""Private R21 byte compositor proof; no production/shared build or native use."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,random,shutil,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_literal_profile as profile
import test_geos_row_leaf as leaf
import test_geos_row as model
from overlays import wrap,HEADER
BASE=ROOT/'build/geos-incremental-editor/20261025T122004452115Z/fixture'
PRIVATE=ROOT/'src/render/geos/literal-byte-candidate'

def digest(b):return hashlib.sha256(b).hexdigest()
def prepare(out,base,variant):
 d=out/'link';d.mkdir();src,s,ls,payload,modules=profile.build(d,base,variant=='candidate',variant=='candidate')
 assert ls['se_geos_packed']==0xabf3 and ls['se_geos_widths']==0xaedb and ls['row_clear']==0xaf5b
 for name,segments in modules.items():assert all(not size for seg,(off,size) in segments.items()if seg in ['BSS','DATA','ZEROPAGE'])
 report=json.loads((base/'build/editor-report.json').read_text());image=wrap(payload,0,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))
 if variant=='control':assert image==(base/'build/overlays/geosrow.seo').read_bytes()
 (d/'geosrow.seo').write_bytes(image)
 return d,src,s,ls,payload,image,modules

class Fixture(profile.Fixture):
 def invoke(self,op=0,ctx=leaf.F,owner=4):
  self.m.write(self.s['se_f_owner'],owner);self.m.load(self.s['se_overlay_frame'],bytes([op,ctx&255,ctx>>8]));before=self.read(0,65536)
  for n,v in [('pc',0xa010),('sp',0xfd),('p',0x24),('a',0),('x',0),('y',0)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
  self.m.write(0x1fe,0xfe);self.m.write(0x1ff,2);used=self.r.lp_run(self.m.handle,3_000_000);assert used
  return self.m.regs(),before,self.read(0,65536)
 def refuse(self,error=0x90,op=0,ctx=leaf.F,owner=4,frame=True,partial=False):
  r,before,after=self.invoke(op,ctx,owner);assert r.p&1 and r.a==error,('refusal',error,r.a,r.p)
  want=bytearray(before);want[0x100:0x200]=after[0x100:0x200]
  if frame:
   want[leaf.F+20:leaf.F+leaf.SIZE]=after[leaf.F+20:leaf.F+leaf.SIZE]
   for n in ['text_ptr','screen_ptr']:a=self.s[n];want[a:a+2]=after[a:a+2]
  if partial:
   row=before[leaf.F];want[0x6000+row*320:0x6000+(row+1)*320]=after[0x6000+row*320:0x6000+(row+1)*320];want[0x4000+row*40:0x4000+(row+1)*40]=after[0x4000+row*40:0x4000+(row+1)*40]
   for i in range(before[leaf.F+1]):
    desc=0x8d00+i*17;want[desc+14:desc+17]=after[desc+14:desc+17];at=int.from_bytes(before[desc+12:desc+14],'little');n=before[desc];want[at:at+2*(n+1)]=after[at:at+2*(n+1)]
  assert after==want,('refusal guard',next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
  if frame:
   assert after[leaf.F+20]==0
   if not partial:assert after[leaf.F+98:leaf.F+658]==before[leaf.F+98:leaf.F+658], 'histogram changed before validated paint'


def component(out,base,variant):
 d,src,s,ls,payload,image,modules=prepare(out,base,variant);f=Fixture(d,base,src,s,ls,payload);rows=0;faults=0;metrics=[];aggregate=hashlib.sha256();rng=random.Random(0x216510)
 def rec(chars,x=0,y=0,style=0,flag=0,role=0):return profile.rec(chars,x,y,style,flag,role)
 def check(runs,row=2,clip=(0,320,0,8),reset=True,hist=None):
  nonlocal rows
  used,counts,weights=f.check(runs,row,clip,reset,hist);rows+=1
  for a,n in [(0x6000+row*320,320),(0x4000+row*40,40),(leaf.F+98,560)]:aggregate.update(f.read(a,n))
  return used,weights
 try:
  reu=f.reu()
  cases=[('blank',[],(0,320,0,8)),('prose',[rec(b'Wim. gjpqy Mixed UPPER/lower')],(0,320,0,8)),('dense',[rec(b'Wim. gjpqy '*9,style=3,role=7)],(0,320,0,8)),('selected',[rec(b'Wim. gjpqy '*9,style=3,flag=6,role=7)],(0,320,0,8)),('partial',[rec(b'Wim. gjpqy Mixed UPPER/lower')],(7,319,1,7)),('two-runs',[rec(b'gjpqy Previous line',y=-8,style=2,role=3),rec(b'Next logical line',y=1,style=1,flag=2,role=8)],(0,320,0,8)),('native',[rec(bytes([0x5c,0x5e,0x7f,0xa1,0xff])*10,style=3,role=2)],(0,320,0,8))]
  for name,runs,clip in cases:
   used,_=check(runs,clip=clip);metrics.append(dict(case=name,instructions=used));print('PROFILE',name,used,flush=True)
  # Every PETSCII byte, style, inverse/selection/caret combination and ink role.
  for value in range(256):
   for style in range(4):
    chars=bytes([value])*8;flags=bytes(range(8));roles=bytes((value+i)%14 for i in range(8))
    check([(chars,bytes([style])*8,roles,flags,(value+style)%8,0),(chars,bytes([style])*8,roles,flags,128+(value+style)%8,-8)],row=value%25)
  print('PASS all256bytes/4styles/8flags',rows,flush=True)
  # Signed left edge and exact right edge use the original slow path as needed.
  for x in list(range(-15,0))+[0,1,7,8,15,16,245,246,255,256,309,315,319,320,1000,0x8000,0xfff0]:
   for style in range(4):
    for flag in range(8):check([rec(b'Wim. gjpq',x=x,style=style,flag=flag,role=(flag+style)%14)],row=(x+style+flag)%25)
  clips=[(0,0,0,8),(320,320,0,8),(7,9,0,8),(0,320,3,5),(11,319,8,8),(19,301,1,7),(0,320,0,8)]
  for clip in clips:
   for x in [-15,-8,-1,0,1,7,313,319]:
    check([rec(b'gjpq Wim.',x=x,y=-3,style=3,flag=3,role=2),rec(b'Next',x=x,y=6,style=2,flag=6,role=8)],row=24,clip=clip)
  # Independent stable-priority ties and overlapping glyph votes; repeated
  # append reaches saturation without changing the vote-before-XOR contract.
  for first in range(14):
   for second in range(14):check([rec(b'Wim.',role=first,flag=1),rec(b'Wim.',role=second,flag=1)],row=(first+second)%25)
  dense=rec(b' '*80,flag=1,role=2);_,hist=check([dense],row=6)
  for i in range(6):_,hist=check([dense],row=6,reset=False,hist=hist)
  assert hist[0][2]==255
  for _ in range(256):
   runs=[]
   for i in range(rng.randrange(3)):
    n=rng.randrange(1,45);runs.append((rng.randbytes(n)if hasattr(rng,'randbytes')else bytes(rng.randrange(256)for _ in range(n)),bytes(rng.randrange(4)for _ in range(n)),bytes(rng.randrange(14)for _ in range(n)),bytes(rng.randrange(8)for _ in range(n)),rng.choice([-15,-8,-1,0,1,7,15,315]),rng.randrange(-8,8)))
   check(runs,row=rng.randrange(25),clip=rng.choice(clips))
  # Strict invalid owner checks precede all frame dereferences. Operation1 is
  # admission/NOP; malformed frames remain totally opaque on owner/entry errors.
  f.setup([rec(b'Valid')])
  for owner in [0,1,2,3,5,255]:f.refuse(0xb2,ctx=0xc600,owner=owner,frame=False);faults+=1
  for op in [2,3,255]:f.refuse(0x90,op=op,frame=False);faults+=1
  for ctx in [0x8881,0xc600,0xffff]:f.refuse(0x90,ctx=ctx,frame=False);faults+=1
  # A bad frame clears VALID only after entry context checks; preset VALID0
  # lets every malformed pre-validation path share the strict zero contract.
  mutations=[(0,25),(1,3),(2,2),(3,16),(18,9),(19,9),(15,2),(17,2),(5,0xc6),(7,0x60),(11,0xc6),(13,0x88),('count',129),('origin',8),('origin',0xf7),('style',4),('role',14),('flag',8),('map',0x917f),('chars',0x8800)]
  for field,value in mutations:
   _,records=f.setup([rec(b'Valid')]);f.m.write(leaf.F+20,0)
   if isinstance(field,int):f.m.write(leaf.F+field,value)
   elif field=='count':f.m.write(0x8d00,value)
   elif field=='origin':f.m.write(0x8d01,value)
   elif field in ['style','role','flag']:f.m.write(records[0][2][{'style':1,'role':2,'flag':3}[field]],value)
   else:f.m.load(0x8d00+{'map':12,'chars':4}[field],value.to_bytes(2,'little'))
   f.refuse();faults+=1
  f.setup([rec(b'Append')],reset=False);f.m.write(leaf.F+20,0);f.refuse();faults+=1
  for role in range(14):
   f.setup([rec(b'Palette')]);f.m.write(leaf.F+20,0);f.m.write(leaf.PALETTE+role,16);f.refuse();faults+=1;f.m.load(leaf.PALETTE,model.PALETTE)
  packed=(base/'fonts/bsw9-original.bin').read_bytes();widths=(base/'fonts/bsw9-widths.bin').read_bytes()
  for at in range(8):
   f.setup([rec(b'Font')]);f.m.write(leaf.F+20,0);bad=bytearray(packed);bad[at]^=1;f.m.load(0x8200,bad);f.m.load(leaf.F+6,(0x8200).to_bytes(2,'little'));f.refuse(0x94);faults+=1
  for value in [0,9,255]:
   f.setup([rec(b' A')]);f.m.write(leaf.F+20,0);bad=bytearray(widths);bad[1]=value;f.m.load(0x8600,bad);f.m.load(leaf.F+8,(0x8600).to_bytes(2,'little'));f.refuse(0x94,partial=True);faults+=1
  f.setup([rec(bytes([0x5c]))]);f.m.write(leaf.F+20,0);bad=bytearray(widths);bad[28]=7;f.m.load(0x8600,bad);f.m.load(leaf.F+8,(0x8600).to_bytes(2,'little'));f.refuse(0x94,partial=True);faults+=1
  for start,end in [(0,480),(480,481),(20,19),(65535,0),(0,512)]:
   f.setup([rec(b' A')]);f.m.write(leaf.F+20,0);bad=bytearray(packed);bad[8+65*2:12+65*2]=start.to_bytes(2,'little')+end.to_bytes(2,'little');f.m.load(0x8200,bad);f.m.load(leaf.F+6,(0x8200).to_bytes(2,'little'));f.refuse(0x94,partial=True);faults+=1
  # Deliberate violation of the documented disjoint-array caller contract:
  # an initial map write changes the first style after the validation pass.
  # Keep original GG's second style guard despite fixed-frame specialization.
  _,records=f.setup([rec(b'AA',x=4)]);f.m.write(leaf.F+20,0);f.m.load(0x8d00+12,records[0][2][1].to_bytes(2,'little'));f.refuse(0x90,partial=True);faults+=1
  assert f.reu()==reu
  result=dict(status='passed',variant=variant,rows=rows,faults=faults,pixels=rows*2560,attributes=rows*40,payload_bytes=len(payload),new_BSS=0,new_ZP=0,fixed_font=[hex(ls[n])for n in ['se_geos_packed','se_geos_widths']],aggregate_outputs_sha256=aggregate.hexdigest(),metrics=metrics,full_RAM_guard=65536,whole_REU_guard=16777216,scope='ActualisolatedR21entry, independentpixels/attrs/saturatingvotes/maps. No overlayloader/nativecycleclaim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('COMPONENT PASS',rows,faults,flush=True);return result
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),rows=rows,faults=faults))+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()


def public_gate(out,base,variant,suite):
 d,src,s,ls,payload,image,modules=prepare(out,base,variant)
 private=out/'private-input';shutil.copytree(base,private)
 (private/'build/overlays/geosrow.seo').write_bytes(image)
 identity=json.loads((private/'freeze.json').read_text());old=identity['assets']['geosrow'];identity['assets']['geosrow']=digest(image);(private/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 seam=dict(kind='PrivateR21SEOsubstitution',variant=variant,original_sha256=old,private_sha256=digest(image),source_files={str(p.relative_to(ROOT)):digest(p.read_bytes())for p in PRIVATE.iterdir()if p.is_file()})
 (private/'private-R21-substitution.json').write_text(json.dumps(seam,indent=2)+'\n')
 target=out/'public';target.mkdir()
 if suite=='incremental':
  import test_geos_incremental_editor as public
  result=public.run(target,private)
 elif suite=='inline':
  import test_geos_semantic_editor as public
  result=public.run(target,private,inline_case=True)
 elif suite=='fold':
  import test_geos_fold_editor as public
  result=public.run(target,private)
 else:
  import test_geos_preview_editor as public
  result=public.run(target,private)
 if result is None:result=json.loads((target/'result.json').read_text())
 result['private_R21_substitution']=seam;(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--variant',choices=['control','candidate'],default='candidate');p.add_argument('--suite',choices=['component','incremental','inline','fold','preview'],default='component');a=p.parse_args()
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/geos-literal-byte-candidate'/stamp;out.mkdir(parents=True);print('RUN',out,flush=True)
 if a.suite=='component':component(out,a.base.resolve(),a.variant)
 else:public_gate(out,a.base.resolve(),a.variant,a.suite)
if __name__=='__main__':main()
