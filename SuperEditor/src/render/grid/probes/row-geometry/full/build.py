"""Private complete geometry build, real frozen current59 controls first."""
from pathlib import Path
import hashlib,importlib.util,json,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[6];D=Path(__file__).resolve().parent
BASE=ROOT/'build/capture-lexical-integrated/20261026T190219265642Z/fixture'
def command(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
def build(out):
 out.mkdir(parents=True)
 spec=importlib.util.spec_from_file_location('geometry_bridge',D.parent/'c33-budget.py');bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge);bridge.BASE=BASE;bridge.build(out/'bridge')
 tree=out/'bridge/tree'
 # The geometry latch is also a sparse-index loan: do not write it before
 # the actual old-source admission and retained-index revocation.
 ctl=tree/'src/render/grid/paragraph/controller.inc';body=ctl.read_text();assert body.count('long_try:\n lda #0\n sta RG_GEOM\n')==1;body=body.replace('long_try:\n lda #0\n sta RG_GEOM\n','long_try:\n');needle=' sta se_n_cache_count\n';assert body.count(needle)==1;body=body.replace(needle,needle+' sta RG_GEOM\n');ctl.write_text(body)
 p=tree/'src/render/grid/caret/build.py';spec=importlib.util.spec_from_file_location('geometry_c33_final',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.build(out/'c33',BASE)
 report=json.loads((BASE/'build/editor-report.json').read_text());digest=report['resident_binding']['digest'];s=report['symbols']
 (out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 entry=tree/'src/render/geos/fold-entry.s';query=tree/'src/render/geos/fold-query.s'
 def link(name,paths):
  dest=out/name;dest.mkdir();objs=[]
  for i,p in enumerate(paths):
   o=dest/(str(i)+'.o');command('ca65','-g','-I',out,'-I',tree/'src','-o',o,p);objs.append(o)
   dumped=subprocess.check_output(['od65','--dump-segments',str(o)],text=True);sizes={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',dumped,re.S)};assert not any(sizes.get(n,0)for n in('BSS','DATA','ZEROPAGE'))
  command(sys.executable,ROOT/'tools/module_bindings.py','--report',BASE/'build/editor-report.json','--output',dest/'aliases.s',*objs);command('ca65','-g','-o',dest/'aliases.o',dest/'aliases.s')
  command('ld65','-C',tree/'cfg/overlay-r.cfg','-o',dest/'leaf.bin','-Ln',dest/'leaf.lbl','-m',dest/'leaf.map',*objs,dest/'aliases.o');return(dest/'leaf.bin').read_bytes()
 original=link('r24-control',[entry,query]);assert original==(BASE/'build/overlays/geosfold.seo').read_bytes()[36:]
 e=entry.read_text().replace('.import se_f_owner','.import se_f_owner,rg_boundary,rg_prepare,rg_apply').replace(' lda #$90\n sec\n rts',' cmp #3\n beq prepare\n cmp #4\n beq apply\n cmp #5\n beq boundary\n lda #$90\n sec\n rts');e+='\nprepare:jmp rg_prepare\napply:jmp rg_apply\nboundary:jmp rg_boundary\n';entry.write_text(e)
 # Exact checked component kernel, transformed only in the private build tree.
 v=(D.parent/'vertical.s').read_text().replace('.import root,se_f_owner,se_mode,se_render_caps,se_sel_mark','.import se_f_owner,se_mode,se_render_caps,se_sel_mark').replace('.import se_gc_handle,se_gc_epoch,se_reu_map,se_rg_owned,se_gc_valid','.import se_gc_handle,se_gc_epoch,se_reu_map,se_gc_valid\n.import se_reu_epoch,se_reu_retired,se_reu_logical_owner,se_reu_physical_owner').replace('.export se_rg_dispatch','.export se_rg_prepare,se_rg_apply,se_rg_check_owner\nse_rg_check_owner=check_owner')
 lo=v.index('se_rg_dispatch:');hi=v.index('busy:',lo);v=v[:lo]+v[hi:];v=v.replace(' jmp se_rg_owned',' jmp owned').replace('prepare:\n','se_rg_prepare:\n').replace('apply:\n','se_rg_apply:\n').replace(' jsr prepare',' jsr se_rg_prepare')
 # A zero-length interval may end exactly one-past-body; no DMA then occurs.
 v=v.replace(': clc\n adc FIRST\n cmp #22',': clc\n adc FIRST\n cmp #23')
 v+='''\nowned:\n lda se_reu_retired\n bne stale\n lda se_gc_epoch\n cmp se_reu_epoch\n bne stale\n lda se_gc_epoch+1\n cmp se_reu_epoch+1\n bne stale\n lda se_reu_epoch\n ora se_reu_epoch+1\n beq stale\n ldx se_gc_handle\n beq stale\n lda se_reu_logical_owner,x\n cmp #$FE\n bne stale\n ldy se_reu_map,x\n beq stale\n lda se_reu_physical_owner,y\n cmp #$FE\n bne stale\n clc\n rts\nstale:\n lda #$18\n sec\n rts\n'''
 kernel=out/'kernel.s';kernel.write_text(v)
 raw=link('r24',[entry,query,kernel,D/'authority.s',D/'transaction.s']);assert len(raw)<=4096
 sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
 image=wrap(raw,0,24,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'r24/leaf.seo').write_bytes(image)
 fixture=out/'fixture';shutil.copytree(BASE,fixture);images={'grid':(out/'c33/grid.seo').read_bytes(),'geosfold':image};identity=json.loads((fixture/'freeze.json').read_text())
 for n,image in images.items():(fixture/'build/overlays'/(n+'.seo')).write_bytes(image);identity['assets'][n]=hashlib.sha256(image).hexdigest()
 identity['private_change']='C33/R24 raw physical-row geometry transaction';(fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 result=dict(status='built',scope='Private complete body, not qualified until real public oracle gate.',R24=len(raw),R24_free=4096-len(raw),C33=4096,C33_prefont_end='BEFD',C33_prefont_free=2,R25_exact=True,new_BSS=0,new_ZP=0,changed={n:identity['assets'][n]for n in images});(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve())[1])
