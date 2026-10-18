"""Opt-in standalone IEC helpers. Does not build/change the emulator or contact a device."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
EXPECTED={'full':'4a2308ff3c6a369ed5f7cd7da03d91f429fcc20c716b450f38add97cc2863ba4','small':'37e044cd94d71300297fbea4afd75762d31f40df8af87af84b8bba1c738d3cb5'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(project,ca65='ca65',ld65='ld65'):
    out=project/'build/iec-standalone';out.mkdir(parents=True,exist_ok=True)
    tools={}
    for name,requested in [('ca65',ca65),('ld65',ld65)]:
        found=shutil.which(requested)
        if not found:raise ValueError('Missing tool '+requested)
        path=Path(found).resolve();tools[name]={'path':str(path),'sha256':digest(path),'version':subprocess.check_output([str(path),'--version'],stderr=subprocess.STDOUT,text=True).strip()}
    outputs={}
    for kind in ['full','small']:
        objs=[]
        for stem in ['iec_standalone','reu']:
            obj=out/(stem+'-'+kind+'.o');args=[tools['ca65']['path'],'-I',str(project/'include')]
            if kind=='small':args+=['-D','DOS64_IEC_SMALL=1']
            subprocess.run([*args,str(project/'src'/(stem+'.s')),'-o',str(obj)],check=True);objs.append(str(obj))
        stem=project/'build'/('dos64-iec-standalone'+('-small' if kind=='small' else ''))
        subprocess.run([tools['ld65']['path'],'-C',str(project/'cfg/dos64-iec-standalone.cfg'),'-o',str(stem)+'.prg','-Ln',str(stem)+'.labels','-m',str(stem)+'.map',*objs],check=True)
        prg=Path(str(stem)+'.prg');sha=digest(prg)
        if sha!=EXPECTED[kind]:raise ValueError(f'{kind} target changed: {sha}')
        outputs[kind]={'prg':str(prg.relative_to(project)),'bytes':prg.stat().st_size,'sha256':sha,'labels_sha256':digest(Path(str(stem)+'.labels')),'map_sha256':digest(Path(str(stem)+'.map'))}
    sources=['src/iec_standalone.s','src/reu.s','include/abi.inc','include/reu.inc','cfg/dos64-iec-standalone.cfg','build_support/build_iec_standalone.py']
    m={'schema':1,'standalone_only':True,'runtime_profile':False,'outputs':outputs,'tools':tools,'source_files':{n:{'bytes':(project/n).stat().st_size,'sha256':digest(project/n)} for n in sources}}
    (project/'build/dos64-iec-standalone.json').write_text(json.dumps(m,indent=2)+'\n');return m
def check_build(project):
    manifest=json.loads((project/'build/dos64-iec-standalone.json').read_text())
    if manifest.get('schema')!=1 or set(manifest.get('outputs',{}))!=set(EXPECTED):raise ValueError('Incomplete IEC output manifest')
    required={'src/iec_standalone.s','src/reu.s','include/abi.inc','include/reu.inc','cfg/dos64-iec-standalone.cfg','build_support/build_iec_standalone.py'}
    if set(manifest.get('source_files',{}))!=required:raise ValueError('Incomplete IEC input manifest')
    for name,item in manifest['source_files'].items():
        path=project/name
        if path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:raise ValueError('Stale IEC source: '+name)
    for kind,item in manifest['outputs'].items():
        path=project/item['prg']
        if digest(path)!=EXPECTED[kind] or path.stat().st_size!=item['bytes']:raise ValueError('Stale IEC binary: '+kind)
        for suffix in ['labels','map']:
            if digest(path.with_suffix('.'+suffix))!=item[suffix+'_sha256']:raise ValueError('Stale IEC '+suffix)
    return manifest
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ca65',default='ca65');ap.add_argument('--ld65',default='ld65');ap.add_argument('--ensure',action='store_true',help='Validate all products and rebuild if anything is missing/stale');a=ap.parse_args();project=Path(__file__).resolve().parents[1]
    manifest=None
    if a.ensure:
        try:manifest=check_build(project)
        except (OSError,ValueError,KeyError,TypeError):pass
    if manifest is None:manifest=build(project,a.ca65,a.ld65)
    print(json.dumps(manifest['outputs'],indent=2))
