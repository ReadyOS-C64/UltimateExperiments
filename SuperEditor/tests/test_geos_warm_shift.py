"""Private general two-byte/remainder shift; exact registered62 source input."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,subprocess,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_shift8_candidate as old
D=ROOT/'src/render/geos/warm-shift-probe'
BASE=ROOT/'build/cache-rebase-committed/20261026T224637147761Z/fixture'
def build_component(out,base,variant,is_wide):
 assert is_wide;out.mkdir(parents=True);symbols=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'loans.s').write_text(f'.exportzp gt_base,gt_bitmap\ngt_base=${symbols["text_ptr"]:02x}\ngt_bitmap=${symbols["screen_ptr"]:02x}\n')
 source=D/('wide-before.s'if variant=='before'else'wide.s');cfg=out/'component.cfg';cfg.write_text('MEMORY {IMAGE:file=%O,start=$A000,size=$1000,type=ro;} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}')
 include=out/'include/render/geos/style-typing';include.mkdir(parents=True);shutil.copy2(D/'wide.inc',include/'wide.inc');objects=[]
 for tag,path in [('wide',source),('loans',out/'loans.s')]:
  o=out/(tag+'.o');subprocess.run(['ca65','-g','-I',out/'include','-o',o,path],check=True);objects.append(o)
 subprocess.run(['ld65','-C',cfg,'-o',out/'component.bin','-Ln',out/'component.lbl','-m',out/'component.map',*objects],check=True)
 s={t[2].lstrip('.'):int(t[1],16)for l in(out/'component.lbl').read_text().splitlines()if len(t:=l.split())==3 and t[0]=='al'};return(out/'component.bin').read_bytes(),s

def run(out,base):
 out.mkdir(parents=True);old.build_component=build_component;variants={}
 for variant in('before','after'):
  d=out/variant;d.mkdir();variants[variant]=old.component(d,base,variant)
 diff=old.bounds.compare(variants['before'],variants['after']);result=dict(status='PASS',fixture=str(base),component=diff,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(D/'wide-before.s',D/'wide.s',D/'wide.inc')});(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/geos-warm-shift'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve())
