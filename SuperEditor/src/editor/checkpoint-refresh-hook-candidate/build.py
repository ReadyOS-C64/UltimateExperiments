"""Coherent same-repository private editor build; canonical files never edited."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[3];D=Path(__file__).resolve().parent
BASE=ROOT/'build/geos-incremental-editor/20261025T194101943594Z/fixture'
CACHE=ROOT/'build/preflush-product/20261025T1931'
sys.path.insert(0,str(ROOT/'tools'))
from d81_image import D81Image
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def build(out,base=BASE,certificate=True):
 out.mkdir(parents=True);project=out/'project';project.mkdir()
 # Cached build artifacts are only bootstrap inputs. Every product source is
 # replaced from the immutable ZIP, then ALL sealed controls must reproduce.
 for directory in ['assets','config','build']:
  shutil.copytree(CACHE/directory,project/directory)
 shutil.copytree(ROOT/'tools',project/'tools',ignore=shutil.ignore_patterns('__pycache__'))
 (project/'tests').mkdir();shutil.copy2(ROOT/'tests/test_geos_editor.py',project/'tests/test_geos_editor.py')
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(project)
 for p in (ROOT/'src').rglob('*.py'):
  q=project/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 tools={str(p.relative_to(project)):SHA(p)for directory in['tools','src']for p in(project/directory).rglob('*.py')}
 def make(tag,*targets):
  with(out/(tag+'.log')).open('w')as log:p=subprocess.run(['make','-j4',*targets],cwd=project,stdout=log,stderr=subprocess.STDOUT)
  assert not p.returncode,(tag,str(out/(tag+'.log')))
 make('control','editor','build/supereditor.d81')
 controls={};names=json.loads((base/'freeze.json').read_text())['names']
 for relative in ['build/editor.prg']+['build/overlays/'+n+'.seo'for n in names]+['build/geos-font-catalog/font-pack.bin']:
  expected=(base/relative).read_bytes()if(base/relative).exists()else D81Image((base/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data
  assert(project/relative).read_bytes()==expected,('control-not-byte-identical',relative)
  controls[relative]=SHA(project/relative)
 assert SHA(project/'build/supereditor.d81')==SHA(base/'build/supereditor.d81'),'controlD81notidentical'
 control_map=json.loads((project/'build/editor-report.json').read_text());(out/'control-report.json').write_text(json.dumps(control_map,indent=2)+'\n')
 # Four exactdead-X fixed3-byte copies. DEX/BPL do not change carry.
 commands=project/'src/editor/commands.s';s=commands.read_text();proof=[]
 for label,source,target,following in [
  ('history','se_hot_caret','se_e_target','    lda se_e_command'),
  ('reload','se_e_target','se_hot_position','    lda #W_LOAD'),
  ('history_done','se_h_caret','se_e_target','@target:\n    jmp reload'),
  ('flushed','se_hot_caret','se_e_target','    jmp reload')]:
  old='    COPY24 '+source+','+target+'\n'+following
  assert s.count(old)==1,(label,s.count(old))
  loop='    ldx #2\n@refresh_copy_'+label+':\n    lda '+source+',x\n    sta '+target+',x\n    dex\n    bpl @refresh_copy_'+label+'\n'
  s=s.replace(old,loop+following,1);proof.append(dict(label=label,old_bytes=18,new_bytes=11,saved=7,source=source,target=target,following=following))
 commands.write_text(s)
 main=project/'src/editor/main.s';s=main.read_text();needle='''    cpx #3
    bcs @done
    sta se_overlay_frame
    lda #33
    ldx #1
    jsr se_overlay_call
@done:
''';replacement='''    cpx #3
    bcc @narrow
    bne @done ;invalid mode>=4 retains the original no-overlay behavior
    lda GEC_SEQUENCE
    clc
    adc #1
    cmp se_e_draw_sequence
    bne @done ;cheap necessary test only; fullauthority remains inside AUX
    lda #6
    sta se_overlay_frame
    lda #13
    bne @invoke
@narrow:
    sta se_overlay_frame
    lda #33
@invoke:
    ldx #1
    jsr se_overlay_call
@done:
''';assert s.count(needle)==1;s=s.replace(needle,replacement,1)
 if '.include "render/geos/edit-certificate.inc"'not in s:s=s.replace('.setcpu "6502"','.setcpu "6502"\n.include "render/geos/edit-certificate.inc"',1)
 main.write_text(s)
 # ExistingAUX op6, unchanged source-reader normal API and no extraasset.
 target=project/'src/render/geos/checkpoint/rekey.s';shutil.copy2(ROOT/'src/render/geos/semantic-refresh-candidate/rekey.s',target)
 entry=project/'src/overlays/aux.s';s=entry.read_text();needle='    cmp #A_LAYOUT_CONTEXT';assert s.count(needle)==1;s=s.replace(needle,'    cmp #6\n    jeq se_gsr_refresh\n'+needle,1);s+='\n.import se_gsr_refresh\n';entry.write_text(s)
 pub=project/'src/render/geos/checkpoint/publish.inc';s=pub.read_text();needle='@invalidate_previous:\n lda #0\n jsr gsc_valid_write';assert s.count(needle)==1;s=s.replace(needle,'@invalidate_previous:\n lda se_v_top\n ora se_v_top+1\n ora se_v_top+2\n bne @skip\n lda #0\n jsr gsc_valid_write',1);pub.write_text(s)
 if certificate:
  cert=ROOT/'src/render/geos/source-style-window-candidate'
  for name in ['source-line.s','source-inline.s','source-certificate.inc','source-certificate.s','certificate-consumer.s']:shutil.copy2(cert/name,project/'src/render/geos'/name)
  page=project/'src/render/geos/page.s';s=page.read_text();needle='    lda #8\n    sta PS\n    lda #GI_ID\n    ldx #GI_BEGIN\n';replacement='    lda #8\n    sta PS\n    lda SC_VALID\n    cmp #2\n    bne :+\n    lda #GP_LAYOUT_ID\n    ldx #SC_CONSUME\n    jmp request\n:\n    lda #GI_ID\n    ldx #GI_BEGIN\n';assert s.count(needle)==1;s=s.replace(needle,replacement,1).replace('.include "render/geos/source-line.inc"\n','.include "render/geos/source-line.inc"\n.include "render/geos/source-certificate.inc"\n',1);page.write_text(s)
 m=project/'Makefile';s=m.read_text();needle='AUX_CONTROL_OBJ = ';a=s.index(needle);b=s.index('\n',a);s=s[:b]+' build/aux-control/checkpoint-refresh.o'+s[b:];s+='''
# PRIVATE coherent publication refresh component, no canonical Make edits.
build/aux-control/checkpoint-refresh.o: src/render/geos/checkpoint/rekey.s build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D GSR_AUX=1 -I build/geos-prod -I src -o $@ $<
build/geos-prod/page.o: src/render/geos/checkpoint/publish.inc
''';
 if certificate:s+='''build/geos-prod/page.o: src/render/geos/source-certificate.inc
build/geos-prod/source-line.o: src/render/geos/source-certificate.inc src/render/geos/source-certificate.s src/render/geos/certificate-consumer.s
'''
 m.write_text(s)
 make('candidate','editor','build/supereditor.d81')
 report=json.loads((project/'build/editor-report.json').read_text());assets={n:dict(bytes=len((project/'build/overlays'/(n+'.seo')).read_bytes())-36,sha256=SHA(project/'build/overlays'/(n+'.seo')))for n in names};assert len(names)==48;assert assets['aux']['bytes']==3398 and assets['geospage']['bytes']==(4073 if certificate else 4059)
 changes={str(p.relative_to(project)):SHA(p)for p in [commands,main,entry,pub,target,m]}
 result=dict(status='built',project=str(project),baseline=str(base),certificate=certificate,control_sha256=controls,tool_sha256=tools,copy24_proof=proof,changed_files=changes,assets=assets,report=report,scope='Private copied coherent project only; actualpostpublicationAUX6 hook. No canonical/sharedbuild/newasset/state.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');(project/'PRIVATE_EXPERIMENT.json').write_text(json.dumps(dict(base=str(base),scope=result['scope']),indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--out',type=Path);p.add_argument('--no-certificate',action='store_true');a=p.parse_args();out=a.out or ROOT/'build/checkpoint-refresh-hook'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);r=build(out.resolve(),a.base.resolve(),not a.no_certificate);print('BUILT',r['project'],r['assets']['aux']['bytes'],r['assets']['geospage']['bytes'])
