from pathlib import Path
import json,hashlib,subprocess,shutil,sys,time,platform
P=Path(__file__).parent;S=P/'project';R=P/'closed-final';R.mkdir(exist_ok=False)
def ident(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def write(p,j):p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def command(name,argv,cwd=S):
 t=time.monotonic()
 with(R/(name+'.stdout')).open('wb')as o,(R/(name+'.stderr')).open('wb')as e:q=subprocess.run(argv,cwd=cwd,stdin=subprocess.DEVNULL,stdout=o,stderr=e)
 row={'name':name,'argv':list(map(str,argv)),'cwd':str(cwd),'exit':q.returncode,'seconds':time.monotonic()-t};commands.append(row);write(R/'COMMANDS.json',commands);assert q.returncode==0,row;return row
commands=[];sources={};excluded={'build','.zig-cache','zig-out','__pycache__'}
for p in sorted(S.rglob('*')):
 if not p.is_file()or any(n in excluded for n in p.relative_to(S).parts)or p.suffix=='.pyc':continue
 n=str(p.relative_to(S));dst=R/'source'/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst);v=ident(p);assert ident(dst)==v;sources[str(p)]=v;sources[str(dst)]=v
sources[str(Path(__file__).resolve())]=ident(Path(__file__))
zig=Path('/Users/karlprosserpp/dev/c64projects/zeropage-tooling/bin/zig').resolve()
for tool in [zig,Path(shutil.which('make')).resolve(),Path(shutil.which('ca65')).resolve(),Path(shutil.which('ld65')).resolve(),Path(sys.executable).resolve()]:sources[str(tool)]=ident(tool)
# Pin source resources once before compilation/execution, recheck all afterward.
for base in [zig.parent/'lib',Path('/opt/homebrew/share/cc65/asminc'),Path('/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include')]:
 for p in sorted(base.rglob('*')):
  if p.is_file():sources[str(p.resolve())]=ident(p)
write(R/'INPUTS_BEFORE.json',sources)
command('native-build',['make','-j4','build','hardware-helpers','range-probe','DOS64_TRAP1=1','DOS64_ZIG='+str(zig)])
command('zig-compile',[str(zig),'build','base-full-compile','cpu-trap-compile','-Dcpu-corpus=true','--summary','all','--cache-dir',str(R/'zig-cache')])
products={str(p):ident(p)for p in (S/'build').rglob('*')if p.is_file()and p.suffix in('.prg','.bin','.o','.map','.labels')}
products.update({str(S/'zig-out/bin'/n):ident(S/'zig-out/bin'/n)for n in ['cpu-trap-tests','base-full-tests']})
write(R/'PRODUCTS_BEFORE.json',products)
command('trap18',[str(S/'zig-out/bin/cpu-trap-tests')])
command('base507-full5701',[str(S/'zig-out/bin/base-full-tests')])
for n,v in sources.items():assert ident(Path(n))==v,n
for n,v in products.items():assert ident(Path(n))==v,n
write(R/'INPUTS_AFTER.json',sources);write(R/'PRODUCTS_AFTER.json',products)
corpus=json.loads((S/'build/cpu-corpus-full.json').read_text());assert corpus['hardware_cases']==5701 and corpus['full_pinned_corpus'] is True
traplog=(R/'trap18.stderr').read_text();baselog=(R/'base507-full5701.stderr').read_text();assert 'All 18 tests passed' in traplog,traplog[-500:];assert 'All 507 tests passed' in baselog,baselog[-1000:]
report={'status':'PASSED_PRIVATE_OPTIONAL_8088_TF_COMPONENT','groups':{'actual_trap':18,'actual_base':507,'hardware_corpus_cases':5701},'inputs':len(sources),'products':len(products),'all_inputs_copies_before_after_exact':True,'all_products_before_after_exact':True,'commands':commands,'runtime':ident(S/'build/dos64.prg'),'UNIT':ident(S/'build/dos64-tests.prg'),'physical':False,'source_only_runtime_media_builder':False,'genuine_DEBUG_DOS_execution':False,'public_native_changes':False,'performance_claim':False,'platform':platform.platform()}
write(R/'RESULT.json',report);print(json.dumps(report,indent=2))
