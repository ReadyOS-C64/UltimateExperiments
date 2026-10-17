#!/usr/bin/env python3
"""Opt-in source-only native SETUP/Peddle integration tests with local DOS media."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.pycache_prefix=str(ROOT/'build'/('.absent-setup-tests-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Test driver cache prefix must be absent')
import argparse
import hashlib
import importlib.util
import json
import shutil
import struct
import subprocess
import tempfile

TESTS=ROOT/'tests/setup_installer'
DISKS=['MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - '+str(i)+' of 3.img'for i in [1,2,3]]
CASES=['test_full_native_SYS_UI_sources_disks_publication_root_success','test_existing_C_collision_root_failure_no_publication','test_START_collision_never_publishes_CFG','test_CFG_collision_preserves_original_after_verified_START']

def digest(p):
    b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def verify(record):
    for n,want in record.items():
        if digest(Path(n))!=want:raise RuntimeError('Input/product changed: '+n)
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def executable(name,override=None):
    path=shutil.which(override or name)
    if not path:raise RuntimeError('Required test tool not found: '+name)
    return str(Path(path).resolve())
def toolchain():
    installer=load_module('setup_production_builder',ROOT/'build_support/setup_installer.py');t=installer.toolchain()
    candidate=os.environ.get('DOS64_ZIG')or shutil.which('zig')
    fallback=ROOT.parents[1]/'zeropage-tooling/bin/zig'
    if not candidate and fallback.is_file():candidate=str(fallback)
    if not candidate:raise RuntimeError('Set DOS64_ZIG to the Zig compiler executable')
    t.update({'zig':executable('zig',candidate),'clang++':executable('clang++',os.environ.get('DOS64_CLANGXX')or os.environ.get('DOS64_CLANG++')),'make':executable('make',os.environ.get('DOS64_MAKE')),'python':str(Path(sys.executable).resolve())})
    return t

def copy(source,target,record):
    want=digest(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    if digest(target)!=want:raise RuntimeError('Source copy mismatch: '+str(source))
    record[str(source)]=want;record[str(target)]=want

def validate_disk(path,number,oracle):
    if not path.is_file():raise RuntimeError('DOS disk'+str(number)+' not found; use --disk'+str(number)+' PATH: '+str(path))
    b=path.read_bytes()
    if len(b)!=368640 or struct.unpack_from('<H',b,11)[0]!=512 or b[13]!=2 or b[16]!=2 or struct.unpack_from('<H',b,19)[0]!=720 or struct.unpack_from('<HH',b,24)!=(9,2):
        raise RuntimeError('DOS disk'+str(number)+' must be a complete360KiB,512-byte-sector,9x2 FAT12 image')
    volume=oracle.Volume(b)
    if not volume.payloads:raise RuntimeError('DOS disk'+str(number)+' has no files')
    if number==1 and not {'IO.SYS','MSDOS.SYS','COMMAND.COM'}<=set(volume.payloads):raise RuntimeError('DOS disk1 must contain IO.SYS, MSDOS.SYS and COMMAND.COM')
    return digest(path)

def command(argv,cwd,env,log,commands):
    argv=[str(x)for x in argv];commands.append(argv)
    with log.with_suffix('.stdout').open('wb')as out,log.with_suffix('.stderr').open('wb')as err:
        r=subprocess.run(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
    if r.returncode:raise RuntimeError('Command failed ('+str(r.returncode)+'); see '+str(log.with_suffix('.stderr')))

def stop_owned(jobs):
    errors=[]
    for proc,*_ in jobs:
        if proc.poll() is None:
            try:proc.terminate()
            except BaseException as e:errors.append(type(e).__name__+': '+str(e))
    for proc,o,e,*_ in jobs:
        try:
            if proc.poll() is None:
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
        except BaseException as failure:errors.append(type(failure).__name__+': '+str(failure))
        for stream in [o,e]:
            try:stream.close()
            except BaseException as failure:errors.append(type(failure).__name__+': '+str(failure))
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for i,name in enumerate(DISKS,1):p.add_argument('--disk'+str(i),type=Path,default=ROOT/'reference'/name,help='Locally supplied DOS disk'+str(i)+' (not distributed)')
    p.add_argument('--out',type=Path,default=ROOT/'build/setup-installer-tests',help='Owned results directory; each invocation creates a fresh source-only run')
    args=p.parse_args();media=[getattr(args,'disk'+str(i)).resolve()for i in [1,2,3]];t=toolchain()
    oracle=load_module('setup_test_disk_oracle',TESTS/'dos_disk_inspect.py')
    for i,q in enumerate(media,1):validate_disk(q,i,oracle)
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='run-',dir=out));commands=[];phase='start template';work=None;jobs=[];result_path=run/'RESULT.json'
    record={str(Path(n)):digest(Path(n))for n in [__file__,*t.values()]};record.update({str(q):digest(q)for q in media});products={}
    includes=Path(t['cc65']).parent.parent/'share/cc65/include'
    for name in ['string.h','stddef.h']:
        q=includes/name
        if q.is_file():record[str(q)]=digest(q)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    for n in ['DOS64_TEST_PHASE','SOURCE_ONLY','PYTHONPATH','PYTHONPYCACHEPREFIX']:env.pop(n,None)
    for n in ['cc65','ca65','ld65']:env['DOS64_'+n.upper()]=t[n]
    env['DOS64_CC65_LIB']=t['library'];env['DOS64_PYTHON']=t['python'];env['DOS64_ZIG']=t['zig']
    try:
        (out/'RESULT.json').write_text(json.dumps({'status':'running','run':str(run)},indent=2)+'\n')
        start_builder=load_module('setup_start_source_graph',ROOT/'build_support/start_launcher.py')
        for n in [ROOT/'Makefile',ROOT/'build_support/setup.mk',ROOT/'build_support/start_launcher.py',ROOT/'build_support/start_template_descriptor.py',*[ROOT/x for x in start_builder.NATIVE.values()]]:record[str(n)]=digest(n)
        command([t['make'],'-C',ROOT,'start-template'],ROOT,env,run/'START_TEMPLATE',commands)
        start=ROOT/'build/start';start_result=json.loads((start/'RESULT.json').read_text())
        if start_result['status']!='passed':raise RuntimeError('START template source build did not pass')
        record.update(start_result['source_inputs'])
        for dest,src in start_builder.NATIVE.items():
            staged=start/'work'/dest;record[str(staged)]=digest(staged)
            if record[str(staged)]!=digest(ROOT/src):raise RuntimeError('START staged source mismatch: '+dest)
        phase='production builder'
        command([t['python'],'-B',ROOT/'build_support/setup_installer.py','--out',run/'production'],ROOT,env,run/'PRODUCTION_BUILD',commands)
        built=json.loads((run/'production/RESULT.json').read_text())
        if built['status']!='passed':raise RuntimeError('Production installer source build did not pass')
        record.update(built['source_inputs']);work=Path(built['work'])
        phase='test source staging'
        # Only independent Python/oracle/Zig and model code is staged here.
        # Native C/ASM comes exclusively from the public production builder.
        for q in sorted(TESTS.iterdir()):
            if q.is_file()and q.suffix in ['.py','.zig']:copy(q,work/q.name,record)
        for q in sorted((TESTS/'support').rglob('*')):
            if q.is_file():copy(q,work/q.relative_to(TESTS/'support'),record)
        for i,q in enumerate(media,1):copy(q,work.parent/'inputs'/('disk'+str(i)+'.img'),record)
        copy(start/'START.PRG',work.parent/'inputs/START.TPL',record);copy(start/'START.REL',work.parent/'inputs/START.REL',record)
        phase='host model compile'
        shared=['-dynamiclib']if sys.platform=='darwin'else['-shared','-fPIC']
        command([t['clang++'],'-std=c++20','-O2',*shared,'-Itests/floppy_export','-Itests/host','-Ithird_party/peddle/Peddle','tests/floppy_export/bridge.cpp',*[str(Path('third_party/peddle/Peddle')/n)for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o','browser-peddle.dylib'],work,env,run/'BRIDGE',commands)
        command([t['zig'],'build','--build-file','build-coordinator.zig','compile','--summary','all'],work,env,run/'ZIG_BUILD',commands)
        products={str(q):digest(q)for q in sorted((work/'build').rglob('*'))if q.is_file()}
        products.update({str(q):digest(q)for q in [work/'browser-peddle.dylib',work/'zig-out/bin/coordinator-tests']})
        products.update({str(q):digest(q)for q in sorted((start/'work').rglob('*'))if q.is_file()})
        for q in [start/'START.PRG',start/'START.REL',start/'START.labels',start/'START.map']:products[str(q)]=digest(q)
        verify(record);verify(products)
        (run/'INPUTS_BEFORE.json').write_text(json.dumps(record,indent=2)+'\n');(run/'PRODUCTS_BEFORE.json').write_text(json.dumps(products,indent=2)+'\n')
        phase='actual native integrations';jobs=[]
        for i,name in enumerate(CASES):
            argv=[t['python'],'-B','test_full_installer.py','Cases.'+name];commands.append(argv);o=(run/('CASE'+str(i)+'.stdout')).open('wb');e=(run/('CASE'+str(i)+'.stderr')).open('wb');caseenv=dict(env,ROOT_FLOW_REPORT='CASE'+str(i)+'.json');proc=subprocess.Popen(argv,cwd=work,env=caseenv,stdin=subprocess.DEVNULL,stdout=o,stderr=e);jobs.append((proc,o,e,name))
        results=[]
        for i,(proc,o,e,name)in enumerate(jobs):
            code=proc.wait();o.close();e.close();results.append({'name':name,'exit':code});print(name,code,flush=True)
            log=(run/('CASE'+str(i)+'.stderr')).read_text()
            if code==0 and ('Ran 1 test in 'not in log or not log.rstrip().endswith('OK')):results[-1]['exit']=1
        phase='actual Zig execution'
        command([work/'zig-out/bin/coordinator-tests'],work,env,run/'ZIG_ACTUAL',commands)
        if 'All 5 tests passed.'not in(run/'ZIG_ACTUAL.stderr').read_text():raise RuntimeError('Five actual Zig tests were not confirmed')
        phase='final source/product closure';verify(record);verify(products)
        (run/'INPUTS_AFTER.json').write_text(json.dumps(record,indent=2)+'\n');(run/'PRODUCTS_AFTER.json').write_text(json.dumps(products,indent=2)+'\n')
        if any(r['exit']for r in results):raise RuntimeError('Actual native integration failed; inspect CASE logs')
        report={'status':'passed','run':str(run),'work':str(work),'actual_python_groups':4,'actual_Zig_groups':5,'source_inputs':record,'products':products,'native':digest(work/'build/setup.prg'),'memory':built['memory'],'cases':results,'commands':commands,'source_and_products_unchanged':True,'media_not_distributed':True,'hardware':False,'DOS_cold_consumer_test':False,'full_UI_reconfiguration_or_INI':False}
        result_path.write_text(json.dumps(report,indent=2)+'\n');(out/'RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS native installer4+Zig5: '+str(run),flush=True)
    except BaseException as first:
        cleanup=stop_owned(jobs)
        closure_error=None
        try:
            verify(record);verify(products)
            (run/'FAILED_INPUTS_AFTER.json').write_text(json.dumps(record,indent=2)+'\n');(run/'FAILED_PRODUCTS_AFTER.json').write_text(json.dumps(products,indent=2)+'\n')
        except BaseException as changed:closure_error=type(changed).__name__+': '+str(changed)
        failure={'cleanup_errors':cleanup,'closure_error':closure_error,'status':'failed','phase':phase,'first_type':type(first).__name__,'first_message':str(first),'run':str(run),'work':str(work)if work else None,'commands':commands}
        for path in [result_path,out/'RESULT.json']:
            try:path.write_text(json.dumps(failure,indent=2)+'\n')
            except BaseException:pass
        raise

if __name__=='__main__':main()
