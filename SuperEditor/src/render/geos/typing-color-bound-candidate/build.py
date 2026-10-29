"""Private read-only bound + provisional shift/publish component, no product edits."""
from pathlib import Path
import sys,subprocess,json,re
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);objects=[];sizes={}
 def run(a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 for name,path in [('bound',D/'bound.s'),('wide',D/'wide-provisional.s'),('loans',D/'loans.s'),('transport',ROOT/'src/render/geos/typing/transfer.s')]:
  p=out/(name+'.o');run(['ca65','-g','-I',D,'-I',ROOT/'src','-o',p,path]);objects.append(p);t=subprocess.check_output(['od65','--dump-segments',p],text=True);sizes[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',t,re.S)};assert all(sizes[name].get(n,0)==0 for n in['BSS','ZEROPAGE','DATA'])
 run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);run(['ca65','-g','-o',out/'aliases.o',out/'aliases.s']);run(['ld65','-C',D/'probe.cfg','-o',out/'probe.bin','-Ln',out/'probe.lbl','-m',out/'probe.map',*objects,out/'aliases.o']);ls={p[2].lstrip('.'):int(p[1],16)for l in(out/'probe.lbl').read_text().splitlines()if(p:=l.split())and p[0]=='al'};budget=dict(segments=sizes,component=len((out/'probe.bin').read_bytes()),bound=sum(sizes['bound'].values()),provisional_with_publisher=sum(sizes['wide'].values()),canonical_wide=1113,current_C32_raw=3521,stamp_limit=4064,projected_C32_raw=3521-1113+sum(sizes['wide'].values())+sum(sizes['bound'].values()),scope='Component only; existing C6 rejects these mixed rows. Integrating requires C6 defer-neighbor proof plus prepublication transaction reorder. No newBSS/ZP.');(out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n');return ls,(out/'probe.bin').read_bytes(),budget
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[2])
