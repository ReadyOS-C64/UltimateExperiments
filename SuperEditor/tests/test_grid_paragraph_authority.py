"""Actual C14/R14 SP2 literal-paragraph authority, no new typing worker yet."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,importlib.util,binascii
import test_geos_fold_editor as fold
import test_grid_modes as grid
from supermark_model import blocks
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/grid-prose-authority/20261025T190208381544Z/fixture'
def run(out):
 frozen=out/'fixture';shutil.copytree(BASE,frozen);spec=importlib.util.spec_from_file_location('paragraphbuild',ROOT/'src/render/grid/long-prose-candidate/build-authority.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf');identity=json.load(open(frozen/'freeze.json'))
 for n,image in seos.items():(frozen/'build/overlays'/(n+'.seo')).write_bytes(image);identity['assets'][n]=hashlib.sha256(image).hexdigest()
 (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];f=fold.Fixture(out,frozen,dll,True);cases=[]
 try:
  for width in(60,80):
   for tag,text in [('literal','Alpha '+('word '*100)+'ends.\rTail.'),('closed-fences',':::basic\r10 PRINT 1\r:::\r:::asm\rlda #1\r:::\rAlpha '+('word '*100)+'ends.\rTail.'),('unmatched-marker','Alpha '+('word '*60)+'*'+('word '*40)+'ends.\rTail.'),('late-escape','Alpha '+('word '*60)+'£'+('word '*40)+'ends.\rTail.'),('matched-inline','Alpha '+('word '*60)+'**bold**'+('word '*40)+'ends.\rTail.'),('nonalpha-first','#A '+('word '*100)+'ends.\rTail.'),('multiple','Alpha '+('word '*30)+'\rBeta '+('word '*40)+'\rGamma '+('word '*30)+'ends.\rTail.')]:
    data=grid.native_text(text.replace('£','\\'));at=data.find(grid.native_text('word'))+width*2+1;f.source(data);f.command(97 if width==60 else 98);f.position(at);f.render();f.finish_style();bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));cert=f.reu()[bank*65536+0x1600:bank*65536+0x1680];assert cert[:4]==b'SP\2\xa5'and binascii.crc_hqx(cert[:126],65535)==int.from_bytes(cert[126:],'little'),(width,tag,cert.hex());assert cert[4:37]==f.read(f.s['se_st_descriptor'],33)and cert[37:39]==f.read(f.s['se_doc_epoch'],2)and cert[39:41]==f.read(f.s['se_st_generation'],2)
    starts=[int.from_bytes(cert[42+i*3:45+i*3],'little')for i in range(22)];events=blocks(data);want=0
    for i,p in enumerate(starts):
     event=next((e for e in events if e['start']<=p<e['end']),None)
     if event and event['kind']==0:
      line=data[event['start']:event['end']];first=line[0]&127
      if 65<=first<=90 and not any(c in line for c in b'*@\\'):want|=1<<i
    actual=int.from_bytes(cert[111:114],'little');assert actual==want,(width,tag,bin(actual),bin(want));(bits,attrs),_,_,_=grid.expected(f,data);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.merged()==data and f.read(0xc600,1024)==f.shim
    cases.append(dict(width=width,tag=tag,rows=actual,continuation_rows=sum(1 for i,p in enumerate(starts)if actual&(1<<i)and all(e['start']!=p for e in events))));print('PASS',cases[-1],flush=True)
  result=dict(status='passed',budget=budget,cases=cases,scope='Private no-inline/alphabetic paragraph authority only; oldSP1consumer must decline version2.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/grid-paragraph-authority'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
