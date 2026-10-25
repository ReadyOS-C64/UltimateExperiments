"""Actual editor automatic edited-fold retention; private frozen CPU gate.
Default prepares requirements. --run freezes current product; no shared make.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,ctypes as C,hashlib,json,shutil,subprocess,sys
import test_fold_projection as projection
import test_fold_transform as transform
import test_fold_builder as builder
import test_grid_modes as grid
from test_folds import action_model
from redraw_model import native_text,Screen,verify_screen
from bindings import verify
ROOT=grid.ROOT

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def freeze(out,previous=None):
 target=out/'fixture'
 if previous:shutil.copytree(previous,target)
 else:
  names=list(grid.cpu_editor.NAMES);report=json.loads((ROOT/'build/editor-report.json').read_text());seal=verify(ROOT/'build/editor.prg',ROOT/'build/editor.lbl')
  assert report['sha256']==seal['resident_sha256'] and len(names)<=report['symbols']['se_overlay_capacity']<=64
  (target/'build/overlays').mkdir(parents=True)
  for n in ['editor.prg','editor.lbl','editor.map','editor-report.json','editor-bindings.json'] :shutil.copy2(ROOT/'build'/n,target/'build'/n)
  for n in names:
   p=ROOT/'build/overlays'/(n+'.seo');b=p.read_bytes();assert b[20:36]==b[36:52]==bytes.fromhex(seal['digest']);shutil.copy2(p,target/'build/overlays'/p.name)
  (target/'fonts').mkdir()
  for n in ['native8.bin','narrow4.bin','narrow5.bin','manifest.json']:shutil.copy2(ROOT/'assets/fonts/generated'/n,target/'fonts'/n)
  font=json.loads((target/'fonts/manifest.json').read_text());raw=Path(font['native_source']).read_bytes();assert hashlib.sha256(raw).hexdigest()==font['native_sha256'];(target/'fonts/chargen.bin').write_bytes(raw)
  identity=dict(names=names,prg_sha256=sha(target/'build/editor.prg'),assets={n:sha(target/'build/overlays'/(n+'.seo')) for n in names},fonts={p.name:sha(p) for p in (target/'fonts').iterdir()})
  assert identity['prg_sha256']==report['sha256']==sha(ROOT/'build/editor.prg');(target/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 identity=json.loads((target/'freeze.json').read_text());assert sha(target/'build/editor.prg')==identity['prg_sha256']
 for n,h in identity['assets'].items():assert sha(target/'build/overlays'/(n+'.seo'))==h
 for n,h in identity['fonts'].items():assert sha(target/'fonts'/n)==h
 return target,identity

def runner(out):
 """Retain grid's explicit ROM-read seam; audit each real resident DMA stash."""
 grid.runner(out);p=out/'runner.cpp';source=p.read_text();needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
 assert source.count(needle)==1
 extra='''
static uint8_t audit_mask[16777216];static bool audit_on=false;static uint32_t audit_bad=0,audit_writes=0;
static uint16_t audit_pc,audit_request,audit_offset,audit_length,audit_map,audit_lowner,audit_powner;
static void audit(ZeroPagePeddle*m,const ZeroPagePeddleRegs&r){
 if(!audit_on || r.pc!=audit_pc || r.a!=0)return;
 uint8_t logical=zeropage_peddle_read(m,audit_request),bank=zeropage_peddle_read(m,audit_map+logical);
 uint8_t lo=zeropage_peddle_read(m,audit_lowner+logical),po=zeropage_peddle_read(m,audit_powner+bank);
 uint32_t at=zeropage_peddle_read(m,audit_offset)|(zeropage_peddle_read(m,audit_offset+1)<<8);
 uint32_t n=zeropage_peddle_read(m,audit_length)|(zeropage_peddle_read(m,audit_length+1)<<8);if(!n)n=65536;
 if((lo!=0x46 && lo!=0xfe) || po!=lo || at+n>65536){audit_bad++;return;}
 memset(audit_mask+uint32_t(bank)*65536+at,1,n);audit_writes++;
}
extern "C" void fr_begin(uint16_t pc,uint16_t request,uint16_t offset,uint16_t length,uint16_t map,uint16_t lo,uint16_t po){audit_pc=pc;audit_request=request;audit_offset=offset;audit_length=length;audit_map=map;audit_lowner=lo;audit_powner=po;memset(audit_mask,0,sizeof(audit_mask));audit_bad=0;audit_writes=0;audit_on=true;}
extern "C" void fr_end(){audit_on=false;}
extern "C" uint32_t fr_bad(){return audit_bad;}
extern "C" uint32_t fr_writes(){return audit_writes;}
extern "C" void fr_mask(uint8_t*p){memcpy(p,audit_mask,sizeof(audit_mask));}
'''
 # The wrapper names its register struct in its checked public header.
 header=(grid.VENDOR/'zeropage_peddle.h').read_text()
 import re
 typename=re.search(r'}\s*(\w+)\s*;\s*\n',header).group(1)
 # Use decltype rather than depending on the C typedef's spelling.
 extra=extra.replace('const ZeroPagePeddleRegs&r','const decltype(zeropage_peddle_regs((ZeroPagePeddle*)nullptr))&r')
 source=source.replace(needle,extra+needle+'audit(m,r);');p.write_text(source)
 ext='.dylib' if sys.platform=='darwin' else '.so';path=out/('retention-runner'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+ext)),'-o',str(path)],check=True)
 dll=C.CDLL(str(path));dll.gm_rom.argtypes=[C.c_void_p,C.c_void_p];dll.gm_rom_count.restype=C.c_uint64
 dll.gm_profile.argtypes=[C.c_uint16,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,C.c_uint16,C.c_uint16];dll.gm_metric.argtypes=[C.c_int];dll.gm_metric.restype=C.c_uint64
 dll.gm_run.argtypes=[C.c_void_p,C.c_uint64];dll.gm_run.restype=C.c_uint64;dll.gm_idle.argtypes=[C.c_void_p,C.c_uint16,C.c_uint64];dll.gm_idle.restype=C.c_uint64;dll.gm_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];dll.gm_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p]
 dll.fr_begin.argtypes=[C.c_uint16]*7;dll.fr_mask.argtypes=[C.c_void_p];dll.fr_bad.restype=C.c_uint32;dll.fr_writes.restype=C.c_uint32;return dll

