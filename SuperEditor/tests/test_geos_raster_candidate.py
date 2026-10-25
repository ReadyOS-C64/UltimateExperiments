"""Private actual sealed R21 A/B raster proof; production row.s is unchanged.

Both leaves use the frozen resident and the same independent pixel/vote oracle.
The candidate reuses bitmap and histogram addresses within an eight-pixel tile.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_row_leaf as leaf
import test_geos_row as model
CANDIDATE=ROOT/'src/render/geos/raster-candidate/row.s'
class Fixture(leaf.Fixture):
 def setup(self,runs,*args,**kwargs):
  return super().setup([(*r[:4],r[4]&65535,r[5]) for r in runs],*args,**kwargs)
 def check(self,runs,row=0,clip=(0,320,0,8),reset=True,hist=None):
  frame,records=self.setup(runs,row,clip,reset);start=self.m.regs().cycles;r,before,after=self.invoke();self.last_cycles=self.m.regs().cycles-start;wanted,weights,maps,dones=model.Fixture.oracle(self,runs,row,clip,before,hist)
  assert not r.p&1 and r.a==0,(row,clip,r.a,r.p)
  assert after[leaf.F:leaf.F+20]==frame and after[leaf.F+20]==1
  assert after[leaf.F+98:leaf.F+658]==bytes(v for tile in weights for v in tile),('histogram',row,clip)
  for i,(at,n,arrays) in enumerate(records):
   expected=b''.join((v&65535).to_bytes(2,'little') for v in maps[i]);assert after[at:at+len(expected)]==expected;assert after[at+len(expected):at+2*(n+1)]==b'\xa7'*(2*(n+1)-len(expected));desc=0x8d00+i*17+14;assert after[desc:desc+3]==bytes([dones[i]])+(maps[i][-1]&65535).to_bytes(2,'little');wanted[at:at+len(expected)]=expected;wanted[desc:desc+3]=after[desc:desc+3]
  wanted[leaf.F+20:leaf.F+leaf.SIZE]=after[leaf.F+20:leaf.F+leaf.SIZE];self.loader_expected(wanted,before,after)
  for n in ['text_ptr','screen_ptr']:at=self.s[n];wanted[at:at+2]=after[at:at+2]
  assert after==wanted,('fullRAM/pixels/votes/attributes/maps/guards',row,clip,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
  return weights,maps,dones

def full_gate(base,source,output):
 cmd=[sys.executable,ROOT/'tests/test_geos_row_leaf.py','--base',base,'--row-source',source]
 r=subprocess.run(list(map(str,cmd)),cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);output.write_text(r.stdout);assert r.returncode==0,r.stdout[-4000:]
 evidence=Path(r.stdout.rsplit('EVIDENCE ',1)[1].strip());return evidence,json.loads((evidence/'build/result.json').read_text())
def rec(chars,x=0,y=0,style=0,flag=0,role=0):
 n=len(chars);return chars,bytes([style])*n,bytes([role])*n,bytes([flag])*n,x,y

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=ROOT/'build/geos-semantic-editor/20261025T075329265974Z/fixture');p.add_argument('--smoke',action='store_true');p.add_argument('--candidate',type=Path,default=CANDIDATE);p.add_argument('--baseline',type=Path,default=ROOT/'src/render/geos/row.s');a=p.parse_args();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/geos-raster-candidate'/stamp;out.mkdir(parents=True)
 base=out/'fixture';shutil.copytree(a.base,base);names=json.loads((base/'freeze.json').read_text())['names'];leaf.resident.cpu_editor.ROOT=leaf.resident.editor_fixture.ROOT=base;leaf.resident.cpu_editor.NAMES=leaf.resident.editor_fixture.NAMES=names
 full={}
 if not a.smoke:
  for tag,source in [('baseline',a.baseline),('candidate',a.candidate)]:
   e,r=full_gate(base,source,out/(tag+'-full.stdout'));full[tag]=dict(evidence=str(e),result=r)
   print(tag,'full',r['rows'],'rows',r['invalid_frames'],'faults',flush=True)
 results={};profiles={};counts={}
 for tag,source in [('baseline',a.baseline),('candidate',a.candidate)]:
  b=out/tag;b.mkdir();ls,payload,image=leaf.build(b,base,source);f=Fixture(b,ls,payload,image);checks=0;metrics=[]
  try:
   reu=f.reu();f.check([rec(b'Warm admission',style=3,role=2)],row=2)
   for label,runs,clip in [('blank',[],(0,320,0,8)),('prose',[rec(b'Wim. gjpqy Mixed UPPER/lower')],(0,320,0,8)),('dense',[rec(b'Wim. gjpqy '*9,style=3,role=7)],(0,320,0,8)),('selected',[rec(b'Wim. gjpqy '*9,style=3,flag=6,role=7)],(0,320,0,8)),('partial',[rec(b'Wim. gjpqy Mixed UPPER/lower')],(7,319,1,7)),('two-runs',[rec(b'gjpqy Previous line',y=-8,style=2,role=3),rec(b'Next logical line',y=1,style=1,flag=2,role=8)],(0,320,0,8))]:
    f.check(runs,row=2,clip=clip);checks+=1;metrics.append(dict(label=label,instructions=f.last_used,cycles=None,bitmap=hashlib.sha256(f.read(0x6280,320)).hexdigest(),attributes=hashlib.sha256(f.read(0x4050,40)).hexdigest(),histogram=hashlib.sha256(f.read(leaf.F+98,560)).hexdigest()))
   # Same packed glyphs/inverse/selected union on both sides of tile and signed
   # zero boundaries. Full RAM and actual source lease/provider state guarded.
   origins=[-15,-8,-1,0,1,7,8,15,16,309,315,319,320,1000,0x8000,0xfff0]
   for x in origins:
    for style in range(4):
     for flag in range(8):
      f.check([rec(b'Wim. gjpq',x=x,style=style,flag=flag,role=(style+flag)%14)],row=(x+style+flag)%25);checks+=1
   for x in [-15,-8,-1,1,7,8,313,319]:
    for clip in [(0,0,0,8),(7,29,1,7),(0,320,3,5),(0,320,0,8)]:
     f.check([rec(b'gjpq Wim.',x=x,y=-3,style=3,flag=3,role=2),rec(b'Next',x=x,y=6,style=2,flag=6,role=8)],row=24,clip=clip);checks+=1
   dense=rec(b' '*80,flag=1,role=2);weights,_,_=f.check([dense],row=6)
   for _ in range(4):weights,_,_=f.check([dense],row=6,reset=False,hist=weights);checks+=1
   assert weights[0][2]==255
   assert f.reu()==reu
   results[tag]=dict(payload=len(payload),spare=4096-len(payload),checks=checks,code=json.loads((b/'build.json').read_text()),metrics=metrics);profiles[tag]=metrics;counts[tag]=checks;(b/'result.json').write_text(json.dumps(results[tag],indent=2)+'\n')
  finally:f.close()
 for old,new in zip(profiles['baseline'],profiles['candidate']):
  assert old['label']==new['label'] and all(old[k]==new[k] for k in ['bitmap','attributes','histogram'])
  new['instruction_change']=new['instructions']-old['instructions'];new['instruction_reduction_percent']=round((1-new['instructions']/old['instructions'])*100,2)
 result=dict(status='passed',resident_sha256=json.loads((base/'build/editor-report.json').read_text())['sha256'],full_gates=full,source_paths=dict(baseline=str(a.baseline),candidate=str(a.candidate)),variants=results,scope='Private actual sealed R21 CPU A/B. Exact independent pixels, attributes, saturating ink histogram, source maps; full64KiB and16MiB guards. No production integration/native/fullpage speed claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');evidence=ROOT/'agentsworking/evidence/M8'/(stamp+'-geos-raster-candidate');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build')
 with zipfile.ZipFile(evidence/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for n in ['tests/test_geos_raster_candidate.py','tests/test_geos_row_leaf.py','tests/test_geos_row.py','src/render/geos/raster-candidate/row.s','src/render/geos/raster-candidate/row-blit.s','src/render/geos/raster-candidate/row-blit-resolve.s','src/render/geos/raster-candidate/row-blit-validate.s','src/render/geos/row.s','src/render/geos/row-fast.s','src/render/geos/row-validate.s','src/render/geos/row-resolve.s','src/render/geos/row.inc','src/render/geos/api.inc','src/render/geos/glyph.s','src/render/geos/measure.s','src/render/geos/assets.s','src/render/geos/editor-row-entry.s','cfg/geos-editor-row.cfg']:z.write(ROOT/n,n)
 print(json.dumps(dict(status='passed',counts=counts,profiles=profiles,evidence=str(evidence)),indent=2))
if __name__=='__main__':main()
