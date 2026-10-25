"""Actual bounded pure6510 streaming BASIC overlap repair; independent unchanged oracle."""
from pathlib import Path
from datetime import datetime,timezone
import json,random,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools')]
from peddle import Machine
from supermark_model import lex,BASIC
from supermark_probe import petscii

def run(out):
 out.mkdir(parents=True,exist_ok=True);source=ROOT/'src/supermark/lexer-overlap-candidate/lexer.s';obj=out/'lexer.o';subprocess.run(['ca65','-g','-I',str(ROOT/'src'),'-o',str(obj),str(source)],check=True);subprocess.run(['ld65','-C',str(source.with_name('lexer.cfg')),'-o',str(out/'lexer.bin'),'-Ln',str(out/'lexer.lbl'),str(obj)],check=True)
 symbols={p[2].lstrip('.'):int(p[1],16)for line in(out/'lexer.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'};image=(out/'lexer.bin').read_bytes();m=Machine();m.load(0xA000,image);m.load(0xc600,bytes((i*73+29)&255 for i in range(1024)));guard=bytes(m.read(i)for i in range(65536));cases=0;sourcebytes=0;maxqueue=0;peak=0
 def get(n,w=1):return int.from_bytes(bytes(m.read(symbols[n]+i)for i in range(w)),'little')
 def call(n,a=0):
  nonlocal peak
  r,c=m.call(symbols[n],a=a);peak=max(peak,c);assert not r.p&1,(n,r.a);return r
 def check(data,lang=1,start=0):
  nonlocal cases,sourcebytes,maxqueue
  call('se_sl_init',lang);m.load(symbols['se_sl_pos'],start.to_bytes(3,'little'));events=[]
  def drain():
   nonlocal maxqueue
   maxqueue=max(maxqueue,get('se_sl_count'));assert get('se_sl_count')<=2,('queue overflow',data,get('se_sl_count'))
   while get('se_sl_count'):
    call('se_sl_next');events.append(tuple(get('se_sl_'+n,w)for n,w in [('start',3),('end',3),('style',1)]))
  for byte in data:call('se_sl_feed',byte);drain()
  call('se_sl_finish');drain();expected=lex(data,lang,start);assert events==expected,(data,lang,start,events,expected);cases+=1;sourcebytes+=len(data)
 try:
  for text in ['SECOND','Second code row','CON','CONT','CONX','COS','RESTOR','RESTORE','RESTOX','PRINTX','XPRINT','aON','ON','10 SECOND+PRINT"HI"','REM SECOND','DATA SECOND,"CONT":PRINT SECOND','SECOND\nCONT\nRESTOR\n']:
   check(petscii(text));check(petscii(text),1,0xfffa)
  # Every keyword and every strict prefix, with all byte-level continuations,
  # covers overlap disambiguation, CR separators, native aliases and queue2.
  prefixes=sorted({word[:i]for word in BASIC for i in range(1,len(word)+1)})
  for prefix in prefixes:
   check(petscii(prefix))
   for suffix in (b'X',b' ',b'\r',b'+',b'"Q"',b'123',b':PRINT'):
    check(petscii(prefix)+suffix)
  for left in BASIC:
   for right in BASIC:check(petscii(left+right))
  for prefix in prefixes:
   for byte in range(256):check(petscii(prefix)+bytes([byte]))
  rng=random.Random(0xB451C);alphabet=petscii('CONTEXTORIPFSAD_@09.$:()+-"\n')
  for _ in range(1500):check(bytes(rng.choice(alphabet)for _ in range(rng.randrange(80))),1,0xfff0 if _%2 else 0)
  for language in(0,2):
   for data in [petscii('start: lda #$2A ; comment\nnext: sta $D020\n'),bytes(range(256)),petscii('"quote" REM DATA CONT PRINTX')]:check(data,language,0x1fff0)
  roundtrips=0
  for text in ['SECOND:PRINTX', 'RESTOR+XPRINT', 'CONT COS CON\nSECOND', 'DATA SECOND,"CONT":PRINT SECOND', 'REM SECOND\nPRINTX']:
   data=petscii(text)
   for cut in range(1,len(data)):
    q=Machine();q.load(0xa000,image);events=[]
    def qcall(name,a=0):
     r,c=q.call(symbols[name],a=a);assert not r.p&1;return r
    def qget(name,w=1):return int.from_bytes(bytes(q.read(symbols[name]+i)for i in range(w)),'little')
    def qdrain():
     while qget('se_sl_count'):
      qcall('se_sl_next');events.append(tuple(qget('se_sl_'+n,w)for n,w in [('start',3),('end',3),('style',1)]))
    qcall('se_sl_init',1);q.load(symbols['se_sl_pos'],(0xfffa).to_bytes(3,'little'))
    for byte in data[:cut]:qcall('se_sl_feed',byte);qdrain()
    state=bytes(q.read(0x8d00+i)for i in range(60));q.close();q=Machine();q.load(0xa000,image);q.load(0x8d00,state)
    for byte in data[cut:]:qcall('se_sl_feed',byte);qdrain()
    qcall('se_sl_finish');qdrain();assert events==lex(data,1,0xfffa),(text,cut,events);q.close();roundtrips+=1
  call('se_sl_init',1)
  for byte in petscii('RESTOR'):call('se_sl_feed',byte)
  call('se_sl_feed',ord('+'));assert get('se_sl_count')==2
  for name in ['se_sl_feed','se_sl_finish']:
   before=bytearray(m.read(0x8d00+i)for i in range(60));r,c=m.call(symbols[name],a=ord('X'));after=bytearray(m.read(0x8d00+i)for i in range(60))
   # Existing feed records its byte before checking backpressure; only that
   # scratch byte may change. Position/unread queue/count/other state cannot.
   after[symbols['sl_byte']-0x8d00]=before[symbols['sl_byte']-0x8d00]
   assert r.p&1 and after==before,(name,'backpressure')
  after=bytes(m.read(i)for i in range(65536));wanted=bytearray(guard);wanted[0x8d00:0x8d3c]=after[0x8d00:0x8d3c];wanted[0x100:0x200]=after[0x100:0x200];assert after==wanted,('wholeRAMguard',next(hex(i)for i,(a,b)in enumerate(zip(after,wanted))if a!=b))
  result=dict(status='passed',cases=cases,source_bytes=sourcebytes,lexer_bytes=len(image),delta=len(image)-2704,phase_state60=60,fresh_CPU_roundtrips=roundtrips,newBSS=0,newZP=0,max_queue=maxqueue,peak_instructions_per_call=peak,wholeRAMguard=65536,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Private actual purelexer only; host model unchanged. No production promotion/C25/C15/C31 packaging/native claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result);return result
 finally:m.close()
if __name__=='__main__':run(ROOT/'build/lexer-overlap-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
