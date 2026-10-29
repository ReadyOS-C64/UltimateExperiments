"""Private actual lexer producer/typed53 lexicalpage probe; no main build."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,re,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_editor as geos
from supermark_model import lex,blocks
from overlays import wrap
D=ROOT/'src/cache/lexical-probe';BASE=ROOT/'build/cache-editor-product/20261026T035310363807Z/fixture'
F=0x8d00;IO=F+448

def command(args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 assert not p.returncode,p.stdout+p.stderr
 return p.stdout

def labels(path):return {n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',path.read_text())}

def build(out,base):
 out.mkdir(parents=True);r=json.load(open(base/'build/editor-report.json'));binding=r['resident_binding']['digest']
 with zipfile.ZipFile(base/'product-sources.zip')as z:(out/'lexer.s').write_bytes(z.read('src/supermark/lexer.s'))
 (out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 objs=[]
 for name,source,defs in [('worker',D/'worker.s',[]),('lexer',out/'lexer.s',['SE_SM_CODE_ONLY=1']),('state',out/'lexer.s',['SE_SM_STATE_ONLY=1'])]:
  p=out/(name+'.o');command(['ca65','-g','-I',out,'-I',ROOT/'src',*[a for d in defs for a in ['-D',d]],'-o',p,source]);objs.append(p)
 command(['python3','tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objs]);command(['ca65','-o',out/'aliases.o',out/'aliases.s'])
 (out/'worker.cfg').write_text('MEMORY { C:file=%O,start=$B000,size=$1000;S:file="",start=$8D5E,size=60; } SEGMENTS { LX_CODE:load=C,type=ro;SM_LEXER:load=C,type=ro;SM_STATE:load=S,type=bss; }')
 command(['ld65','-C',out/'worker.cfg','-o',out/'worker.bin','-Ln',out/'worker.lbl','-m',out/'worker.map',*objs,out/'aliases.o'])
 raw=(out/'worker.bin').read_bytes();assert len(raw)<=4096 and raw[:16]==bytes.fromhex(binding)
 sizes={name:sum(int(x)for x in re.findall(r'Size:\s+(\d+)',command(['od65','--dump-segments',out/(name+'.o')])))for name in ['worker','lexer','state']}
 result=dict(total_bytes=len(raw),sizes=sizes,sha256=hashlib.sha256(raw).hexdigest(),binding=binding)
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');print('BUDGET',result,flush=True);return raw,labels(out/'worker.lbl'),result

def build_page(out,base):
 out.mkdir(parents=True);report=json.load(open(base/'build/editor-report.json'));binding=report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 objects=[]
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in ('core','page'):(out/(name+'.s')).write_bytes(z.read('src/cache/arena/'+name+'.s'))
 for name,source in [('entry',D/'page.s'),('core',out/'core.s'),('reader',out/'page.s')]:
  obj=out/(name+'.o');command(['ca65','-g','-I',out,'-I',ROOT/'src','-o',obj,source]);objects.append(obj)
 command(['python3','tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);command(['ca65','-o',out/'aliases.o',out/'aliases.s'])
 (out/'page.cfg').write_text('MEMORY {R:file=%O,start=$A000,size=$1000;} SEGMENTS {CODE:load=R,type=ro;RODATA:load=R,type=ro;}')
 command(['ld65','-C',out/'page.cfg','-o',out/'page.bin','-Ln',out/'page.lbl','-m',out/'page.map',*objects,out/'aliases.o'])
 raw=(out/'page.bin').read_bytes();assert len(raw)<=4096 and raw[:16]==bytes.fromhex(binding)
 sizes={name:sum(int(x)for x in re.findall(r'Size:\s+(\d+)',command(['od65','--dump-segments',out/(name+'.o')])))for name in ('entry','core','reader')}
 result=dict(total_bytes=len(raw),sizes=sizes,sha256=hashlib.sha256(raw).hexdigest());(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');print('PAGE_BUDGET',result,flush=True);return raw,labels(out/'page.lbl'),result

class Fixture(geos.Fixture):
 def lx(self,op):
  self.put('se_overlay_frame',op,1);r,n=self.fast_call(self.s['se_overlay_call'],a=29,x=1);self.total_instructions+=n;return r,n
 def lp(self,op):
  self.put('se_overlay_frame',op,1);r,n=self.fast_call(self.s['se_overlay_call'],a=26,x=0);self.total_instructions+=n;return r,n

def run(out,base,build_only=False):
 out.mkdir(parents=True);frozen,identity=geos.freeze(out,base);raw,linked,budget=build(out/'link',frozen)
 page_raw,page_linked,page_budget=build_page(out/'page',frozen)
 if build_only:return budget,page_budget
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True);cases=[]
 report=json.load(open(frozen/'build/editor-report.json'));digest=bytes.fromhex(report['resident_binding']['digest']);api=(f.s['se_overlay_call'],f.s['se_overlay_frame'])
 f.assets['lifectrl']=wrap(raw,1,29,api=api,binding_digest=digest);f.assets['lifecopy']=wrap(page_raw,0,26,api=api,binding_digest=digest)
 (out/'private-worker.seo').write_bytes(f.assets['lifectrl']);(out/'private-page.seo').write_bytes(f.assets['lifecopy'])
 def query(data,target):
  f.source(data);f.command(99);f.render();assert f.get('se_bc_flags',1)&15==1
  for n in ('se_i_ready','se_i_count','se_n_cache_count'):f.put(n,0,1)
  f.put('se_f_owner',4,1);f.m.write(0x8b40+21,0);f.m.load(0x8b40,target.to_bytes(3,'little'))
  f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  steps=0
  while r.a==1 and not r.p&1:
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1);steps+=1;assert steps<20000
  assert not r.p&1 and r.a==0 and f.m.read(0x8b40+5)==5,(r.a,r.p,f.read(0x8b40,29).hex())
  # Actual C35 has left fullrootFS59/AUTH13 and genuineCR96 in its ABIframe.
  f.linked=linked;return steps
 def original_window(data,body,end,language,q,count):
  # Reference-only caller packet staging: actual original packagedC25 checks
  # every visible byte against R14. Preserve the privatecache caller phase.
  phase=f.read(F,1152);gsem=f.read(0x8b40,192);packet=f.read(0x8200,512);before=f.reu();canonical=f.canonical();start=f.total_instructions;loads=f.get('se_overlay_loads',2)
  assert not f.get('se_doc_read_locks',1) and not any(f.read(0x912c,2))
  f.m.load(0x8b40,q.to_bytes(3,'little')+bytes([language,count]));f.m.load(0x8b40+12,end.to_bytes(3,'little'));f.m.load(0x8b40+15,body.to_bytes(3,'little'));f.m.load(0x8200,data[q:q+count])
  f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=25,x=1);f.total_instructions+=n
  steps=0
  while r.a==1 and not r.p&1:
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=25,x=1);f.total_instructions+=n;steps+=1;assert steps<100000
  assert not r.p&1 and r.a==0,('originalC25',r.a,r.p)
  answer=f.read(0x8300,count);used=f.total_instructions-start;load_delta=(f.get('se_overlay_loads',2)-loads)&65535
  assert f.reu()==before and f.canonical()==canonical and not f.get('se_doc_read_locks',1)
  f.m.load(F,phase);f.m.load(0x8b40,gsem);f.m.load(0x8200,packet)
  return answer,used,load_delta
 def free_builder(data,target):
  query(data,target);r,_=f.lx(0);assert not r.p&1 and r.a==1
  r,_=f.lp(0);assert not r.p&1 and r.a==1
  for _ in range(256):
   r,_=f.lp(1);assert not r.p&1
   if r.a!=1:break
  assert r.a==0 and f.m.read(F+79)==2
  return f.m.read(F+80)
 def fault_gate():
  groups=[];source=geos.native_text('Prose before.\r:::basic\r10 PRINT "Hi":REM tail\r:::\rTail.');target=source.index(geos.native_text('10 PRINT'))
  # Activeowneropacity is tested through actual sealed selectors/loaders.
  query(source,target)
  for owner in (0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);phase=f.read(F,576);reu=f.reu()
   for fn,ops in ((f.lx,range(5)),(f.lp,range(6))):
    for op in ops:
     r,_=fn(op);assert r.p&1 and r.a==0xb2 and f.read(F,576)==phase and f.reu()==reu
  f.put('se_f_owner',4,1);groups.append('sixforeignowners/all11actualopcodes/opaque576+wholeREU')
  for caps in (0,1):
   f.put('se_render_caps',caps,1);phase=f.read(F,576);reu=f.reu();locks=f.get('se_doc_read_locks',1)
   for fn in (f.lx,f.lp):
    r,_=fn(0);assert not r.p&1 and r.a==2 and f.read(F,576)==phase and f.reu()==reu and f.get('se_doc_read_locks',1)==locks
  f.put('se_render_caps',3,1);groups.append('Plain+Markdown-bypass-no-frame-no-lease-no-sourcefeed')
  # Corrupt classifiedCR CRC, and mismatched rootFS59 cannot start lexing.
  query(source,target);f.m.write(F+259+74,f.m.read(F+259+74)^1);reu=f.reu();r,_=f.lx(0);assert r.p&1 and not f.get('se_doc_read_locks',1) and f.reu()==reu
  query(source,target);f.m.write(F+32+25,f.m.read(F+32+25)^1);reu=f.reu();r,_=f.lx(0);assert r.p&1 and r.a==0xb1 and not f.get('se_doc_read_locks',1) and f.reu()==reu
  groups.append('actualCR-CRC/rootFS59-mismatch-no-lexer-authority')
  # Idempotent cancellation at real heldoutput and during everysealphase.
  for point in ('before-span','held-span','descriptor','payloadCRC','header','page-valid','directory','directory-valid'):
   page=free_builder(source,target);before=f.reu();canonical=f.canonical()
   if point!='before-span':
    for _ in range(1000):
     r,_=f.lx(1);assert not r.p&1
     ready=f.m.read(F+4)
     if ready==1:
      if point=='held-span':break
      r,_=f.lp(3);assert not r.p&1 and r.a==0
      f.lx(3)
     elif ready==2:break
    if point!='held-span':
     r,_=f.lp(5);assert not r.p&1
     desired={'descriptor':1,'payloadCRC':1,'header':2,'page-valid':3,'directory':4,'directory-valid':5}[point]
     for _ in range(100):
      if f.m.read(F+92)==desired:break
      r,_=f.lp(1);assert not r.p&1 and r.a==1
     assert f.m.read(F+92)==desired
   old=f.reu();r,_=f.lp(2);assert not r.p&1 and r.a==0;r,_=f.lx(2);assert not r.p&1 and r.a==0;f.lx(2)
   assert f.reu()==old and f.canonical()==canonical and not f.get('se_doc_read_locks',1)
   # Cancellation permits only candidateunreachablepage/directorypartial;
   # roots and everypreviouslyreferencedpage remain byteexact.
   token=f.read(f.s['se_bc_arena'],5);obj=token[0];b=f.m.read(f.s['se_reu_map']+f.m.read(f.s['object_extents']+obj*16));lo=b*65536;after=f.reu();wanted=bytearray(before);wanted[lo+page*4096:lo+(page+1)*4096]=after[lo+page*4096:lo+(page+1)*4096];d=lo+0x100+page*8;wanted[d:d+8]=after[d:d+8]
   assert after==wanted and after[lo:lo+256]==before[lo:lo+256] and not after[d+3]
  groups.append('8cancelpoints/idempotent-ownedlease/oldroots+referencedpages+foreignREU-exact')
  # Pending sourcechange and capabilityfaults stop before any new payloadDMA.
  for name in ('se_bc_ticket','se_bc_incarnation','se_r_revision','se_doc_generation'):
   free_builder(source,target);at=f.s[name];old=f.m.read(at);f.m.write(at,old^1);reu=f.reu();r,_=f.lp(1);assert r.p&1 and f.reu()==reu
   f.m.write(at,old);f.lp(2);f.lx(2);assert not f.get('se_doc_read_locks',1)
  free_builder(source,target);token=f.read(f.s['se_bc_arena'],5);logical=f.m.read(f.s['object_extents']+token[0]*16);physical=f.m.read(f.s['se_reu_map']+logical);at=f.s['se_reu_physical_owner']+physical;old=f.m.read(at);f.m.write(at,0x77);reu=f.reu();r,_=f.lp(1);assert r.p&1 and r.a==0x34 and f.reu()==reu;f.m.write(at,old);f.lp(2);f.lx(2)
  groups.append('ticket/incarnation/live-source-generation+revision/typed-map-guard-before-DMA')
  # Keep current overlay admission valid while the held reader belongs to
  # an old provider epoch; changing the live epoch first correctly prevents
  # the loader from entering C29 at all (separate residentcleanup contract).
  free_builder(source,target);f.m.write(F+173+27,f.m.read(F+173+27)^1);f.put('se_doc_read_locks',7,1);r,_=f.lx(2);assert not r.p&1 and f.get('se_doc_read_locks',1)==7;f.put('se_doc_read_locks',0,1);f.lp(2)
  groups.append('staleepoch-cancel-preserves-seven-foreign-readleases')
  # Realspanpressure; no truncatedpage or lexicalcompleteness publication.
  dense=geos.native_text('A')*2000+geos.native_text('\r:::basic\r')+geos.native_text('10 PRINT "x":')*200+geos.native_text('\r:::\rTail.')
  target=dense.index(geos.native_text('10 PRINT'));page=free_builder(dense,target);before=f.reu();canonical=f.canonical();stream=False
  for _ in range(30000):
   r,_=f.lx(1);assert not r.p&1
   if f.m.read(F+4)==1:
    r,_=f.lp(3);assert not r.p&1
    if r.a==3:stream=True;break
    assert r.a==0;f.lx(3)
   elif f.m.read(F+4)==2:break
  assert stream and f.m.read(F+79)==0 and int.from_bytes(f.read(F+83,2),'little')==562
  f.lp(2);f.lx(2);assert not f.get('se_doc_read_locks',1) and f.canonical()==canonical
  token=f.read(f.s['se_bc_arena'],5);b=f.m.read(f.s['se_reu_map']+f.m.read(f.s['object_extents']+token[0]*16));lo=b*65536;after=f.reu();wanted=bytearray(before);wanted[lo+page*4096:lo+(page+1)*4096]=after[lo+page*4096:lo+(page+1)*4096]
  assert after==wanted and after[lo+0x100+page*8:lo+0x108+page*8]==bytes(8)
  groups.append('563rdspan-STREAM/candidateunreferenced/no-truncatedLEX/rootunchanged')
  print('FAULT_GROUPS',groups,flush=True);return groups
 def check(tag,data,target,extra_windows=()):
  qsteps=query(data,target);before=f.reu();canonical=f.canonical();catalog=f.catalog();ram=f.read(0,65536);start=f.total_instructions;loads=f.get('se_overlay_loads',2)
  # Authenticate actual feed entry through the real C29 activecatalog tag.
  dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('lifectrl')+1,0,linked['se_sl_feed'],0,0,0)
  r,n=f.lx(0);assert not r.p&1 and r.a==1,(tag,'begin',r.a,r.p)
  body=int.from_bytes(f.read(linked['se_sl_pos'],3),'little');end=int.from_bytes(f.read(F+24,3),'little');language=f.m.read(F+6);events=[];steps=0
  r,n=f.lp(0);assert not r.p&1 and r.a==1
  for _ in range(256):
   r,n=f.lp(1);assert not r.p&1 and r.a in (0,1),('FIND',r.a,r.p,f.read(F,94).hex(),f.read(F+387,61).hex())
   if not r.a:break
  else:raise AssertionError('boundedfree-page search')
  page=f.m.read(F+80);assert page and f.m.read(F+79)==2
  while True:
   prior=int.from_bytes(f.read(F+41,3),'little');reads=int.from_bytes(f.read(F+47,3),'little');r,n=f.lx(1);steps+=1
   assert not r.p&1 and r.a==1,(tag,'STEP',r.a,r.p)
   assert int.from_bytes(f.read(F+41,3),'little')-prior<=32
   assert int.from_bytes(f.read(F+47,3),'little')-reads<=1
   assert steps<100000
   ready=f.m.read(F+4)
   if ready:
    output=f.read(IO,7);snapshot=f.read(F,94);again,_=f.lx(1);assert again.a==1 and not again.p&1 and f.read(IO,7)==output and f.read(F,94)==snapshot
    if ready==1:
     events.append((int.from_bytes(output[1:4],'little'),int.from_bytes(output[4:7],'little'),output[0]))
     stored,_=f.lp(3);assert not stored.p&1 and stored.a==0,(tag,'APPEND',stored.a,stored.p)
    else:
     final,_=f.lp(5);assert not final.p&1 and final.a==1
     for _ in range(100):
      final,_=f.lp(1);assert not final.p&1,(tag,'SEAL',final.a,final.p)
      if not final.a:break
     else:raise AssertionError('boundedlexicalpage seal')
     assert f.m.read(F+79)==3
    ack,_=f.lx(3);assert not ack.p&1
    if ready==2:assert ack.a==0;break
  expected=list(lex(data[body:end],language,start=body))
  assert events==expected,(tag,events,expected)
  assert int.from_bytes(f.read(F+41,3),'little')==end-body
  assert dll.gm_metric(0)==end-body,('actualfeedPCcalls',dll.gm_metric(0),end-body)
  build_instructions=f.total_instructions-start;build_loads=(f.get('se_overlay_loads',2)-loads)&65535
  token=f.read(f.s['se_bc_arena'],5);obj=token[0];logical=f.m.read(f.s['object_extents']+obj*16+page//16);bank=f.m.read(f.s['se_reu_map']+logical);at=bank*65536+(page%16)*4096;firstlogical=f.m.read(f.s['object_extents']+obj*16);first=f.m.read(f.s['se_reu_map']+firstlogical)*65536;directory=first+0x100+page*8
  after=f.reu();wanted=bytearray(before);assert before[directory:directory+8]==bytes(8)
  wanted[at:at+4096]=after[at:at+4096];wanted[directory:directory+8]=after[directory:directory+8]
  assert after==wanted,'wholeREU outside actualfreepage+directory8'
  assert after[first:first+256]==before[first:first+256],'baseline roots changed'
  h=after[at:at+64];used=int.from_bytes(h[21:23],'little');payload=after[at+64:at+64+used]
  assert h[:6]==b'BP\1\1'+bytes([page,3])
  assert int.from_bytes(h[39:41],'little')==binascii.crc_hqx(payload,65535)
  assert payload[:7]==b'LXC1\1\1'+bytes([language]) and int.from_bytes(payload[86:88],'little')==len(events)
  assert [tuple([int.from_bytes(payload[i+1:i+4],'little'),int.from_bytes(payload[i+4:i+7],'little'),payload[i]])for i in range(96,used,7)]==events
  assert f.canonical()==canonical and f.catalog()==catalog and f.read(0xc600,1024)==f.shim and not f.get('se_doc_read_locks',1)
  # Actual selectors, source provider and typed transport may touch only
  # these declared scratch/service ranges. VIEW/NAV/shim/settings stay exact.
  now=f.read(0,65536);allowed=[(2,0x1a),(0x100,0x200),(0x5000,0x6000),(0x8000,0x8800),(F,F+576),(0x9a00,0x9d85),(0x9e00,0x9fb5),(0x9fc2,0x9fc3),(0xa000,0xc000),(0xc000,0xc600),(0xca00,0xcb80),(0xcbc0,0xcc00),(0xdf00,0xdf0b)];at_=0
  for a,b in allowed:
   assert now[at_:a]==ram[at_:a],(tag,'foreignRAM',[(hex(i),x,y)for i,(x,y)in enumerate(zip(ram,now))if at_<=i<a and x!=y][:20]);at_=b
  assert now[at_:]==ram[at_:],(tag,'foreignRAMtail')
  windows=[]
  for offset,count in [(0,min(5,end-body)),(2,min(7,end-body-2)),(max(0,end-body-9),min(9,end-body))]+list(extra_windows):
   q=body+offset;before_window=f.reu();start_window=f.total_instructions;window_loads=f.get('se_overlay_loads',2);feeds=dll.gm_metric(0)
   opened,_=f.lx(4);assert not opened.p&1 and opened.a==0
   f.m.load(F+94,q.to_bytes(3,'little')+bytes([count]));r,n=f.lp(4);assert not r.p&1 and r.a==1
   for _ in range(2000):
    r,n=f.lp(1);assert not r.p&1,(tag,'CONSUME',r.a,r.p)
    if not r.a:break
   else:raise AssertionError('boundedwindow consume')
   assert f.m.read(F+112)==1
   roles=bytearray([4])*count
   for a,b,role in expected:
    for x in range(max(a,q),min(b,q+count)):roles[x-q]=role
   assert f.read(0x8200,count)==roles,(tag,q,count,f.read(0x8200,count).hex(),roles.hex())
   closed,_=f.lx(2);assert not closed.p&1 and closed.a==0
   assert dll.gm_metric(0)==feeds,'retainedwindow calledactuallexerfeed'
   assert f.reu()==before_window and f.canonical()==canonical and not f.get('se_doc_read_locks',1)
   retained_instructions=f.total_instructions-start_window;retained_loads=(f.get('se_overlay_loads',2)-window_loads)&65535
   reference,ref_instructions,ref_loads=original_window(data,body,end,language,q,count)
   assert reference==roles,(tag,'independentcached-vsactualC25',q,count)
   windows.append(dict(query=q,count=count,instructions=retained_instructions,loads=retained_loads,actual_lexer_feeds=0,original_C25_instructions=ref_instructions,original_C25_loads=ref_loads))
  consumer_faults=[]
  if tag=='BASIC-24bit-window':
   receipt=f.read(F,576) # actual successful producer-returned page reference
   # Dimensions are immutable after accepted READ_BEGIN, even before a DMA.
   f.lx(4);f.m.load(F+94,body.to_bytes(3,'little')+bytes([5]));r,_=f.lp(4);assert not r.p&1
   f.m.write(F+97,6);readonly=f.reu();r,_=f.lp(1);assert r.p&1 and r.a==0xc1 and f.reu()==readonly
   f.lp(2);f.lx(2);f.m.load(F,receipt);consumer_faults.append('accepted-query-dimension-mutation-refuses-before-DMA')
   # Corrupt an actually published payload through the real typed copy API.
   # Retain the returned reference; never invent a page or descriptor.
   offset=page*4096+64+used-1;original=payload[-1:]
   def write_payload(value):
    f.m.load(f.s['se_object_id'],token);f.put('se_object_offset',offset);f.put('se_object_length',1,2);f.put('se_object_c64',IO,2);f.m.load(IO,value);assert not f.call('se_object_copy',a=0).p&1
   write_payload(bytes([original[0]^1]));corrupt=f.reu();f.lx(4);f.m.load(F+94,body.to_bytes(3,'little')+bytes([5]));r,_=f.lp(4);assert not r.p&1
   for _ in range(200):
    r,_=f.lp(1)
    if r.p&1 or r.a!=1:break
   assert r.p&1 and r.a==0xc2 and not f.m.read(F+112) and f.reu()==corrupt
   f.lp(2);f.lx(2);write_payload(original);f.m.load(F,receipt);consumer_faults.append('checked-published-payload-corruption-wholeCRC-refuses-noREADY')
   assert f.canonical()==canonical and not f.get('se_doc_read_locks',1)
  dll.gm_profile(0,0,0,0,0,0,0)
  result=dict(tag=tag,source_bytes=len(data),BODY=body,END=end,language=language,events=events,steps=steps,source_feeds=end-body,query_steps=qsteps,consumer_faults=consumer_faults,cold_build_instructions=build_instructions,cold_build_loads=build_loads,windows=windows,page=page,page_service_bytes=page_budget['total_bytes']);cases.append(result);print('PASS',result,flush=True)

 try:
  data=geos.native_text('Intro\r:::basic\r10 PRINT "Hello":REM tail\r20 DATA 1,2,3\r:::\rTail.');check('BASIC',data,data.index(geos.native_text('10 PRINT')))
  data=geos.native_text(':::asm\rstart: lda #$2A ;comment\r .byte "abc",$FF\r:::\rTail.');check('asm',data,data.index(geos.native_text('start:')))
  data=geos.native_text('A')*65450+geos.native_text('\r:::basic\r10 REM ')+geos.native_text('x')*1000+geos.native_text('\r:::\rTail.');target=data.index(geos.native_text('10 REM'));check('BASIC-24bit-window',data,target,[(65530-target,128),(30,32),(128,128)])
  faults=fault_gate()
  result=dict(status='passed',budget=budget,page_budget=page_budget,cases=cases,faults=faults,scope='Private C29/R26 substitutions only: actualC35/rootFS59→R14/se_sl once-perBODY→typed53unusedLEXpage; realoverlayseals/guards/loadcost; retainedwindowszeroactuallexerfeeds. No persistentroot/CRlexref or editorconsumer integration claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--build-only',action='store_true');a=p.parse_args();out=ROOT/'build/cache-lexical'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.build_only)
