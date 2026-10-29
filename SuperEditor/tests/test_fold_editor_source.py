"""Optional source callback against an immutable actual editor build.

Actual piece/splice/hot calls run before private capsule injection. Product slot
bytes are restored before any subsequent editor overlay operation. This is a
CPU capsule test, not integrated UI, a new editor build or a VICE claim.
"""
from pathlib import Path
import importlib.util,json,sys,subprocess,re,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import editor_fixture,cpu_editor
FROZEN=ROOT/'build/editor-file-integration/20261024T213441593038Z';FREEZE=json.loads((FROZEN/'freeze.json').read_text());assert FREEZE['prg_sha256']=='2f6d1a76cb12424e03d2965e33853fb343032eead32797eca0a4b46fd9bf72ff'
editor_fixture.ROOT=FROZEN;cpu_editor.ROOT=FROZEN;editor_fixture.NAMES=cpu_editor.NAMES=FREEZE['names']
from supermark_probe import petscii
spec=importlib.util.spec_from_file_location('builder_oracle',ROOT/'tests/test_fold_builder.py');model=importlib.util.module_from_spec(spec);sys.modules[spec.name]=model;spec.loader.exec_module(model)
OUT=ROOT/'build/folds/editor-source';OUT.mkdir(parents=True,exist_ok=True)
MODULES=['state','store','validate','query','action','builder-state','builder','builder-filter','builder-retain','source-state','source-context','source-read','source-lease']

def build():
 objects=[]
 for name in MODULES+['parser']:
  src=ROOT/'src'/('supermark/block.s' if name=='parser' else 'fold/'+name+'.s');out=OUT/(name+'.o');args=['ca65','-I',str(ROOT/'src'),'-g','-o',str(out)]
  if name=='builder':args+=['-D','SE_FOLD_EDITOR_SOURCE']
  subprocess.run(args+[str(src)],check=True);objects.append(out)
 imports=set();exports=set()
 for obj in objects:
  for flag,values in [('--dump-imports',imports),('--dump-exports',exports)]:
   text=subprocess.run(['od65',flag,str(obj)],capture_output=True,text=True,check=True).stdout;values.update(re.findall(r'Name:\s+"([^"]+)"',text))
 root=json.loads((FROZEN/'build/editor-report.json').read_text());external=imports-exports
 assert external<=root['symbols'].keys(),sorted(external-root['symbols'].keys())
 lines=[]
 for name in sorted(external):lines+=['.exportzp '+name if name in ['text_ptr','se_hot_ptr','se_hot_packet'] else '.export '+name,name+' = $%04X'%root['symbols'][name]]
 (OUT/'externals.s').write_text('\n'.join(lines)+'\n');subprocess.run(['ca65','-o',str(OUT/'externals.o'),str(OUT/'externals.s')],check=True)
 subprocess.run(['ld65','-C',str(ROOT/'src/fold/source-probe.cfg'),'-o',str(OUT/'unused.bin'),'-m',str(OUT/'capsule.map'),'-Ln',str(OUT/'capsule.lbl'),*map(str,objects),str(OUT/'externals.o')],cwd=ROOT,check=True)
 (OUT/'binding.json').write_text(json.dumps(dict(prg_sha256=FREEZE['prg_sha256'],external_symbols={n:root['symbols'][n] for n in sorted(external)},assets=FREEZE['assets']),indent=2)+'\n')

