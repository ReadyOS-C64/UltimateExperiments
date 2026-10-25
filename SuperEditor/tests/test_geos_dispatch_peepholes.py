"""Private before/after dispatch ABI equivalence; child endpoints explicitly stubbed."""
from pathlib import Path
import itertools,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
O=ROOT/'build/crc-inline/dispatch-fit'
def labels(p):return {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',p.read_text())}
s=json.loads((O/'editor-report.json').read_text())['symbols'];prg=(O/'editor.prg').read_bytes()
endpoints=['se_editor_render_ui','se_editor_reload','se_editor_reveal','se_editor_render_failed','se_editor_error','se_fs_end']

def execute(name,entry,request,result,error,owner,job,operation):
 lab=labels(O/(name+'.lbl'));m=Machine()
 try:
  m.load(int.from_bytes(prg[:2],'little'),prg[2:]);m.load(0x7000,(O/(name+'.bin')).read_bytes());m.load(0xC600,bytes((i*73+29)&255 for i in range(1024)))
  for i,n in enumerate(endpoints):m.load(s[n],bytes([0xEE,(0x8000+i)&255,(0x8000+i)>>8,0x60]))
  # Child overlay ABI: return selectedA/C, deliberately clobberX/Y. The test
  # compares resident control flow; it is not parser/render acceptance.
  m.load(s['se_overlay_call'],bytes([0xA9,result,0xA2,0xA7,0xA0,0xB6,0x38 if error else 0x18,0x60]))
  m.write(s['se_f_owner'],owner);m.write(s['se_e_job'],job);m.load(0x9134,bytes([1,request,operation])+bytes(65));m.load(0x912C,bytes(2))
  reg,count=m.call(lab[entry]);ram=bytes(m.read(i) for i in range(65536));return reg,count,ram
 finally:m.close()

cases=[]
for entry in ['se_geos_render','se_geos_navigate','se_geos_service']:
 requests=[20,24,25,21,22,23] if entry=='se_geos_service' else [21]
 for request in requests:
  for result,error,owner,job,operation in itertools.product([0,1], [0,1],[0,1,4],[11,12],[0,1]):
   if error:result=0x17
   cases.append((entry,request,result,error,owner,job,operation))
# C21's actual unseen-caret signal is A2; workers/C22 promise only A0/1.
for job in [11,12]:cases.append(('se_geos_service',21,2,0,4,job,1))
results=[]
for case in cases:
 a,na,ra=execute('before',*case);b,nb,rb=execute('after',*case)
 assert (a.a,a.x,a.y,a.p,a.sp,a.pc)==(b.a,b.x,b.y,b.p,b.sp,b.pc),(case,'register',a,b)
 aa=bytearray(ra);bb=bytearray(rb)
 for start,n in [(0x100,256),(0x7000,4096)]:aa[start:start+n]=bytes(n);bb[start:start+n]=bytes(n)
 assert aa==bb,(case,'RAM',[hex(i) for i,(x,y) in enumerate(zip(aa,bb)) if x!=y][:10])
 results.append(dict(case=case,before_instructions=na,after_instructions=nb))
r=dict(status='passed',cases=len(results),before_bytes=len((O/'before.bin').read_bytes()),after_bytes=len((O/'after.bin').read_bytes()),resident_byte_saving=8,registers_identical=True,RAM_identical_except_code_stack=True,results=results,scope='Actual assembled resident dispatch with explicit overlay/endpoint stubs; full sealed editor acceptance remains parent gate')
(O/'equivalence-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='results'},indent=2))
