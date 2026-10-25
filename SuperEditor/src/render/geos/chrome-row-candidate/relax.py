"""Private measured shortbranch selection; ca65 AND actual linkedrange proof."""
from pathlib import Path
import sys,json,re,shutil,difflib
from importlib.util import spec_from_file_location,module_from_spec
D=Path(__file__).resolve().parent;sp=spec_from_file_location('rowbuild',D/'build.py');b=module_from_spec(sp);sp.loader.exec_module(b)
def run(out):
 src=out/'src';cfg=out/'range.cfg';cfg.write_text('MEMORY{IMAGE:file=%O,start=$B000,size=$2000;}SEGMENTS{CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}')
 objs=[out/(n+'.o')for n in('editor','mode','gridcache','gridchrome','gridheader')];changes=[];before={};mapping={'eq':'eq','ne':'ne','cc':'cc','cs':'cs','mi':'mi','pl':'pl','vc':'vc','vs':'vs'}
 b.command('ld65','-C',cfg,'-o',out/'range.bin',*objs);bestsize=(out/'range.bin').stat().st_size
 sources=[src/'render/grid'/n for n in('finalize.s','preflight.s','source.s','mode.s','cache.s')]+[src/'overlays/grid-editor.s',src/'tui/editor-chrome40.s',src/'tui/header40.s']
 def assemble(path):
  tag='gridchrome'if path.name=='editor-chrome40.s'else'gridheader'if path.name=='header40.s'else'mode'if path.name=='mode.s'else'gridcache'if path.name=='cache.s'else'editor';main=path if tag in ('gridchrome','gridheader','mode','gridcache')else src/'overlays/grid-editor.s';return b.command('ca65','-g','-D','EDITOR_OVERLAY=1','-I',src,'-I',out,'-o',out/(tag+'.o'),main,okay=False)
 for path in sources:
  lines=path.read_text().splitlines(keepends=True);before[path]=list(lines)
  for i,line in enumerate(lines):
   if not re.search(r'\bj(eq|ne|cc|cs|mi|pl|vc|vs)\b',line):continue
   trial=re.sub(r'\bj(eq|ne|cc|cs|mi|pl|vc|vs)\b',lambda m:'b'+m[1],line);lines[i]=trial;path.write_text(''.join(lines));p=assemble(path)
   if not p.returncode:p=b.command('ld65','-C',cfg,'-o',out/'range.bin',*objs,okay=False)
   size=(out/'range.bin').stat().st_size
   if p.returncode or size>=bestsize:
    lines[i]=line;path.write_text(''.join(lines));assert not assemble(path).returncode
    continue
   bestsize=size
   changes.append(dict(path=str(path.relative_to(src)),line=i+1,before=line.strip(),after=trial.strip()))
   size=(out/'range.bin').stat().st_size
   if size<=4096:break
  if size<=4096:break
 assert size<=4096,(size,changes)
 short=D/'short';short.mkdir(exist_ok=True);patch=[]
 for path,old in before.items():
  new=path.read_text().splitlines(keepends=True)
  if old!=new:
   dest=short/path.relative_to(src);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);patch.extend(difflib.unified_diff(old,new,fromfile=str(path.relative_to(src)),tofile=str(path.relative_to(src))))
 (D/'short-branches.json').write_text(json.dumps(dict(bytes=size,changes=changes,proof='EveryindividualbranchassembledANDlinkedagainstactualB000objects; subsequentchangesonlyshrinkintervals.'),indent=2)+'\n');(D/'short-branches.patch').write_text(''.join(patch));print(size,len(changes))
if __name__=='__main__':run(Path(sys.argv[1]).resolve())
