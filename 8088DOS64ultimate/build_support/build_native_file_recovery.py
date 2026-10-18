"""Build opt-in source-complete development recovery helpers; no device I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys

NATIVE_SHA='38806976236c39df7b392b8dbf5312adb92c4ac4f9ac60460f664a3eb61e905b'
SERVICE_SHA='40fe690953c245c8093c7cd5e5cb91684df7290602d8afa44dbd2e0b5b30d09e'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ca65',default='ca65');parser.add_argument('--ld65',default='ld65')
    args=parser.parse_args(argv);project=Path(__file__).resolve().parents[1]
    def tool(name):
        found=shutil.which(name)
        if not found:raise ValueError('Missing configured assembler/linker: '+name)
        path=Path(found).resolve()
        version=subprocess.check_output([str(path),'--version'],stderr=subprocess.STDOUT,text=True).strip()
        return {'requested':name,'path':str(path),'version':version,'binary_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    tools={'ca65':tool(args.ca65),'ld65':tool(args.ld65)}
    build=project/'build';objects=build/'native-file-recovery';objects.mkdir(parents=True,exist_ok=True)
    sources=['native_file_restore_boot','native_file_restore','reu','uci','files','host_clock','elapsed','bulk_reu_service']
    for name in sources:
        subprocess.run([tools['ca65']['path'],'-g','-I',str(project/'include'),'-o',str(objects/(name+'.o')),str(project/'src'/(name+'.s'))],check=True)
    outputs={}
    for kind,names,config,expected in [
        ('native-file-restore',sources[:-1],'dos64-native-file-restore.cfg',NATIVE_SHA),
        ('bulk-reu-service',['bulk_reu_service','reu'],'dos64-bulk-reu.cfg',SERVICE_SHA)]:
        stem=build/('dos64-'+kind)
        subprocess.run([tools['ld65']['path'],'-C',str(project/'cfg'/config),'-o',str(stem)+'.prg','-Ln',str(stem)+'.labels','-m',str(stem)+'.map',*[str(objects/(name+'.o')) for name in names]],check=True)
        body=Path(str(stem)+'.prg').read_bytes();digest=hashlib.sha256(body).hexdigest()
        if digest!=expected:raise ValueError(f'{kind} no longer reproduces reviewed disabled native/service identity: {digest}')
        outputs[kind]={'path':str(stem)+'.prg','bytes':len(body),'sha256':digest}
    inputs=[Path(__file__).resolve(),*[project/'src'/(name+'.s') for name in sources],*[project/'include'/name for name in ['abi.inc','reu.inc','uci.inc','files.inc','host_clock.inc','elapsed.inc','native_file_restore.inc']],project/'cfg/dos64-native-file-restore.cfg',project/'cfg/dos64-bulk-reu.cfg']
    manifest={'schema':1,'hardware_executed':False,'native_disabled':True,'outputs':outputs,'toolchain':tools,
              'python':{'path':str(Path(sys.executable).resolve()),'version':sys.version},
              'source_files':{str(p.relative_to(project)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs}}
    (build/'dos64-native-file-recovery.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(outputs,indent=2))

if __name__=='__main__':main()
