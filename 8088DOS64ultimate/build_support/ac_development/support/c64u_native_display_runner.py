"""Opt-in MODE CO40/CO80 with existing full native-file REU recovery.

--validate-only does not contact any host. Physical execution is Terminal-owned.
The shared VER/DIR application and its runner are unchanged.
"""
import argparse
import ftplib
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from c64u_native_display_application import DisplayApplication, PROJECT, FONT_NAMES
import c64u_native_file_recovery as h
from c64u_native_file_runner import clock_evidence,checked_application
from c64u_native_application import labels_from,resident_from_map,checked_observation_interval,checked_application_seconds
from c64u_native_shadow_identity import metadata_from_paths
from c64u_native_mode_identity import load_proof
from c64u_bulk_reu_recovery import run_with_recovery,dump,sha


def validate_inputs(args):
    """Local gate: role-specific source/artifact pins, no network calls."""
    identity=json.loads(Path(args.build_manifest).read_text())
    files=identity.get('files',{})
    for role,path in [('build/dos64.prg',args.prg),('build/dos64.labels',args.labels),('build/dos64.map',args.map)]:
        if sha(Path(path).read_bytes())!=files.get(role):raise ValueError('Role-specific runtime identity absent/different: '+role)
    # Bind the complete current source cohort rather than accepting any matching
    # hash elsewhere in a manifest. Reject entries outside this project.
    for name,digest in files.items():
        path=(PROJECT/name).resolve()
        if not path.is_relative_to(PROJECT) or not path.is_file() or sha(path.read_bytes())!=digest:
            raise ValueError('Reviewed build source/artifact changed: '+name)
    mode_proof=load_proof(args.mode_proof,args.mode_proof_sha256,identity,args.expected_prg_sha256,PROJECT)
    proposal=json.loads(Path(args.proposal_manifest).read_text())
    for name in ('c64u_native_display_application.py','c64u_native_display_runner.py','c64u_native_mode_identity.py'):
        if sha((HERE/name).read_bytes())!=proposal.get('proposal_files',{}).get('build_support/'+name):raise ValueError('Display proposal source changed: '+name)
    if args.shadow_package and args.shadow_memory:
        for role,path in [('build/dos64-overlay-package.json',args.shadow_package),('build/dos64.memory.json',args.shadow_memory)]:
            if sha(Path(path).read_bytes())!=files.get(role):raise ValueError('Role-specific copied shadow artifact differs: '+role)
    base=h.base_prg(args.restore_prg);pal=clock_evidence(args.pal_clock_evidence)
    app=DisplayApplication(Path(args.prg).read_bytes(),labels_from(args.labels),json.loads(Path(args.media_manifest).read_text()),args.source,Path(args.service).read_bytes(),args.expected_prg_sha256,seconds=args.application_seconds,resident_segments=resident_from_map(args.map),build_identity=identity,observation_interval=args.observation_interval,shadow_metadata=metadata_from_paths(args.shadow_package,args.shadow_memory,set(files.values())))
    if sha(app.service_prg)!=h.SERVICE_SHA:raise ValueError('Original frozen40fe DRS1 service required')
    stage=json.loads(Path(args.staging_manifest).read_text())
    if stage.get('offline_validation_fixture') is True and not args.validate_only:
        raise ValueError('Synthetic offline PRG registry is forbidden for physical execution')
    # Construction validates the complete existing native/service registry.
    client=h.NativeFileClient(h.DeadlineClient(args.host),stage,{'native':app.prg,'recovery':app.service_prg},app.base)
    watched=[Path(args.build_manifest),Path(args.mode_proof),Path(args.proposal_manifest),Path(args.prg),Path(args.labels),Path(args.map),Path(args.media_manifest),Path(args.source),Path(args.service),Path(args.restore_prg),Path(args.staging_manifest),Path(args.pal_clock_evidence),HERE/'c64u_native_display_application.py',Path(__file__).resolve()]
    watched += [HERE/'c64u_native_mode_identity.py']
    watched += [Path(item['path']) for item in mode_proof['proof_inputs'].values()]
    watched += [Path(path) for path in (args.shadow_package,args.shadow_memory) if path]
    watched += [PROJECT/'assets/native-text'/name for name in FONT_NAMES]
    watched += [PROJECT/'build_support'/name for name in ('c64u_native_application.py','c64u_native_application_support.py','c64u_native_shadow_identity.py','c64u_native_file_recovery.py','c64u_native_file_runner.py','c64u_bulk_reu_recovery.py','c64u_ftp_put_transport.py','c64u_probe.py')]
    pins={str(p.resolve()):sha(p.read_bytes()) for p in watched}
    return app,client,base,pal,pins,stage,mode_proof


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-only',action='store_true')
    for name in ('host','output','prg','labels','map','build_manifest','mode_proof','mode_proof_sha256','proposal_manifest','media_manifest','source','expected_prg_sha256','service','restore_prg','staging_manifest','pal_clock_evidence'):
        parser.add_argument('--'+name.replace('_','-'),required=True)
    parser.add_argument('--observation-interval',type=checked_observation_interval,default=0.25)
    parser.add_argument('--application-seconds',type=checked_application_seconds,default=180)
    parser.add_argument('--shadow-package')
    parser.add_argument('--shadow-memory')
    args=parser.parse_args(argv);output=Path(args.output).resolve()
    if not output.is_relative_to((PROJECT/'agentworking/runs').resolve()) or output.exists():parser.error('Use a fresh project-owned agentworking/runs directory')
    app,client,base,pal,pins,stage,mode_proof=validate_inputs(args)
    if args.validate_only:
        print(json.dumps({'status':'validated-local-only','hardware_executed':False,'mode_runtime_sha256':args.expected_prg_sha256,'configured_native_sha256':sha(app.prg),'mode_proof':mode_proof,'observation_interval':app.observation_interval,'application_seconds':app.seconds,'transport_staging_scope':'explicit synthetic offline fixture' if stage.get('offline_validation_fixture') is True else 'supplied verified registry; no fresh remote readback in validate-only','source_identities':pins},indent=2));return 0
    def ftp_factory(timeout):
        ftp=ftplib.FTP()
        try:ftp.connect(args.host,21,timeout=timeout);ftp.login('anonymous','anonymous@');return ftp
        except Exception:
            try:ftp.close()
            except Exception:pass
            raise
    def factory(adapter,prg,journal):
        dump(output/'display-mode-proof.json',mode_proof);dump(output/'display-reviewed-inputs-before.json',pins);dump(output/'display-pal-evidence.json',pal);dump(output/'original-prg-staging-input.json',stage)
        return h.NativeFileService(adapter,prg,journal,base=base,ftp_factory=ftp_factory,backup_path=output/'reu-before.bin',output=output)
    result=run_with_recovery(client,app.service_prg,output,application=checked_application(app),service_factory=factory,restore_attempts=2)
    result['recovery_backend']='native-file';result['workflow']='genuine DOS MODE CO40 then CO80'
    result['limitations']=[item for item in result.get('limitations',[]) if item!='No persistent media or UCI writes; REST is development control only']+['FTP creates only new owned backup/PRG files; native UCI opens its backup read-only','PAL timing requires reviewed prior clock evidence and current PAL System Mode','Native BIOS keys and RAM framebuffer proofs; physical matrix input and external display remain untested']
    result['external_display_capture']='not attempted; known stream ownership is a separate gate'
    after={}
    try:
        after={path:sha(Path(path).read_bytes()) for path in pins}
        if after!=pins:raise ValueError('Frozen display inputs changed during execution')
    except Exception as error:result['status']='failed';result.setdefault('late_evidence_errors',[]).append(repr(error))
    dump(output/'display-reviewed-inputs-after.json',after);dump(output/'result.json',result)
    print(json.dumps({k:result[k] for k in ('status','reu_restored','configuration_restored','reset_resumed')}))
    return result['status']!='passed'


if __name__=='__main__':raise SystemExit(main())
