"""Actual cold startup followed by BOOT-poisoned public warm editor operations.

This is instruction-level warm-code independence, not ReadyOS suspend/resume or
native ROM/IRQ proof. The only ROM seams are existing asset imports/chargen reads.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, shutil, subprocess, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor, editor_fixture
from bindings import verify
import test_grid_modes as grid
from redraw_model import native_text

EXPECTED='c39cadcc9245c348727c1d052587013adc1ba685f6b72f02d6e4da4e95161565'
OLD=ROOT/'agentsworking/evidence/M5/20261025T013239650306Z-fold-selection-native/product-sources.zip'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out,smoke=False):
 frozen,identity=grid.freeze(out,None)
 with zipfile.ZipFile(out/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for directory in ['src','cfg','assets','tools']:
   for path in sorted((ROOT/directory).rglob('*')):
    if path.is_file() and '__pycache__' not in path.parts:z.write(path,path.relative_to(ROOT))
  z.write(ROOT/'Makefile','Makefile')
 assert identity['prg_sha256']==EXPECTED,identity
 seal=verify(frozen/'build/editor.prg',frozen/'build/editor.lbl')
 report=json.loads((frozen/'build/editor-report.json').read_text());s=report['symbols']
 assert 0x80D<=s['se_object_init']<0xF00
 cold=next(x for x in report['segments'] if x['name']=='COLD')
 assert cold['start']==0x80D and cold['end']<0xF00
 for name in identity['names']:
  raw=(frozen/f'build/overlays/{name}.seo').read_bytes()
  assert raw[20:36]==raw[36:52]==bytes.fromhex(seal['digest'])
 cpu_editor.ROOT=editor_fixture.ROOT=frozen
 cpu_editor.NAMES=editor_fixture.NAMES=identity['names']
 # No source(), se_clear_state(), object_init(), or provider_init() after this
 # real startup. All document bytes below enter through the public input path.
 dll=grid.runner(out);f=grid.Fixture(out,frozen,dll,colored=True);cases=[];states=[]
 try:
  initial=f.merged();assert initial and f.get('se_object_epoch',2)==f.get('se_reu_epoch',2)>0, (initial[:80],f.get('se_object_epoch',2),f.get('se_reu_epoch',2))
  (out/'startup-source.bin').write_bytes(initial)
  boot=bytes([0xA5])*2048;f.m.load(0x800,boot)
  def check(label,expected):
   assert f.merged()==expected,(label,f.merged(),expected)
   assert f.read(0x800,2048)==boot,(label,'BOOT clobbered')
   assert f.read(0xC600,1024)==f.shim,(label,'ReadyOS shim clobbered')
   assert f.get('se_e_error',1)==f.get('se_doc_read_locks',1)==f.get('se_f_owner',1)==0
   states.append(dict(label=label,length=len(expected),caret=f.get('se_hot_caret'),
      generation=f.get('se_doc_generation',2),current=f.get('se_h_current',4),saved=f.get('se_h_saved',4),
      mode=f.get('se_mode',1),pending=f.get('se_hot_pending',1),boot_sha256=hashlib.sha256(f.read(0x800,2048)).hexdigest()))
  for b in native_text('hello'):f.key(b)
  check('typing',native_text('hello')+initial);assert f.get('se_hot_pending',1)
  f.command(1);check('publicLEFT-flush',native_text('hello')+initial);assert not f.get('se_hot_pending',1)
  f.command(16);check('undo',initial)
  f.command(17);check('redo',native_text('hello')+initial)
  cases.append('coldstartup-tutorial/BOOT2048A5/publictyping/LEFTflush/undo/redo')
  if not smoke:
   exercise(f,check,cases)
  result=dict(status='passed',resident_sha256=identity['prg_sha256'],binding=seal['digest'],
      cold_init=s['se_object_init'],cold=cold,cases=cases,states=states,
      instructions=f.total_instructions,peak_call=f.peak,boot_guard_bytes=2048,shim_guard_bytes=1024,
      scope='Actual startup, then public warm editor input/commands; no source resets or initialization calls after BOOT poison. Existing modeled ROM imports/chargen reads only. Not native/ReadyOS resume proof.')
  (out/'warm-result.json').write_text(json.dumps(result,indent=2)+'\n')
  if not smoke:result['static']=static_checks(out,frozen,identity)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  (out/'final-c64.bin').write_bytes(f.read(0,65536));print(json.dumps(result,indent=2))
 finally:f.close()
 return result

def exercise(f,check,cases):
 prior=f.merged()
 # A flushed edit must replay exactly, retaining the earlier tutorial/savepoint.
 f.command(3);deleted=prior[:4]+prior[5:];check('BACK',deleted)
 f.command(1);check('BACK-flush',deleted)
 f.command(16);check('BACK-undo',prior)
 f.command(17);check('BACK-redo',deleted)
 f.command(16);check('BACK-undo-restore',prior)
 f.command(4);deleted=prior[:5]+prior[6:];check('DELETE',deleted)
 f.command(1);check('DELETE-flush',deleted)
 f.command(16);check('DELETE-undo',prior)
 f.command(17);check('DELETE-redo',deleted)
 f.command(16);check('DELETE-undo-restore',prior)
 cases.append('publicBACK-andDELETE/flush/undo-redo-exactcanonicalbytes')
 f.command(34);f.command(68)
 for _ in range(5):f.command(2)
 f.command(69);check('COPY-first5',prior)
 assert f.get('se_clip_length')==5
 token=f.read(f.s['se_clip_token'],5);logical=f.m.read(f.s['object_extents']+16*token[0]);physical=f.m.read(f.s['se_reu_map']+logical)
 assert bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,physical*65536+i) for i in range(5))==prior[:5]
 f.command(50);f.command(35);f.command(71);check('PASTE-atEOF',prior+prior[:5])
 f.command(16);check('PASTE-undo',prior)
 f.command(17);check('PASTE-redo',prior+prior[:5])
 f.command(16);check('PASTE-undo-restore',prior)
 cases.append('publicMARK/RIGHT/COPY/UNMARK/BOTTOM/PASTE/undo-redo/typedclipboardbytes')
 f.command(115);f.render();check('FOLDALL',prior)
 assert f.get('se_ef_valid',1)==1 and f.get('se_ef_count',2)>0
 f.command(116);f.render();check('UNFOLDALL',prior)
 assert f.get('se_ef_valid',1)==1
 cases.append('actualC19-build/collapseall/expandall/samecanonicalhistory')
 # Do not use grid.Fixture.mode(): its CPU-port query stub intentionally lives
 # at0E20 and is now poisoned. Product mode commands have no such dependency.
 for command,mode,width in [(97,1,60),(98,2,80),(96,0,0),(100,1,60),(100,2,80),(101,1,60),(96,0,0)]:
  canonical=f.canonical();catalog=f.catalog();f.command(command);f.render()
  assert f.get('se_mode',1)==mode and f.get('se_v_columns',1)==width
  assert f.canonical()==canonical and f.catalog()==catalog
  if mode==0:assert f.read(0x4800,2048)==f.fonts['chargen.bin'][2048:]
  check('mode-'+str(command)+'-'+str(mode),prior)
 cases.append('actual40-60-80/direct-next-prev/paint/fontrestore/canonicalhistory-catalogstable')
 # More editing after all mode/font/leaf transitions proves warm mutation still
 # works; expanded folds revalidate through real content changes.
 f.command(35);f.key(ord('!'));check('typing-aftermodes',prior+b'!')
 f.command(1);f.command(16);check('undo-aftermodes',prior)
 assert f.get('se_h_saved',4)==1 and f.get('se_h_current',4)!=1
 cases.append('postmode-realtyping/flush/undo/originalsavepointretained')

def static_checks(out,frozen,identity):
 from peddle import Machine
 s=json.loads((frozen/'build/editor-report.json').read_text())['symbols']
 audit=out/'static';audit.mkdir();labels={};allobjects={};module_names=set()
 # The linked labels contain every generated resident alias actually exported
 # into each packaged image. Numeric all-public includes omit COLD aliases.
 for name in identity['names']:
  for suffix in ['lbl','map']:
   shutil.copy2(ROOT/f'build/overlays/{name}.{suffix}',audit/f'{name}.{suffix}')
  module_names.update(re.findall(r'^([^\s:]+\.o):', (audit/f'{name}.map').read_text().split('Segment list:')[0],re.M))
  text=(audit/f'{name}.lbl').read_text()
  pairs=re.findall(r'^al ([0-9A-Fa-f]+) \.([^\s]+)',text,re.M)
  unsafe=[(n,int(a,16)) for a,n in pairs if 0x800<=int(a,16)<0x1000]
  assert not unsafe,(name,unsafe)
  labels[name]=len(pairs)
 # Only current-seal binding records are used, never stale other private runs.
 records=[]
 for directory in ['build','build/aux-control','build/diagnostics-editor','build/editor-file-prod','build/style-prod','build/grid-prod','build/fold-prod']:
  for path in (ROOT/directory).glob('*bindings.json'):
   value=json.loads(path.read_text())
   if value.get('resident_sha256')!=identity['prg_sha256'] or 'imports' not in value:continue
   assert not [(n,a) for n,a in value['imports'].items() if 0x800<=(a['address'] if isinstance(a,dict) else a)<0x1000],path
   dest=audit/path.relative_to(ROOT/'build');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
   records.append(str(path.relative_to(ROOT)))
   for name,h in value.get('object_sha256',{}).items():
    obj=ROOT/name if not Path(name).is_absolute() else Path(name)
    assert sha(obj)==h,(obj,'changed linked object')
    allobjects[obj]=h
 # Directly linked entry/bitmap/chrome objects use generated constants rather
 # than module_bindings. Include their actual top-level production objects.
 for directory in ['build/overlays','build/editor','build/grid-prod','build/engine','build/aux-control','build/diagnostics-editor','build/editor-file-prod','build/style-prod','build/fold-prod']:
  for obj in (ROOT/directory).glob('*.o'):
   if obj.name in module_names:allobjects[obj]=sha(obj)
 assert module_names<={p.name for p in allobjects},('uninspected packaged modules',module_names-{p.name for p in allobjects})
 import_audit={}
 for obj in sorted(allobjects):
  dump=subprocess.run(['od65','--dump-imports',str(obj)],check=True,capture_output=True,text=True).stdout
  names=re.findall(r'Name:\s*"([^"\n]+)"',dump)
  assert 'se_object_init' not in names,(obj,'cold initializer import')
  cold=[n for n in names if n in s and 0x800<=s[n]<0x1000];assert not cold,(obj,cold)
  import_audit[str(obj.relative_to(ROOT))]=dict(sha256=allobjects[obj],imports=names)
 (audit/'object-imports.json').write_text(json.dumps(import_audit,indent=2)+'\n')
 # An explicit malicious direct import must be refused by the real binder.
 stub=audit/'cold-request.s';stub.write_text('.import se_object_init\n.segment "CODE"\njsr se_object_init\n')
 subprocess.run(['ca65',str(stub),'-o',str(stub.with_suffix('.o'))],check=True)
 rejected=subprocess.run([sys.executable,str(ROOT/'tools/module_bindings.py'),'--report',str(frozen/'build/editor-report.json'),'--output',str(audit/'must-not-exist.s'),str(stub.with_suffix('.o'))],capture_output=True,text=True)
 (audit/'cold-request.stdout').write_text(rejected.stdout+rejected.stderr)
 assert rejected.returncode and 'Unsafe resident alias' in rejected.stderr and 'se_object_init' in rejected.stderr
 assert not (audit/'must-not-exist.s').exists()
 generic=generic_equivalence(audit,frozen)
 return dict(packaged_images=len(labels),linked_alias_counts=labels,current_binding_records=records,
    object_imports_checked=len(import_audit),direct_cold_request_rejected=True,generic=generic)

def generic_equivalence(out,frozen):
 from peddle import Machine
 # Source snapshot predates the editor-only COLD switch; assemble both with no
 # define against identical sealed warm imports and identical linker placement.
 oldsrc=zipfile.ZipFile(OLD).read('src/object/allocate.s')
 paths=[];results=[]
 config=out/'generic.cfg';config.write_text('MEMORY { CODE:file=%O,start=$5000,size=$1000; STATE:file="",start=$8800,size=$0100; }\nSEGMENTS {CODE:load=CODE,type=ro; OBJECTS:load=STATE,type=bss;}\n')
 for label,source in [('previous80659',oldsrc),('current-default',(ROOT/'src/object/allocate.s').read_bytes())]:
  d=out/label;d.mkdir();src=d/'allocate.s';src.write_bytes(source);obj=d/'allocate.o'
  subprocess.run(['ca65','-g','-I',str(ROOT/'src'),str(src),'-o',str(obj)],check=True)
  aliases=d/'bindings.s'
  subprocess.run([sys.executable,str(ROOT/'tools/module_bindings.py'),'--report',str(frozen/'build/editor-report.json'),'--output',str(aliases),str(obj)],check=True,capture_output=True,text=True)
  subprocess.run(['ca65',str(aliases),'-o',str(d/'bindings.o')],check=True)
  image=d/'allocate.bin';lbl=d/'allocate.lbl'
  subprocess.run(['ld65','-C',str(config),'-o',str(image),'-Ln',str(lbl),str(obj),str(d/'bindings.o')],check=True)
  paths.append(image)
  names={n:int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.([^\s]+)',lbl.read_text(),re.M)}
  report=json.loads((frozen/'build/editor-report.json').read_text());symbols=report['symbols'];m=Machine()
  try:
   m.load(0x801,(frozen/'build/editor.prg').read_bytes()[2:]);m.load(0x5000,image.read_bytes())
   m.call(symbols['se_clear_state']);m.load(symbols['se_reu_banks'],(256).to_bytes(2,'little'))
   r,n=m.call(symbols['se_reu_provider_init']);assert not r.p&1
   calls=[]
   for name,a,x,expected_c in [('se_object_init',0,0,0),('se_object_init',0,0,1),('se_object_create',99,1,0),('se_object_release',0,0,0)]:
    r,n=m.call(names[name],a=a,x=x);assert bool(r.p&1)==bool(expected_c),(label,name,r.a)
    calls.append(dict(name=name,A=r.a,X=r.x,Y=r.y,C=r.p&1,instructions=n))
   results.append(calls)
  finally:m.close()
 assert paths[0].read_bytes()==paths[1].read_bytes() and results[0]==results[1]
 return dict(previous_source_zip=str(OLD.relative_to(ROOT)),previous_source_zip_sha256=sha(OLD),
    default_binary_bytes=paths[0].stat().st_size,default_binary_sha256=sha(paths[0]),
    byte_identical=True,instruction_results_identical=True,calls=results[0])

def main():
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');a=p.parse_args()
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/editor-cold-init'/stamp;out.mkdir(parents=True)
 try:run(out,a.smoke)
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');raise
 print('OUTPUT',out)
 if not a.smoke:
  evidence=ROOT/'agentsworking/evidence/M7'/(stamp+'-editor-cold-init');evidence.mkdir(parents=True)
  shutil.copytree(out,evidence/'build')
  with zipfile.ZipFile(evidence/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
   for path in [Path(__file__),ROOT/'tests/test_grid_modes.py',ROOT/'tools/editor_fixture.py',ROOT/'tools/cpu_editor.py',ROOT/'tools/module_bindings.py',ROOT/'tools/overlay_api.py',ROOT/'tools/peddle.py']:
    z.write(path,path.relative_to(ROOT))
  print('EVIDENCE',evidence)
if __name__=='__main__':main()
