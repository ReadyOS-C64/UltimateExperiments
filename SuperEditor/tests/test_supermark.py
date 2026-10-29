"""Independent whole-input oracles against the emitted 6510 parser modules."""
import hashlib
import json
from pathlib import Path
import random
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from supermark_probe import SuperMark,petscii
from supermark_model import BASIC,ASM,DIRECTIVES,blocks,inline,lex
OUT=ROOT/'build/supermark'
result_path=OUT/'result.json';result_path.unlink(missing_ok=True)
rng=random.Random(0x534D6510)
p=SuperMark()
source_bytes=0;comparisons=0;fixtures=0;roundtrips=0

# Poison every unowned workspace and compare afterwards, including code/ZP/shim.
for address,length in [(0x0000,256),(0x0800,0x7800),(0xB000,0x1000),(p.symbols['__SM_STATE_RUN__']+p.symbols['__SM_STATE_SIZE__'],0x600-p.symbols['__SM_STATE_SIZE__'])]:
 p.m.load(address,bytes((i*37+11)&255 for i in range(length)))
protected=[(a,bytes(p.m.read(a+i) for i in range(n))) for a,n in [(0,256),(0x0800,0x7800),(0x8000,0x3000),(0xB000,0x1000),(p.symbols['__SM_STATE_RUN__']+p.symbols['__SM_STATE_SIZE__'],0x600-p.symbols['__SM_STATE_SIZE__']),(0xC600,1024)]]

def check(data,start=0,chunked=False):
 global source_bytes,comparisons,fixtures
 fixtures+=1;source_bytes+=len(data)
 chunks=[];i=0
 while i<len(data):
  n=rng.randrange(1,19);chunks.append(data[i:i+n]);i+=n
 if not chunks:chunks=[b'']
 actual=p.blocks(data,start,chunks if chunked else None);expected=blocks(data,start)
 assert actual==expected,('block',data,actual,expected)
 actual=p.inline(data,start,chunks if chunked else None);expected=inline(data,start)
 assert actual==expected,('inline',data,actual,expected)
 for language in (0,1,2):
  actual=p.lex(data,language,start,chunks if chunked else None);expected=lex(data,language,start)
  assert actual==expected,('lexer',language,data,actual,expected)
  for a,b,style in actual:assert start<=a<b<=start+len(data) and style in range(7,14)
  comparisons+=1
 comparisons+=2

