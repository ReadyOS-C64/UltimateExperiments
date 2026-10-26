"""Actual resident dispatcher assembly with explicit worker/endpoint stubs.

The differential oracle preserves A/X/Y/P/SP, destination, all 64KiB RAM except
relocated code/stack return addresses. No parser, loader, or VIC proof is claimed.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,itertools,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,library
D=ROOT/'src/render/geos/cache-handoff-candidate'
BASE=ROOT/'build/cache-editor-product/20261026T010418788084Z/fixture'
def labels(p):return {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',p.read_text())}
def command(args):subprocess.run(list(map(str,args)),check=True,capture_output=True,text=True)
def run(base,out):
 s=json.loads((base/'build/editor-report.json').read_text())['symbols'];prg=(base/'build/editor.prg').read_bytes();start=int.from_bytes(prg[:2],'little')
 out.mkdir(parents=True);print('RUN',out,flush=True)
 cfg=out/'probe.cfg';cfg.write_text('MEMORY { C:file=%O,start=$7000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; }\n')
 images={};labs={}
 for name in ('before','reference','dispatch'):
  command(['ca65','-I',ROOT/'src',D/(name+'.s'),'-o',out/(name+'.o'),'-l',out/(name+'.lst')])
  command([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),out/(name+'.o')])
  command(['ca65',out/(name+'-aliases.s'),'-o',out/(name+'-aliases.o')])
  command(['ld65','-C',cfg,out/(name+'.o'),out/(name+'-aliases.o'),'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl')])
  images[name]=(out/(name+'.bin')).read_bytes();labs[name]=labels(out/(name+'.lbl'))
 # Prove the unmodified source is the frozen resident's actual instruction stream.
 at=s['se_geos_render'];cfg2=out/'resident.cfg';cfg2.write_text(f'MEMORY {{ C:file=%O,start=${at:04x},size=$1000; }} SEGMENTS {{ CODE:load=C,type=ro; }}\n')
 command(['ld65','-C',cfg2,out/'before.o',out/'before-aliases.o','-o',out/'resident-before.bin'])
 assert (out/'resident-before.bin').read_bytes()==prg[2+at-start:2+at-start+len(images['before'])]
 assert len(images['dispatch'])==len(images['before'])+1
 # Private bulk reader uses the existing wrapper API; no emulator/vendor changes.
 lib=library();source=out/'snapshot.cpp';source.write_text('extern "C" unsigned char zeropage_peddle_read(const void*,unsigned short);\nextern "C" void snapshot(const void* p,unsigned char* b){for(unsigned i=0;i<65536;i++)b[i]=zeropage_peddle_read(p,i);}\n')
 dll=out/'snapshot.dylib';command(['clang++','-O2','-dynamiclib',source,ROOT/'build/libse_peddle.dylib','-o',dll]);snap=C.CDLL(str(dll));snap.snapshot.argtypes=[C.c_void_p,C.c_void_p]
 endpoints=['se_editor_render_ui','se_editor_reload','se_editor_reveal','se_editor_render_failed','se_editor_redraw','se_editor_error','se_fs_end','se_er_published']
 seed=bytearray((i*73+29)&255 for i in range(65536));seed[start:start+len(prg)-2]=prg[2:]
 machines={n:Machine() for n in images};buffer=C.create_string_buffer(65536)
 def execute(name,request,result,error,owner,job,op,handoff=False,entry='se_geos_service'):
  m=machines[name];m.load(0,seed);m.load(0x7000,images[name])
  for i,n in enumerate(endpoints):m.load(s[n],bytes([0xEE,i,0x68,0x60]))
  child=[]
  if handoff:child=[0xA9,35,0x8D,0x35,0x91,0xA9,0,0x8D,0x36,0x91]
  m.load(s['se_overlay_call'],bytes(child+[0xA9,result,0xA2,0xA7,0xA0,0xB6,0x38 if error else 0x18,0x60]))
  m.load(s['se_ef_prepare'],bytes([0xA9,0,0x18,0x60]))
  m.write(s['se_f_owner'],owner);m.write(s['se_e_job'],job);m.write(s['se_bc_flags'],0)
  m.load(0x9134,bytes([1,request,op])+bytes(65));m.load(0x912C,bytes(2))
  reg,count=m.call(labs[name][entry]);snap.snapshot(m.handle,buffer);ram=bytearray(buffer.raw)
  signature=(reg.a,reg.x,reg.y,reg.p,reg.sp,reg.pc)
  for a,n in [(0x100,256),(0x7000,4096)]:ram[a:a+n]=bytes(n)
  return signature,bytes(ram),count,m.read(0x9135),m.read(0x9136)
 cases=0;oldcases=0;handoffs=[];entry_cases=0
 try:
  # 29 requests, four A results, both C results, four owners, two jobs, four OPs.
  for values in itertools.product(list(range(16,44))+[255],range(4),range(2),(0,1,3,4),(11,12),(0,1,2,255)):
   a=execute('reference',*values);b=execute('dispatch',*values)
   assert a[:2]==b[:2],('optimized ABI/RAM',values,a[0],b[0])
   request,result,error,owner,job,op=values
   if request not in (35,36,37):
    old=execute('before',*values);assert old[:2]==b[:2],('legacy ABI/RAM',values,old[0],b[0]);oldcases+=1
   if not error and request in (34,35,36,37) and result==1:
    assert b[3]==request and b[4]==(1 if request%2==0 else op),(values,b[3:])
   cases+=1
  for entry,result,error,owner in itertools.product(('se_geos_render','se_geos_navigate'),(0,1,2),(0,1),(0,1,3,4)):
   old=execute('before',21,result,error,owner,11,0,entry=entry);new=execute('dispatch',21,result,error,owner,11,0,entry=entry)
   assert old[:2]==new[:2],('entry ABI/RAM',entry,result,error,owner,old[0],new[0])
   entry_cases+=1
  for op in (0,1,2,255):
   a=execute('reference',37,1,0,4,11,op,True);b=execute('dispatch',37,1,0,4,11,op,True)
   assert a[:2]==b[:2] and b[3:]==(35,0)
   handoffs.append(dict(initial_operation=op,request_after=b[3],operation_after=b[4],instructions=b[2]))
  # Worker BEGIN/STEP endpoint is explicit: first resident slice handoff0;
  # next slice calls the BEGIN stub and it publishes its own STEP1.
  m=machines['dispatch'];execute('dispatch',37,1,0,4,11,1,True)
  m.load(s['se_overlay_call'],bytes([0xAD,0x36,0x91,0xD0,0x03,0xEE,0x20,0x68,0xA9,1,0x8D,0x36,0x91,0x18,0x60]));m.write(0x6820,0)
  r,n=m.call(labs['dispatch']['se_geos_service']);assert m.read(0x6820)==1 and m.read(0x9135)==35 and m.read(0x9136)==1 and not r.p&1
  stack=[]
  for name in ('before','dispatch'):
   execute(name,34,1,0,4,11,0);m=machines[name]
   for field,value in [('a',0),('x',0),('y',0),('p',0x24),('sp',0xFD),('pc',labs[name]['se_geos_service'])]:
    getattr(m.lib,'zeropage_peddle_set_'+field)(m.handle,value)
   m.write(0x1FE,0xFE);m.write(0x1FF,2);low=0xFD;trace=[]
   for _ in range(1000):
    r=m.regs();low=min(low,r.sp);trace.append([r.pc,r.sp])
    if r.pc==0x2FF:break
    m.lib.zeropage_peddle_step_instruction(m.handle)
   else:raise AssertionError('stack probe did not return')
   stack.append(dict(variant=name,minimum_SP=low,trace=trace))
  assert stack[0]['minimum_SP']==stack[1]['minimum_SP']
  result=dict(status='passed',cases=cases,stack=stack,legacy_cases=oldcases,render_navigation_entry_cases=entry_cases,handoffs=handoffs,next_slice_BEGIN_count=m.read(0x6820),before_bytes=len(images['before']),candidate_bytes=len(images['dispatch']),resident_growth=1,full_RAM_bytes_per_comparison=65536,registers='A/X/Y/P/SP/returnPC exact',worker_scope='explicit endpoint stubs, not actual C35 parser/loader',frozen_PRG_sha256=hashlib.sha256(prg).hexdigest(),source_sha256={n:hashlib.sha256((D/(n+'.s')).read_bytes()).hexdigest() for n in images},candidate_sha256=hashlib.sha256(images['dispatch']).hexdigest())
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:
  for m in machines.values():m.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();run(a.fixture.resolve(),ROOT/'build/cache-handoff'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
