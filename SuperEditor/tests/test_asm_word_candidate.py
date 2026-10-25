"""Private ASM indexed table whole-word match; BASIC prefix behavior preserved."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools')]
from peddle import Machine
from supermark_model import lex,ASM,DIRECTIVES,BASIC
from supermark_probe import petscii
SOURCE=ROOT/'src/supermark/asm-word-candidate/lexer.s'
def compile(out,source):
 out.mkdir(parents=True,exist_ok=True);subprocess.run(['ca65','-g','-I',ROOT/'src','-o',out/'lexer.o',source],check=True);subprocess.run(['ld65','-C',SOURCE.with_name('lexer.cfg'),'-o',out/'lexer.bin','-Ln',out/'lexer.lbl',out/'lexer.o'],check=True);s={p[2].lstrip('.'):int(p[1],16)for line in(out/'lexer.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'};return(out/'lexer.bin').read_bytes(),s
def events(image,s,data,lang,start=0):
 m=Machine();m.load(0xa000,image);m.load(0xc600,bytes((i*73+29)&255 for i in range(1024)));before=bytes(m.read(i)for i in range(65536));out=[];instructions=0
 def call(n,a=0):
  nonlocal instructions
  r,c=m.call(s[n],a=a);assert not r.p&1;(instructions:=instructions+c);return r
 def get(n,z=1):return int.from_bytes(bytes(m.read(s[n]+i)for i in range(z)),'little')
 def drain():
  assert get('se_sl_count')<=2
  while get('se_sl_count'):call('se_sl_next');out.append(tuple(get('se_sl_'+n,z)for n,z in [('start',3),('end',3),('style',1)]))
 try:
  call('se_sl_init',lang);m.load(s['se_sl_pos'],start.to_bytes(3,'little'))
  for b in data:call('se_sl_feed',b);drain()
  call('se_sl_finish');drain();after=bytes(m.read(i)for i in range(65536));wanted=bytearray(before);wanted[0x8d00:0x8d3c]=after[0x8d00:0x8d3c];wanted[0x100:0x200]=after[0x100:0x200];assert bytes(wanted)==after,'whole64KiBguard';return out,instructions
 finally:m.close()
def run(out):
 image,s=compile(out/'candidate',SOURCE);old,olds=compile(out/'baseline',ROOT/'src/supermark/lexer.s');cases=[];defects=[]
 for word in sorted(ASM):
  for suffix in ('','Q','X','0','_','QQQQQQQQQQQQQ',':',' ;comment',' "quoted"','+#1','\r'):
   for native in(False,True):
    text=word+suffix;data=petscii(text)if native else text.encode();start=0x1fffa if native else 0;actual,n=events(image,s,data,2,start);expected=lex(data,2,start);assert actual==expected,(data,actual,expected);cases.append(dict(language=2,text=text,native=native,start=start,instructions=n))
    if word=='LDA'and suffix=='Q'and not native:
     prior,_=events(old,olds,data,2,start);assert prior!=expected;defects.append(dict(data=data.hex(),baseline=prior,expected=expected,candidate=actual))
 for word in sorted(DIRECTIVES):
  for suffix in('','X','Q',':',' #$12',' "text"','\r'):
   data=petscii(word+suffix);actual,n=events(image,s,data,2,0xfffa);assert actual==lex(data,2,0xfffa),(data,actual,lex(data,2,0xfffa));cases.append(dict(language=2,text=word+suffix,instructions=n))
 for word in BASIC:
  for suffix in('','X','Q','ON','PRINT','0','_','+1','\r'):
   data=petscii(word+suffix);actual,n=events(image,s,data,1,0xfffa);prior,_=events(old,olds,data,1,0xfffa);assert actual==prior==lex(data,1,0xfffa),(data,actual,prior,lex(data,1,0xfffa));cases.append(dict(language=1,text=word+suffix,instructions=n))
 result=dict(status='passed',cases=len(cases),ASM_cases=sum(c['language']==2 for c in cases),BASIC_cases=sum(c['language']==1 for c in cases),old_bytes=len(old),new_bytes=len(image),delta=len(image)-len(old),defects=defects,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),scope='Actual6510 purelexer only; fullRAMguard percase, host model unchanged, everyBASICcase identical to oldlexer.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);return result
if __name__=='__main__':
 out=ROOT/'build/asm-word-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
