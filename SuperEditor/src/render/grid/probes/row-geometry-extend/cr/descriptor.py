"""Private complete NR-input template; no borrowed scratch input or new calls."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,os,re,shutil,sys
ROOT=Path(__file__).resolve().parents[6]
def build(out,source,base):
 out.mkdir(parents=True);tree=out/'tree';shutil.copytree(source,tree)
 p=tree/'src/render/grid/caret/build.py';spec=importlib.util.spec_from_file_location('nr_descriptor_builder',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.build(out/'control',base)
 for name in('grid','geostail'):assert(out/'control'/(name+'.seo')).read_bytes()==(base/f'build/overlays/{name}.seo').read_bytes(),('source-matched control',name)
 p=tree/'src/render/grid/caret/caret.s';original=p.read_text();start=original.index(' ldx #67\n lda #0\n@clear:\n sta NC_NR,x',original.index('type_try:'));end=original.index(' lda #<NC_NR\n',start)
 replacement=''' ; Every public NR input is initialized; remaining49 bytes are worker scratch.
 ldx #18
@descriptor:
 lda nr_defaults,x
 sta NC_NR,x
 dex
 bpl @descriptor
 lda W
 sta NC_NR
 sta NC_NR+2
 lda ROW
 clc
 adc #2
 sta NC_NR+1
'''
 s=original[:start]+replacement+original[end:]
 s+='''\n.segment "RODATA"
nr_defaults:
 .byte 0,0,0,0,6
 .word $6000,$4000,$A800,P,P+80,P+160,palette
.assert *-nr_defaults=19,error,"complete native-row public input template"
'''
 p.write_text(s);(out/'descriptor.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='control/caret.s',tofile='candidate/caret.s')))
 m.build(out/'candidate',base);assert(out/'candidate/geostail.seo').read_bytes()==(base/'build/overlays/geostail.seo').read_bytes()
 fixture=out/'fixture';shutil.copytree(base,fixture,copy_function=os.link)
 target=fixture/'build/overlays/grid.seo';target.unlink();shutil.copyfile(out/'candidate/grid.seo',target)
 identity=json.loads((fixture/'freeze.json').read_text());identity['assets']['grid']=hashlib.sha256(target.read_bytes()).hexdigest();identity['private_change']='NR19 fullinput template, remove unused49 scratch clear; source-matched terminal-corrected control'
 fp=fixture/'freeze.json';fp.unlink();fp.write_text(json.dumps(identity,indent=2)+'\n')
 def end(path):return int(re.search(r'RODATA\s+[0-9A-F]+\s+([0-9A-F]+)',path.read_text().split('Segment list:')[1]).group(1),16)
 before=end(out/'control/grid.map');after=end(out/'candidate/grid.map')
 result=dict(status='BUILT',control_end=hex(before),candidate_end=hex(after),bytes_recovered=before-after,prefont_free=0xbf00-after-1,payload=4096,R25_unchanged=True,new_overlay_calls=0,newBSS=0,newZP=0,sha256=identity['assets']['grid'],baseline=str(base),source=str(source));(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':print(build(*[Path(x).resolve()for x in sys.argv[1:]])[1])
