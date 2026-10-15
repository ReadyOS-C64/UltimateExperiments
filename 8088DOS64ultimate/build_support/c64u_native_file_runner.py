"""Explicit --recovery native-file development runner; default shared delta is unchanged.

Use --validate-only for local review without contacting FTP/REST. Physical runs
remain Terminal-owned after review. Source assembly and its388069 PRG are frozen.
"""
import argparse
import ftplib
import json
from pathlib import Path
import sys
import c64u_native_file_recovery as h
from c64u_native_shadow_identity import metadata_from_paths
from c64u_bulk_reu_recovery import run_with_recovery,dump,sha
from c64u_native_application import Application,labels_from,resident_from_map,pinned_hashes,checked_observation_interval,checked_application_seconds


def clock_evidence(path):
    blob=Path(path).read_bytes();record=json.loads(blob)
    speeds=record.get('speeds',[])
    if record.get('status')!='passed' or record.get('configuration_restored') is not True or record.get('reset_resumed') is not True or not any(item.get('mhz_setting')==64 and item.get('profile')=='PAL-312x63' and item.get('expected_ticks',0)>0 and abs(item.get('error_ticks',100000))<=item.get('tolerance_ticks',-1) for item in speeds):raise ValueError('Reviewed successful64MHz PAL CIA/VIC clock evidence required')
    return {'path':str(Path(path).resolve()),'sha256':sha(blob),'profile':'PAL-312x63','prior_run_evidence':True,'limitation':'Prior clock calibration plus current System Mode PAL checked at each recovery pass'}


def checked_application(application):
    def invoke(client,output):
        value=application(client,output)
        if not isinstance(value,dict) or value.get('status')!='passed':raise RuntimeError('Application returned a failed/missing status; recovery continues')
        return value
    return invoke


