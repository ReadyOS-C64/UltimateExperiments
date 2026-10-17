#!/usr/bin/env python3
"""Opt-in actual native INI component tests with synthetic files; no DOS images."""
import sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-ini-tests-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Cache prefix must be absent')
import argparse,importlib.util,json,shutil,subprocess
s=importlib.util.spec_from_file_location('ini_bundle',ROOT/'build_support/start_ini_bundle.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'build/start-options-tests');a=p.parse_args();result=b.build(a.out);run=Path(result['run']);work=run/'start';e=run/'native-tests';e.mkdir();inputs=result['source_inputs'].copy();products=result['products'].copy();inputs[str(Path(__file__).resolve())]=b.digest(Path(__file__).resolve())
 for root in [ROOT/'tests/start_launcher',ROOT/'tests/start_options']:
  for q in sorted(root.glob('*.py')):b.copy(q,work/q.name,inputs)
 for root in ['tests/host','tests/floppy_export','third_party/peddle/Peddle']:
  for q in(ROOT/root).glob('*'):
   if q.is_file()and q.suffix in ['.cpp','.h']:b.copy(q,work/q.relative_to(ROOT),inputs)
 for q in(ROOT/'tests/start_options/support').glob('*'):b.copy(q,work/('tests/host'if q.name=='peddle_bridge.h'else'tests/floppy_export')/q.name,inputs)
 for src,dst in [(ROOT/'build_support/setup_release_descriptor.py',work/'make_release_options.py'),(ROOT/'build_support/start_template_descriptor.py',work/'start_template_metadata.py'),(run/'bundle/START.REL',work/'START.REL'),(run/'bundle/DOS64.REL',work/'DOS64.REL'),(run/'main/build/dos64.prg',run/'inputs/build/dos64.prg'),(run/'main/build/dos64.labels',run/'inputs/build/dos64.labels')]:b.copy(src,dst,inputs)
 clang=shutil.which(os.environ.get('DOS64_CLANGXX')or os.environ.get('DOS64_CLANG++')or'clang++')
 if not clang:raise RuntimeError('clang++ required for actual Peddle tests')
 clang=str(Path(clang).resolve());inputs[clang]=b.digest(Path(clang));commands=[]
 def command(argv,name):
  commands.append(list(map(str,argv)))
  with(e/(name+'.stdout')).open('wb')as o,(e/(name+'.stderr')).open('wb')as err:subprocess.run(commands[-1],cwd=work,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdin=subprocess.DEVNULL,stdout=o,stderr=err,check=True)
 command([clang,'-std=c++20','-O2','-dynamiclib','-Itests/floppy_export','-Itests/host','-Ithird_party/peddle/Peddle','tests/floppy_export/bridge.cpp',*[f'third_party/peddle/Peddle/{n}'for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o','bulk-peddle.dylib'],'bridge');products[str(work/'bulk-peddle.dylib')]=b.digest(work/'bulk-peddle.dylib');b.atomic_json(e/'INPUTS_BEFORE.json',inputs);b.atomic_json(e/'PRODUCTS_BEFORE.json',products)
 for name in ['test_ini_overlay.py','test_ini_io.py','test_ini_matched.py']:command([sys.executable,'-B',name],name)
 b.verify(inputs);b.verify(products);b.atomic_json(e/'INPUTS_AFTER.json',inputs);b.atomic_json(e/'PRODUCTS_AFTER.json',products);b.atomic_json(e/'RESULT.json',{'status':'passed','actual_native_groups':23,'scope':'SYNTHETIC_INPUT_COMPONENTS_NOT_DOS_OR_INSTALLER_FLOW','source_inputs':inputs,'products':products,'commands':commands,'physical':False});print(e)
if __name__=='__main__':main()