class Fixture(editor_fixture.EditorFixture):
 def __init__(self,data):
  super().__init__();self.source(data,banks=2,physical=32);self.data=data;self.cs={p[2].lstrip('.'):int(p[1],16) for line in (OUT/'capsule.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'};self.peak={};self.steps=0;self.short=0
  self.product=None;self.phase=None;self.product_index=None;self.install(clear=True)
 def cget(self,name,n=1):return int.from_bytes(self.read(self.cs[name],n),'little')
 def cput(self,name,value,n=1):self.m.load(self.cs[name],value if isinstance(value,bytes) else value.to_bytes(n,'little'))
 def cc(self,name):
  r,used=self.m.call(self.cs[name],limit=100000);self.peak[name]=max(self.peak.get(name,0),used);return r
 def install(self,clear=False):
  self.product=[(a,self.read(a,4096)) for a in [0x5000,0x6000,0xB000]];self.product_index=self.read(0x8D00,0x480)
  for a,n in [(0x5000,'r1.bin'),(0x6000,'r2.bin'),(0xB000,'c.bin')]:self.m.load(a,(OUT/n).read_bytes())
  if clear:self.m.load(0x8D00,bytes(0x480))
  elif self.phase is not None:self.m.load(0x8D00,self.phase)
 def restore(self):
  self.phase=self.read(0x8D00,0x480)
  for a,data in self.product:self.m.load(a,data)
  self.m.load(0x8D00,self.product_index)
 def canonical(self):
  return self.read(self.s['se_doc_roots'],512)+b''.join(self.read(self.s[n],w) for n,w in [('se_doc_generation',2),('se_doc_length',3),('se_doc_meta',15),('se_hot_ready',1),('se_hot_pending',1),('se_hot_base',3),('se_hot_caret',3),('se_hot_left',2),('se_hot_right',2)])+self.read(0x9200,2048)+self.read(self.s['se_sel_mark'],13)
 def read_at(self,pos,request=128,buffer=0x8880,error=0):
  self.cput('se_fs_offset',pos,3);self.cput('se_fs_count',request);self.cput('se_fs_buffer',buffer,2);r=self.cc('se_fs_read');assert bool(r.p&1)==bool(error),(pos,r.a,error)
  if error:assert r.a==error;return b''
  count=self.cget('se_fs_done');assert 0<=count<=request
  if count<request and pos+count<self.cget('se_fs_length',3):self.short+=1
  return self.read(buffer,count)
 def scan(self,modelbytes):
  before=self.canonical();view=self.read(0x8C00,256)+self.read(0x9180,128);leases=self.get('se_doc_read_locks',1);r=self.cc('se_fs_begin');assert not r.p&1,(r.a,'begin');assert self.get('se_doc_read_locks',1)==leases+1 and self.cget('se_fs_length',3)==len(modelbytes)
  out=bytearray()
  while len(out)<len(modelbytes):
   chunk=self.read_at(len(out));assert chunk;out+=chunk
  assert bytes(out)==modelbytes;assert self.read_at(len(modelbytes))==b''
  # Absolute restart at arbitrary offsets must not depend on previous view/cache.
  for pos in sorted({0,len(modelbytes),len(modelbytes)//2,*[i for i in [65530,65535,65536] if i<len(modelbytes)]}):
   chunk=self.read_at(pos,17);assert chunk==modelbytes[pos:pos+len(chunk)]
  assert not self.cc('se_fs_end').p&1;assert self.get('se_doc_read_locks',1)==leases and self.canonical()==before;assert self.read(0x8C00,256)+self.read(0x9180,128)==view;assert self.read(0xC600,1024)==self.shim
 def builder(self,modelbytes):
  self.restore();r,_=self.m.call(self.s['se_object_create'],a=0x46,x=1);assert not r.p&1
  token=self.read(self.s['se_object_id'],5);self.put('se_object_offset',65536);assert not self.call('se_object_resize').p&1
  self.install();self.cput('se_fold_token',token);self.cput('se_fb_capacity',2048,2);self.cput('se_fb_old_valid',0)
  before=self.canonical();reu_before=self.reu_image();leases=self.get('se_doc_read_locks',1);r=self.cc('se_fb_begin');assert not r.p&1,(r.a,'builder begin')
  while self.cget('se_fb_busy'):
   old=self.cget('se_sm_pos',3);r=self.cc('se_fb_step');assert not r.p&1,(r.a,self.cget('se_fb_phase'));assert self.cget('se_sm_pos',3)-old<=32;self.steps+=1;assert self.steps<100000
  assert self.cget('se_fold_valid') and not self.cget('se_fs_owned') and self.get('se_doc_read_locks',1)==leases
  expected,omitted,empty,error=model.oracle(modelbytes);assert not error
  actual=self.object_bytes(token[0],len(expected)*32);assert actual==b''.join(x.bytes() for x in expected),(actual.hex(),b''.join(x.bytes() for x in expected).hex())
  assert self.cget('se_fold_count',2)==len(expected) and self.cget('se_fb_omitted',2)==omitted
  assert self.canonical()==before and self.document()==self.data
  image=self.reu_image();bank=self.m.read(self.s['se_reu_map']+self.m.read(self.s['object_extents']+token[0]*16))
  assert all(image[i*65536:(i+1)*65536]==reu_before[i*65536:(i+1)*65536] for i in range(32) if i!=bank)
  return len(expected)
 def reu_image(self):return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,i) for i in range(32*65536))
 def object_bytes(self,id,length):
  banks=[self.m.read(self.s['se_reu_map']+self.m.read(self.s['object_extents']+id*16+i)) for i in range(self.m.read(self.s['object_banks']+id))]
  return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,banks[i>>16]*65536+(i&65535)) for i in range(length))
 def splice(self,pos,data):
  self.restore();self.put('se_doc_edit_position',pos);self.put('se_doc_edit_delete',0);self.put('se_doc_edit_insert',len(data));assert not self.call('se_doc_splice_begin').p&1
  self.m.load(0x8000,data);self.put('se_doc_count',len(data),2);self.put('se_doc_c64',0x8000,2);assert not self.call('se_doc_splice_feed').p&1
  while self.get('se_doc_busy',1):assert not self.call('se_doc_splice_step').p&1
  self.data=self.data[:pos]+data+self.data[pos:];self.install()

