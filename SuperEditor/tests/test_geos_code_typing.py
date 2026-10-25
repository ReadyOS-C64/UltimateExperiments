"""Pure existing lexer/native8 foundation and honest R31 composition budget.
This is not a complete cache/source publication worker.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,random,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
import test_geos_row_leaf as leaf
from supermark_model import lex
BASE=ROOT/'build/geos-incremental-editor/20261025T095507963106Z/fixture'
PALETTE=(1,3,7,10,14,1,1,7,13,5,15,7,3,1)
class Fixture(fold.Fixture):
 cache_allowed=leaf.Fixture.cache_allowed
 loader_expected=leaf.Fixture.loader_expected

def run(out,base,smoke=False):
 frozen=out/'fixture';shutil.copytree(base,frozen)
 spec=importlib.util.spec_from_file_location('code_typing_build',ROOT/'src/render/geos/code-typing-candidate/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);payload,image,budget=b.build(out/'capsule',frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(out);f=Fixture(out,frozen,dll,True);f.payload=payload;f.image=image;cases=0;faults=0;peak=0;native=(frozen/'fonts/native8.bin').read_bytes();rng=random.Random(0x6531)
 def install():
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==31 and f.m.read(f.s['image_slot']+i)==0:f.m.write(f.s['se_overlay_ids']+i,0)
  f.m.write(f.s['se_overlay_active'],0);f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
 def check(data,language,caret,top=16,owner=4,error=0):
  nonlocal cases,faults,peak
  f.m.load(0x8b40,bytes([len(data),top,caret,language])+b'\xa7'*10+b'\x00');f.m.load(0x8200,data+b'\xa7'*(40-len(data)));f.m.load(0x8300,b'\xa7'*40);f.put('se_f_owner',owner,1);f.m.write(f.s['se_overlay_frame'],3)
  before=f.read(0,65536);canonical=f.canonical();r,n=f.fast_call(f.s['se_overlay_call'],a=31,x=0);peak=max(peak,n);after=f.read(0,65536);wanted=bytearray(before);f.loader_expected(wanted,before,after)
  assert r.a==error and bool(r.p&1)==bool(error),(data,language,caret,top,r.a,r.p)
  if not error:
   roles=bytearray([4]*40)
   for start,end,role in lex(data,language,start=0):roles[start:end]=bytes([role])*(end-start)
   assert after[0x8300:0x8328]==roles,(data,language,'real lexer roles',after[0x8300:0x8328].hex(),roles.hex())
   wanted[0x8300:0x8328]=roles
   for col in range(40):
    code=fold.geos.native(data[col])if col<len(data)else 32;glyph=native[(code&127)*8:(code&127)*8+8];wanted[0x6000+top*40+col*8:0x6000+top*40+col*8+8]=bytes(v^(255 if bool(code&128)^(col==caret) else 0)for v in glyph)
    ink=PALETTE[roles[col]]if col<len(data)else 1;wanted[0x4000+(top//8)*40+col]=(ink<<4)|6
   for a,z in [(0x8b40+4,0x8b40+14),(0x8d00,0x8d00+60),(f.s['text_ptr'],f.s['text_ptr']+2),(f.s['screen_ptr'],f.s['screen_ptr']+2)]:wanted[a:z]=after[a:z]
   cases+=1
  else:
   # Scalar invalidity is established before the lexer initializes its state.
   faults+=1
  assert f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  assert after==wanted,('wholeRAM/source/font/shim/input/phase',data,language,caret,top,next((hex(i),a,z)for i,(a,z)in enumerate(zip(after,wanted))if a!=z))
 try:
  source=fold.geos.native_text('Intro.\r:::basic\r10 PRINT "HI"\r:::\rTail.');f.source(source);f.command(99);f.render();install();f.put('se_i_ready',0,1);reu=f.reu()
  examples=[(1,'10 PRINT "HELLO":REM tail'),(1,'20 DATA 1,2,"A:B":PRINT 42'),(1,'30 LEFT$(A$,2)+SIN(1.2)'),(2,'start: lda #$2A ; comment'),(2,' .byte "text",$FF,%101'),(2,'@loop: sta $D020')]
  for lang,text in examples:
   data=fold.geos.native_text(text)
   for caret in (range(len(data)+1)if not smoke else[0,len(data)//2,len(data)]):check(data,lang,caret,16+8*(caret%22))
  if not smoke:
   alphabet=fold.geos.native_text('ABCdef09 +-*/=$%.,:;()"')+b'\x27'
   for lang in [1,2]:
    for _ in range(80):
     count=rng.randrange(40);data=bytes(rng.choice(alphabet)for _ in range(count));check(data,lang,rng.randrange(count+1),16+8*rng.randrange(22))
   for byte in range(256):check(bytes([byte]),1,0,16+8*(byte%22))
   for owner in [0,1,2,3,5,255]:check(b'lda',2,1,owner=owner,error=0xb2)
   for data,lang,caret,top in [(b'A'*40,1,0,16),(b'A',0,0,16),(b'A',3,0,16)]:check(data,lang,caret,top,error=0x90)
  assert f.reu()==reu
  # A real mutation supplies the separate independent source/GEC/GCC proof.
  f.put('se_f_owner',0,1);f.position(source.index(fold.geos.native_text('PRINT'))+2);f.render();f.key(fold.geos.native_text('X')[0]);f.put('se_f_owner',4,1);f.m.write(f.s['se_overlay_frame'],2);canonical=f.canonical();reu=f.reu();r,n=f.fast_call(f.s['se_overlay_call'],a=31,x=0);assert r.a==0 and not r.p&1 and f.canonical()==canonical and f.reu()==reu
  result=dict(status='component-passed/full-worker-does-not-fit',cases=cases,faults=faults,peak_instructions=peak,source_guard_instructions=n,budget=budget,wholeRAM=65536,wholeREU=16777216,scope='Real unchanged pure lexer + native8 component and independent current-source guard. Explicit row/packet/language inputs; no FE transaction, cached language authority, root route, status or publication claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 except BaseException:
  (out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-code-typing-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base,a.smoke)
