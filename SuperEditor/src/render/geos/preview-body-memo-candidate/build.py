from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[4]
SOURCE=Path(__file__).resolve().parent
BASE=ROOT/'build/geos-incremental-editor/20261025T122004452115Z/fixture'
def command(args,cwd,log):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True)
 with log.open('a')as f:f.write(' '.join(map(str,args))+'\n'+p.stdout+p.stderr)
 if p.returncode:raise AssertionError(p.stdout[-4000:]+p.stderr[-4000:])
 return p.stdout

def build(out):
 private=out/'product';private.mkdir(parents=True);(private/'build/overlays').mkdir(parents=True);log=out/'build.log'
 with zipfile.ZipFile(BASE/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith(('src/','cfg/'))or name=='Makefile':
    p=private/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 for source in (ROOT/'src').rglob('*.py'):
  p=private/source.relative_to(ROOT);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,p)
 shutil.copytree(ROOT/'tools',private/'tools',ignore=shutil.ignore_patterns('__pycache__'))
 shutil.copytree(ROOT/'assets',private/'assets')
 shutil.copytree(ROOT/'config',private/'config')
 for name in ('geos-font-catalog','editor-settings'):
  src=BASE/('genuine'if name=='geos-font-catalog'else'build/'+name)
  if not src.exists():src=ROOT/'build'/name
  shutil.copytree(src,private/'build'/name)
 # Generated files are trusted immutable inputs, newer than extracted sources.
 for p in (private/'build').rglob('*'):
  if p.is_file():p.touch()
 command(['make','-j2','build/editor.prg'],private,log)
 command(['make','-j2','editor'],private,log)
 baseline=(private/'build/editor.prg').read_bytes();assert baseline==(BASE/'build/editor.prg').read_bytes(),'Full frozen-source resident rebuild mismatch'
 for p in (BASE/'build/overlays').glob('*.seo'):assert (private/'build/overlays'/p.name).read_bytes()==p.read_bytes(),('baseline asset mismatch',p.name)
 shutil.copy2(private/'build/editor-report.json',out/'baseline-report.json')
 for src,dst in [('dma.s','src/reu/dma.s'),('cache.s','src/overlay/cache.s'),('preview.s','src/render/geos/preview.s'),('preview.inc','src/render/geos/preview.inc'),('preview-cache.s','src/render/geos/preview-cache.s'),('preview-cache.inc','src/render/geos/preview-cache.inc'),('copy-entry.s','src/lifecycle/copy-entry.s')]:shutil.copy2(SOURCE/src,private/dst);(private/dst).touch()
 with (private/'Makefile').open('a')as f:f.write('\nbuild/lifecycle-prod/copy-entry.o: src/lifecycle/copy-entry.s\n\t$(CA65) -g -D EDITOR_MANAGED_CODE=1 -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<\n')
 command(['make','-j2','build/editor.prg'],private,log)
 command(['make','-j2','editor'],private,log)
 report=json.loads((private/'build/editor-report.json').read_text());segments={s['name']:s for s in report['segments']}
 result=dict(status='fit-passed',base=str(BASE),sha256=report['sha256'],binding=report['resident_binding'],preview_payload=len((private/'build/overlays/geospreview.bin').read_bytes()),segments={k:segments[k]for k in ['COLD','CODE','CORE','RODATA','CRC_TABLE','BSS','ZEROPAGE']},baseline_all47_byteidentical=True)
 fixture=out/'fixture';shutil.copytree(BASE,fixture)
 for path in (private/'build').glob('editor*'):
  if path.is_file()and path.suffix in ('.prg','.lbl','.map','.json'):shutil.copy2(path,fixture/'build'/path.name)
 for path in (private/'build/overlays').glob('*.seo'):shutil.copy2(path,fixture/'build/overlays'/path.name)
 identity=json.loads((fixture/'freeze.json').read_text());identity['prg_sha256']=hashlib.sha256((fixture/'build/editor.prg').read_bytes()).hexdigest();identity['assets']={n:hashlib.sha256((fixture/f'build/overlays/{n}.seo').read_bytes()).hexdigest()for n in identity['names']};identity['cpu_only_private_candidate']=True;identity['d81_scope']='Historical baseline D81 unchanged, not candidate native/package proof';(fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 shutil.copytree(private/'build/geos-font-catalog',fixture/'genuine',dirs_exist_ok=True);shutil.copytree(private/'build/editor-settings',fixture/'build/editor-settings',dirs_exist_ok=True)
 with zipfile.ZipFile(fixture/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in [private/'Makefile',*sorted((private/'src').rglob('*.s')),*sorted((private/'src').rglob('*.inc')),*sorted((private/'cfg').rglob('*.cfg'))]:z.write(p,p.relative_to(private))
 (out/'fit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
 return private
if __name__=='__main__':
 out=ROOT/'build/geos-preview-body-memo'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);build(out)
