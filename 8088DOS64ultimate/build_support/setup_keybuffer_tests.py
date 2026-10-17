"""Fast real-6510/Peddle input compatibility tests; no DOS images or hardware."""
from pathlib import Path
import sys,os,json,hashlib,shutil,subprocess,tempfile
P=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=P/'build/setup-keybuffer-tests';out.mkdir(exist_ok=True);run=Path(tempfile.mkdtemp(prefix='run-',dir=out));inputs={};result={'status':'failed','physical':False,'scope':'Native standard-buffer input and physical CIA menu compatibility'}
 def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);inputs[str(p)]=digest(p);inputs[str(q)]=digest(q)
 def command(args,cwd,label):
  with(run/(label+'.stdout')).open('wb')as a,(run/(label+'.stderr')).open('wb')as b:subprocess.run(list(map(str,args)),cwd=cwd,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdin=subprocess.DEVNULL,stdout=a,stderr=b,check=True,timeout=120)
 try:
  command([sys.executable,'-B',P/'build_support/setup_installer.py','--out',run/'native'],P,'BUILD');native=json.loads((run/'native/RESULT.json').read_text());work=run/'tests';work.mkdir()
  for n in ['test_browser.py','test_select.py','test_keybuffer.py','test_capsule.py','test_source_load.py']:copy(P/'tests/setup_installer'/n,work/n)
  for source,target in [('SETUP.PRG','setup.prg'),('SETUP.labels','setup.labels'),('SETUP.FAT','fat-overlay.bin'),('SETUP.FAT','SETUP.FAT')]:copy(run/'native'/source,work/'build'/target)
  for p in (P/'tests/setup_installer/support').rglob('*'):
   if p.is_file():copy(p,work/p.relative_to(P/'tests/setup_installer/support'))
  for p in (P/'third_party/peddle/Peddle').rglob('*'):
   if p.is_file()and p.suffix in ['.h','.cpp','.hpp','.inc']:copy(p,work/p.relative_to(P))
  clang=os.environ.get('DOS64_CLANGXX','clang++');flags=['-dynamiclib']if sys.platform=='darwin'else['-shared','-fPIC']
  command([clang,'-std=c++20','-O2',*flags,'-Itests/floppy_export','-Itests/host','-Ithird_party/peddle/Peddle','tests/floppy_export/bridge.cpp',*[str(Path('third_party/peddle/Peddle')/n)for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o','browser-peddle.dylib'],work,'MODEL')
  for n,label in [('test_keybuffer.py','BUFFER'),('test_select.py','CIA')]:command([sys.executable,'-B',n],work,label)
  command([sys.executable,'-B','-m','unittest','-v','test_source_load.Loading.test_uppercase_lowercase_and_mixed_firmware_hex_receipts','test_source_load.Loading.test_all_five_sources_exact_twice_read_closed_private_bound_receipts','test_source_load.Loading.test_HIGH_copy_exact_and_code_survives_UI_to_FAT_retirement'],work,'HEX_SOURCES')
  assert all(digest(Path(p))==h for p,h in inputs.items());result.update(status='passed',native_keybuffer_cases=5,physical_shift_values_compared=256,existing_CIA_menu_cases=12,firmware_hex_case_groups=3,whole_sources_twice_read=5,native_SHA256=digest(run/'native/SETUP.PRG'),inputs_after_exact=True)
 except BaseException as e:result['error']=repr(e);raise
 finally:
  result.update(run=str(run),inputs=inputs);(run/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='inputs'},indent=2))
if __name__=='__main__':main()
