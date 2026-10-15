"""Explicit development transport alternative; root reviews and launches in Terminal.

Uses CURRENT shared Application/support without copies or monkey patches, so
AH01 periodic observation and cursor-local pagination fixes remain active.
No FTP/network action occurs on import. --prepare-only is entirely local.
"""
import argparse
import json
from pathlib import Path
import sys
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'build_support'))
from c64u_native_application import Application,labels_from,resident_from_map,pinned_hashes
from c64u_probe import Client
from c64u_bulk_reu_recovery import run_with_recovery,Journal,dump,durable_write
from c64u_ftp_put_transport import FtpPutClient,sha
from c64u_delta_reu_recovery import DeltaService
SOURCE_NAMES=('c64u_native_ftp_put_runner.py','c64u_ftp_put_transport.py','c64u_delta_reu_recovery.py',
              'c64u_native_application.py','c64u_native_application_support.py','c64u_bulk_reu_recovery.py','c64u_probe.py')
REJECTED_NATIVE='e7fe23622f50bec7d055d4fd1c82c604f3ad53d0e5b7e0a024d471a6de0b617c'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport',choices=['ftp-put'],required=True)
    parser.add_argument('--prepare-only',action='store_true',help='Write exact patched native PRG/identities locally; no device contact')
    for name in ('prg','labels','map','build_manifest','media_manifest','source','service','output','expected_prg_sha256'):
        parser.add_argument('--'+name.replace('_','-'),required=True)
    parser.add_argument('--host')
    parser.add_argument('--staging-manifest')
    args=parser.parse_args()
    if args.expected_prg_sha256==REJECTED_NATIVE:parser.error('Superseded native blink-bug PRG is explicitly rejected')
    out=Path(args.output).resolve()
    if not out.is_relative_to((PROJECT/'agentworking/runs').resolve()):parser.error('Output must be a fresh project-owned agentworking/runs directory')
    identity=json.loads(Path(args.build_manifest).read_text());pins=pinned_hashes(identity)
    for file in (args.prg,args.labels,args.map):
        if sha(Path(file).read_bytes()) not in pins:parser.error('Source/binary artifact is absent from reviewed build manifest: '+file)
    app=Application(Path(args.prg).read_bytes(),labels_from(args.labels),json.loads(Path(args.media_manifest).read_text()),
                    args.source,Path(args.service).read_bytes(),args.expected_prg_sha256,
                    resident_segments=resident_from_map(args.map),build_identity=identity)
    if args.prepare_only:
        out.mkdir(parents=True,exist_ok=False)
        durable_write(out/'NATIVE-DOS.PRG',app.prg);durable_write(out/'REU-RECOVERY.PRG',app.service_prg)
        files={}
        for role,name in (('native','NATIVE-DOS.PRG'),('recovery','REU-RECOVERY.PRG')):
            body=(out/name).read_bytes();files[role]={'path':str(out/name),'bytes':len(body),'sha256':sha(body)}
        dump(out/'transport-inputs.json',{'schema':1,'hardware_executed':False,'transport':'ftp-put','files':files,
                                         'base_native_sha256':args.expected_prg_sha256,'patch':app.patch,
                                         'native_diag_address':app.base,'current_shared_application_sha256':sha((PROJECT/'build_support/c64u_native_application.py').read_bytes()),
                                         'current_shared_support_sha256':sha((PROJECT/'build_support/c64u_native_application_support.py').read_bytes())})
        print(json.dumps({'status':'prepared-local-only','files':files}));return 0
    if not args.host or not args.staging_manifest:parser.error('Physical transport needs explicit --host and actual verified --staging-manifest')
    manifest=json.loads(Path(args.staging_manifest).read_text())
    # Constructor validates every registered blob and owned remote path before
    # run_with_recovery can make its first development REST request.
    adapter=FtpPutClient(Client(args.host),manifest,{'native':app.prg,'recovery':app.service_prg},app.base)
    def application(client,directory):
        journal=Journal(Path(directory)/'ftp-put-transport-journal.jsonl');client.journal=journal
        dump(Path(directory)/'prg-staging-input.json',manifest)
        identities={str(p):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in
                    (PROJECT/'build_support'/name for name in SOURCE_NAMES)}
        dump(Path(directory)/'transport-source-identities.json',identities)
        try:return app(client,directory)
        finally:dump(Path(directory)/'transport-counters.json',client.stats)
    result=run_with_recovery(adapter,app.service_prg,out,application=application,service_factory=DeltaService)
    dump(out/'prg-staging-input.json',manifest)
    dump(out/'transport-source-identities.json',{str(p):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in (PROJECT/'build_support'/name for name in SOURCE_NAMES)})
    dump(out/'transport-counters-final.json',adapter.stats)
    print(json.dumps({k:result[k] for k in ('status','reu_restored','configuration_restored','reset_resumed')}))
    return result['status']!='passed'

if __name__=='__main__':raise SystemExit(main())