def main():
 build();(OUT/'result.json').unlink(missing_ok=True)
 data=petscii('# Head\n')+b'A'*66000+petscii('\n:::region Tail\n:::basic\n10 PRINT "Mixed CASE"\n:::\n:::end\n# End\nbody\n')
 f=Fixture(data);cases=[]
 try:
  f.scan(data);cases.append('actual hot cache + committed suffix >64KiB')
  # Close the unchanged hot cache through the real window service, then use
  # actual full byte splices to create many short alternating source pieces.
  f.restore();assert not f.call('se_hot_call',10).p&1;f.install()
  for i in range(40):f.splice(8+2*i,b'x')
  assert f.get('se_hot_ready',1)==0;modelbytes=f.data;f.scan(modelbytes);assert f.short>0;cases.append('40 actual splices / fragmented read_some partial spans')
  folds=f.builder(modelbytes);cases.append('actual piece-table parser builder exact fold records')
  # Real hot LOAD and INSERT/BACK operations create a pending merged view.
  f.restore();f.position(65550)
  for byte in petscii('Pending\n'):f.key(byte)
  caret=f.get('se_hot_caret');pending=petscii('Pending\n');merged=modelbytes[:65550]+pending+modelbytes[65550:]
  assert f.get('se_hot_pending',1)==1;f.install();f.scan(merged);cases.append('actual pending gap insertion across64KiB')
  f.restore();f.key(0x89);f.install();assert f.get('se_sel_mark',1)==1;f.builder(merged);cases.append('parser builder over real pending merged view, preserving actual mark/anchors')
  # Repeated output refusals precede document DMA and preserve protected bytes.
  assert not f.cc('se_fs_begin').p&1;before=f.get('se_reu_dma_calls',2)
  for address,count in [(0x8800,1),(0x887F,1),(0x8BFF,2),(0x8C00,1),(0x9180,1),(0x91FF,1),(0x9200,1),(0xC600,128),(0xFFF0,128),(0x8880,0),(0x8880,129),(f.cs['se_fs_state'],1)]:f.read_at(0,count,address,0xB0)
  assert f.get('se_reu_dma_calls',2)==before;assert not f.cc('se_fs_end').p&1;cases.append('VIEW/NAV/shim/overflow/diagnostic prefix refused before DMA')
  # A foreign lease remains after our idempotent END.
  assert not f.call('se_doc_read_acquire').p&1;assert f.get('se_doc_read_locks',1)==1;assert not f.cc('se_fs_begin').p&1;assert f.get('se_doc_read_locks',1)==2
  f.cc('se_fs_end');f.cc('se_fs_end');assert f.get('se_doc_read_locks',1)==1;assert not f.call('se_doc_read_release').p&1;cases.append('foreign counted lease preserved')
  # Actual pending typing while the adapter owns a committed read lease is
  # source-context change; restore product overlays for the real key event.
  assert not f.cc('se_fs_begin').p&1;f.restore();f.put('se_e_mods',0,1);f.put('se_e_key',petscii('Q')[0],1);f.call('se_editor_input');assert not f.get('se_e_job',1) and not f.get('se_e_error',1) and f.get('se_doc_read_locks',1)==1;f.install();r=f.cc('se_fs_guard');assert r.p&1 and r.a==0xB1;f.cc('se_fs_end');assert f.get('se_doc_read_locks',1)==0;cases.append('actual pending typing invalidates source context')
  # Shape failures are rejected before acquiring a lease or reading a gap.
  for name,width,value in [('se_hot_right',2,2049),('se_hot_left',2,2049),('se_hot_length',2,2049),('se_hot_old_length',2,2049),('se_hot_base',3,0xFFFFFF),('se_hot_epoch',2,0xFFFF)]:
   original=f.read(f.s[name],width);f.put(name,value,width);before=f.get('se_reu_dma_calls',2);r=f.cc('se_fs_begin');assert r.p&1 and f.get('se_doc_read_locks',1)==0 and f.get('se_reu_dma_calls',2)==before;f.m.load(f.s[name],original)
  cases.append('malformed pending bounds/epoch refused before lease/DMA')
  # Cleanup cannot decrement a newly current provider/document/graph's lease.
  for changed in ['se_reu_epoch','se_doc_epoch','se_doc_meta']:
   assert not f.cc('se_fs_begin').p&1;size=5 if changed=='se_doc_meta' else 2;original=f.read(f.s[changed],size);f.put(changed,int.from_bytes(original,'little')+1,size);f.put('se_doc_read_locks',7,1);f.cc('se_fs_end');f.cc('se_fs_end');assert f.get('se_doc_read_locks',1)==7 and not f.cget('se_fs_owned');f.m.load(f.s[changed],original);f.put('se_doc_read_locks',0,1)
  cases.append('END preserves7foreign leases after provider/doc/graph replacement')
  # Root busy operations are refused; our cleanup may release exactly our lease
  # after a changed motion/source generation, with the same graph lifetime.
  for name in ['se_doc_busy','se_hot_phase','se_h_phase','se_b_phase','se_clip_busy','se_snapshot_busy']:
   original=f.get(name,1);f.put(name,1,1);r=f.cc('se_fs_begin');assert r.p&1 and f.get('se_doc_read_locks',1)==0;f.put(name,original,1)
  assert not f.cc('se_fs_begin').p&1;identity=f.read(f.cs['se_fs_identity'],59);assert f.cc('se_fs_begin').p&1;assert f.get('se_doc_read_locks',1)==1 and f.read(f.cs['se_fs_identity'],59)==identity;f.cc('se_fs_end');cases.append('competing BEGIN/busy phases preserve owned and foreign contexts')
  # Existing source-client ownership must survive rejected builder BEGIN.
  assert not f.cc('se_fs_begin').p&1;assert f.cc('se_fb_begin').p&1;assert f.cget('se_fs_owned') and f.get('se_doc_read_locks',1)==1;f.cc('se_fs_end')
  # Actual public splice admission is blocked by the counted lease. Restore
  # product slot/index bytes before invoking its real engine overlay.
  assert not f.cc('se_fs_begin').p&1;before=f.canonical();f.restore();f.put('se_doc_edit_position',0);f.put('se_doc_edit_delete',0);f.put('se_doc_edit_insert',1);r=f.call('se_doc_splice_begin');assert r.p&1 and r.a==0x41 and not f.get('se_doc_busy',1);f.install();assert f.canonical()==before;f.cc('se_fs_end')
  # Builder CANCEL/END releases only its own lease, preserving another reader.
  assert not f.call('se_doc_read_acquire').p&1;assert not f.cc('se_fb_begin').p&1;assert f.get('se_doc_read_locks',1)==2;f.cc('se_fb_cancel');f.cc('se_fb_cancel');assert f.get('se_doc_read_locks',1)==1;f.call('se_doc_read_release')
  f.cput('se_fb_old_valid',1);assert f.cc('se_fb_begin').p&1 and f.get('se_doc_read_locks',1)==0;f.cput('se_fb_old_valid',0)
  cases.append('actual splice admission blocked; builder BEGIN/cancel/retention ownership safe')
  assert f.read(0xC600,1024)==f.shim
  result=dict(status='passed',editor_prg_sha256=FREEZE['prg_sha256'],editor_assets=FREEZE['assets'],cases=cases,canonical_source_length=len(modelbytes),merged_source_length=len(merged),actual_splices=40,short_nonEOF_reads=f.short,builder_fold_count=folds,builder_steps=f.steps,adapter_context_bytes=f.cs['se_fs_state_size'],full_phase_bytes=557+f.cs['se_fs_state_size'],zero_page_bytes_added=0,exact_committed_source_verified_after_each_build=True,unchanged_reu_bytes_per_build=31*65536,shim_bytes=1024,peak_instructions=f.peak,source_bindings=json.loads((OUT/'binding.json').read_text()),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted([* (ROOT/'src/fold').glob('*'),Path(__file__).resolve(),ROOT/'tools/editor_fixture.py',ROOT/'tools/cpu_editor.py',ROOT/'tools/peddle.py']) if p.is_file()},capsule_sha256={n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in ['r1.bin','r2.bin','c.bin']},limits=['CPU capsule calls immutable editor resident piece/splice/hot code; no product integration/placement or VICE/UI claim.','Fixture startup imports emulate ROM asset loads; source is initialized through actual object/adopt APIs.','Editor-source old-map retention is rejected until full identity retention proof exists.'])
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()

if __name__=='__main__':main()
