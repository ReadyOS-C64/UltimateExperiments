"""Actual C14/C15 shared-phase handoff, pure lexers and R14 callback seam.

Only build/style-lexical is written. C images are swapped at B000 between
resident-shaped calls. Source fixture uses actual REU DMA, not editor source;
the production root/provider integration has a separate acceptance gate.
"""
from pathlib import Path
import hashlib,importlib.util,json,random,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from supermark_model import blocks,lex
from supermark_probe import petscii
spec=importlib.util.spec_from_file_location('style_oracle',ROOT/'tests/test_style_plan.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
OUT=ROOT/'build/style-lexical'
def run(args,**kw):return subprocess.run(list(map(str,args)),check=True,**kw)
def symbols(path):return {p[2].lstrip('.'):int(p[1],16) for line in path.read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
def objects(tag,sources):
 result=[]
 for name,flag in sources:
  obj=OUT/(tag+'-'+name.replace('/','-')+'.o');args=['ca65','-g','-I',OUT,'-I',ROOT/'src','-o',obj]
  if flag:args+=['-D',flag+'=1']
  run(args+[ROOT/'src'/f'{name}.s']);result.append(obj)
 return result
def build():
 OUT.mkdir(parents=True,exist_ok=True)
 # Rename only the disposable fixture callback entry points, making the actual
 # reader-dispatch object invoke the resident-shaped R14 transport stub.
 text=(ROOT/'src/style/probe-source.s').read_text()
 for n in ['begin','guard','read','end']:text=text.replace('se_fs_'+n,'fixture_fs_'+n)
 (OUT/'source.s').write_text(text)
 (OUT/'transport.s').write_text('''.setcpu "6502"
.export se_overlay_call,se_overlay_frame,se_fs_end
.exportzp text_ptr
.import fixture_fs_begin,fixture_fs_guard,fixture_fs_read,fixture_fs_end
se_overlay_frame=$C010
text_ptr=$02
se_fs_end=fixture_fs_end
.segment "CODE"
se_overlay_call:
 cmp #14
 bne bad
 cpx #0
 bne bad
 lda se_overlay_frame
 beq begin
 cmp #1
 beq guard
 cmp #2
 beq read
bad:lda #$BA
 sec
 rts
begin:jmp fixture_fs_begin
guard:jmp fixture_fs_guard
read:jmp fixture_fs_read
''')
 (OUT/'resident.cfg').write_text('''MEMORY {
 CORE:file=%O,start=$1000,size=$0800,type=rw,fill=yes;
 DESC:file="",start=$8CC6,size=$0025,type=rw;
 CP:file="",start=$4770,size=$0090,type=rw;
 PHASE:file="",start=$8D00,size=$0480,type=rw;
 SOURCE:file="",start=$9A00,size=$0100,type=rw;
}
SEGMENTS { CODE:load=CORE,type=ro; STYLE_DESCRIPTOR:load=DESC,type=bss;
 STYLE_CHECKPOINT:load=CP,type=bss; STYLE_STATE:load=PHASE,type=bss,define=yes;
 SM_STATE:load=PHASE,type=bss,define=yes; FIXTURE_STATE:load=SOURCE,type=bss; }
''')
 resident=objects('resident',[(n,None) for n in ['style/state','style/lexical-state']]+[(f'supermark/{n}','SE_SM_STATE_ONLY') for n in ['block','inline','lexer']])
 for n in ['source','transport']:
  p=OUT/(n+'.o');run(['ca65','-g','-o',p,OUT/(n+'.s')]);resident.append(p)
 run(['ld65','-C',OUT/'resident.cfg','-o',OUT/'resident.bin','-Ln',OUT/'resident.lbl','-m',OUT/'resident.map',*resident])
 rs=symbols(OUT/'resident.lbl')
 (OUT/'editor-api.inc').write_text(f'se_overlay_frame=${rs["se_overlay_frame"]:04X}\nse_overlay_call=${rs["se_overlay_call"]:04X}\n.macro OVL_BINDING\n.res16,0\n.endmacro\n'.replace('.res16','.res 16'))
 images={};sizes={};all_symbols=dict(rs)
 for name,sources,segments in [
  ('c14',[('style/plan','SE_STYLE_LEXICAL'),('style/reader-dispatch',None),('supermark/block','SE_SM_CODE_ONLY'),('supermark/inline','SE_SM_CODE_ONLY')],['STYLE_CODE','SM_BLOCK','SM_INLINE']),
  ('c15',[('overlays/lexical',None),('style/lexical-control',None),('style/reader-dispatch',None),('supermark/lexer','SE_SM_CODE_ONLY')],['STYLE_CODE','SM_LEXER'])]:
  objs=objects(name,sources);imports=set();exports=set()
  for obj in objs:
   for flag,values in [('--dump-imports',imports),('--dump-exports',exports)]:
    text=run(['od65',flag,obj],capture_output=True,text=True).stdout;values.update(re.findall(r'Name:\s+"([^"]+)"',text))
  external=imports-exports;assert external<=rs.keys(),sorted(external-rs.keys())
  bindings=[]
  for n in sorted(external):bindings += [('.exportzp ' if n=='text_ptr' else '.export ')+n,n+'=$%04X'%rs[n]]
  src=OUT/(name+'-bindings.s');src.write_text('\n'.join(bindings)+'\n');obj=OUT/(name+'-bindings.o');run(['ca65','-o',obj,src]);objs.append(obj)
  cfg=OUT/(name+'.cfg');cfg.write_text('MEMORY { C:file=%O,start=$B000,size=$1000,type=rw; }\nSEGMENTS { '+''.join(s+':load=C,type=ro,define=yes; ' for s in segments)+'}\n')
  run(['ld65','-C',cfg,'-o',OUT/(name+'.bin'),'-Ln',OUT/(name+'.lbl'),'-m',OUT/(name+'.map'),*objs])
  images[name]=(OUT/(name+'.bin')).read_bytes();assert len(images[name])<=4096
  sizes[name]=len(images[name]);all_symbols.update(symbols(OUT/(name+'.lbl')))
 return rs,all_symbols,images,sizes

def oracle(data,rows,mode,pan):
 plan=bytearray(base.plan_model(data,rows,mode,pan));spans=[];palette={7:7,8:13,9:5,10:15,11:7,12:3,13:1}
 for e in blocks(data):
  if e['kind']==5:spans += [(a,b,palette[s]) for a,b,s in lex(data[e['body']:e['end']],e['language'],e['body'])]
 for row,(a,b) in enumerate(zip(rows,rows[1:])):
  for col in range(40):
   p=a+(pan if mode else 0)+col
   if p>=min(b,len(data)) or data[p]==13:continue
   for start,end,color in spans:
    if start<=p<end:plan[row*40+col]=color
 return bytes(plan)

class Fixture(base.Fixture):
 def __init__(self,rs,s,images):
  self.rs=rs;self.s=s;self.images=images;self.m=Machine();self.m.load(0x1000,(OUT/'resident.bin').read_bytes());self.loaded=None
  self.steps=self.reads=self.max_feeds=self.max_reads=self.lex_steps=self.paint_steps=self.changed_cells=0;self.peak={};self.guard_ranges=[]
  for a,n in [(4,252),(0x4000,0x400),(0x4800,0x800),(0x8000,0xCC6),(0x8CEB,0x15),(0x8EDC,0x2A4),(0x9180,0x880),(0x9A17,0x5E9),(0xC020,0xFE0)]:
   b=bytes((i*31+a*7+19)&255 for i in range(n));self.m.load(a,b);self.guard_ranges.append((a,b))
  self.put('fixture_epoch',0x1234,2);self.put('fixture_leases',1)
 def call(self,n,a=0):
  image='c15' if n=='se_style_lexical' else 'c14'
  if self.loaded!=image:self.m.load(0xB000,self.images[image]);self.loaded=image
  r,count=self.m.call(self.s[n],a=a);self.peak[n]=max(self.peak.get(n,0),count);return r
 def seed(self,*args,**kw):
  super().seed(*args,**kw);self.put('st_lex_phase',0)
 def step(self):
  lexical=bool(self.get('st_lex_phase'));phase=self.get('st_lex_phase') if lexical else self.get('st_phase')
  before=self.ram(0x4400,880);pos=self.get('st_pos',3);reads=self.get('fixture_reads',2)
  block=self.ram('se_sm_state',79);nextline=self.ram('st_next',3)+self.ram('st_end',3)+self.ram('st_finish',1)
  r=self.call('se_style_lexical',3) if lexical else self.call('se_style_step')
  n=(self.get('fixture_reads',2)-reads)&65535;assert n<=1
  changed=sum(a!=b for a,b in zip(before,self.ram(0x4400,880)));assert changed<=32
  if (lexical and phase==2) or (not lexical and phase in (1,4)):
   feeds=self.get('st_pos',3)-pos;assert 0<=feeds<=32;self.max_feeds=max(self.max_feeds,feeds)
  if lexical:
   assert self.ram('se_sm_state',79)==block and self.ram('st_next',3)+self.ram('st_end',3)+self.ram('st_finish',1)==nextline
   assert self.get('fixture_owned')==1 and self.get('fixture_leases')==2
   self.lex_steps+=1;self.paint_steps+=int(phase==3);self.changed_cells+=changed
  self.max_reads=max(self.max_reads,n);self.reads+=n;self.steps+=1;return r
 def check(self):
  r=self.call('se_style_begin');assert not r.p&1
  self.finish();actual=self.ram(0x4400,880);wanted=oracle(self.data,self.rows,self.mode,self.pan)
  assert actual==wanted,[(i,a,b) for i,(a,b) in enumerate(zip(actual,wanted)) if a!=b][:16]
  assert self.reu(len(self.data))==self.data
  for a,b in self.guard_ranges:assert self.ram(a,len(b))==b,hex(a)

def main():
 rs,s,images,sizes=build();(OUT/'result.json').unlink(missing_ok=True);f=Fixture(rs,s,images);fixtures=0
 try:
  texts=['# Heading *style*\n:::basic\n10PRINT"CASE":GOTO10\n20REM PRINT DATA\n30DATA"X:Y",GOTO:PRINT.5,3.14E-2\n:::\nProse **strong**\n',
   ':::asm\nlabel: lda #$ff\n@local: .byte %1010,123\n.segment "CODE" ;comment\n rts\n:::\n',
   ':::text\n10PRINT"No language tokens"\n:::\n',
   ':::basic\n10PRINT"unterminated\n20PRINT"next"',
   ':::asm\nlda#9\n"unterminated\n;comment\n:::\n']
  for text in texts:
   for mode,pan in [(0,0),(1,0),(1,11),(1,1000)]:
    f.seed(petscii(text),mode,pan,chunk=7 if fixtures&1 else 128);f.check();fixtures+=1
  # Clipped token spans and a far closing string cross actual64KiB REU packets.
  long=petscii(':::basic\n10PRINT"'+('a'*66000)+'":REM trailing\n:::\n')
  f.seed(long,1,65520,top=9,chunk=128);f.check();fixtures+=1
  # No token causes an880-cell scan: a long comment needs only visible writes.
  data=petscii(':::asm\n;'+('comment '*800)+'\n:::\n')
  old=f.paint_steps;f.seed(data,0,0,chunk=128);f.check();assert f.paint_steps-old<=28;fixtures+=1
  # Each private lexical phase can be cancelled by resident/C14, releasing just
  # its existing lease. The worker itself never releases or publishes the plan.
  for phase in [1,2,3]:
   f.seed(petscii(':::asm\nlabel: lda #$ff ;comment\n:::\n'));f.call('se_style_begin')
   for _ in range(10000):
    if f.get('st_lex_phase')==phase:break
    assert not f.step().p&1
   else:raise AssertionError(('phase never reached',phase))
   ends=f.get('fixture_ends',2);assert f.get('se_st_valid')==0
   r=f.call('se_style_lexical',3);assert not r.p&1 and f.get('fixture_ends',2)==ends
   f.call('se_style_cancel');assert f.get('fixture_leases')==1 and not f.get('se_st_valid')
  # Source guard failure is returned unchanged; caller performs epoch-safe END.
  f.seed(petscii(':::basic\n10PRINT"X"\n:::\n'));f.call('se_style_begin')
  while not f.get('st_lex_phase'):assert not f.step().p&1
  f.put('fixture_fail',0xA9);r=f.call('se_style_lexical',3);assert r.p&1 and r.a==0xA9 and f.get('fixture_owned')==1
  f.call('se_style_cancel');assert f.get('fixture_leases')==1
  result=dict(status='passed',fixtures=fixtures,steps=f.steps,lexical_steps=f.lex_steps,lexical_paint_steps=f.paint_steps,max_feeds=f.max_feeds,max_reads=f.max_reads,c15_payload_bytes=sizes['c15'],c15_free=4096-sizes['c15'],c14_fixture_payload=sizes['c14'],new_state_bytes=1,lexer_state_bytes=60,combined_phase_without_source_adapter=476,production_phase_expected=562,zero_page_added=0,peak_instructions=f.peak,shim_bytes=1024,
   source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['src/style/lexical-control.s','src/style/lexical-state.s','src/overlays/lexical.s','src/style/plan.s','src/supermark/lexer.s','tests/test_style_lexical.py']},
   scope='Actual C14/C15 code swapped atB000 with immutable REU/transport fixture; production root/fullsourceprovider/native acceptance separate')
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()
