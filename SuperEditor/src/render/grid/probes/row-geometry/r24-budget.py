"""Private existing-R24 geometry service budget; old fold operations stay exact."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[5];D=Path(__file__).resolve().parent
BASE=ROOT/'build/capture-index-fixed/20261026T183928480377Z/fixture'
def command(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True,capture_output=True)
def build(out):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(BASE/'product-sources.zip')as z:z.extractall(tree)
 report=json.loads((BASE/'build/editor-report.json').read_text());digest=report['resident_binding']['digest'];s=report['symbols']
 (out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def link(name,paths):
  d=out/name;d.mkdir();objects=[]
  for i,p in enumerate(paths):
   o=d/(str(i)+'.o');command('ca65','-g','-I',out,'-I',tree/'src','-o',o,p);objects.append(o)
  command(sys.executable,ROOT/'tools/module_bindings.py','--report',BASE/'build/editor-report.json','--output',d/'aliases.s',*objects);command('ca65','-g','-o',d/'aliases.o',d/'aliases.s')
  command('ld65','-C',tree/'cfg/overlay-r.cfg','-o',d/'leaf.bin','-Ln',d/'leaf.lbl','-m',d/'leaf.map',*objects,d/'aliases.o')
  raw=(d/'leaf.bin').read_bytes();assert len(raw)<=4096
  labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(d/'leaf.lbl').read_text())}
  return raw,labels
 entry=tree/'src/render/geos/fold-entry.s';query=tree/'src/render/geos/fold-query.s'
 original,oldlabels=link('control',[entry,query]);image=(BASE/'build/overlays/geosfold.seo').read_bytes();assert image[36:]==original,'R24 control mismatch'
 e=entry.read_text();e=e.replace('.import se_f_owner','.import se_f_owner,se_rg_prepare,se_rg_apply');e=e.replace(' lda #$90\n sec\n rts',' cmp #3\n beq prepare\n cmp #4\n beq apply\n lda #$90\n sec\n rts');e+='\nprepare:jmp se_rg_prepare\napply:jmp se_rg_apply\n';entry.write_text(e)
 # Keep the primitive in the new private namespace, never alter R24 production.
 v=(D/'vertical.s').read_text();v=v.replace('.import root,se_f_owner,se_mode,se_render_caps,se_sel_mark','.import se_f_owner,se_mode,se_render_caps,se_sel_mark').replace('.import se_gc_handle,se_gc_epoch,se_reu_map,se_rg_owned,se_gc_valid','.import se_gc_handle,se_gc_epoch,se_reu_map,se_gc_valid\n.import se_reu_epoch,se_reu_retired,se_reu_logical_owner,se_reu_physical_owner').replace('.export se_rg_dispatch','.export se_rg_prepare,se_rg_apply')
 lo=v.index('se_rg_dispatch:');hi=v.index('busy:',lo);v=v[:lo]+v[hi:];v=v.replace(' jmp se_rg_owned',' jmp owned').replace('prepare:\n','se_rg_prepare:\n').replace('apply:\n','se_rg_apply:\n').replace(' jsr prepare',' jsr se_rg_prepare')
 v+='''\n; Provider authority is checked independently on both primitive calls.\nowned:\n lda se_reu_retired\n bne stale\n lda se_gc_epoch\n cmp se_reu_epoch\n bne stale\n lda se_gc_epoch+1\n cmp se_reu_epoch+1\n bne stale\n lda se_reu_epoch\n ora se_reu_epoch+1\n beq stale\n ldx se_gc_handle\n beq stale\n lda se_reu_logical_owner,x\n cmp #$FE\n bne stale\n ldy se_reu_map,x\n beq stale\n lda se_reu_physical_owner,y\n cmp #$FE\n bne stale\n clc\n rts\nstale:\n lda #$18\n sec\n rts\n'''
 vertical=tree/'src/render/geos/vertical.s';vertical.write_text(v)
 authority=tree/'src/render/geos/geometry-authority.s';shutil.copy2(D/'authority.s',authority)
 candidate,labels=link('candidate',[entry,query,vertical,authority])
 # Old entries may move, but their objects and all frame/call semantics are unchanged.
 sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
 seo=wrap(candidate,0,24,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'candidate/leaf.seo').write_bytes(seo)
 fixture=out/'fixture';shutil.copytree(BASE,fixture);(fixture/'build/overlays/geosfold.seo').write_bytes(seo)
 identity=json.loads((fixture/'freeze.json').read_text());identity['assets']['geosfold']=hashlib.sha256(seo).hexdigest();identity['private_change']='R24 ops3/4 bounded vertical transport component only';(fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 result=dict(status='PASS',scope='Component budget only; no source-authoritative editor integration.',control=len(original),candidate=len(candidate),remaining=4096-len(candidate),primitive_and_dispatch=len(candidate)-len(original),control_exact=True,sha256=identity['assets']['geosfold'],labels={k:labels[k]for k in ('se_rg_prepare','se_rg_apply','se_gfq_begin','se_gfq_step','se_gfq_cancel')})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve())[1])
