"""One final-build real source insert that provably crosses320px softwrap."""
from pathlib import Path
import argparse,json,hashlib,subprocess,shutil,zipfile
import test_geos_edit_profile as profile
from d81_image import D81Image
ROOT=profile.ROOT;timing=profile.timing
ORIGINAL_FREEZE=timing.freeze

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
 widths=(a.fixture/'fonts/bsw9-widths.bin').read_bytes();native=timing.native.live.geos.native;encode=timing.native.live.grid.native_text
 W=encode('W')[0];A=encode('A')[0];tiny=encode('i')[0];line=bytearray([A])
 while sum(widths[native(v)]for v in line)+widths[native(W)]<=320:line.append(tiny)
 oldwidth=sum(widths[native(v)]for v in line);assert oldwidth<320<oldwidth+widths[native(W)]
 data=bytes(line)+encode('\rFollowing source line.\rTail.');at=15;after=data[:at]+bytes([W])+data[at:]
 def freeze(base,standard):
  e=ORIGINAL_FREEZE(base,standard);(e/'wrapdoc.bin').write_bytes(data)
  result=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'wrapdoc.bin'),'wrapdoc,s'],capture_output=True,text=True);(e/'wrapdoc-package.log').write_text(result.stdout+result.stderr);assert not result.returncode
  assert D81Image((e/'working.d81').read_bytes()).read(b'WRAPDOC',kind=1).data==data
  shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
  (e/'wrap-geometry.json').write_text(json.dumps(dict(before_pixels=oldwidth,insert_pixels=widths[native(W)],after_pixels=oldwidth+widths[native(W)],canonical=at,old_logical_line_bytes=len(line),source_sha256=hashlib.sha256(data).hexdigest()),indent=2)+'\n')
  with zipfile.ZipFile(e/'wrap-verifier.zip','w',zipfile.ZIP_DEFLATED)as z:z.write(Path(__file__),Path(__file__).relative_to(ROOT))
  return e
 def scenario(e):
  n=profile.Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True;n.boot();n.open('open_real_wrapdoc',b'WRAPDOC');n.typed('wrapdoc_geos','mode hires');n.send('place_wrap_caret',b'\x1d'*at);n.memory('exact_wrap_caret','se_hot_caret',at,3);n.measure('prose-insert-crosses320',after,3,key=W,category='actual-softwrap-threshold');return n
 timing.freeze=freeze;profile.scenario=scenario
 import sys
 sys.argv=[str(Path(__file__)),'--run','--fixture',str(a.fixture)];profile.main()
if __name__=='__main__':main()
