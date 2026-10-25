"""Actual bounded6510 source-color planner; isolated build/style-plan only.

The callback fixture reads immutable raw REU bytes. The production merged-view
adapter has a separate gate; this test does not claim editor/video integration.
"""
from pathlib import Path
import hashlib,json,random,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from supermark_model import blocks,inline
from supermark_probe import petscii
OUT=ROOT/'build/style-plan'
SOURCES=['style/state','style/plan','style/probe-source','supermark/block','supermark/inline']

def build():
 OUT.mkdir(parents=True,exist_ok=True);objects=[]
 for n in SOURCES:
  p=OUT/(n.replace('/','-')+'.o');objects.append(str(p))
  subprocess.run(['ca65','-I',str(ROOT/'src'),'-g','-o',str(p),str(ROOT/'src'/f'{n}.s')],check=True)
 subprocess.run(['ld65','-C',str(ROOT/'src/style/probe.cfg'),'-o',str(OUT/'probe.bin'),'-m',str(OUT/'probe.map'),'-Ln',str(OUT/'probe.lbl'),*objects],check=True)

def rowmap(data,mode=0,top=0):
 starts=[top];p=top
 for _ in range(22):
  if mode:
   e=data.find(b'\r',p);p=len(data) if e<0 else e+1
  else:
   for _ in range(40):
    if p==len(data):break
    c=data[p];p+=1
    if c==13:break
  starts.append(p)
 return starts

def plan_model(data,rows,mode=0,pan=0):
 styles=bytearray([1]*len(data))
 for e in blocks(data):
  base=0x87 if e['kind']==2 else 14 if e['kind']==5 else 15 if e['kind'] in (4,6,7,8) else 1
  styles[e['start']:e['end']]=bytes([base])*(e['end']-e['start'])
  if e['kind'] in (4,5,6):continue
  origin=e['body'];part=data[origin:e['end']]
  for kind,style,width,a,b in inline(part,origin,body_column=(origin-e['start']) or None):
   if kind!=1:continue
   for p in range(a+width,b):
    mask=(styles[p]&0xF0)|(style<<4)
    styles[p]=mask|(14 if mask&64 else [1,3,7,10][(mask>>4)&3])
 result=[]
 for a,b in zip(rows,rows[1:]):
  result += [styles[p] if p<min(b,len(data)) and data[p]!=13 else 1 for c in range(40) for p in [a+(pan if mode else 0)+c]]
 return bytes(result)