def identities():
    support=Path(__file__).resolve().parent
    paths=[support/'c64u_native_file_recovery.py',support/'c64u_native_file_runner.py',h.PROJECT/'build/dos64-native-file-restore.prg']+[h.PROJECT/'build_support'/name for name in ('c64u_bulk_reu_recovery.py','c64u_ftp_put_transport.py','c64u_probe.py','c64u_native_application.py','c64u_native_shadow_identity.py','c64u_native_application_support.py')]
    return {str(p):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in paths}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recovery',choices=['native-file'],required=True)
    parser.add_argument('--validate-only',action='store_true',help='Local identities/registry/configuration validation; no network')
    parser.add_argument('--recovery-only',action='store_true',help='Restore a supplied immutable complete backup without executing an application')
    for name in ('host','output','service','staging_manifest','pal_clock_evidence'):parser.add_argument('--'+name.replace('_','-'),required=True)
    parser.add_argument('--restore-prg',default=str(h.PROJECT/'build/dos64-native-file-restore.prg'))
    parser.add_argument('--backup');parser.add_argument('--backup-manifest')
    parser.add_argument('--registered-native-prg');parser.add_argument('--native-diag-address',type=lambda v:int(v,0))
    for name in ('prg','labels','map','build_manifest','media_manifest','source','expected_prg_sha256'):parser.add_argument('--'+name.replace('_','-'))
    parser.add_argument('--observation-interval',type=checked_observation_interval,default=0.25,
                        help='Coherent screen cadence0.25..2.0seconds; stable blocking input is serviced promptly')
    parser.add_argument('--application-seconds',type=checked_application_seconds,default=180,
                        help='Application/evidence bound10..600seconds; larger budgets require an explicit option')
    parser.add_argument('--shadow-package');parser.add_argument('--shadow-memory')
    args=parser.parse_args(argv)
    output=Path(args.output).resolve()
    if not output.is_relative_to((h.PROJECT/'agentworking/runs').resolve()):parser.error('Output must be a fresh project-owned agentworking/runs directory')
    if bool(args.backup)!=bool(args.backup_manifest):parser.error('Backup and complete manifest required together')
    base=h.base_prg(args.restore_prg);pal=clock_evidence(args.pal_clock_evidence);source_before=identities()
    backup_manifest=json.loads(Path(args.backup_manifest).read_text()) if args.backup_manifest else None
    if args.backup:
        if Path(args.backup).stat().st_mode&0o222:parser.error('Existing immutable backup must be read-only')
        h.verify_backup(Path(args.backup),backup_manifest)
    if args.recovery_only:
        if not args.backup or not args.registered_native_prg or args.native_diag_address is None:parser.error('Recovery-only needs backup, manifest and actual registered native PRG/diagnostic address')
        native=Path(args.registered_native_prg).read_bytes();diag=args.native_diag_address;application=None;service=Path(args.service).read_bytes()
    else:
        for name in ('prg','labels','map','build_manifest','media_manifest','source','expected_prg_sha256'):
            if not getattr(args,name):parser.error('Application mode requires --'+name.replace('_','-'))
        identity=json.loads(Path(args.build_manifest).read_text());pins=pinned_hashes(identity)
        for artifact in (args.prg,args.labels,args.map):
            if sha(Path(artifact).read_bytes()) not in pins:parser.error('Runtime artifact absent from reviewed build manifest: '+artifact)
        app=Application(Path(args.prg).read_bytes(),labels_from(args.labels),json.loads(Path(args.media_manifest).read_text()),args.source,Path(args.service).read_bytes(),args.expected_prg_sha256,seconds=args.application_seconds,resident_segments=resident_from_map(args.map),build_identity=identity,observation_interval=args.observation_interval,shadow_metadata=metadata_from_paths(args.shadow_package,args.shadow_memory,pins))
        native=app.prg;diag=app.base;service=app.service_prg;application=checked_application(app)
    if sha(service)!=h.SERVICE_SHA:parser.error('Original frozen40fe DRS1 recovery service required')
    stage=json.loads(Path(args.staging_manifest).read_text())
    client=h.NativeFileClient(h.DeadlineClient(args.host),stage,{'native':native,'recovery':service},diag)
    if args.validate_only:
        print(json.dumps({'status':'validated-local-only','hardware_executed':False,'native_restore_base_sha256':h.BASE_SHA,'pal_evidence':pal,'source_identities':source_before},indent=2));return 0
    def ftp_factory(timeout):
        ftp=ftplib.FTP()
        try:ftp.connect(args.host,21,timeout=timeout);ftp.login('anonymous','anonymous@');return ftp
        except Exception:
            try:ftp.close()
            except Exception:pass
            raise
    def factory(adapter,prg,journal):
        dump(output/'native-file-host-identities-before.json',source_before);dump(output/'native-file-pal-evidence.json',pal);dump(output/'original-prg-staging-input.json',stage)
        return h.NativeFileService(adapter,prg,journal,base=base,ftp_factory=ftp_factory,backup_path=Path(args.backup) if args.backup else output/'reu-before.bin',backup_manifest=backup_manifest,output=output)
    result=run_with_recovery(client,service,output,application=application,backup_path=args.backup,backup_manifest=backup_manifest,service_factory=factory,restore_attempts=2)
    result['recovery_backend']='private-native-file'
    result['limitations']=[item for item in result.get('limitations',[]) if item!='No persistent media or UCI writes; REST is development control only']+['FTP creates only new owned backup/PRG files; native UCI opens its backup read-only','PAL timing requires reviewed prior clock evidence and current PAL System Mode']
    try:
        after=identities();dump(output/'native-file-host-identities-after.json',after)
        if after!=source_before:raise ValueError('Reviewed host/binary sources changed during execution')
    except Exception as error:result['status']='failed';result.setdefault('late_evidence_errors',[]).append(repr(error))
    try:dump(output/'result.json',result)
    except Exception as error:result['status']='failed';result.setdefault('late_evidence_errors',[]).append(repr(error))
    print(json.dumps({k:result[k] for k in ('status','reu_restored','configuration_restored','reset_resumed')}))
    return result['status']!='passed'

if __name__=='__main__':raise SystemExit(main())
