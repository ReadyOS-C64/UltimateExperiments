"""Isolated real semantic C worker + sealed editor R14 source provider.

No shared build, host parser events, source flattening in the worker, renderer
integration or native timing claim. Whole source and16MiB remain read-only.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,re,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_consumer as product
from supermark_model import blocks,inline
geos=product.geos
BASE=ROOT/'build/plain-geos/20261025T223041055764Z/fixture'
D=ROOT/'src/cache/semantic';F=0x8d00;CR=F+291;IO=F+448

def command(args):return subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True).stdout
def labels(path):return {n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',path.read_text())}
def build(out,base):
 out.mkdir(parents=True);report=json.load(open(base/'build/editor-report.json'));s=report['symbols'];binding=report['resident_binding']['digest']
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in ['block.s','inline.s']:(out/name).write_bytes(z.read('src/supermark/'+name))
 (out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 objs=[]
 for name,src,defs in [('entry',D/'entry.s',[]),('worker',D/'worker.s',[]),('state',D/'state.s',[]),('block',out/'block.s',['SE_SM_CODE_ONLY=1']),('inline',out/'inline.s',['SE_SM_CODE_ONLY=1']),('cache-state',ROOT/'src/cache/state.s',[])]:
  obj=out/(name+'.o');command(['ca65','-g','-I',out,'-I',ROOT/'src',*[a for d in defs for a in ['-D',d]],'-o',obj,src]);objs.append(obj)
 imports=set();exports=set()
 for obj in objs:
  for flag,dest in [('--dump-imports',imports),('--dump-exports',exports)]:dest.update(re.findall(r'Name:\s+"([^\"]+)"',command(['od65',flag,obj])))
 externals=imports-exports;assert externals<=s.keys(),externals-s.keys()
 (out/'externals.s').write_text('\n'.join(('.exportzp 'if n in ['text_ptr','screen_ptr']else'.export ')+n+'\n'+n+'=$%04X'%s[n]for n in sorted(externals))+'\n')
 command(['ca65','-o',out/'externals.o',out/'externals.s'])
 (out/'worker.cfg').write_text('''MEMORY {
 C:file=%O,start=$B000,size=$1000,type=ro;
 P:file="",start=$8D5E,size=79,type=rw;
 O:file="",start=$9FB5,size=17,type=rw;
 R:file="",start=$9D85,size=96,type=rw;
 } SEGMENTS {
 BSC_CODE:load=C,type=ro; SM_BLOCK:load=C,type=ro; SM_INLINE:load=C,type=ro;
 BSC_PARSER:load=P,type=bss; OBJECTS:load=O,type=bss; DOCSTATE:load=R,type=bss;
 }''')
 command(['ld65','-C',out/'worker.cfg','-o',out/'worker.bin','-m',out/'worker.map','-Ln',out/'worker.lbl',*objs,out/'externals.o'])
 raw=(out/'worker.bin').read_bytes();assert raw[:16]==bytes.fromhex(binding)and len(raw)<=4096
 # Byte-layout proof against the actual parser state-only assemblies.
 actual={}
 for name in ['block','inline']:
  command(['ca65','-D','SE_SM_STATE_ONLY=1','-I',ROOT/'src','-o',out/(name+'-state.o'),out/(name+'.s')])
  (out/'state.cfg').write_text('MEMORY {S:file="",start=$8D5E,size=128,type=rw;} SEGMENTS {SM_STATE:load=S,type=bss;}')
  command(['ld65','-C',out/'state.cfg','-o',out/'empty.bin','-Ln',out/(name+'-state.lbl'),out/(name+'-state.o')]);actual.update(labels(out/(name+'-state.lbl')))
 linked=labels(out/'worker.lbl')
 for name,address in actual.items():assert linked[name]==address,(name,address,linked[name])
 sizes={name:sum(int(n)for n in re.findall(r'Size:\s+(\d+)',command(['od65','--dump-segments',out/(name+'.o')])))for name in ['entry','worker','block','inline']}
 result=dict(total_bytes=len(raw),sizes=sizes,sha256=hashlib.sha256(raw).hexdigest(),binding=binding,scope='Private C-slot capsule; new17B descriptor/96B ring bound to granted existing segment tails, not an integrated product image.')
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return linked,result

class Fixture(product.Fixture):
 def install(self,raw,linked):self.m.load(0xb000,raw);self.c=linked
 def cc(self,name):
  self.put('se_overlay_frame',{'se_bsc_begin':0,'se_bsc_step':1,'se_bsc_cancel':2,'se_bsc_ack':3}[name],1)
  r,n=self.fast_call(self.c['entry']);self.total_instructions+=n;self.worker_peak=max(getattr(self,'worker_peak',0),n);return r,n

def run(out,base,smoke=False):
 frozen,identity=geos.freeze(out,base);linked,budget=build(out/'link',frozen)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True);cases=[]
 raw=(out/'link/worker.bin').read_bytes()
 def setup(data,pending=False,fragmented=False):
  f.source(data)
  if fragmented:
   assert not f.call('se_hot_call',10).p&1
   for at in range(3000,3600,17):
    f.put('se_doc_edit_position',at);f.put('se_doc_edit_delete',0);f.put('se_doc_edit_insert',1)
    assert not f.call('se_doc_splice_begin').p&1
    f.m.load(0x8000,b'z');f.put('se_doc_count',1,2);f.put('se_doc_c64',0x8000,2);assert not f.call('se_doc_splice_feed').p&1
    while f.get('se_doc_busy',1):assert not f.call('se_doc_splice_step').p&1
    data=data[:at]+b'z'+data[at:]
   f.position(0)
  if pending:f.key(geos.native_text('Q')[0]);data=geos.native_text('Q')+data
  r,_=f.fast_call(f.s['se_object_create'],a=0x53,x=1);assert not r.p&1,hex(r.a)
  token=f.read(f.s['se_object_id'],5);f.put('se_object_offset',65536);assert not f.call('se_object_resize').p&1
  f.m.load(linked['se_bc_arena'],token+(9).to_bytes(4,'little')+(7).to_bytes(4,'little')+b'\1\0\0\0')
  for name in ['se_i_ready','se_i_count','se_n_cache_count']:f.put(name,0,1)
  f.put('se_f_owner',4,1);f.m.load(F,bytes(576));f.m.write(F,1);f.m.write(F+5,1);f.m.load(F+8,token+(7).to_bytes(4,'little')+(9).to_bytes(4,'little'))
  # Arena-owned61B must remain opaque to the semantic worker.
  f.m.load(F+387,bytes((i*17+31)&255 for i in range(61)))
  f.product_c=f.read(0xb000,4096);f.install(raw,linked);return data
 def check(tag,data,pending=False,fragmented=False):
  data=setup(data,pending,fragmented);before=f.reu();canonical=f.canonical();catalog=f.catalog();protected=f.read(0x8800,128)+f.read(0x8c00,256)+f.read(0x9180,128);arena=f.read(F+387,61);start=f.total_instructions;ram=f.read(0,65536)
  fields=[('object_owner',8),('object_gen_lo',8),('object_gen_hi',8),('object_banks',8),('object_extents',128),('object_size_lo',8),('object_size_mid',8),('object_size_hi',8),('se_reu_map',256),('se_reu_logical_owner',256),('se_reu_physical_owner',256),('se_r_revision',4)]
  capabilities=b''.join(f.read(f.s[n],count)for n,count in fields)
  r,_=f.cc('se_bsc_begin');assert not r.p&1 and r.a==1,(tag,'begin',r.a)
  records=[];events=[];steps=0
  while True:
   counters=[int.from_bytes(f.read(F+at,3),'little')for at in [41,44,47]]
   r,_=f.cc('se_bsc_step');steps+=1;assert not r.p&1,(tag,'step',hex(r.a),f.read(F,94).hex());assert steps<200000
   after=[int.from_bytes(f.read(F+at,3),'little')for at in [41,44,47]];delta=[a-b for a,b in zip(after,counters)]
   assert sum(delta[:2])<=32 and delta[2]<=1,(tag,'unboundedSTEP',delta)
   if not r.a:break
   ready=f.m.read(F+4)
   if ready:
    packet=f.read(IO,96 if ready==1 else 10);state=f.read(F+21,45)
    # Repeated STEP is pure backpressure: no restart/feed/IO overwrite.
    again,_=f.cc('se_bsc_step');assert again.a==1 and not again.p&1 and f.read(IO,len(packet))==packet and f.read(F+21,45)==state
    if ready==1:records.append(packet)
    else:events.append((int.from_bytes(f.read(CR+16,3),'little'),packet))
    a,_=f.cc('se_bsc_ack');assert not a.p&1,(tag,'ack',a.a)
  expected=blocks(data);real=[x for x in records if not x[2]&8];assert len(real)==len(expected),(tag,'records',len(real),len(expected))
  wanted=[];carry=bytes(6);overflow=0
  for record,event in zip(real,expected):
   start_=event['start'];end=event['end'];next_=end+int(end<len(data)and data[end]==13)
   assert record[0:2]==b'\1\1' and record[3]==event['kind']
   assert [int.from_bytes(record[a:a+3],'little')for a in [16,19,22,25]]==[start_,end-start_,event['body']-start_,next_-start_],(tag,'anchors',record.hex(),event)
   assert tuple(record[a]for a in [69,70])==(event['language'],event['level'])
   text=bytes(v&0x7f if 0xc1<=v<=0xda else v for v in data[start_:end])
   if not carry[0]:
    if re.fullmatch(rb':::REGION(?: .*)?',text)and carry[2]==16:overflow+=1
    elif text==b':::END'and overflow:overflow-=1
   outgoing=bytes([event['fence'],event['language'],event['regions']])+overflow.to_bytes(3,'little')
   assert record[28:34]==carry and record[34:40]==outgoing,(tag,'six-byte-carry',record[28:40].hex(),carry.hex(),outgoing.hex());carry=outgoing
   assert int.from_bytes(record[74:76],'little')==binascii.crc_hqx(record[1:74]+record[76:],0xffff),(tag,'recordCRC')
   if event['kind']<4:
    pairs=inline(data[event['body']:end],start=event['body'],body_column=event['body']-start_)
    for kind,style,width,opened,closed in pairs:wanted.append((start_,bytes([kind,style,width])+(opened-start_).to_bytes(3,'little')+(closed-start_).to_bytes(3,'little')+b'\0'))
    assert record[2]&4 and int.from_bytes(record[44:47],'little')==len(pairs)
   else:assert not record[2]&4 and record[44:47]==b'\0\0\0'
  assert events==wanted,(tag,'inline events',events,wanted)
  assert len(records)==len(expected)+int(not data or data[-1]==13),(tag,'EOFsentinel')
  counts={name:int.from_bytes(f.read(F+at,3),'little')for name,at in [('block_feeds',41),('inline_feeds',44),('source_reads',47),('records',50),('events',53),('body_scans',56)]}
  assert counts['block_feeds']==len(data) and counts['inline_feeds']==sum(e['end']-e['body']for e in expected if e['kind']<4)
  assert counts['body_scans']==sum(e['kind']<4 for e in expected)
  assert f.reu()==before and f.canonical()==canonical and f.catalog()==catalog and f.read(0xc600,1024)==f.shim
  assert b''.join(f.read(f.s[n],count)for n,count in fields)==capabilities,(tag,'object/provider/source authority')
  # FullRAM outside explicit service workspaces remains exact. Canonical graph,
  # gap/history, object/provider tables, catalog identity, VIEW/NAV/diag and the
  # arena-owned61B are separately protected even within those workspaces.
  allowed=[(2,0x1a),(0x100,0x200),(0x5000,0x6000),(0x8000,0x8800),(F,F+576),(0x9a00,0x9d85),(0x9e00,0x9fb5),(0xa000,0xb000),(0xc000,0xc600),(0xca00,0xcb80),(0xcbc0,0xcc00),(0xdf00,0xdf0b)]
  now=f.read(0,65536);at=0
  for a,b in allowed:assert now[at:a]==ram[at:a],(tag,'foreignRAM',hex(at),hex(a));at=b
  assert now[at:]==ram[at:],(tag,'foreignRAMtail',[(hex(i),a,b)for i,(a,b)in enumerate(zip(now,ram))if i>=at and a!=b][:20])
  assert f.read(0x8800,128)+f.read(0x8c00,256)+f.read(0x9180,128)==protected and f.read(F+387,61)==arena
  assert f.get('se_doc_read_locks',1)==0 and f.m.read(F+3)==f.m.read(F+1)==0
  entry=dict(tag=tag,source_bytes=len(data),records=len(records),events=len(events),steps=steps,instructions=f.total_instructions-start,peak_instructions=f.worker_peak,counts=counts);cases.append(entry);print('PASS',entry,flush=True)
 def faults():
  source=geos.native_text('Prose **pair** and £*literal.\rTail.');groups=[]
  for owner in [0,1,2,3,5,255]:
   setup(source);f.put('se_f_owner',owner,1);f.m.load(F,bytes((i*37+19)&255 for i in range(576)));reu=f.reu()
   for name,op in [('se_bsc_begin',0),('se_bsc_step',1),('se_bsc_ack',3),('se_bsc_cancel',2)]:
    f.put('se_overlay_frame',op,1);ram=f.read(0,65536)
    r,_=f.cc(name);assert r.p&1 and r.a==0xb2;now=f.read(0,65536);assert now[:0x100]==ram[:0x100]and now[0x200:]==ram[0x200:]and f.reu()==reu
  groups.append('six foreign owners/all four entries: fullRAM+16MiB opaque')
  setup(source);f.m.write(F+5,0);phase=f.read(F,576);r,_=f.cc('se_bsc_begin');assert not r.p&1 and r.a==2 and f.read(F,576)==phase and not f.get('se_doc_read_locks',1);groups.append('Plain misses without frame writes/parser/lease')
  for flags,budget,accepted in [(2,0,False),(3,128,False),(6,128,False),(2,128,True)]:
   setup(source);f.m.write(linked['se_bc_flags'],flags);f.m.write(F+6,budget);r,_=f.cc('se_bsc_begin');assert bool(not r.p&1)==accepted,(flags,budget,r.a)
   if accepted:
    assert f.get('se_doc_read_locks',1)==1;f.cc('se_bsc_step');f.cc('se_bsc_cancel')
   assert f.m.read(linked['se_bc_flags'])==flags and not f.get('se_doc_read_locks',1)
  groups.append('explicit unarmed REBUILD permits LOST; never clears it; armed/mutating refused')
  for field,width in [('se_bc_ticket',4),('se_bc_incarnation',4),('se_bc_arena',5)]:
   setup(source);assert not f.cc('se_bsc_begin')[0].p&1;before=f.canonical();reu=f.reu();f.m.write(linked[field],f.m.read(linked[field])^1)
   r,_=f.cc('se_bsc_step');assert r.p&1 and r.a==0xb1 and not f.get('se_doc_read_locks',1)and f.canonical()==before and f.reu()==reu
  groups.append('ticket/incarnation/fulltoken changes release only own lease')
  for changed,width in [('se_reu_epoch',2),('se_doc_epoch',2),('se_doc_meta',5)]:
   setup(source);f.cc('se_bsc_begin');original=f.read(f.s[changed],width);f.m.write(f.s[changed],original[0]^1);f.put('se_doc_read_locks',7,1)
   r,_=f.cc('se_bsc_cancel');assert not r.p&1 and f.get('se_doc_read_locks',1)==7 and not f.m.read(F+3);f.m.load(f.s[changed],original);f.put('se_doc_read_locks',0,1)
  groups.append('END cannot decrement seven new epoch/graph leases')
  setup(source);assert not f.call('se_doc_read_acquire').p&1;f.cc('se_bsc_begin');assert f.get('se_doc_read_locks',1)==2;f.cc('se_bsc_cancel');f.cc('se_bsc_cancel');assert f.get('se_doc_read_locks',1)==1;f.call('se_doc_read_release');groups.append('idempotent CANCEL preserves preexisting counted reader')
  for target in ['block','body','inline','record']:
   setup(source);f.cc('se_bsc_begin');before=f.canonical();reu=f.reu()
   for _ in range(100):
    if target=='block'or target=='body'and f.m.read(F+1)==2 or target=='inline'and f.m.read(F+4)==2 or target=='record'and f.m.read(F+4)==1:break
    if f.m.read(F+4):f.cc('se_bsc_ack')
    f.cc('se_bsc_step')
   else:raise AssertionError(('fault phase not reached',target))
   f.cc('se_bsc_cancel');assert f.get('se_doc_read_locks',1)==0 and f.m.read(F+4)==f.m.read(F+1)==0 and f.canonical()==before and f.reu()==reu
  groups.append('cancel during block/BODY/held inline/held descriptor discards private output')
  setup(source);f.cc('se_bsc_begin');before=f.canonical();reu=f.reu()
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==14 and not f.m.read(f.s['image_slot']+i)&1:f.m.write(f.s['se_overlay_ids']+i,0);break
  else:raise AssertionError('missing actual R14 fault target')
  f.m.write(f.s['se_overlay_active'],0);r,_=f.cc('se_bsc_step');assert r.p&1 and r.a==0x17 and not f.get('se_doc_read_locks',1)and f.canonical()==before and f.reu()==reu;groups.append('missing real R14 cleanup uses resident END')
  # Real local editing deliberately bypasses normal job-cancel ordering here,
  # solely to demonstrate the checked source snapshot rejects unobserved input.
  setup(source);f.cc('se_bsc_begin');phase=f.read(F,576);f.m.load(0xb000,f.product_c);f.put('se_f_owner',0,1);f.put('se_e_mods',0,1);f.put('se_e_key',geos.native_text('Z')[0],1);f.call('se_editor_input');assert f.get('se_e_job',1)==0 and f.get('se_e_error',1)==0
  after=f.canonical();reu=f.reu();f.install(raw,linked);f.m.load(F,phase);f.put('se_f_owner',4,1);r,_=f.cc('se_bsc_step');assert r.p&1 and r.a==0xb1 and not f.get('se_doc_read_locks',1)and f.canonical()==after and f.reu()==reu;groups.append('actual pending edit invalidates old FS without mutating successful new source')
  setup(source);f.put('se_hot_right',2049,2);r,_=f.cc('se_bsc_begin');assert r.p&1 and r.a==0xb0 and not f.get('se_doc_read_locks',1);groups.append('malformed gap refused before acquisition/source read')
  setup(source);f.cc('se_bsc_begin');f.m.load(F+21,(0xffffff).to_bytes(3,'little'));r,_=f.cc('se_bsc_step');assert r.p&1 and not f.get('se_doc_read_locks',1);groups.append('out-of-source progress fails without output/publication')
  print('FAULTS PASS',len(groups),flush=True);return groups
 try:
  check('mixed',geos.native_text('# Heading **bold** *emph*\r:::basic\r10 PRINT "Hi"\r:::\rTail @@code@@.'))
  if not smoke:
   for tag,data in [('empty',b''),('terminal-CR',b'\r\r'),('late-close',geos.native_text('**'+('body '*300)+'**\rTail.')),('far-body',b'A'*66000+geos.native_text(' **late**\r# Far **heading**\r:::region R\rText\r:::end\r')),('region-overflow',geos.native_text(':::region R\r')*18+geos.native_text('Body\r')+geos.native_text(':::end\r')*18),('nested-escapes',geos.native_text('## **outer *inner* outer** @@*literal*@@ £*escaped\r  - ***both*** £- literal\rUnclosed **marker')),('packet-boundaries',b'a'*31+geos.native_text('**pair** ')+b'b'*31+geos.native_text('£* raw @@code@@\rTail.'))]:check(tag,data)
   check('pending',geos.native_text('Prose **pair**\rTail.'),True)
   check('fragmented',geos.native_text('Prose words '*5500+' **close**\rTail.'),False,True)
  fault_groups=faults()if not smoke else[]
  result=dict(status='passed',identity=identity,budget=budget,cases=cases,fault_groups=fault_groups,scope='Actual parser code/aliased proven state + actual sealed R14 merged/piece source reader. Controlled owner4 caller, no root/editor/cache transport integration or native claim. All source/history/catalog/shim/VIEW/NAV/arena61 unchanged; complete16MiB REU read-only.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/cache-semantic'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture.resolve(),a.smoke);print('RESULT',r['status'],len(r['cases']),r['budget']['total_bytes'])