class Fixture:
 def __init__(self):
  self.s={p[2].lstrip('.'):int(p[1],16) for line in (OUT/'probe.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
  self.m=Machine();self.m.load(0x1000,(OUT/'probe.bin').read_bytes())
  self.steps=self.reads=self.max_feeds=self.max_reads=0;self.peak={};self.guard_ranges=[]
  # No source/font/renderer/ReadyOS memory belongs to this pure service.
  for a,n in [(0,256),(0x4000,0x400),(0x4800,0x800),(0x8000,0xCC6),(0x8CEB,0x15),(0x8E9F,0x2E1),(0x9180,0x880),(0x9A17,0x5E9),(0xC000,0x1000)]:
   b=bytes((i*31+a*7+19)&255 for i in range(n));self.m.load(a,b);self.guard_ranges.append((a,b))
  self.put('fixture_epoch',0x1234,2);self.put('fixture_leases',1) #foreignlease
 def close(self):self.m.close()
 def ram(self,a,n):
  if isinstance(a,str):a=self.s[a]
  return bytes(self.m.read(a+i) for i in range(n))
 def get(self,k,n=1):return int.from_bytes(self.ram(k,n),'little')
 def put(self,k,v,n=1):self.m.load(self.s[k],v.to_bytes(n,'little'))
 def call(self,k):
  regs,count=self.m.call(self.s[k]);self.peak[k]=max(self.peak.get(k,0),count);return regs
 def reu(self,n):return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,i) for i in range(n))
 def seed(self,data,mode=0,pan=0,top=0,revision=1,chunk=128,preserve=False):
  assert len(data)<=1<<20
  # Actual REU stash is fixture setup, never part of planner execution.
  for p in range(0,len(data),8192):
   part=data[p:p+8192];self.m.load(0x6000,part)
   for a,v in [(0xDF02,0),(0xDF03,0x60),(0xDF04,p&255),(0xDF05,(p>>8)&255),(0xDF06,p>>16),(0xDF07,len(part)&255),(0xDF08,len(part)>>8),(0xDF0A,0),(0xDF01,0x90)]:self.m.write(a,v)
  self.data=data;self.rows=rowmap(data,mode,top);self.mode=mode;self.pan=pan
  key=bytes(range(1,16))+b'\x01\x00'+revision.to_bytes(4,'little')+len(data).to_bytes(3,'little')+top.to_bytes(3,'little')+pan.to_bytes(3,'little')+b'\x34\x12'+bytes([mode])
  assert len(key)==33
  self.m.load(self.s['se_st_key'],key);self.m.load(self.s['se_st_rows'],b''.join(x.to_bytes(3,'little') for x in self.rows))
  self.put('se_fs_length',len(data),3);self.put('fixture_chunk',chunk);self.put('fixture_fail',0);self.put('fixture_begin_fail',0)
  if not preserve:self.put('se_st_cp_valid',0);self.put('se_st_cp_dirty',0)
 def step(self):
  before_reads=self.get('fixture_reads',2);phase=self.get('st_phase');pos=self.get('st_pos',3)
  r=self.call('se_style_step');n=(self.get('fixture_reads',2)-before_reads)&65535
  assert n<=1,('readbudget',n)
  # Feed phases advance input once per feed; metadata/painting do not feed.
  if phase in (1,4):
   fed=self.get('st_pos',3)-pos
   assert 0<=fed<=32,('feedbudget',phase,pos,self.get('st_pos',3))
   self.max_feeds=max(self.max_feeds,fed)
  self.max_reads=max(self.max_reads,n);self.reads+=n;self.steps+=1
  return r
 def finish(self):
  n=0
  while self.get('se_st_busy'):
   r=self.step();assert not r.p&1,(r.a,self.get('st_phase'),self.get('st_pos',3));n+=1
   assert n<250000,('hung',self.get('st_phase'),self.get('st_pos',3))
  assert self.get('se_st_valid')==1
  assert self.get('fixture_owned')==0 and self.get('fixture_leases')==1
  return n
 def check(self):
  r=self.call('se_style_begin');assert not r.p&1 and r.a==2
  self.finish();actual=self.ram(0x4400,880);wanted=plan_model(self.data,self.rows,self.mode,self.pan)
  assert actual==wanted,[(i,a,b) for i,(a,b) in enumerate(zip(actual,wanted)) if a!=b][:12]
  assert self.reu(len(self.data))==self.data
  for a,b in self.guard_ranges:assert self.ram(a,len(b))==b,hex(a)

