"""Pinned KERNAL stack-content CFG for the standalone IEC API contract.

Branches are overapproximated except named, byte-checked device8/9 guards.
Returns/unwind PLA operate on actual abstract stack bytes, not a call-count guess.
No product/shared builds/native execution. Unresolved paths prohibit a bound.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import deque
import argparse,hashlib,json,sys,subprocess,zipfile,re,binascii
ROOT=Path(__file__).resolve().parents[1]
ROM=Path('/opt/homebrew/share/vice/C64/kernal-901227-03.bin')
BASE=ROOT/'build/geos-incremental-editor/20261025T085903355763Z/fixture'
# Official NMOS6502 opcodes only; decode from reached PC, never a linear sweep.
ROWS=['BRK.i ORA.ix - - - ORA.z ASL.z - PHP.i ORA.n ASL.a - - ORA.b ASL.b -',
'BPL.r ORA.iy - - - ORA.zx ASL.zx - CLC.i ORA.by - - - ORA.bx ASL.bx -',
'JSR.b AND.ix - - BIT.z AND.z ROL.z - PLP.i AND.n ROL.a - BIT.b AND.b ROL.b -',
'BMI.r AND.iy - - - AND.zx ROL.zx - SEC.i AND.by - - - AND.bx ROL.bx -',
'RTI.i EOR.ix - - - EOR.z LSR.z - PHA.i EOR.n LSR.a - JMP.b EOR.b LSR.b -',
'BVC.r EOR.iy - - - EOR.zx LSR.zx - CLI.i EOR.by - - - EOR.bx LSR.bx -',
'RTS.i ADC.ix - - - ADC.z ROR.z - PLA.i ADC.n ROR.a - JMP.ind ADC.b ROR.b -',
'BVS.r ADC.iy - - - ADC.zx ROR.zx - SEI.i ADC.by - - - ADC.bx ROR.bx -',
'- STA.ix - - STY.z STA.z STX.z - DEY.i - TXA.i - STY.b STA.b STX.b -',
'BCC.r STA.iy - - STY.zx STA.zx STX.zy - TYA.i STA.by TXS.i - - STA.bx - -',
'LDY.n LDA.ix LDX.n - LDY.z LDA.z LDX.z - TAY.i LDA.n TAX.i - LDY.b LDA.b LDX.b -',
'BCS.r LDA.iy - - LDY.zx LDA.zx LDX.zy - CLV.i LDA.by TSX.i - LDY.bx LDA.bx LDX.by -',
'CPY.n CMP.ix - - CPY.z CMP.z DEC.z - INY.i CMP.n DEX.i - CPY.b CMP.b DEC.b -',
'BNE.r CMP.iy - - - CMP.zx DEC.zx - CLD.i CMP.by - - - CMP.bx DEC.bx -',
'CPX.n SBC.ix - - CPX.z SBC.z INC.z - INX.i SBC.n NOP.i - CPX.b SBC.b INC.b -',
'BEQ.r SBC.iy - - - SBC.zx INC.zx - SED.i SBC.by - - - SBC.bx INC.bx -']
OPS=[None if token=='-' else tuple(token.split('.'))for row in ROWS for token in row.split()]
LENGTH=dict(i=1,a=1,n=2,z=2,zx=2,zy=2,ix=2,iy=2,r=2,b=3,bx=3,by=3,ind=3)
ROOTS=dict(SETNAM=0xffbd,SETLFS=0xffba,READST=0xffb7,OPEN=0xffc0,CLOSE=0xffc3,CHKIN=0xffc6,CHKOUT=0xffc9,CLRCHN=0xffcc,CHRIN=0xffcf,CHROUT=0xffd2,STOP=0xffe1)
# Each guard names its exact branch opcode/target; scope supplies its predicate.
# 9A may be stock screen3 or selected serial8/9. 99 for public CHRIN is8/9.
GUARDS={
0xfe0b:(0xd0,True,'BA8/9 != RS2322'),
0xf159:(0xd0,True,'selected CHRIN device8/9 != keyboard0'),
0xf168:(0xd0,True,'selected CHRIN device8/9 != screen3'),
0xf173:(0xb0,True,'selected CHRIN device8/9 >=3'),
0xf1d5:(0x90,False,'CHROUT device is screen3 or serial8/9, never tape/RS232'),
0xf21b:(0xf0,False,'lookup BA8/9 !=0'),0xf21f:(0xf0,False,'lookup BA8/9 !=3'),0xf221:(0xb0,True,'lookup BA8/9 >=3'),
0xf25d:(0xd0,True,'lookup BA8/9 !=0'),0xf264:(0xf0,False,'lookup BA8/9 !=3'),0xf266:(0xb0,True,'lookup BA8/9 >=3'),
0xf29f:(0xf0,False,'lookup BA8/9 !=0'),0xf2a3:(0xf0,False,'lookup BA8/9 !=3'),0xf2a5:(0xb0,True,'lookup BA8/9 >=3'),
0xf377:(0xf0,False,'OPEN BA8/9 !=0'),0xf37b:(0xf0,False,'OPEN BA8/9 !=3'),0xf37d:(0x90,False,'OPEN BA8/9 >=3'),
}

class Analysis:
 def __init__(self,rom,regions=(),opaque=(),summaries=None,stops=()):
  self.rom=rom;self.vectors={a:int.from_bytes(rom[0x1d30+a-0x314:0x1d32+a-0x314],'little')for a in range(0x314,0x334,2)}
  self.regions=regions;self.opaque=set(opaque)
  self.summaries=summaries or {}
  self.stops=set(stops)
 def byte(self,a):
  for start,data in self.regions:
   if start<=a<start+len(data):return data[a-start]
  if not 0xe000<=a<=0xffff:raise ValueError(('outside ROM',hex(a)))
  return self.rom[a-0xe000]
 def analyze(self,name,start,limit=1_000_000,initial_stack=(1,0x22)):
  initial=(start,initial_stack,(None,)*4) #C/Z/N/V, optional caller return0123
  q=deque([initial]);seen={initial};pred={initial:None};peak=initial;rompeak=initial;terminals=0;faults=[];pcs=set();clis=set();edges=0;usedguards=set();opaque_calls=set();summary_peak=0;summary_where=None;summary_state=None;stop_depths=set()
  def enqueue(state,parent):
   nonlocal peak,edges
   edges+=1
   if len(state[1])>128:raise ValueError(('positive stack cycle or >128',hex(state[0])))
   if len(state[1])>len(peak[1]):peak=state
   if state not in seen:seen.add(state);pred[state]=parent;q.append(state)
  while q:
   state=q.popleft();pc,st,flags=state;c,z,n,v=flags;pcs.add(pc)
   if 0xe000<=pc<=0xffff and len(st)>len(rompeak[1]):rompeak=state
   if len(seen)>limit:faults.append(('state budget',limit));break
   if pc in self.stops:stop_depths.add(len(st));continue
   if pc==0x123:
    if st:faults.append(('external return with residual stack',hex(pc),len(st)))
    else:terminals+=1
    continue
   try:
    if pc in self.opaque:
     # A reviewed non-IEC helper returns before any IEC is entered. Its own
     # internal depth is deliberately outside this transport-prefix result.
     opaque_calls.add(pc)
     if len(st)<2 or not all(isinstance(x,int)for x in st[-2:]):raise ValueError(('opaque helper has invalid return',hex(pc)))
     if pc in self.summaries:
      bound=len(st)-2+self.summaries[pc]
      if bound>summary_peak:summary_peak=bound;summary_where=pc;summary_state=state
     enqueue((((st[-2]<<8)|st[-1])+1,st[:-2],(None,)*4),state);continue
    opcode=self.byte(pc);opmode=OPS[opcode]
    if opmode is None:raise ValueError(('unofficial/invalid opcode',hex(pc),hex(opcode)))
    op,mode=opmode;length=LENGTH[mode];nxt=pc+length;arg=self.byte(pc+1)if length>1 else 0
    target=arg+(self.byte(pc+2)<<8)if length==3 else arg
    outst=st
    if op=='JSR':enqueue((target,st+((nxt-1)>>8,(nxt-1)&255),flags),state);continue
    if op=='RTS':
     if len(st)<2 or not all(isinstance(x,int)for x in st[-2:]):raise ValueError(('unresolved RTS',hex(pc),str(st[-4:])))
     enqueue((((st[-2]<<8)|st[-1])+1,st[:-2],flags),state);continue
    if op in ('BRK','RTI','TXS'):raise ValueError(('unexpected control/stack reset',hex(pc),op))
    if op=='JMP':
     if mode=='ind':
      if target not in self.vectors:raise ValueError(('unresolved indirect',hex(pc),hex(target)))
      target=self.vectors[target]
     enqueue((target,st,flags),state);continue
    if mode=='r':
     taken={'BCC':None if c is None else not c,'BCS':c,'BNE':None if z is None else not z,'BEQ':z,'BMI':n,'BPL':None if n is None else not n,'BVS':v,'BVC':None if v is None else not v}[op]
     if pc in GUARDS:
      expected,taken,reason=GUARDS[pc];assert opcode==expected,(hex(pc),hex(opcode));usedguards.add(pc)
     dest=nxt+(arg if arg<128 else arg-256)
     for yes in (False,True):
      if taken is None or bool(taken)==yes:enqueue((dest if yes else nxt,st,flags),state)
     continue
    if op in ('PHA','PHP'):outst=st+(('P',*flags)if op=='PHP'else None,)
    if op in ('PLA','PLP'):
     if not st:raise ValueError(('underflow',hex(pc),op))
     top=st[-1];outst=st[:-1]
     if op=='PLP':c,z,n,v=top[1:]if isinstance(top,tuple)and top[0]=='P'else(None,)*4
     else:z,n=(int(top==0),int(bool(top&128)))if isinstance(top,int)else(None,None)
    elif op=='CLC':c=0
    elif op=='SEC':c=1
    elif op=='CLV':v=0
    elif op in ('ADC','SBC'):c=z=n=v=None
    elif op in ('ASL','LSR','ROL','ROR'):c=z=n=None
    elif op in ('CMP','CPX','CPY'):c=z=n=None
    elif op=='BIT':z=n=v=None
    elif op in ('LDA','LDX','LDY'):
     z,n=(int(arg==0),int(bool(arg&128)))if mode=='n'else(None,None)
    elif op in ('AND','ORA','EOR','INC','DEC','INX','DEX','INY','DEY','TAX','TAY','TXA','TYA','TSX'):z=n=None
    if op=='CLI':clis.add(pc)
    enqueue((nxt,outst,(c,z,n,v)),state)
   except (ValueError,AssertionError)as error:faults.append(str(error))
  def path(at):
   result=[]
   while at is not None:result.append(dict(pc=at[0],bytes=len(at[1])));at=pred[at]
   return result[::-1]
  return dict(name=name,root=start,status='bounded'if not faults else'unresolved',states=len(seen),edges=edges,instruction_addresses=sorted(pcs),max_stack_including_caller=len(peak[1]),rom_additional_bytes=len(peak[1])-2,max_live_at_ROM_including_caller=max(len(rompeak[1]),summary_peak),rom_peak_pc=rompeak[0],summary_peak=summary_peak,summary_where=summary_where,summary_stack=list(summary_state[1])if summary_state else[],summary_path=path(summary_state),stop_depths=sorted(stop_depths),peak_pc=peak[0],peak_stack=list(peak[1]),terminal_states=terminals,cli_addresses=sorted(clis),opaque_non_IEC_calls=sorted(opaque_calls),used_guards=[dict(pc=a,reason=GUARDS[a][2])for a in sorted(usedguards)],faults=faults[:30],fault_count=len(faults),peak_path=path(peak))

def calibration():
 assert len(OPS)==256 and sum(x is not None for x in OPS)==151
 def check(code,sub,**expected):
  r=bytearray([0xea])*8192;r[:len(code)]=code;r[0x100:0x100+len(sub)]=sub
  result=Analysis(bytes(r)).analyze('calibration',0xe000)
  for n,v in expected.items():assert result[n]==v,(n,result[n],v)
 # Caller2 + JSR2 + PHP1 + PHA1; PHP/PLP must preserve flags exactly.
 check(bytes.fromhex('2000e160'),bytes.fromhex('0848682860'),status='bounded',max_stack_including_caller=6)
 # Actual KERNAL-style discard-subroutine-return + branch on known return high.
 check(bytes.fromhex('2000e160'),bytes.fromhex('6868d0016060'),status='bounded',max_stack_including_caller=4)
 check(bytes.fromhex('4860'),b'',status='unresolved')
 check(bytes.fromhex('6c0010'),b'',status='unresolved')
 check(bytes.fromhex('08d0fd60'),b'',status='unresolved') #positive-stack cycle

def caller_proof(out,base,rom):
 s=json.loads((base/'build/editor-report.json').read_text())['symbols'];prg=(base/'build/editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little')
 def resident(a,b):return(a,prg[2+a-load:2+b-load])
 named={v:sorted(k for k,x in s.items()if x==v)for v in set(s.values())}
 ext={v for v in s.values()if 0x0800<=v<0x4000}
 results=[]
 def analyze(name,entry,regions,summaries=None,stops=()):
  inside={v for a,b in regions for v in range(a,a+len(b))};a=Analysis(rom,regions,ext-inside,summaries,stops)
  if stops:a.vectors[s['ovl_ptr']]=0xb010
  r=a.analyze(name,entry);r['opaque_names']={hex(v):named[v]for v in r['opaque_non_IEC_calls']};results.append(r);assert r['status']=='bounded',(name,r['faults'])
  return r
 # Cache helpers finish before module entry. Compute retained live frames from
 # actual resident CFG, stopping exactly at fixed B010 entry, not guessed bytes.
 cache=analyze('overlay-module-entry',s['se_overlay_call'],[resident(s['se_overlay_call'],s['jump_overlay']+3)],stops=[0xb010]);assert cache['stop_depths']==[5]
 local=[]
 for name in ['block','aux','geosfontin']:
  image=(base/'build/overlays'/(name+'.seo')).read_bytes();assert image[:4]==b'SEO2'and image[5]==1;raw=image[36:];entry=0xb010
  if name=='block':
   # Actual branch from C10entry: FT>=C0 tail-jumps to transport, no extra frame.
   assert raw[16:23]==bytes([0xad,s['se_overlay_frame']&255,s['se_overlay_frame']>>8,0xc9,0xc0,0x90,3])and raw[23]==0x4c
   entry=int.from_bytes(raw[24:26],'little')
  r=analyze(name,entry,[(0xb000,raw)]);r['image_sha256']=hashlib.sha256(image).hexdigest();local.append(r)
  if name=='block':assert not r['opaque_non_IEC_calls']
 # Initial module summary includes the jump_overlay JSR2. Cache additionally
 # retains caller JSR2+slotPHA1: cache-entry5 minus module-initial2 =3.
 overlay=max(r['max_live_at_ROM_including_caller']for r in local)+3
 summaries={s['se_overlay_call']:overlay}
 read=compiled_resident(out,base,'iec/overlay_read.s','se_overlay_read','file_ptr','se_file_device')
 analyze('resident-overlay-read',s['se_overlay_read'],read)
 dispatch=compiled_resident(out,base,'editor_file/dispatch.s','se_editor_file_call')
 commands=compiled_resident(out,base,'editor/commands.s','se_editor_input',rodata='hot_commands')
 for name in ['se_editor_file_call','se_editor_file_pump']:
  analyze(name,s[name],dispatch,summaries)
 for name in ['se_editor_input','se_editor_command','se_editor_service']:
  analyze(name,s[name],commands+dispatch,summaries)
 cold=next(x for x in json.loads((base/'build/editor-report.json').read_text())['segments']if x['name']=='COLD')
 reader=next(r for r in results if r['name']=='resident-overlay-read')['max_live_at_ROM_including_caller']
 font=next(r for r in local if r['name']=='geosfontin')['max_live_at_ROM_including_caller']
 r=analyze('cold-startup',s['se_editor_startup'],[resident(cold['start'],cold['end']+1)],{s['se_overlay_read']:reader,s['se_overlay_call']:font+3})
 # Only direct cold overlay call is the explicit C28 font importer. History/
 # document helpers use warmed REU images and cannot perform IEC internally.
 coldcalls=[pc for pc in r['instruction_addresses']if cold['start']<=pc<=cold['end']-2 and prg[2+pc-load]==0x20 and int.from_bytes(prg[3+pc-load:5+pc-load],'little')==s['se_overlay_call']]
 assert len(coldcalls)==1 and prg[2+coldcalls[0]-4-load:2+coldcalls[0]-load]==bytes.fromhex('a91ca201')
 return dict(status='bounded',overlay_summary_including_caller=overlay,results=results,max_IEC_bytes_beyond_idle=max(r['max_live_at_ROM_including_caller']for r in results if r['name']in('se_editor_input','se_editor_command','se_editor_service')),cold_IEC_bytes_beyond_entry=r['max_live_at_ROM_including_caller'],scope='IEC-live caller prefixes only. Reviewed non-IEC helpers return before IEC; their internal stack maxima are not bounded by this result. Initial two bytes represent actual idle JSR into input/service.')

def compiled_resident(out,base,source,first,zp=None,bss=None,rodata=None):
 """Rebuild only an audited source object privately and compare exact bytes."""
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];sources=out/'frozen-source'
 if not sources.exists():
  sources.mkdir()
  with zipfile.ZipFile(base/'product-sources.zip')as z:
   for n in z.namelist():
    if n.startswith('src/')and n.endswith(('.s','.inc')):z.extract(n,sources)
 tag=source.replace('/','-').replace('.s','');obj=out/(tag+'.o')
 def command(*args):
  p=subprocess.run(list(map(str,args)),capture_output=True,text=True,cwd=ROOT)
  assert not p.returncode,p.stdout+p.stderr
 command('ca65','-g','-I',sources/'src','-o',obj,sources/'src'/source)
 command(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(tag+'-aliases.s'),obj)
 command('ca65','-o',out/(tag+'-aliases.o'),out/(tag+'-aliases.s'))
 regions=[('CODE',s[first],True)]
 if rodata:regions.append(('RODATA',s[rodata],True))
 if zp:regions.append(('ZEROPAGE',s[zp],False))
 if bss:regions.append(('BSS',s[bss],False))
 cfg=out/(tag+'.cfg');cfg.write_text('MEMORY {'+''.join(f'M{i}:file="{out/(tag+name+".bin")}"'+f',start=${addr:04X},size=$1000;'if data else f'M{i}:file="",start=${addr:04X},size=$1000;'for i,(name,addr,data)in enumerate(regions))+'} SEGMENTS {'+''.join(f'{name}:load=M{i},type='+('zp'if name=='ZEROPAGE'else'ro'if data else'bss')+';'for i,(name,addr,data)in enumerate(regions))+'}')
 command('ld65','-C',cfg,'-o',out/(tag+'.unused'),obj,out/(tag+'-aliases.o'))
 prg=(base/'build/editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');result=[]
 for name,addr,data in regions:
  if data:
   raw=(out/(tag+name+'.bin')).read_bytes();assert raw==prg[2+addr-load:2+addr-load+len(raw)],(source,name,'not byte identical')
   result.append((addr,raw))
 return result

def foreground_proof(out,base,rom,callers,idle_log=None):
 """Layer actual R, C, then root graphs using the enforced slot nesting DAG.

 R cannot load another slot; C may load R; root may load C or R. The only
 summary seam is the byte/instruction-audited resident overlay trampoline.
 All formerly opaque resident helpers execute in the graph at every layer.
 """
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];freeze=json.loads((base/'freeze.json').read_text());prg=(base/'build/editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little')
 assert hashlib.sha256(prg).hexdigest()==report['sha256']==freeze['prg_sha256']
 # Reuse the independently proved16-byte interrupt allowance only for the exact
 # audited handler source, privately reassembled and bytechecked at this seal.
 with zipfile.ZipFile(base/'product-sources.zip')as z:irq_source=z.read('src/input/keyboard_irq.s')
 irq_sha=hashlib.sha256(irq_source).hexdigest()
 assert irq_sha=='70ac420e462937a4e3031e2d032747dd3951bebed50da35c46313a352426b82c'
 compiled_resident(out,base,'input/keyboard_irq.s','se_input_init',bss='se_input_head')
 cold=next(x for x in report['segments']if x['name']=='COLD')
 regions=[(0x1000,prg[2+0x1000-load:2+0x4000-load]),(cold['start'],prg[2+cold['start']-load:2+cold['end']+1-load])]
 def bound(r):return max(r['max_stack_including_caller'],r['summary_peak'])
 results=[]
 def analyze(name,entry,extra=(),summary=None,stops=(),initial=(1,0x22)):
  a=Analysis(rom,list(extra)+regions,opaque=[s['se_overlay_call']]if summary is not None else(),summaries={s['se_overlay_call']:summary}if summary is not None else{},stops=stops)
  if name=='loader':a.vectors[s['ovl_ptr']]=0xb010
  r=a.analyze(name,entry,initial_stack=initial);results.append(r);assert r['status']=='bounded',(name,r['faults']);return r
 loader=analyze('loader',s['se_overlay_call'],stops=[0xb010]);assert loader['stop_depths']==[5]
 L=bound(loader)
 images={}
 for name in freeze['names']:
  image=(base/'build/overlays'/(name+'.seo')).read_bytes()
  assert hashlib.sha256(image).hexdigest()==freeze['assets'][name]
  assert image[:4]==b'SEO2'and image[36:52]==bytes.fromhex(report['resident_binding']['digest'])
  assert binascii.crc_hqx(image[36:],0xffff)==int.from_bytes(image[12:14],'little')
  assert int.from_bytes(image[10:12],'little')==16
  images[name]=image
 R=[];C=[]
 for name,image in images.items():
  if image[5]:continue
  r=analyze('R:'+name,0xa010,[(0xa000,image[36:])],L,stops=[0x900]if name=='lifecopy'else())
  if name=='lifecopy':assert r['stop_depths']==[2]
  R.append(r)
 Rmax=max(map(bound,R));Ccall=max(L,Rmax+3)
 for name,image in images.items():
  if not image[5]:continue
  C.append(analyze('C:'+name,0xb010,[(0xb000,image[36:])],Ccall))
 Cmax=max(map(bound,C));rootcall=max(L,Rmax+3,Cmax+3)
 roots=[]
 for name in ('se_editor_input','se_editor_command','se_editor_service','se_idle','se_entry'):
  roots.append(analyze(name,s[name],summary=rootcall,initial=()if name in('se_idle','se_entry')else(1,0x22)))
 entryidle=analyze('entry-to-idle',s['se_entry'],summary=rootcall,stops=[s['se_idle']],initial=());assert entryidle['stop_depths']==[0]
 # R26's explicit nonreturning commit is a declared barrier, not an unexplained
 # target: exact thunk and C29 template both start SEI/CLD/LDX#FF/TXS.
 thunk=images['lifecopy'][36:];reset=bytes.fromhex('78d8a2ff9a');assert thunk.count(reset)==1
 reset_offset=thunk.index(reset)
 commit=analyze('fresh-thunk-after-TXS',0x905,[(0x900,thunk[reset_offset:])],rootcall,stops=[0xa00],initial=())
 assert commit['stop_depths']==[0]and bound(commit)==0
 prelude=images['lifectrl'][36+0x800:36+0x900];assert prelude[:5]==bytes.fromhex('78d8a2ff9a')
 resume=analyze('fresh-prelude-after-TXS',0xa05,[(0xa00,prelude)],rootcall,initial=())
 # Enumerate every previously opaque helper, now fully decoded, in the most
 # permissive root context. New C6/R30 bodies are additionally explicit above.
 helpers=[];aliases={v:sorted(k for k,x in s.items()if x==v)for v in set(s.values())}
 helper_addresses=sorted({v for r in callers['results']for v in r['opaque_non_IEC_calls']})
 for address in helper_addresses:
  r=analyze('helper:'+aliases[address][0],address,summary=rootcall);helpers.append(dict(address=address,names=aliases[address],bound_including_caller=bound(r)))
 F=max(bound(r)for r in roots)
 result=dict(status='bounded',resident_sha256=hashlib.sha256(prg).hexdigest(),binding=report['resident_binding']['digest'],assets=len(images),interrupt_source_sha256=irq_sha,interrupt_source_matches_emitted=True,loader=L,R=Rmax,C=Cmax,C_overlay_summary=Ccall,root_overlay_summary=rootcall,foreground_beyond_entry_idle=F,one_IRQ_NMI=16,relative_combined=F+16,fresh_resume_from_FF=max(F,bound(resume))+16,helper_roots=helpers,results=results,scope='All actual R/C images and full resident/cold instruction graphs. Only overlay-call summaries remain; legal slot nesting makes the layer order acyclic. R26 stops at explicit0900 stack-reset barrier; fresh immutable prelude resumes at0A05 after TXS. Valid owned RAM/frame/channel/vector contracts required.')
 if idle_log:
  text=idle_log.read_text();line=next(x for x in text.splitlines()if x.startswith('.;'));tokens=line.split();pc=int(tokens[0][2:],16);sp=int(tokens[4],16)
  native=idle_log.parent.parent;native_report=json.loads((native/'editor-report.json').read_text());assert native_report['sha256']==report['sha256']
  baseline=analyze('natural-baseline-PC',s['se_idle'],summary=rootcall,stops=[pc],initial=());assert baseline['stop_depths']==[0]
  assert tokens[6]=='36'and int(tokens[7],2)&4==0
  result['native_baseline']=dict(log=str(idle_log),sha256=hashlib.sha256(idle_log.read_bytes()).hexdigest(),pc=pc,sp=sp,preexisting_bytes=255-sp,source='Parent native read-only breakpoint/register capture before stopwatch PC/SP intervention; this verifier consumes evidence, launches no emulator.')
  result['absolute_stack_bytes_from_FF']=255-sp+F+16;result['minimum_SP']=sp-F-16
 return result

def run(out,rompath,base,foreground=False,idle_log=None):
 raw=rompath.read_bytes();assert hashlib.sha256(raw).hexdigest()=='83c60d47047d7beab8e5b7bf6f67f80daa088b7a6a27de0d7e016f6484042721'
 calibration()
 a=Analysis(raw);results=[]
 for name,entry in ROOTS.items():
  result=a.analyze(name,entry);results.append(result);print(name,result['status'],result['states'],result['rom_additional_bytes'],hex(result['peak_pc']),result['faults'][:2],flush=True)
  (out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
 assert all(r['status']=='bounded'for r in results)
 byname={r['name']:r for r in results}
 assert {0xf3f1,0xf3f2,0xf707,0xf715,0xedad,0xedb2}<=set(byname['OPEN']['instruction_addresses'])
 assert {0xee3e,0xee42,0xee44,0xedb2}<=set(byname['CHRIN']['instruction_addresses'])
 assert {0xf6f3,0xf6f4,0xf6f9}<=set(byname['STOP']['instruction_addresses'])
 callers=caller_proof(out,base,raw)
 result=dict(status='bounded-IEC',calibration='passed: official151 opcodes, nested push6, destructive return unwind4, unknown return/indirect/positive-stack-cycle refuse',rom_sha256=hashlib.sha256(raw).hexdigest(),fixture=str(base),resident_sha256=hashlib.sha256((base/'build/editor.prg').read_bytes()).hexdigest(),source_zip_sha256=hashlib.sha256((base/'product-sources.zip').read_bytes()).hexdigest(),vectors=a.vectors,roots=results,callers=callers,combined_IEC_plus_one_IRQ_NMI=callers['max_IEC_bytes_beyond_idle']+16,declared_stack_contract_closed=False,scope='Stack-content CFG overapproximation under explicit byte-checked serialdevice8/9 guards; data/status/timing branches nondeterministic. IEC-live bound relative to idle/entry SP; non-IEC helper maxima and native BASIC SYS baseline remain separate.')
 if foreground:
  result['foreground']=foreground_proof(out,base,raw,callers,idle_log);result['status']='bounded-declared-foreground'
  result['declared_stack_contract_closed']=bool(idle_log)
  result['scope']=result['foreground']['scope']+' Absolute bound requires the matching nonintervening native BASIC SYS baseline and the separately proved IRQ/NMI allowance. This is not arbitrary replacement-ROM/vector or recursive-NMI proof.'
  print('FOREGROUND',json.dumps({k:v for k,v in result['foreground'].items()if k not in('results','helper_roots')}),flush=True)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,default=ROM);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--foreground',action='store_true');p.add_argument('--idle-log',type=Path);args=p.parse_args();out=ROOT/'build/kernal-stack-bound'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,args.rom,args.fixture,args.foreground,args.idle_log)