try:
 native=[
 '# Project notes\nA **strong** idea, an *aside*, and @@lda #0@@ inline.\n- First task\n  - Smaller task\n1. Build the disk\n2. Open it in VICE\n:::basic\n10 PRINT "HELLO"\n20 GOTO 10\n:::\n:::region Drawing routine\n:::asm\nloop: lda #$00\n      sta $d020\n      rts\n:::\n:::end\nA literal £*asterisk£* and a price of £5.\n',
 '*unclosed\n**unclosed\n***unclosed\n@@unclosed\n£\n****literal****\n@@@@literal@@@@\n',
 '**outer *inner* outer** ***both*** *outer **inner** outer* @@£*no escapes£*@@\n',
 '£# escaped header\n£:::basic\n  £- escaped list\n123£. escaped list\nx £# ordinary pound\n££ currency\n£a literal\n£#no header\n£-no list\n£:no fence\n£####### no header\n   12£. no list\n',
 '\n#\n####### no\n## yes\n  ### no\n   - no\n      * yes\n        - no\n',
 ':::end\n:::region title with *inline* markup\n:::region Nested\n:::text\n:::region code, not region\n:::end\n:::\n:::end\n:::end\n',
 '10PRINT"HELLO":GOTO10\n20IFA1=1THENPRINTLEFT$("X",1)\n30REM PRINT:DATA"GOTO"\n40DATA"X:Y",PRINT:PRINT.5,3.14E-2,5.\n',
 '10pR"SHIFTED ABBREVIATION IS LITERAL"\n20PRINT"FULL WORDS"\n',
 'label: lda #$0f\n@local: .byte %1010,123\n  .segment "CODE" ; comment lda #1\n .endmacro\n unknown: UNKNOWN $G %2\n',
 '10PRINT"unterminated\n20PRINT"next"\n:::basic extra\nordinary\n:::\n',
 ]
 native += [(':'*n)+'basic\n10PRINT"'+(':'*n)+'"\n'+(':'*(n-1))+'\n'+(':'*n)+' \n'+(':'*n)+'\n' for n in range(3,17)]
 native += [':::region x\n'*18+':::end\n'*18]
 native += ['1'*300+'. huge numeric marker\n','1'*4096+'. large numeric marker\n']
 native += [('#'*n)+' title\n' for n in range(1,8)]
 # All BASIC tokens with no spaces around transitions, and each asm token.
 native += [str(i)+' '+word.lower()+' 123\n' for i,word in enumerate(BASIC)]
 native += [word.lower()+' #$12\n' for word in sorted(ASM)]
 native += [word.lower()+' "x"\n' for word in sorted(DIRECTIVES)]
 # Native-case distinctions, graphics and unsupported controls remain source bytes.
 exact=[bytes([0x41,0xC1,0x61,0xE1,0,10,0x93,0xFF,13]),b'\x23 \x41\xc1\x61\xe1\r',bytes(range(256))]
 for text in native:
  data=petscii(text);check(data);check(data,0xFFF9,True)
 for data in exact:check(data,0x1FFF9,True)
 alphabet=petscii('abcPRINTem£*#:@0123456789 -.$%\'"+()[]\n')+bytes([0,10,0x61,0xA0,0xFF])
 for case in range(1000):
  data=bytes(rng.choice(alphabet) for _ in range(rng.randrange(110)))
  check(data,0xFFF9 if case%3==0 else 0,case%2==0)
 # Source-preserving incremental edit fuzz: reparsing may change styles, not bytes.
 text=petscii(native[0]);edits=0
 for _ in range(100):
  a=rng.randrange(len(text)+1);b=min(len(text),a+rng.randrange(8));insert=bytes(rng.choice(alphabet) for _ in range(rng.randrange(6)))
  text=text[:a]+insert+text[b:];check(text,0xFFFA,True);edits+=1

 # Block precedence: omit valid block prefixes from inline scanning, retaining
 # the original logical column so a title/body cannot invent a heading escape.
 for text in ['* item *emphasis*','## title £# literal and **strong**','  123. body *emphasis* and £- literal','1'*300+'. body £# literal *style*']:
  data=petscii(text);event=p.blocks(data)[0];body=event['body'];source=data[body:]
  actual=p.inline(source,body,body_column=body);expected=inline(source,body,body_column=body)
  assert actual==expected,('block precedence',data,actual,expected)
  assert all(pair[3]>=body for pair in actual)
  comparisons+=1

 # Mid-token/mid-fence/mid-delimiter state survives transfer to a fresh CPU.
 # No hidden ZP, stack, or self-modified code is copied to that CPU.
 for prefix,data,initarg in [('se_sm',petscii(':::basic\n10PRINT"HI"\n:::\n:::region x\n:::end\n'),0),('se_si',petscii('**abc *nested* @@code@@ def** £*literal\n'),0),('se_sl',petscii('10PRINT"HELLO":DATA"A:B":GOTO10\n20REM X\n'),1),('se_sl',petscii('loop: lda #$12 ;comment\n.segment "CODE"\n'),2)]:
  for cut in range(1,len(data)):
   q=SuperMark();q.call(prefix+'_init',initarg);events=[]
   def consume(machine):
    if prefix=='se_sl':
     while machine.get('se_sl_count'):
      machine.call('se_sl_next');events.append(tuple(machine.get('se_sl_'+key,n) for key,n in [('start',3),('end',3),('style',1)]))
    elif prefix=='se_si':
     if machine.get('se_si_ready'):events.append(tuple(machine.get('se_si_'+key,n) for key,n in [('kind',1),('style',1),('width',1),('open',3),('close',3)]))
    elif machine.get('se_sm_ready'):
     events.append({key:machine.get('se_sm_'+key,n) for key,n in [('kind',1),('start',3),('end',3),('body',3),('level',1),('language',1),('fence',1),('regions',1)]})
   for byte in data[:cut]:q.call(prefix+'_feed',byte);consume(q)
   addr=q.symbols[prefix+'_state'];size=q.symbols[prefix+'_state_size'];state=bytes(q.m.read(addr+i) for i in range(size));q.close()
   q=SuperMark();q.m.load(addr,state)
   for byte in data[cut:]:q.call(prefix+'_feed',byte);consume(q)
   q.call(prefix+'_finish');consume(q);q.safe();q.close()
   expected=(blocks(data) if prefix=='se_sm' else inline(data) if prefix=='se_si' else lex(data,initarg))
   assert events==expected,('checkpoint',prefix,cut,events,expected)
   roundtrips+=1

 # Backpressure: a producer cannot overwrite unread lexical spans or advance input.
 p.call('se_sl_init',2)
 for byte in petscii('lda'):assert not p.call('se_sl_feed',byte).p&1
 p.call('se_sl_feed',ord('#'));assert p.get('se_sl_count')==2
 pos=p.get('se_sl_pos',3);queue=bytes(p.m.read(p.symbols['sl_queue']+i) for i in range(14))
 regs=p.call('se_sl_feed',ord('9'));assert regs.p&1 and regs.a==1
 assert p.get('se_sl_pos',3)==pos and bytes(p.m.read(p.symbols['sl_queue']+i) for i in range(14))==queue
 regs=p.call('se_sl_finish');assert regs.p&1 and p.get('se_sl_pos',3)==pos
 p.call('se_sl_next');p.call('se_sl_next');assert p.call('se_sl_next').p&1
 for a,expected in protected:assert bytes(p.m.read(a+i) for i in range(len(expected)))==expected,hex(a)

 module_sizes={}
 for line in (OUT/'probe.map').read_text().splitlines():
  if match:=re.fullmatch(r'(SM_BLOCK|SM_INLINE|SM_LEXER|SM_STATE)\s+[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]+)\s+[0-9A-F]+',line):module_sizes[match[1]]=int(match[2],16)
 assert all(module_sizes[key]<=4096 for key in ['SM_BLOCK','SM_INLINE','SM_LEXER'])
 files=sorted([* (ROOT/'src/supermark').glob('*'),* (ROOT/'probes/supermark').glob('*'),ROOT/'tools/supermark_probe.py',ROOT/'tools/supermark_model.py',Path(__file__).resolve()])
 result=dict(status='passed',engine='Peddle MOS_6510',probe_sha256=hashlib.sha256((OUT/'probe.bin').read_bytes()).hexdigest(),source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.is_file()},module_bytes=module_sizes,zero_page_bytes=0,fixtures=fixtures,source_bytes=source_bytes,independent_oracle_comparisons=comparisons,incremental_edit_reparses=edits,fresh_cpu_context_roundtrips=roundtrips,protected_bytes=sum(len(v) for _,v in protected),shim_bytes=1024,maximum_observed_instructions=p.peak,limitations=['Standalone pure modules; editor styles/source mapping/fold tree not integrated.','No VICE/video/color/physical keyboard proof.','BASIC shifted abbreviations remain literal; full mixed-case keywords supported.','ca65 lexical subset, not a compiler; no string escape interpretation.'])
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:p.close()