def main():
 build();(OUT/'result.json').unlink(missing_ok=True);f=Fixture();fixtures=0
 try:
  texts=['','# Head\nplain *emphasis* **strong** ***both*** @@code@@\n',
   '**outer *inner* outer** *outer **inner** outer*\n',
   '# *heading* **strong** @@code@@\n- list *body*\n12. **ordered**\n',
   ':::basic\n10PRINT"*literal*"\n::: \n:::\nplain\n',
   ':::region A *title*\n:::asm\nloop: lda #$ff\n:::\n:::end\n',
   '*unclosed\n**unclosed\n@@unclosed *literal*\n@@@@literal@@@@\n',
   '£# literal\n£*literal£* £@@literal£@@ ££ £5\n',
   '\n'*24,'x'*40+'\n# afterexactwrap\n','x'*39+'\n# afterpartial\n']
  for text in texts:
   data=petscii(text)
   for mode,pan in [(0,0),(1,0),(1,7)]:
    f.seed(data,mode,pan,chunk=7 if fixtures&1 else 128);f.check();fixtures+=1
  rng=random.Random(0xC014)
  for _ in range(28):
   text='\n'.join(rng.choice(['# *Heading*','plain **strong**','- a *list*','**outer *inner* outer**','£*lit£* @@code@@',':::text',':::', '## Next', '']) for _ in range(8))
   f.seed(petscii(text),rng.randrange(2),rng.randrange(12),chunk=rng.choice([1,7,31,128]));f.check();fixtures+=1
  # Actual 24-bit packet source, closer beyond64KiB, no line buffer.
  long=petscii('# Preamble\n*'+('a'*66000)+'* end\n# Next\n')
  f.seed(long,1,65520,top=11,chunk=128);f.check();fixtures+=1
  # A complete block checkpoint avoids scanning unchanged prefix on viewport move.
  cpdata=petscii(('prefix line\n'*300)+'# Visible\n*tail*\n')
  top=cpdata.index(b'#');f.seed(cpdata,top=top);f.check();assert f.get('se_st_cp_valid')
  anchor=f.get('se_st_cp_anchor',3);before=f.get('fixture_reads',2)
  f.seed(cpdata,top=top,preserve=True);f.check();assert (f.get('fixture_reads',2)-before)&65535<12
  # Mutation proof after checkpoint is retained even after R1 consumed its damage.
  edited=cpdata[:-2]+b'X'+cpdata[-2:]
  f.seed(edited,top=top,revision=2,preserve=True);f.put('se_st_cp_dirty',1);f.put('se_st_cp_damage',len(cpdata)-2,3);f.check();assert f.get('se_st_cp_anchor',3)==anchor
  fixtures+=3
  # Every cancellable phase, competingBEGIN, complete/repeatedCANCEL and foreignlease.
  for phase in range(6):
   f.seed(petscii('# H\nplain *emphasis* **strong**\n'));assert not f.call('se_style_begin').p&1
   for _ in range(20000):
    if f.get('st_phase')==phase:break
    f.step()
   else:raise AssertionError(('missingphase',phase))
   owned=f.get('fixture_owned');assert f.call('se_style_begin').p&1 and f.get('fixture_owned')==owned
   assert not f.call('se_style_cancel').p&1 and not f.get('se_st_valid') and f.get('fixture_leases')==1
   ends=f.get('fixture_ends',2);f.call('se_style_cancel');assert f.get('fixture_ends',2)==ends
  # Context change and exact root key mismatch never publish a partial plan.
  for kind in ('viewport','provider','readfailure'):
   f.seed(petscii('*later*\n'));f.call('se_style_begin');f.step()
   if kind=='viewport':f.m.write(f.s['se_st_key']+24,1)
   elif kind=='provider':f.put('fixture_epoch',0x1235,2);f.put('fixture_leases',1)
   else:f.put('fixture_fail',0xA9)
   r=f.step();assert r.p&1 and not f.get('se_st_valid') and not f.get('fixture_owned')
   assert f.get('fixture_leases')==1
   f.put('fixture_epoch',0x1234,2)
  for a,b in f.guard_ranges:assert f.ram(a,len(b))==b,hex(a)
  s=f.s;payload=s['__STYLE_CODE_SIZE__']+s['__SM_BLOCK_SIZE__']+s['__SM_INLINE_SIZE__']
  result=dict(status='passed',fixtures=fixtures,steps=f.steps,reads=f.reads,max_feeds_per_step=f.max_feeds,max_reads_per_step=f.max_reads,
   module_bytes=dict(controller=s['__STYLE_CODE_SIZE__'],block=s['__SM_BLOCK_SIZE__'],inline=s['__SM_INLINE_SIZE__'],payload_without_binding=payload),
   phase_bytes=s['__STYLE_STATE_SIZE__']+s['__SM_STATE_SIZE__'],descriptor_bytes=s['__STYLE_DESCRIPTOR_SIZE__'],checkpoint_bytes=s['__STYLE_CHECKPOINT_SIZE__'],
   peak_instructions=f.peak,zero_page_bytes=0,shim_bytes=1024,
   source_sha256={str(ROOT/'src'/f'{n}.s'):hashlib.sha256((ROOT/'src'/f'{n}.s').read_bytes()).hexdigest() for n in SOURCES},
   scope='Isolated actual6510 planner with directREU callback fixture; production source adapter/root/R1/native integration not claimed')
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
def editor_source_main():
 """Real frozen piece table + pending gap, independent plan oracle.

 Product overlays/index are saved/restored around capsule use. This tests the
 actual provider callbacks, not production overlay placement or the root pump.
 """
 import re
 import editor_fixture,cpu_editor
 frozen=ROOT/'build/editor-file-integration/20261024T213441593038Z'
 freeze=json.loads((frozen/'freeze.json').read_text())
 assert freeze['prg_sha256']=='2f6d1a76cb12424e03d2965e33853fb343032eead32797eca0a4b46fd9bf72ff'
 editor_fixture.ROOT=cpu_editor.ROOT=frozen
 editor_fixture.NAMES=cpu_editor.NAMES=freeze['names']
 out=OUT/'editor-source';out.mkdir(parents=True,exist_ok=True)
 sources=['style/state','style/plan','supermark/block','supermark/inline']+['fold/'+n for n in ['source-state','source-context','source-read','source-lease']]
 objects=[]
 for n in sources:
  p=out/(n.replace('/','-')+'.o');objects.append(p)
  subprocess.run(['ca65','-I',str(ROOT/'src'),'-g','-o',str(p),str(ROOT/'src'/f'{n}.s')],check=True)
 imports=set();exports=set()
 for obj in objects:
  for flag,values in [('--dump-imports',imports),('--dump-exports',exports)]:
   text=subprocess.run(['od65',flag,str(obj)],capture_output=True,text=True,check=True).stdout
   values.update(re.findall(r'Name:\s+"([^"]+)"',text))
 report=json.loads((frozen/'build/editor-report.json').read_text());external=imports-exports
 assert external<=report['symbols'].keys(),sorted(external-report['symbols'].keys())
 lines=[]
 for n in sorted(external):lines+=['.exportzp '+n if n in ['text_ptr','se_hot_ptr','se_hot_packet'] else '.export '+n,n+' = $%04X'%report['symbols'][n]]
 (out/'externals.s').write_text('\n'.join(lines)+'\n')
 subprocess.run(['ca65','-o',str(out/'externals.o'),str(out/'externals.s')],check=True)
 subprocess.run(['ld65','-C',str(ROOT/'src/style/editor-source-probe.cfg'),'-o',str(out/'unused.bin'),'-m',str(out/'probe.map'),'-Ln',str(out/'probe.lbl'),*map(str,objects),str(out/'externals.o')],cwd=ROOT,check=True)
 symbols={p[2].lstrip('.'):int(p[1],16) for line in (out/'probe.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
 f=editor_fixture.EditorFixture();peak={};steps=0;cases=[]
 def get(n,w=1):return int.from_bytes(f.read(symbols[n],w),'little')
 def put(n,v,w=1):f.m.load(symbols[n],v if isinstance(v,bytes) else v.to_bytes(w,'little'))
 def call(n):
  r,c=f.m.call(symbols[n],limit=100000);peak[n]=max(peak.get(n,0),c);return r
 def reu_image():return bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,i) for i in range(32*65536))
 def install():
  saved=[(a,f.read(a,n)) for a,n in [(0x6000,4096),(0xB000,4096),(0x8D00,1152)]]
  f.m.load(0x6000,(out/'source.bin').read_bytes());f.m.load(0xB000,(out/'style.bin').read_bytes())
  f.m.load(0x8D00,bytes(1152));return saved
 def restore(saved):
  for a,b in saved:f.m.load(a,b)
 def configure(data,mode=0,pan=0,top=0):
  key=f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_r_revision'],4)+len(data).to_bytes(3,'little')+top.to_bytes(3,'little')+pan.to_bytes(3,'little')+f.read(f.s['se_reu_epoch'],2)+bytes([mode])
  assert len(key)==33
  put('se_st_key',key);put('se_st_rows',b''.join(x.to_bytes(3,'little') for x in rowmap(data,mode,top)))
  put('se_st_cp_valid',0);put('se_st_cp_dirty',0)
  return rowmap(data,mode,top)
 def check(data,mode=0,pan=0,top=0):
  nonlocal steps
  saved=install();rows=configure(data,mode,pan,top)
  before=reu_image();hot=f.read(0x9200,2048);diag=f.read(0x8800,128)
  canonical=f.read(f.s['se_doc_roots'],512)+f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_hot_caret'],3)
  leases=f.get('se_doc_read_locks',1)
  r=call('se_style_begin');assert not r.p&1,(r.a,'BEGIN')
  assert f.get('se_doc_read_locks',1)==leases+1
  while get('se_st_busy'):
   phase=get('st_phase');pos=get('st_pos',3);r=call('se_style_step');assert not r.p&1,(r.a,get('st_phase'),get('st_pos',3))
   if phase in (1,4):assert 0<=get('st_pos',3)-pos<=32
   steps+=1;assert steps<200000
  assert get('se_st_valid') and f.get('se_doc_read_locks',1)==leases and not get('se_fs_owned')
  actual=f.read(0x4400,880);wanted=plan_model(data,rows,mode,pan)
  assert actual==wanted,[(i,a,b) for i,(a,b) in enumerate(zip(actual,wanted)) if a!=b][:12]
  assert reu_image()==before and f.read(0x9200,2048)==hot and f.read(0x8800,128)==diag
  assert f.read(f.s['se_doc_roots'],512)+f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_hot_caret'],3)==canonical
  assert f.read(0xC600,1024)==f.shim
  restore(saved)
 try:
  data=petscii('# Native *heading*\n:::basic\n10 PRINT "Code CASE"\n:::\n**outer *inner* outer**\n')
  f.source(data,banks=2,physical=32);check(data);cases.append('actual committed document + hot read cache')
  # Use actual source splices to force fragmented read_some descriptors.
  assert not f.call('se_hot_call',10).p&1
  for i in range(12):
   p=20+2*i;part=b'x';f.put('se_doc_edit_position',p);f.put('se_doc_edit_delete',0);f.put('se_doc_edit_insert',1)
   assert not f.call('se_doc_splice_begin').p&1
   f.m.load(0x8000,part);f.put('se_doc_count',1,2);f.put('se_doc_c64',0x8000,2);assert not f.call('se_doc_splice_feed').p&1
   while f.get('se_doc_busy',1):assert not f.call('se_doc_splice_step').p&1
   data=data[:p]+part+data[p:]
  check(data);cases.append('12 actual source splices / fragmented descriptors')
  f.position(5)
  pending=petscii('**X**')
  for byte in pending:f.key(byte)
  data=data[:5]+pending+data[5:]
  assert f.get('se_hot_pending',1);check(data,1,2);cases.append('actual pending gap / no flush / nowrap pan')
  # Source guard and cancellation preserve a foreign counted lease.
  assert not f.call('se_doc_read_acquire').p&1
  saved=install();configure(data);assert not call('se_style_begin').p&1
  assert f.get('se_doc_read_locks',1)==2
  for _ in range(32):assert not call('se_style_step').p&1
  assert not call('se_style_cancel').p&1 and f.get('se_doc_read_locks',1)==1 and not get('se_st_valid')
  call('se_style_cancel');assert f.get('se_doc_read_locks',1)==1
  restore(saved);assert not f.call('se_doc_read_release').p&1;cases.append('partial job cancel preserves foreign counted lease')
  # Native long source and far closing delimiter use the actual reader.
  data=petscii('# Prefix\n*'+('a'*66000)+'* end\n')
  f.source(data,banks=2,physical=32);check(data,1,65520,top=9);cases.append('actual >64KiB source and far inline closer')
  result=dict(status='passed',cases=cases,editor_prg_sha256=freeze['prg_sha256'],steps=steps,peak_instructions=peak,phase_bytes=symbols['__STYLE_STATE_SIZE__']+symbols['__SM_STATE_SIZE__']+symbols['__FOLD_SOURCE_STATE_SIZE__'],
   source_adapter_bytes=symbols['__FOLD_SOURCE_CODE_SIZE__']+symbols['__FOLD_SOURCE_CLEANUP_SIZE__'],style_payload_without_binding=symbols['__STYLE_CODE_SIZE__']+symbols['__SM_BLOCK_SIZE__']+symbols['__SM_INLINE_SIZE__'],
   checked_reu_per_plan=32*65536,shim_bytes=1024,source_sha256={n:hashlib.sha256((ROOT/'src'/f'{n}.s').read_bytes()).hexdigest() for n in sources},
   scope='Isolated actual6510 style + checked merged editor-source callbacks against frozen2f6d resident; no product placement/root/R1/native integration claimed')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()

if __name__=='__main__':
 if '--editor-source' in sys.argv:editor_source_main()
 else:main()
