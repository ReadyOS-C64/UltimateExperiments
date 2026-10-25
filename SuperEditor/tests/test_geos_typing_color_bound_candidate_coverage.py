"""ActualGGunclippedcoverage/inversecontract, sourceR21baseincludesreverse."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,argparse
import test_geos_fold_editor as fold
ROOT=fold.ROOT

def run(out,base):
 out.mkdir(parents=True,exist_ok=True);sp=importlib.util.spec_from_file_location('coverage_build',ROOT/'src/render/geos/typing-color-bound-candidate/coverage-build.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b);ls,payload=b.build(out/'component',base);fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=base;names=json.loads((base/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names;dll=fold.geos.grid.runner(out);f=fold.Fixture(out,base,dll,True);frames=0;peak=0;F=0x8880
 try:
  f.source(fold.geos.native_text('# .\rPlain row having ample room\rTail.'));f.command(99);f.position(8);f.render();cache,bank=f.raw_cache();snapshot=cache[0xb200:0xb200+8000];row8=bytes(snapshot[(24//8)*320+c*8+(24&7)]for c in range(40));heading_width=int.from_bytes(cache[0x200+28:0x200+30],'little');example=dict(heading_width=heading_width,ninth_row_cache_bytes=row8.hex(),ninth_row_ink_votes=sum(bin(x).count('1')for x in row8));assert example['ninth_row_ink_votes']==heading_width and heading_width>0
  f.m.load(0xa000,payload);reu=f.reu();canonical=f.canonical();widths=(base/'fonts/bsw9-widths.bin').read_bytes()
  for code in range(128):
   for style in range(4):
    advance=widths[code]+(style&1)+(style&2);mask=(((1<<advance)-1)<<(16-advance)).to_bytes(2,'big');ink=[]
    for inverse in [0,1]:
     frame=bytes([code,1,style,inverse])+ls['se_geos_packed'].to_bytes(2,'little')+ls['se_geos_widths'].to_bytes(2,'little')+(0x4800).to_bytes(2,'little')+bytes([0,16,0,9]);f.m.load(F,frame+bytes([0xa7])*63);before=f.read(0,65536);r,n=f.fast_call(ls['se_geos_glyph'],x=F&255,y=F>>8);peak=max(peak,n);after=f.read(0,65536);assert not r.p&1 and after[F+18]==advance and after[F+39:F+57]==mask*9,(code,style,inverse,'GGcoverage');wanted=bytearray(before)
     for a,z in [(0x100,0x200),(F+14,F+77),(f.s['text_ptr'],f.s['text_ptr']+2),(f.s['screen_ptr'],f.s['screen_ptr']+2)]:wanted[a:z]=after[a:z]
     assert after==wanted,('wholeRAM',code,style,inverse);ink.append(after[F+21:F+39]);frames+=1
    assert bytes(a^b for a,b in zip(ink[0],mask*9))==ink[1],(code,style,'actualinversebeforevote')
  assert f.reu()==reu and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  result=dict(status='passed',glyphs=frames,wholeRAM=65536,wholeREU=16777216,peak_instructions=peak,example=example,scope='ActualunchangedGG fullcoverage/inverseplanes on realresidentforegroundloans; sourcecache9throwalreadycontainsreverseink. No inverseXORmayberemovedbeforeR21vote.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result,flush=True);return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/geos-typing-two-coverage'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run(out,a.fixture.resolve())