class Fixture(projection.Fixture):
 def reu(self):
  b=C.create_string_buffer(16*1024*1024);self.dll.gm_reu(self.m.handle,len(b),b);return b.raw
 def source(self,data):super().source(data,banks=2,physical=256)
 def audit_begin(self):self.dll.fr_begin(*[self.s[n] for n in ['se_reu_copy','se_reu_logical','se_reu_offset','se_reu_length','se_reu_map','se_reu_logical_owner','se_reu_physical_owner']])
 def audit_end(self,before,tag):
  self.dll.fr_end();assert self.dll.fr_bad()==0,(tag,'render attempted non-derived REU stash')
  mask=C.create_string_buffer(len(before));self.dll.fr_mask(mask);after=self.reu();allowed=mask.raw
  assert all(a==b or allowed[i] for i,(a,b) in enumerate(zip(before,after))),(tag,'REU write outside exact observed typed46/FE DMA spans')
  return self.dll.fr_writes()

def retained(folds,data,p,deleted,inserted):
 hints,_=transform.oracle(folds,len(data),p,deleted,len(inserted));changed=data[:p]+inserted+data[p+deleted:];fresh,_,_,error=builder.oracle(changed);assert not error
 key=lambda x:(x.start,x.hidden,x.end,x.kind,x.level)
 collapsed={key(x) for x in hints if x.flags&1}
 return changed,[replace(x,flags=int(key(x) in collapsed),saved=0,motion=0) for x in fresh]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');parser.add_argument('--fixture',type=Path);parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
 if not args.run:
  print('Prepared actual editor retention gate. Run --run after parent build-ready; --smoke checks first two-fold edit only.');return
 out=ROOT/'build/fold-retention'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);frozen,identity=freeze(out,args.fixture)
 grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];dll=runner(out);frames=[];f=None
 def check(data,folds,tag,valid=True):
  canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();top=f.get('se_v_top');f.audit_begin()
  try:f.render()
  finally:f.dll.fr_end()
  writes=f.audit_end(reu,tag)
  assert f.canonical()==canonical and f.merged()==data and f.catalog()==catalog,(tag,'canonical source/history/clipboard/catalog changed during render')
  assert bool(f.get('se_ef_valid',1))==valid,(tag,'map publication')
  if valid:assert f.metadata()==b''.join(x.bytes() for x in folds),(tag,'fresh parsed map/collapsed flags',f.metadata().hex(),b''.join(x.bytes() for x in folds).hex())
  wanted,anchors,ends,bits,seen=projection.expected(f,data,folds,top)
  actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
  assert actual==anchors,(tag,'anchors',actual,anchors)
  if valid:assert tuple(int.from_bytes(f.read(f.s['se_ef_paint_ends']+i*3,3),'little') for i in range(22))==ends,(tag,'paintends')
  assert f.get('se_ef_fold_rows')==sum(v<<i for i,v in enumerate(bits)),(tag,'fold projection')
  if f.get('se_mode',1):assert f.read(0x6000,8000)==wanted[0] and f.read(0x4000,1000)==wanted[1],(tag,'all bitmap pixels/attributes')
  else:verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),Screen(*wanted,anchors,seen),tag=tag)
  assert not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_ef_active']) and f.read(0xC600,1024)==f.shim
  frames.append(dict(tag=tag,mode=f.get('se_mode',1),source_bytes=len(data),records=len(folds),collapsed=[i for i,x in enumerate(folds) if x.flags&1],caret=f.get('se_hot_caret'),pending=f.get('se_hot_pending',1),derived_dma_writes=writes))
  (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
 def move(data,pos):
  # Use the public GOTO/navigation path: raw W_LOAD deliberately refuses a
  # pending window, while ordinary navigation flushes it with real observers.
  line=data[:pos].count(b'\r')+1;column=pos-(data.rfind(b'\r',0,pos)+1)
  f.typed(native_text(f'goto {line}'))
  for _ in range(column):f.command(2)
  assert f.get('se_hot_caret')==pos,('GOTO target',line,column,pos,f.get('se_hot_caret'))
 def edit(data,folds,pos,raw,tag):
  assert not any(x.flags&1 and x.hidden<=pos<x.end for x in folds),('test edits must use visible source',tag,pos)
  move(data,pos)
  for byte in raw:f.key(byte)
  data,folds=retained(folds,data,pos,0,raw);assert f.merged()==data;check(data,folds,tag);return data,folds
 try:
  f=Fixture(out,frozen,dll,True)
  data=native_text('plain start\r:::region A\ralpha\r:::end\routside middle\r:::region B\rbeta\r:::end\rplain end\r');f.source(data);tree,_,_,error=builder.oracle(data);assert not error and len(tree)==2
  f.command(115);folds,_=action_model(tree,3,0,0,f.get('se_ef_motion',4),0);check(data,folds,'two-fold-before-edit')
  data,folds=edit(data,folds,0,native_text('Q'),'outside-pending-edit-retains-both')
  if not args.smoke:
   # File-phase ownership and close are explicitly modeled here (no DOS).
   # Actual source flush, journal observer, modal helper and auto-rekey run.
   assert f.get('se_hot_pending',1) and f.get('se_ej_status',1)==1 and f.get('se_ej_count',1)==0
   for name in ['se_i_ready','se_i_count','se_n_cache_count']:f.put(name,0,1)
   phase=bytes((i*29+17)&255 for i in range(1152));f.m.load(0x8D00,phase);f.put('se_f_owner',1,1)
   assert not f.call('se_ef_modal').p&1 and not f.get('se_ef_valid',1) and f.get('se_ef_suspended',1)
   assert not f.call('se_hot_call',8).p&1
   for _ in range(10000):
    if not f.get('se_hot_phase',1):break
    assert not f.call('se_hot_call',2).p&1
   else:raise AssertionError('modal known flush did not complete')
   assert not f.get('se_hot_pending',1) and f.document()==data and f.get('se_ej_status',1)==1 and f.get('se_ej_count',1)==0 and f.read(0x8D00,1152)==phase
   f.put('se_f_owner',0,1);assert not f.call('se_ef_modal').p&1
   assert not f.get('se_ef_valid',1) and not f.get('se_ef_suspended',1) and f.get('se_ej_status',1)==1
   check(data,folds,'modal-known-flush-ARMED-invalid-auto-republish')
   # Accumulate disjoint edits without an intermediate fold rebuild.
   p=data.index(native_text('outside middle'));move(data,p);f.key(native_text('R')[0]);data,folds=retained(folds,data,p,0,native_text('R'))
   p=len(data);move(data,p);f.key(native_text('S')[0]);data,folds=retained(folds,data,p,0,native_text('S'));check(data,folds,'multiple-disjoint-edits')
   # Actual ordinary LEFT forces the hot flush without adding another edit.
   f.command(1);assert not f.get('se_hot_pending',1) and f.document()==data;check(data,folds,'known-hot-flush-retains-both')
   # Actual selection/cut/paste/history command paths; no modeled source writer.
   cut=data[:3];move(data,0);f.command(68);move(data,3);f.command(70);data,folds=retained(folds,data,0,3,b'');assert f.get('se_clip_length')==3;check(data,folds,'cut-outside-folds')
   f.command(71);data,folds=retained(folds,data,0,0,cut);check(data,folds,'paste-outside-folds')
   f.command(16);data,folds=retained(folds,data,0,len(cut),b'');check(data,folds,'undo-paste-retains')
   f.command(17);data,folds=retained(folds,data,0,0,cut);check(data,folds,'redo-paste-retains')
   # An opener edit deliberately drops its own old hint, retaining the sibling.
   p=data.index(native_text('region A'))+len(native_text('region '));data,folds=edit(data,folds,p,native_text('X'),'changed-opener-drops-only-A');assert [x.flags&1 for x in folds]==[0,1]
   for mode in [1,2,0]:f.command(96+mode);check(data,folds,f'after-retention-mode{mode}')
   # Parent stays expanded while two nested regions are independently closed.
   nested=native_text('# Parent\rintro\r:::region A\rfirst\r:::end\rmiddle\r:::region B\rsecond\r:::end\r# Tail\rend\r');f.source(nested);tree,_,_,error=builder.oracle(nested);assert not error
   move(nested,nested.index(native_text(':::region A')));f.command(113);folds,_=action_model(tree,1,1,f.get('se_hot_caret'),f.get('se_ef_motion',4),f.get('se_hot_caret'))
   move(nested,nested.index(native_text(':::region B')));f.command(113);folds,_=action_model(folds,1,2,f.get('se_hot_caret'),f.get('se_ef_motion',4),f.get('se_hot_caret'));check(nested,folds,'nested-siblings-before-edit')
   p=nested.index(native_text('region A'))+len(native_text('region '));nested,folds=edit(nested,folds,p,native_text('X'),'nested-opener-drops-A-keeps-B');assert not folds[1].flags&1 and folds[2].flags&1
   # Construct real saved inner-caret metadata at motion serial0, then force
   # the32-bit boundary and execute an ordinary movement through root code.
   wrapdata=native_text('plain\r:::region Saved\rhidden body\r:::end\rtail\r');f.source(wrapdata);tree,_,_,error=builder.oracle(wrapdata);assert not error
   saved=wrapdata.index(native_text('hidden body'))+2;move(wrapdata,saved);f.put('se_ef_motion',0,4);f.put('se_ef_checked_motion',0,4)
   f.command(113);folds,_=action_model(tree,1,0,saved,0,saved);check(wrapdata,folds,'motion-wrap-real-saved-caret-before');assert folds[0].flags==3 and folds[0].saved==saved
   f.put('se_ef_motion',0xffffffff,4);f.command(2);after_motion=f.get('se_hot_caret')
   assert f.get('se_ef_motion',4)==0 and f.get('se_ej_status',1)==0x80 and not f.get('se_ef_valid',1)
   check(wrapdata,[],'motion-wrap-disarms-and-renders-expanded',valid=False)
   f.command(114);assert f.get('se_hot_caret')==after_motion!=saved
   check(wrapdata,tree,'motion-wrap-fresh-expand-no-stale-caret')
  result=dict(status='passed',identity=identity,frames=frames,checked_reu_bytes=16*1024*1024,source_sha256=sha(Path(__file__)),scope='Actual editor automatic journal/R20/certified retention, complete CPU pixel/geometry oracle; ROM-read seam documented by grid fixture; no native/physical-key claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=frames),indent=2)+'\n');raise
 finally:
  if f is not None:f.close()
if __name__=='__main__':main()
