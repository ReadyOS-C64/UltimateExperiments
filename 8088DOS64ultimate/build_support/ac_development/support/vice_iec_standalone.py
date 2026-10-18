"""Opt-in owned localhost VICE IEC proof. No physical C64U/LAN operations."""
import argparse,json,shutil,socket,subprocess,time,uuid
from pathlib import Path
from build_iec_standalone import EXPECTED,check_build
from vice_process_owner import ChildMonitorOwner,OwnedBinaryMonitor
from verify_iec_standalone import DOS_SHA,derived,pattern,seed,sha,verify

def run(project,case='original',serial=False,vice='x64sc',c1541='c1541',timeout=120):
    project=project.resolve()
    if not 10<=timeout<=600:raise ValueError('VICE deadline must be 10..600 seconds')
    kind='small' if serial else 'full';stem=project/'build'/('dos64-iec-standalone'+('-small' if serial else ''))
    prg=Path(str(stem)+'.prg')
    if sha(prg.read_bytes())!=EXPECTED[kind]:raise ValueError('Build the reviewed standalone helper first')
    built=check_build(project)
    for path,record in built['source_files'].items():
        if sha((project/path).read_bytes())!=record['sha256']:raise ValueError('Standalone build is stale: '+path)
    base=seed() if serial else next((project/'reference').glob('*1 of 3.img')).read_bytes()
    if not serial and sha(base)!=DOS_SHA:raise ValueError('Original DOS image changed')
    payload=derived(base,case);run_dir=project/'agentworking/runs'/('iec-standalone-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);run_dir.mkdir(parents=True)
    (run_dir/'input.img').write_bytes(payload);d81=run_dir/'container.d81'
    image_tool=shutil.which(c1541);vice_tool=shutil.which(vice)
    if not image_tool or not vice_tool:raise ValueError('VICE/c1541 not found')
    prep=subprocess.run([image_tool,'-format','dos64iec,01','d81',str(d81),'-write',str(run_dir/'input.img'),'otherdisk,s' if case=='missing' else 'pcdisk,s','-list'],capture_output=True,check=True)
    (run_dir/'c1541-create.log').write_bytes(prep.stdout+b'\nSTDERR\n'+prep.stderr)
    (run_dir/'reu.img').write_bytes(pattern());before=sha(d81.read_bytes())
    with socket.socket() as reserve:reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
    argv=[vice_tool,'-default','-console','+sound','-warp','-pal','-reu','-reusize','4096','-reuimage',str(run_dir/'reu.img'),'-reuimagerw','-drive8type','1581','-drive8truedrive' if serial else '+drive8truedrive','-devicebackend8','0','+busdevice8','+trapdevice8' if serial else '-trapdevice8','-8',str(d81),'-autostartprgmode','1','-autostart',str(prg),'-binarymonitor','-binarymonitoraddress',f'127.0.0.1:{port}']
    result={'schema':1,'status':'failed','standalone_only':True,'case':case,'target_kind':kind,'source_sha256':sha(base),'source_bytes':len(base),'payload_sha256':sha(payload),'payload_bytes':len(payload),'d81_sha256':before,'prg_sha256':EXPECTED[kind],'argv':argv,'timeout_seconds':timeout,'tools':{'vice':{'path':str(Path(vice_tool).resolve()),'sha256':sha(Path(vice_tool).read_bytes())},'c1541':{'path':str(Path(image_tool).resolve()),'sha256':sha(Path(image_tool).read_bytes())}},'build_manifest_sha256':sha((project/'build/dos64-iec-standalone.json').read_bytes())}
    start=time.monotonic();deadline=start+timeout;sock=None;monitor=None;observations=[]
    with (run_dir/'vice.log').open('wb') as log:
        child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT)
        try:
            while time.monotonic()<deadline:
                if child.poll() is not None:raise RuntimeError('Owned VICE child exited '+str(child.returncode))
                try:sock=socket.create_connection(('127.0.0.1',port),timeout=2);break
                except OSError:time.sleep(.1)
            if sock is None:raise TimeoutError('VICE monitor startup deadline')
            sock.settimeout(3)
            owner=ChildMonitorOwner(child,sock,deadline)
            monitor=OwnedBinaryMonitor(sock,owner)
            result['monitor_ownership']=owner.proof
            banks=monitor.banks();result['banks']=banks
            if 'ram' not in banks:raise ValueError('VICE RAM bank unavailable')
            monitor.call(0xaa)
            while time.monotonic()<deadline:
                time.sleep(.2);mb=monitor.read(0x6000,0x601f,banks['ram'])
                if not observations or observations[-1]['mailbox_hex']!=mb.hex():observations.append({'elapsed':time.monotonic()-start,'mailbox_hex':mb.hex()})
                if mb[0] in (0xa5,0xe1):break
                monitor.call(0xaa)
            else:raise TimeoutError('Native IEC external deadline')
            (run_dir/'ram.bin').write_bytes(monitor.read(0,65535,banks['ram']));result['mailbox_hex']=mb.hex()
            result['resources']={name:monitor.resource(name) for name in ['REU','REUsize','Drive8Type','Drive8TrueEmulation','TrapDevice8','InitialWarpMode','MachineVideoStandard']}
            monitor.call(0xbb);child.wait(timeout=10)
            result['observations']=observations;result['total_elapsed']=time.monotonic()-start
            (run_dir/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            accepted=verify(run_dir,project)
            # Source file is never used as an output; check it again before success.
            if not serial and sha(next((project/'reference').glob('*1 of 3.img')).read_bytes())!=DOS_SHA:raise ValueError('Original image changed during run')
            result['status']='passed';(run_dir/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            accepted=verify(run_dir,project);(run_dir/'verification.json').write_text(json.dumps(accepted,indent=2)+'\n')
            return run_dir,accepted
        except BaseException as exc:result['status']='failed';result['error']=repr(exc);raise
        finally:
            if child.poll() is None:
                try:
                    if monitor:monitor.call(0xbb)
                    child.wait(timeout=5)
                except Exception:child.kill();child.wait()
            if sock:sock.close()
            if result['status']!='passed':
                result['observations']=observations;result['total_elapsed']=time.monotonic()-start
                (run_dir/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--case',choices=['original','short','long','crc','missing'],default='original');ap.add_argument('--serial',action='store_true',help='512-byte true-drive 1581 with traps off');ap.add_argument('--vice',default='x64sc');ap.add_argument('--c1541',default='c1541');ap.add_argument('--timeout',type=int,default=120);args=ap.parse_args();folder,result=run(Path(__file__).resolve().parents[1],args.case,args.serial,args.vice,args.c1541,args.timeout);print(json.dumps({'run':str(folder),'verification':result},indent=2))
