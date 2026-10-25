"""Host-search then actual immutable editor proof of minority neighbor ink votes."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_editor as sem
import test_geos_fold_editor as fold
FONTS={n:(ROOT/'assets/fonts/generated'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)}

def search():
 attempts=0
 for prefix in ['Intro.','', 'g', 'gjpqy', 'X']:
  for tail in ['- .','- ,','- :','- -','- _','- i','- !','- ;','# .','# _']:
   for char in ['g','j','p','q','y']:
    for n in [3,4,5,6,7,8,9,10,12,15,20]:
     line=char*n;data=fold.geos.native_text(prefix+'\r'+line+'\r'+tail+'\rTail.');start=len(fold.geos.native_text(prefix))+1
     bits,attrs,rows,s=sem.body(data,FONTS,caret=start+2);top=rows[1].top;a=(top//8)*40;attempts+=1
     if attrs[a:a+80]!=bytes([0x16])*80:continue
     for at in range(start+1,start+n):
      new=data[:at]+data[at+1:];nb,na,_,_=sem.body(new,FONTS,caret=at)
      if na[a:a+80]!=attrs[a:a+80]:return dict(attempts=attempts,source=list(data),at=at,top=top,oldattrs=attrs[a:a+80].hex(),newattrs=na[a:a+80].hex(),diff=[(i,x,y)for i,(x,y)in enumerate(zip(attrs,na))if x!=y])
 return dict(attempts=attempts,found=False)
if __name__=='__main__':
 out=ROOT/'build/geos-style-neighbor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);r=search();(out/'search.json').write_text(json.dumps(r,indent=2)+'\n');print(out);print(json.dumps(r,indent=2))

# Callable independently after bounded host search; actual immutable product,
# actual C6 BACK and root renderer. The reference clears only derivedGCCvalid.
def actual(out,base):
 from shutil import copytree
 frozen=out/'fixture';copytree(base,frozen,dirs_exist_ok=True);fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;identity=json.loads((frozen/'freeze.json').read_text());fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names']
 dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);g=fold.Fixture(out,frozen,dll,True);data=fold.geos.native_text('Intro.\rjjj\r- .\rTail.');frames=[]
 try:
  for x in(f,g):x.source(data);x.command(99);x.position(9);x.render()
  assert g.read(0x4000+120,80)==bytes([0x16])*80
  old=g.read(0x4000,1000)
  for x in(f,g):x.key(0x14)
  assert g.m.read(0x9149)==1,'actualC6certificateaccepted'
  canonical=g.canonical();reu=g.reu();loads=g.get('se_overlay_loads',2)
  started=g.total_instructions;g.render();fastinstructions=g.total_instructions-started
  f.m.write(0xcf90,0);f.render();expected,attrs,_,_=sem.expected(f,f.merged(),FONTS)
  assert f.read(0x6000,8000)==expected and f.read(0x4000,1000)==attrs,'actualforcedfullagreesindependentoracle'
  gb=g.read(0x6000,8000);ga=g.read(0x4000,1000);diff=[(i,a,b)for i,(a,b)in enumerate(zip(ga,attrs))if a!=b]
  assert g.canonical()==canonical and g.merged()==f.merged() and g.read(0xc600,1024)==g.shim
  assert gb==expected and diff==[(160,0x16,0x36)],('exactcounterexample',diff)
  assert g.m.read(0xcf90)==1 and not g.m.read(0x9149),'actualR30published'
  delta_loads=(g.get('se_overlay_loads',2)-loads)&65535
  cache,bank=g.raw_cache();at=bank*65536;now=g.reu();assert now[:at]==reu[:at] and now[at+65536:]==reu[at+65536:]
  fold.geos.png(gb,ga,out/'actual-R30.png');fold.geos.png(expected,attrs,out/'expected-full.png');(out/'actual-R30-ram.bin').write_bytes(g.read(0,65536));(out/'expected-full-ram.bin').write_bytes(f.read(0,65536));result=dict(status='actual-product-counterexample-confirmed',source=list(data),operation='BACKfromcaret9 deletesmiddlej at8',old80attributes='all16',actual_vs_expected_attributes=diff,bitmap='all8000bytesexact',source_history_shim_foreign16MiB='preserved',overlayloads=delta_loads,instructions=fastinstructions,scope='Actualimmutable46 C6-certified R30/root edit vs actualforcedfullrender and independentfont/semanticoracle. Currentfastpathleavesoldwhiteattribute16 although listcyan36nowwins.');(out/'actual-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close();g.close()
