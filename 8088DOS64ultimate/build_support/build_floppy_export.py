"""Build the standalone, disabled actual-assembly floppy export fixture."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ca65',default='ca65');p.add_argument('--ld65',default='ld65')
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    out=root/'build/floppy-export';out.mkdir(parents=True,exist_ok=True)
    sources=['floppy_export_fixture','floppy_export','reu','uci','files']
    tools={}
    for name in ('ca65','ld65'):
        executable=Path(shutil.which(getattr(a,name)) or getattr(a,name)).resolve()
        tools[name]={'path':str(executable),'sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),'version':subprocess.check_output([str(executable),'--version'],stderr=subprocess.STDOUT,text=True).strip()}
    for source in sources:
        subprocess.run([tools['ca65']['path'],'-g',*(['-D','DOS64_FILES_INFO=1'] if source=='files' else []),'-I',str(root/'include'),'-o',str(out/(source+'.o')),str(root/'src'/(source+'.s'))],check=True)
    stem=root/'build/dos64-floppy-export'
    subprocess.run([tools['ld65']['path'],'-C',str(root/'cfg/dos64-floppy-export.cfg'),'-o',str(stem)+'.prg','-m',str(stem)+'.map','-Ln',str(stem)+'.labels',*[str(out/(n+'.o')) for n in sources]],check=True)
    inputs=[Path(__file__).resolve(),root/'cfg/dos64-floppy-export.cfg',*[root/'src'/(n+'.s') for n in sources],*[root/'include'/n for n in ('abi.inc','reu.inc','uci.inc','files.inc','floppy_export.inc')]]
    manifest={'schema':1,'features':{'DOS64_FILES_INFO':1},'scope':'standalone disabled actual assembly; no production integration or physical save acceptance','tools':tools,'sources':{str(x.relative_to(root)):{'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in inputs},'outputs':{str(Path(str(stem)+ext).relative_to(root)):{'bytes':Path(str(stem)+ext).stat().st_size,'sha256':hashlib.sha256(Path(str(stem)+ext).read_bytes()).hexdigest()} for ext in ('.prg','.map','.labels')}}
    (root/'build/dos64-floppy-export.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest['outputs']))
if __name__=='__main__':main()
