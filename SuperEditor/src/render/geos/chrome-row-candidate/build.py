from pathlib import Path
import sys,json,zipfile,subprocess,re,shutil
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent

def command(*args,okay=True):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if okay:assert not p.returncode,p.stdout+p.stderr
 return p

def build(out,fixture,candidate=True):
 out.mkdir(parents=True,exist_ok=True);source=out/'src'
 with zipfile.ZipFile(fixture/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith('src/')or n.startswith('cfg/'):
    p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 if candidate:
  for name,new in [('render/geos/caret-ui.s','caret-ui-row.s'),('render/geos/caret-cache.s','caret-cache-row.s'),('render/grid/finalize.s','finalize-row.s')]:shutil.copy2(D/new,source/name)
 if candidate and (D/'short').exists():
  for p in (D/'short').rglob('*.s'):
   dest=source/p.relative_to(D/'short');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 report=fixture/'build/editor-report.json';command(sys.executable,'src/fold/editor-leaves/binding.py','--report',report,'--output',out/'editor-api.inc')
 objects=[]
 for name,src,flags in [('caret','render/geos/caret-cache.s',[]),('cache','render/geos/cache.s',['-D','SE_GP_CACHE_WARM_ONLY=1']),('ui','render/geos/caret-ui.s',[]),('chrome','tui/editor-chrome40.s',[]),('header','tui/header40.s',[])]:
  o=out/(name+'.o');command('ca65','-g',*flags,'-I',source,'-I',out,'-o',o,source/src);objects.append(o)
 command(sys.executable,'tools/module_bindings.py','--report',report,'--output',out/'bindings.s',*objects);command('ca65','-o',out/'bindings.o',out/'bindings.s');command('ld65','-C',out/'cfg/overlay-r.cfg','-o',out/'r27.bin','-Ln',out/'r27.lbl','-m',out/'r27.map',*objects,out/'bindings.o')
 if not candidate:assert(out/'r27.bin').read_bytes()==(fixture/'build/overlays/geoscaret.seo').read_bytes()[36:],'R27controlbyteidentity'
 # ExactproductionC16 numericbindings; useonlyverifiedimmutableprg/report.
 command(sys.executable,'tools/overlay_api.py','--report',report,'--output',out/'editor-api.inc','--all-public','--symbols','object_owner','object_banks','object_size_lo','object_size_mid','object_size_hi','tui_putc40','tui_color','tui_box_x','tui_box_y','tui_box_w','tui_box_h','box_rx','box_ry','text_ptr','screen_ptr')
 objects=[]
 for name,src,flags in [('editor','overlays/grid-editor.s',['-D','EDITOR_OVERLAY=1']),('mode','render/grid/mode.s',['-D','EDITOR_OVERLAY=1']),('gridcache','render/grid/cache.s',['-D','EDITOR_OVERLAY=1']),('gridchrome','tui/editor-chrome40.s',['-D','EDITOR_OVERLAY=1']),('gridheader','tui/header40.s',['-D','EDITOR_OVERLAY=1'])]:
  o=out/(name+'.o');command('ca65','-g',*flags,'-I',source,'-I',out,'-o',o,source/src);objects.append(o)
 command('ld65','-C',out/'cfg/overlay-c.cfg','-o',out/'c16.bin','-Ln',out/'c16.lbl','-m',out/'c16.map',*objects)
 if not candidate:assert(out/'c16.bin').read_bytes()==(fixture/'build/overlays/gridedit.seo').read_bytes()[36:],'C16controlbyteidentity'
 result=dict(R27=len((out/'r27.bin').read_bytes()),C16=len((out/'c16.bin').read_bytes()),newBSS=0,newZP=0);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),len(sys.argv)<4))
