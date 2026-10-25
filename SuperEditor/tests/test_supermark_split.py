"""Code/state object separation, exact default bytes and actual6510 fixtures.

Builds only build/supermark-split. Existing1475-case parser gate is copied into
two private roots, so none of its outputs alter shared editor/probe artifacts.
"""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from supermark_probe import SuperMark,petscii
from supermark_model import blocks,inline,lex
OUT=ROOT/'build/supermark-split'
BASE_SHA='fecd9b7525dcaad62e58f5ea5c652c462e7f40d8bd4f60267fef4c7a22fd9899'
FUNCTIONS={'block':{'se_sm_init','se_sm_at_line','se_sm_feed','se_sm_finish'},
           'inline':{'se_si_init','se_si_at_body','se_si_feed','se_si_finish'}}
SIZES={'block':(1076,79),'inline':(911,68)}

def run(args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def names(obj,kind):
 text=run(['od65','--dump-'+kind,obj],capture_output=True,text=True).stdout
 return set(re.findall(r'Name:\s+"([^"]+)"',text))
def segments(obj):
 text=run(['od65','--dump-segments',obj],capture_output=True,text=True).stdout
 return {n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)"\s+Flags:[^\n]*\n\s+Size:\s+(\d+)',text) if int(v)}

def build(variant):
 root=OUT/(variant+'-root');out=root/'build/supermark';out.mkdir(parents=True,exist_ok=True)
 objects=[];audit={}
 for n in ['block','inline']:
  for flag in ([None] if variant=='default' else ['SE_SM_STATE_ONLY','SE_SM_CODE_ONLY']):
   obj=out/(n+('-'+flag if flag else '')+'.o');args=['ca65','-g','-I',ROOT/'src','-o',obj]
   if flag:args+=['-D',flag+'=1']
   run(args+[ROOT/'src/supermark'/f'{n}.s']);objects.append(obj)
   exports=names(obj,'exports');imports=names(obj,'imports');parts=segments(obj)
   code,state=SIZES[n];codepart='SM_BLOCK' if n=='block' else 'SM_INLINE'
   if flag=='SE_SM_STATE_ONLY':
    assert parts=={'SM_STATE':state},(obj,parts)
    assert not exports&FUNCTIONS[n],(obj,exports&FUNCTIONS[n])
   elif flag=='SE_SM_CODE_ONLY':
    assert parts=={codepart:code},(obj,parts)
    assert exports==FUNCTIONS[n],(obj,exports)
    assert all(x.startswith(('se_sm_','sm_')) if n=='block' else x.startswith(('se_si_','si_')) for x in imports)
   else:assert parts=={'SM_STATE':state,codepart:code}
   audit[obj.name]=dict(segments=parts,exports=sorted(exports),imports=sorted(imports))
 obj=out/'lexer.o';run(['ca65','-g','-I',ROOT/'src','-o',obj,ROOT/'src/supermark/lexer.s']);objects.append(obj)
 run(['ld65','-C',ROOT/'probes/supermark/probe.cfg','-o',out/'probe.bin','-m',out/'probe.map','-Ln',out/'probe.lbl',*objects])
 assert digest(out/'probe.bin')==BASE_SHA,(variant,digest(out/'probe.bin'))
 # Copy the unchanged full fixture driver into an isolated self-contained root.
 files=[* (ROOT/'src/supermark').glob('*'),* (ROOT/'probes/supermark').glob('*'),ROOT/'tests/test_supermark.py']
 files += [ROOT/'tools'/n for n in ['peddle.py','supermark_probe.py','supermark_model.py']]
 for src in files:
  if src.is_file():
   dest=root/src.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
 for src in [ROOT/'build/peddle-source.json',* (ROOT/'build').glob('libse_peddle.*')]:
  if src.exists():shutil.copyfile(src,root/'build'/src.name)
 (out/'object-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 return root,objects

class Driver(SuperMark):
 def __init__(self,out,relocated=False):
  self.symbols={p[2].lstrip('.'):int(p[1],16) for line in (out/'probe.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
  self.m=Machine();self.instructions={};self.peak={}
  if relocated:
   self.m.load(0xB000,(out/'block-inline.bin').read_bytes());self.m.load(0xA000,(out/'lexer.bin').read_bytes())
  else:self.m.load(0x8000,(out/'probe.bin').read_bytes())
  self.shim=bytes((i*73+29)&255 for i in range(1024));self.m.load(0xC600,self.shim)

def relocated(objects,default_out):
 out=OUT/'relocated';out.mkdir(parents=True,exist_ok=True)
 cfg=f'''MEMORY {{
 BLOCK:file="{out/'block-inline.bin'}",start=$B000,size=$1000,type=ro,fill=yes;
 LEXER:file="{out/'lexer.bin'}",start=$A000,size=$1000,type=ro,fill=yes;
 STATE:file="",start=$8D00,size=$600,type=rw;
}}
SEGMENTS {{
 SM_BLOCK:load=BLOCK,type=ro;
 SM_INLINE:load=BLOCK,type=ro;
 SM_LEXER:load=LEXER,type=ro;
 SM_STATE:load=STATE,type=bss,define=yes;
}}
'''
 (out/'probe.cfg').write_text(cfg)
 run(['ld65','-C',out/'probe.cfg','-o',out/'unused.bin','-m',out/'probe.map','-Ln',out/'probe.lbl',*objects])
 p=Driver(default_out);q=Driver(out,True);comparisons=0
 try:
  assert q.symbols['se_sm_state']==0x8D00 and q.symbols['se_si_state']==0x8D4F
  for address,size in [(0,256),(0x4000,0x4000),(0x8000,0xD00),(0x8DCF,0xD31),(0xC000,0x1000)]:
   # Keep one guard outside all relocated contexts/code, including whole shim.
   data=bytes((i*41+29)&255 for i in range(size));q.m.load(address,data)
  guards=[(a,bytes(q.m.read(a+i) for i in range(n))) for a,n in [(0,256),(0x4000,0x4000),(0x8000,0xD00),(0x8DCF,0xD31),(0xC000,0x1000)]]
  q.shim=bytes(q.m.read(0xC600+i) for i in range(1024))
  texts=['','# Heading\n*one* **two** ***both*** @@code@@\n',':::basic\n10 PRINT "CASE"\n:::\n',
   ':::region A\n:::asm\nlabel: lda #$12\n:::\n:::end\n',
   '**outer *inner* outer** £*literal£* @@*literal*@@\n','*unclosed\n@@unclosed\n',
   '£# literal\n£:::asm\n  £- item\n123£. item\n',('1'*300)+'. body *emphasis*\n']
  texts += [(':'*n)+'asm\nlda #0\n'+(':'*n)+'\n' for n in range(3,17)]
  texts += [':::region x\n'*18+':::end\n'*18]
  for text in texts:
   data=petscii(text)
   for origin in [0,0xFFFA,0x10000]:
    chunks=[data[i:i+7] for i in range(0,len(data),7)] or [b'']
    for name,wanted in [('blocks',blocks(data,origin)),('inline',inline(data,origin))]:
     a=getattr(p,name)(data,origin,chunks);b=getattr(q,name)(data,origin,chunks)
     assert a==b==wanted,(name,origin,text,a,b,wanted);comparisons+=1
    for language in (0,1,2):
     a=p.lex(data,language,origin,chunks);b=q.lex(data,language,origin,chunks)
     assert a==b==lex(data,language,origin),(language,origin,text);comparisons+=1
  for a,data in guards:assert bytes(q.m.read(a+i) for i in range(len(data)))==data,hex(a)
  return dict(comparisons=comparisons,state_base=0x8D00,block_code=0xB000,inline_code=q.symbols['se_si_init'],new_zero_page_bytes=0,shim_bytes=1024)
 finally:p.close();q.close()

def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').unlink(missing_ok=True)
 default,default_objects=build('default');split,split_objects=build('split')
 results={};env=os.environ.copy()
 env['PEDDLE_ROOT']=json.loads((ROOT/'build/peddle-source.json').read_text())['source']
 for name,root in [('default',default),('split',split)]:
  done=subprocess.run([sys.executable,str(root/'tests/test_supermark.py')],env=env,capture_output=True,text=True)
  (root/'fixture.log').write_text(done.stdout+done.stderr)
  assert done.returncode==0,(name,done.stdout[-2000:],done.stderr[-2000:])
  result=json.loads((root/'build/supermark/result.json').read_text());assert result['status']=='passed' and result['fixtures']==1475
  results[name]={k:result[k] for k in ['status','fixtures','independent_oracle_comparisons','fresh_cpu_context_roundtrips','module_bytes','probe_sha256']}
 for n in ['block','inline']:
  p=OUT/(n+'-bad.o');done=subprocess.run(['ca65','-I',str(ROOT/'src'),'-D','SE_SM_STATE_ONLY=1','-D','SE_SM_CODE_ONLY=1','-o',str(p),str(ROOT/'src/supermark'/f'{n}.s')],capture_output=True,text=True)
  assert done.returncode and 'choose one SuperMark split flag' in done.stderr
 result=dict(status='passed',default_byte_identity=BASE_SHA,split_byte_identity=BASE_SHA,
  default_fixture=results['default'],split_fixture=results['split'],relocated=relocated(split_objects,default/'build/supermark'),
  resident_state_bytes=147,block_code_bytes=1076,inline_code_bytes=911,invalid_combined_flags_refused=True,
  source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'src/supermark/block.s',ROOT/'src/supermark/inline.s',Path(__file__)]},
  scope='Isolated code/state link and actual6510 parser fixtures; no shared editor build or native integration')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
