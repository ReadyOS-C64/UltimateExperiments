"""Real C17/C18/R18 catalog leaves against a frozen resident; private build only.
No UI/native claim. Existing block/source/fold modules are compiled unchanged.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,editor_fixture
from bindings import verify
from overlays import wrap,HEADER
from peddle import VENDOR,Machine
from supermark_probe import petscii
spec=importlib.util.spec_from_file_location('leaf_fold_oracle',ROOT/'tests/test_fold_builder.py');model=importlib.util.module_from_spec(spec);sys.modules[spec.name]=model;spec.loader.exec_module(model)
DEFAULT_BASE=ROOT/'build/fold-leaves/0659/fixture'
def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def labels(path):return {p[2].lstrip('.'):int(p[1],16) for line in Path(path).read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
def build(out,base=DEFAULT_BASE):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);base=Path(base);report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];seal=verify(base/'build/editor.prg',base/'build/editor.lbl');assert seal['resident_sha256']==report['sha256'] and seal['digest']==report['resident_binding']['digest'];d=seal['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 def asm(n,p,flags=()):
  obj=out/(n+'.o');run('ca65','-g','-I',out,'-I','src',*[a for f in flags for a in ['-D',f]],'-o',obj,p);return obj
 common=[asm('state','src/fold/state.s'),asm('builder-state','src/fold/builder-state.s'),asm('block-state','src/supermark/block.s',['SE_SM_STATE_ONLY=1'])]
 builder=asm('builder','src/fold/builder.s',['SE_FOLD_EDITOR_SOURCE=1']);retain=asm('retain','src/fold/builder-retain.s');filter_=asm('filter','src/fold/builder-filter.s');block=asm('block','src/supermark/block.s',['SE_SM_CODE_ONLY=1']);bridges=asm('bridges','src/fold/editor-leaves/core-bridges.s');reader=asm('reader','src/style/reader-dispatch.s')
 records={}
 for name,slot,id_,code in [('foldparse',1,17,[asm('parse-entry','src/fold/editor-leaves/builder-entry.s'),builder,retain,block,bridges,reader,asm('parse-stubs','src/fold/editor-leaves/parse-stubs.s')]),('foldfinish',1,18,[asm('finish-entry','src/fold/editor-leaves/builder-entry.s',['FOLD_FINISH=1']),builder,filter_,retain,bridges,reader,asm('finish-stubs','src/fold/editor-leaves/finish-stubs.s')]),('foldcore',0,18,[asm('core-entry','src/fold/editor-leaves/core-entry.s'),*[asm(n,'src/fold/'+n+'.s') for n in ['store','validate','query','action','locate']]])]:
  objects=code+common;aliases=out/(name+'-aliases.s');run(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',aliases,*objects);aobj=asm(name+'-aliases',aliases);kind={'foldparse':'parse','foldfinish':'finish','foldcore':'core'}[name]
  run('ld65','-C',f'cfg/fold-editor-{kind}.cfg','-o',out/(name+'.bin'),'-m',out/(name+'.map'),'-Ln',out/(name+'.lbl'),*objects,aobj)
  payload=(out/(name+'.bin')).read_bytes();ls=labels(out/(name+'.lbl'));assert len(payload)<=4096 and ls['entry']==(0xB010 if slot else 0xA010)
  for n,v in [('se_fold_state',0x8D00),('se_sm_state',0x8E11),('se_fb_state',0x8E60),('se_fold_record',0x8EB9),('se_fb_buffer',0x8F36),('se_fb_old_record',0x8FB6)]:assert ls[n]==v,(n,ls[n],v)
  image=wrap(payload,slot,id_,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));path=out/(name+'.seo');path.write_bytes(image);records[name]=dict(slot=slot,id=id_,payload_bytes=len(payload),sha256=hashlib.sha256(image).hexdigest(),path=str(path),symbols=ls)
 (out/'build.json').write_text(json.dumps(dict(resident_sha256=report['sha256'],binding=d,records=records),indent=2)+'\n');return report,records

def runner(out):
 cpp=out/'runner.cpp';cpp.write_text('#include "zeropage_peddle.h"\nextern "C" uint64_t fl_run(ZeroPagePeddle*m,uint64_t n){auto s=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<n;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-s;zeropage_peddle_step_instruction(m);}return 0;}\nextern "C" void fl_ram(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*p){for(uint32_t i=0;i<n;i++)p[i]=zeropage_peddle_read(m,a+i);}\nextern "C" void fl_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*p){for(uint32_t i=0;i<n;i++)p[i]=zeropage_peddle_read_reu(m,i);}\n')
 ext='.dylib' if sys.platform=='darwin' else '.so';Machine().close();path=out/('runner'+ext);run('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',path);dll=C.CDLL(str(path));dll.fl_run.argtypes=[C.c_void_p,C.c_uint64];dll.fl_run.restype=C.c_uint64;dll.fl_ram.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];dll.fl_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return dll
class Fixture(editor_fixture.EditorFixture):
 def __init__(self,records,out,base):
  self.runner=runner(out);self.records=records;self.cs=records['foldparse']['symbols'];self.steps=0;self.phases=set();self.max_feed=0;self.peak=0;self.admissions=0
  super().__init__();self.m.call=self.fast;self.assets.update({n:Path(r['path']).read_bytes() for n,r in records.items()})
 def fast(self,address,a=0,x=0,y=0,limit=2_000_000):
  for n,v in [('pc',address),('sp',0xFD),('p',0x24),('a',a),('x',x),('y',y)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=self.runner.fl_run(self.m.handle,limit);assert used,('nonreturn',hex(address),hex(self.m.regs().pc));self.peak=max(self.peak,used);return self.m.regs(),used
 def read(self,a,n):
  b=C.create_string_buffer(n);self.runner.fl_ram(self.m.handle,a,n,b);return b.raw
 def reu(self):
  b=C.create_string_buffer(32*65536);self.runner.fl_reu(self.m.handle,len(b),b);return b.raw
 def cg(self,n,w=1):return int.from_bytes(self.read(self.cs[n],w),'little')
 def cp(self,n,v,w=1):self.m.load(self.cs[n],v if isinstance(v,bytes) else v.to_bytes(w,'little'))
 def invoke(self,name,op):
  self.put('se_overlay_frame',op,1);r,_=self.m.call(self.s['se_overlay_call'],a=self.records[name]['id'],x=self.records[name]['slot']);self.admissions+=1;return r
 def preserved(self):
  return self.read(self.s['se_doc_roots'],512)+b''.join(self.read(self.s[n],w) for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_hot_ready',1),('se_hot_pending',1),('se_hot_base',3),('se_hot_caret',3),('se_hot_left',2),('se_hot_right',2),('se_h_token',5),('se_h_current',4),('se_h_saved',4),('se_sel_mark',13)])+self.read(0x9200,2048)+self.read(0x8C00,256)+self.read(0x9180,128)+self.read(0xC600,1024)
 def claim(self):
  self.index=self.read(0x8D00,1152);self.put('se_f_owner',3,1);self.m.load(0x8D00,bytes(1152))
 def release(self):
  assert not self.call('se_fs_end').p&1;self.put('se_f_owner',0,1);self.m.load(0x8D00,self.index)
 def allocate(self):
  r,_=self.m.call(self.s['se_object_create'],a=0x46,x=1);assert not r.p&1;self.token=self.read(self.s['se_object_id'],5);self.put('se_object_offset',65536);assert not self.call('se_object_resize').p&1
 def seed(self):
  self.cp('se_fold_token',self.token);self.cp('se_fb_capacity',2048,2);self.cp('se_fb_old_valid',0)
 def finish(self):
  for _ in range(100000):
   phase=self.cg('se_fb_phase');self.phases.add(phase);pos=self.cg('se_sm_pos',3);r=self.invoke('foldparse' if phase<=3 else 'foldfinish',1);self.steps+=1;feed=self.cg('se_sm_pos',3)-pos;self.max_feed=max(self.max_feed,feed);assert feed<=32
   if r.p&1 or r.a==0:return r
   assert r.a==2
  raise AssertionError('unbounded builder')
 def map_bytes(self):
  count=self.cg('se_fold_count',2);logical=self.m.read(self.s['object_extents']+self.token[0]*16);bank=self.m.read(self.s['se_reu_map']+logical);return self.reu()[bank*65536:bank*65536+count*32],bank

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=DEFAULT_BASE);p.add_argument('--build-only',action='store_true');a=p.parse_args();out=ROOT/'build/fold-leaves/0659/leaves';report,records=build(out,a.base)
 if a.build_only:print({n:r['payload_bytes'] for n,r in records.items()});return
 frozen=json.loads((a.base/'freeze.json').read_text());cpu_editor.ROOT=editor_fixture.ROOT=a.base;cpu_editor.NAMES=editor_fixture.NAMES=frozen['names'];f=Fixture(records,out,a.base);cases=[]
 try:
  data=petscii('# Main\nintro\n## Inner\ninside\n:::region Region\nregion body\n:::basic\n10 PRINT "TEST"\n:::\n:::end\n# Tail\n')+b'x'*65540+b'\rEND\r';f.source(data,banks=2,physical=32);f.position(65542);f.key(ord('Q'));caret=f.get('se_hot_caret');merged=data[:caret-1]+b'Q'+data[caret-1:];assert f.get('se_hot_pending',1)==1
  f.allocate();f.claim();f.seed();before=f.preserved();reu=f.reu();locks=f.get('se_doc_read_locks',1);r=f.invoke('foldparse',0);assert not r.p&1 and r.a==2,(r.a,'begin');assert f.get('se_doc_read_locks',1)==locks+1;r=f.finish();assert not r.p&1 and r.a==0,(r.a,f.cg('se_fb_phase'));assert f.cg('se_fold_valid') and not f.get('se_fs_owned',1) and f.get('se_doc_read_locks',1)==locks
  expected,omitted,empty,error=model.oracle(merged);assert not error;actual,bank=f.map_bytes();assert actual==b''.join(x.bytes() for x in expected);assert f.cg('se_fb_omitted',2)==omitted;assert f.preserved()==before;after=f.reu();assert all(after[i*65536:(i+1)*65536]==reu[i*65536:(i+1)*65536] for i in range(32) if i!=bank);cases.append('actual pending merged >64KiB build / exact independent records / foreign REU')
  # Core query/action/validation execute through the actual R catalog entry.
  f.cp('se_fold_action',3);r=f.invoke('foldcore',10);assert not r.p&1
  while f.cg('se_fold_busy'):assert not f.invoke('foldcore',11).p&1
  assert f.cg('se_fold_valid');f.cp('se_fold_query',expected[0].hidden,3);f.cp('se_fold_mode',0);assert not f.invoke('foldcore',8).p&1
  while f.cg('se_fold_busy'):assert not f.invoke('foldcore',9).p&1
  assert f.cg('se_fold_hidden') and f.cg('se_fold_result',3)==expected[0].start
  assert not f.invoke('foldcore',14).p&1
  while f.cg('se_fold_busy'):assert not f.invoke('foldcore',15).p&1
  assert f.cg('se_fold_target',2)==0 and f.cg('se_fold_valid')
  assert not f.invoke('foldcore',14).p&1;assert not f.invoke('foldcore',16).p&1;assert f.cg('se_fold_valid') and f.cg('se_fold_target',2)==0
  cases.append('actual R18 collapse/query/locator begin-step-cancel core')
  # Wrong owner: every entry refuses before ANY union mutation, even poison.
  saved=f.read(0x8D00,1152)
  for owner in [0,1,2,255]:
   f.put('se_f_owner',owner,1);poison=bytes((i*37+owner)&255 for i in range(1152));f.m.load(0x8D00,poison)
   for name,ops in [('foldparse',[0,1,2,255]),('foldfinish',[0,1,2,255]),('foldcore',list(range(17)))]:
    for op in ops:r=f.invoke(name,op);assert r.p&1 and r.a==0xB2 and f.read(0x8D00,1152)==poison,(owner,name,op,r.a)
  f.put('se_f_owner',3,1);f.m.load(0x8D00,saved);cases.append('foreign owner0/1/2/255 refuses before union reads/writes')
  for name,phases in [('foldparse',[0,4,7,9,255]),('foldfinish',[0,1,2,3,10,255])]:
   for phase in phases:
    f.cp('se_fb_phase',phase);snap=f.read(0x8D00,1152);r=f.invoke(name,1);assert r.p&1 and r.a==0xB0 and f.read(0x8D00,1152)==snap
  f.cp('se_fb_old_valid',1);f.cp('se_fb_busy',0);f.cp('se_fold_busy',0);assert f.invoke('foldparse',0).p&1 and f.get('se_doc_read_locks',1)==locks;f.cp('se_fb_old_valid',0);cases.append('wrong phase no-write / merged old-retention refused')
  assert not f.call('se_doc_read_acquire').p&1;f.seed();assert not f.invoke('foldparse',0).p&1;assert f.get('se_doc_read_locks',1)==locks+2;assert not f.invoke('foldparse',2).p&1;assert not f.invoke('foldfinish',2).p&1;assert f.get('se_doc_read_locks',1)==locks+1;f.call('se_doc_read_release');cases.append('cancel idempotent / own counted lease only')
  # Missing each leaf while a job owns a lease: root emergency END remains real
  # resident and must not depend on either C or R code being available.
  for missing in ['foldparse','foldfinish','foldcore','viewsource']:
   f.seed();assert not f.invoke('foldparse',0).p&1
   slot,id_=(0,14) if missing=='viewsource' else (records[missing]['slot'],records[missing]['id']);idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)==slot);f.m.write(f.s['se_overlay_ids']+idx,0)
   if missing=='foldparse':r=f.invoke('foldparse',1)
   elif missing=='foldfinish':f.cp('se_fb_phase',4);r=f.invoke('foldfinish',1)
   elif missing=='foldcore':r=f.invoke('foldparse',1)
   else:r=f.invoke('foldparse',1)
   assert r.p&1 and r.a==0x17,(missing,r.a);assert not f.call('se_fs_end').p&1;assert f.get('se_doc_read_locks',1)==locks;f.m.write(f.s['se_overlay_ids']+idx,id_);f.cp('se_fb_busy',0);f.cp('se_fold_busy',0)
  cases.append('missing C17/C18/R18/R14 / resident END cleanup')
  # Source identity and candidate token changes fail closed, releasing only
  # our lease. Overlay fetches may DMA; no candidate/source bytes may change.
  for address,width in [(f.s['se_r_revision'],4),(f.s['object_gen_lo']+f.token[0],1)]:
   f.seed();assert not f.invoke('foldparse',0).p&1;original=f.read(address,width);f.m.load(address,(int.from_bytes(original,'little')+1).to_bytes(width,'little'));reu_guard=f.reu();r=f.invoke('foldparse',1);assert r.p&1 and not f.cg('se_fb_busy') and not f.cg('se_fold_valid') and f.get('se_doc_read_locks',1)==locks;assert f.reu()==reu_guard;f.m.load(address,original)
  cases.append('changed source revision / revoked candidate token fail closed')
  assert f.preserved()==before;assert f.read(0xC600,1024)==f.shim;f.release();assert f.document()==data
  # Additional real leaf/callback cases exercise empty/EOF, nested explicit
  # constructs, malformed fences, and capacity refusal with canonical guards.
  extra_fixtures=0
  for case_data,capacity,expected_error in [(b'',2048,0),(petscii('# A\nbody\n## B\n:::region R\n:::asm\nlda #$01\n:::\n:::end\n# C\nlast'),2048,0),(petscii(':::basic\n10 END\n'),2048,0xB5),(petscii('# A\nx\n# B\ny\n'),1,0xB4)]:
   f.source(case_data,banks=2,physical=32);f.allocate();f.claim();f.seed();f.cp('se_fb_capacity',capacity,2);canonical=f.preserved();image=f.reu();assert not f.invoke('foldparse',0).p&1;r=f.finish();assert bool(r.p&1)==bool(expected_error) and r.a==expected_error,(r.a,expected_error);assert f.get('se_doc_read_locks',1)==0 and not f.get('se_fs_owned',1)
   if not expected_error:
    tree,_,_,error=model.oracle(case_data);assert not error;raw,which=f.map_bytes();assert raw==b''.join(x.bytes() for x in tree) and f.cg('se_fold_valid')
   else:assert not f.cg('se_fold_valid');_,which=f.map_bytes()
   newer=f.reu();assert all(newer[i*65536:(i+1)*65536]==image[i*65536:(i+1)*65536] for i in range(32) if i!=which);assert f.preserved()==canonical;f.release();assert f.document()==case_data;extra_fixtures+=1
  cases.append('empty EOF / nested region+assembler / incomplete fence / capacity refusal')
  result=dict(status='passed',resident_sha256=report['sha256'],binding=report['resident_binding']['digest'],payload_bytes={n:r['payload_bytes'] for n,r in records.items()},phase_bytes=643,phase_span_bytes=726,added_resident_bytes=0,added_ZP_bytes=0,source_length=len(data),merged_length=len(merged),records=len(expected),additional_fixtures=extra_fixtures,steps=f.steps,phases=sorted(f.phases),max_feed_per_step=f.max_feed,peak_call_instructions=f.peak,catalog_calls=f.admissions,cases=cases,limits=['Actual imported C17/C18/R18 plus current R14 reader; no product root/UI/native integration.','Missing-leaf recovery invokes actual resident END explicitly, matching required future root coordinator seam.'])
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2));(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':main()
