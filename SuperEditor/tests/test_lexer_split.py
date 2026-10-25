"""Shared native BASIC/assembler lexer: exact split and relocated CPU proof.

Only build/lexer-split is written. No editor make, root integration or VICE.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,random,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from supermark_probe import SuperMark,petscii
from supermark_model import lex
spec=importlib.util.spec_from_file_location('split_fixture_helpers',ROOT/'tests/test_supermark_split.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
OUT=ROOT/'build/lexer-split';helper.OUT=OUT
FUNCTIONS={'se_sl_init','se_sl_feed','se_sl_finish','se_sl_next'}

def run(args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 default,_=helper.build('default')
 split=OUT/'split-root';shutil.copytree(default,split,dirs_exist_ok=True)
 out=split/'build/supermark';objects=[out/'block.o',out/'inline.o'];audit={}
 for flag in ['SE_SM_STATE_ONLY','SE_SM_CODE_ONLY']:
  obj=out/('lexer-'+flag+'.o');run(['ca65','-g','-I',ROOT/'src','-D',flag+'=1','-o',obj,ROOT/'src/supermark/lexer.s']);objects.append(obj)
  parts=helper.segments(obj);exports=helper.names(obj,'exports');imports=helper.names(obj,'imports')
  if flag=='SE_SM_STATE_ONLY':assert parts=={'SM_STATE':60} and not exports&FUNCTIONS
  else:assert parts=={'SM_LEXER':2704} and exports==FUNCTIONS
  audit[flag]=dict(segments=parts,exports=sorted(exports),imports=sorted(imports))
 assert set(audit['SE_SM_CODE_ONLY']['imports'])<=set(audit['SE_SM_STATE_ONLY']['exports'])
 assert all(n.startswith(('se_sl_','sl_')) for n in audit['SE_SM_CODE_ONLY']['imports'])
 run(['ld65','-C',ROOT/'probes/supermark/probe.cfg','-o',out/'probe.bin','-m',out/'probe.map','-Ln',out/'probe.lbl',*objects])
 assert digest(out/'probe.bin')==helper.BASE_SHA==digest(default/'build/supermark/probe.bin')
 bad=subprocess.run(['ca65','-I',str(ROOT/'src'),'-D','SE_SM_STATE_ONLY=1','-D','SE_SM_CODE_ONLY=1','-o',str(OUT/'bad.o'),str(ROOT/'src/supermark/lexer.s')],capture_output=True,text=True)
 assert bad.returncode and 'choose one SuperMark split flag' in bad.stderr
 (OUT/'object-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 return default,split,objects[-2:]

class Lexer(SuperMark):
 def __init__(self,out):
  self.symbols={p[2].lstrip('.'):int(p[1],16) for line in (out/'probe.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
  self.m=Machine();self.m.load(0xB000,(out/'lexer.bin').read_bytes());self.instructions={};self.peak={}
  self.shim=bytes((i*73+29)&255 for i in range(1024));self.m.load(0xC600,self.shim)
 def state(self):return bytes(self.m.read(self.symbols['se_sl_state']+i) for i in range(60))

def relocated(objects,default_out):
 out=OUT/'relocated';out.mkdir(parents=True,exist_ok=True)
 (out/'probe.cfg').write_text(f'''MEMORY {{
 LEXER:file="{out/'lexer.bin'}",start=$B000,size=$1000,type=ro,fill=yes;
 STATE:file="",start=$8D00,size=$003C,type=rw;
}}
SEGMENTS {{ SM_LEXER:load=LEXER,type=ro; SM_STATE:load=STATE,type=bss,define=yes; }}
''')
 run(['ld65','-C',out/'probe.cfg','-o',out/'unused.bin','-m',out/'probe.map','-Ln',out/'probe.lbl',*objects])
 p=helper.Driver(default_out);q=Lexer(out);comparisons=transfers=0
 try:
  assert q.symbols['se_sl_state']==0x8D00 and q.symbols['se_sl_state_size']==60
  ranges=[(0,256),(0x4000,0x1000),(0x6000,0x2000),(0x8000,0xD00),(0x8D3C,0x12C4),(0xB000,0x1000),(0xC000,0x1000)]
  for a,n in ranges:
   if a!=0xB000:q.m.load(a,bytes((i*43+17)&255 for i in range(n)))
  guards=[(a,bytes(q.m.read(a+i) for i in range(n))) for a,n in ranges]
  q.shim=bytes(q.m.read(0xC600+i) for i in range(1024))
  texts=['','10PRINT"Mixed CASE":GOTO10\n20REM PRINT:DATA"X:Y"\n',
   '10DATA"A:B",GOTO,123:PRINT.5,3.14E-2,5.\n20IFA1=1THENPRINTLEFT$("X",1)\n',
   '10pR"shifted abbreviation literal"\n20INPUT#1,A$:PRINT#2,A$\n',
   'label: lda #$ff\n@local: .byte %1010,123\n.segment "CODE" ;comment\n',
   " .proc main\n lda #'x'\n rts\n .endproc\n",'A'*300+': lda #1\n',
   '10PRINT"unterminated\n20PRINT"next"\n',' lda "unterminated\n; comment\n']
  vectors=[petscii(t) for t in texts]+[bytes(range(256))]
  rng=random.Random(0x1E6510)
  atoms=['PRINT','GOTO','REM','DATA','lda','rts','.byte','.include','label:', '@local:', '$ff','%1010','123','.5','3.1E-2','"CASE:X"',"'x'",';comment']
  vectors += [petscii(' '.join(rng.choice(atoms) for _ in range(24))+'\n') for _ in range(35)]
  for data in vectors:
   source=bytes(data);q.m.load(0x5000,source)
   for language in (0,1,2):
    for origin in (0,0xFFFA,0x10000):
     chunks=[data[i:i+7] for i in range(0,len(data),7)] or [b'']
     a=p.lex(data,language,origin,chunks);b=q.lex(data,language,origin,chunks)
     assert a==b==lex(data,language,origin),(language,origin,data,a,b)
     assert bytes(q.m.read(0x5000+i) for i in range(len(source)))==source
     comparisons+=1
  # A fresh CPU receives only the60-byte context at every possible cut, including
  # pending token state. Code-only objects retain no hidden pointers or queue.
  for language,data in [(1,petscii('10PRINT"X":DATA"A:B",PRINT:GOTO10\n')),
                         (2,petscii('loop: lda #$12 ;comment\n.segment "CODE"\n'))]:
   for cut in range(1,len(data)):
    a=Lexer(out);b=None;spans=[]
    try:
     a.call('se_sl_init',language)
     def drain(machine):
      while machine.get('se_sl_count'):
       machine.call('se_sl_next');spans.append(tuple(machine.get('se_sl_'+n,w) for n,w in [('start',3),('end',3),('style',1)]))
     for byte in data[:cut]:a.call('se_sl_feed',byte);drain(a)
     b=Lexer(out);b.m.load(b.symbols['se_sl_state'],a.state())
     for byte in data[cut:]:b.call('se_sl_feed',byte);drain(b)
     b.call('se_sl_finish');drain(b);assert spans==lex(data,language);transfers+=1
    finally:a.close();b.close() if b else None
  # Queue backpressure survives relocation and copying with both slots unread.
  q.call('se_sl_init',2)
  for byte in petscii('lda#'):assert not q.call('se_sl_feed',byte).p&1
  assert q.get('se_sl_count')==2;state=q.state();position=q.get('se_sl_pos',3)
  r=q.call('se_sl_feed',ord('9'));assert r.p&1 and r.a==1 and q.get('se_sl_pos',3)==position
  r=q.call('se_sl_finish');assert r.p&1 and r.a==1
  # The API stores the rejected input byte but cannot overwrite queued spans or
  # advance source. Compare the actual queue explicitly, not that scratch byte.
  qa=q.symbols['sl_queue'];saved=state[qa-q.symbols['se_sl_state']:qa-q.symbols['se_sl_state']+14]
  assert bytes(q.m.read(qa+i) for i in range(14))==saved
  for a,data in guards:assert bytes(q.m.read(a+i) for i in range(len(data)))==data,hex(a)
  return dict(comparisons=comparisons,fresh_context_transfers=transfers,state_base=0x8D00,code_base=0xB000,source_guard=True,queue_backpressure=True,guard_bytes=sum(len(b) for _,b in guards),shim_bytes=1024)
 finally:p.close();q.close()

def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').unlink(missing_ok=True)
 default,split,objects=build();results={};env=os.environ.copy()
 env['PEDDLE_ROOT']=json.loads((ROOT/'build/peddle-source.json').read_text())['source']
 for name,root in [('default',default),('split',split)]:
  done=subprocess.run([sys.executable,str(root/'tests/test_supermark.py')],env=env,capture_output=True,text=True)
  (root/'fixture.log').write_text(done.stdout+done.stderr)
  assert done.returncode==0,(name,done.stdout[-1000:],done.stderr[-2000:])
  r=json.loads((root/'build/supermark/result.json').read_text());assert r['status']=='passed' and r['fixtures']==1475
  results[name]={k:r[k] for k in ['status','fixtures','independent_oracle_comparisons','fresh_cpu_context_roundtrips','probe_sha256']}
 result=dict(status='passed',default_byte_identity=helper.BASE_SHA,split_byte_identity=helper.BASE_SHA,fixtures=results,
  relocated=relocated(objects,default/'build/supermark'),code_bytes=2704,state_bytes=60,zero_page_bytes=0,
  functions=sorted(FUNCTIONS),external_code_dependencies=[],combined_flags_refused=True,
  source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'src/supermark/lexer.s',ROOT/'tests/test_lexer_split.py']},
  scope='Isolated shared BASIC/assembler lexer split; no production overlay/editor/root placement or native claim')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
