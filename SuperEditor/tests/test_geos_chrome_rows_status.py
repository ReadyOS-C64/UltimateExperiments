"""Actualold/new R27STATUS pixel/stack/REU oracle and cost comparison."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,ctypes as C,re
import test_geos_chrome_rows as core
from peddle import Machine
from test_editor_chrome import oracle,settings
ROOT=core.ROOT

def run(out,base):
 frozen,identity=core.public.geos.freeze(out,base);budgets=[core.build(out/'control',frozen,False),core.build(out/'candidate',frozen)];dll=core.public.geos.grid.runner(out);s=json.loads((frozen/'build/editor-report.json').read_text())['symbols'];font=(frozen/'fonts/native8.bin').read_bytes();prg=(frozen/'build/editor.prg').read_bytes();machines=[];costs=[]
 for lane in('control','candidate'):
  m=Machine();m.load(0,bytes((i*73+19)&255 for i in range(65536)));m.load(int.from_bytes(prg[:2],'little'),prg[2:]);m.load(0xa000,(out/lane/'r27.bin').read_bytes());m.load(0x4800,font);labels={n:int(a,16)for a,n in re.findall(r'al ([\da-fA-F]+) \.(\w+)',(out/lane/'r27.lbl').read_text())};machines.append((m,labels))
 def read(m,at,n):raw=C.create_string_buffer(n);dll.gm_read(m.handle,at,n,raw);return raw.raw
 def reu(m):raw=C.create_string_buffer(16*1024*1024);dll.gm_reu(m.handle,len(raw),raw);return raw.raw
 normal=dict(ui=0,error=0,caret=0,pending=0,dirty=0,mark=0,fault=0,trimmed=0,text=b'');states=[]
 for caret in(0,1,255,256,65535,65536,0xffffff):
  for pending,dirty,mark in[(0,0,0),(1,1,0),(0,1,1)]:states.append(normal|dict(caret=caret,pending=pending,dirty=dirty,mark=mark))
 for error in range(256):states.append(normal|dict(error=error))
 for length in range(32):states.append(normal|dict(ui=2,text=b'Mixed CASE 123456789 \xa4 '[0:length].ljust(length,b'Q')))
 for fault,trimmed in[(1,0),(0,1),(0,256),(1,65535)]:states.append(normal|dict(fault=fault,trimmed=trimmed))
 try:
  snapshots=[reu(m)for m,_ in machines]
  for state in states:
   matrix,colors=oracle(state);row=matrix[80:120];fg=colors[80:120];wantbits=b''.join(bytes(b^(255 if code&128 else 0)for b in font[(code&127)*8:(code&127)*8+8])for code in row);counts=[]
   for m,labels in machines:
    settings(m,s,state);m.write(s['se_ink_reverse'],0);m.write(s['se_f_owner'],4);before=read(m,0,65536)
    for n,v in[('pc',labels['se_gcc_status']),('sp',253),('p',0x24),('a',0),('x',0xa5),('y',0x5a)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
    m.write(0x1fe,254);m.write(0x1ff,2);n=dll.gm_run(m.handle,200000);assert n;counts.append(n);r=m.regs();assert not r.p&1 and r.a==0 and r.sp==255;after=read(m,0,65536);want=bytearray(before)
    for at,nbytes in[(0x100,256),(s['text_ptr'],2),(s['screen_ptr'],2),(s['se_v_col'],1),(s['se_v_cell'],1),(0xcfe2,3)]:want[at:at+nbytes]=after[at:at+nbytes]
    want[0x43c0:0x43e8]=bytes((c<<4)|6 for c in fg);want[0xdbc0:0xdbe8]=fg;want[0x7e00:0x7f40]=wantbits;assert after==want;assert before[0x100:0x140]==after[0x100:0x140]
   costs.append(dict(state=state|dict(text=state['text'].hex()),control=counts[0],candidate=counts[1]))
  for (m,_),before in zip(machines,snapshots):assert reu(m)==before
  r=dict(status='passed',cases=len(costs),budgets=budgets,normal=costs[0],total_control=sum(x['control']for x in costs),total_candidate=sum(x['candidate']for x in costs),costs=costs,scope='Actualunchangedsharedstatus/residentprint + independentstatus/fontoracle, full64KiBRAM/lower64stack/whole16MiBguard; includeshotcaretstatuscostcomparison. CPUinstructions, notnativecycles.');(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',out,'normal',costs[0],flush=True)
 finally:
  for m,_ in machines:m.close()
if __name__=='__main__':
 out=ROOT/'build/geos-chrome-rows-status'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,Path(sys.argv[1]).resolve())
