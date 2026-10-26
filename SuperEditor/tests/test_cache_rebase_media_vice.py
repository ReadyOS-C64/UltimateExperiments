"""Actual registered62 media cases, preserving the released native oracles.

Real drive conditions/IRQ STOP/name collisions remain separate from named
monitor ACK/catalog/ordering injections. Own8100/text8200..8239; no hardware.
Only the current source/package authentication, reusable port check and closed
successful output copy are added. No File/status/source/disk oracle is weakened.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,socket,zipfile
import test_combined_media_vice as media
import test_cache_rebase_registered as registered
from closed_runtime_copy import run_with_closed_links

ROOT=media.ROOT
CASES=tuple(media.CASES)+('cancel-read','missing-c12-saved-ack9','missing-c12-savepoint-pending9')
INJECTED={'promotion-ack-injected','missing-c12-save','missing-both-read','missing-c12-saved-ack9','missing-c12-savepoint-pending9'}


def free_ports():
    for port in (8100,*range(8200,8240)):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(('127.0.0.1',port))


def run(fixture,project,cases):
    identity=registered.authenticate(fixture,project)
    free_ports();e=media.freeze(fixture);results=[]
    (e/'registered62-authentication.json').write_text(json.dumps(identity,indent=2)+'\n')
    original_run,original_ports=media.own_run,media.free_ports
    media.free_ports=free_ports
    media.own_run=lambda plan,out,timeout=900:run_with_closed_links(original_run,plan,out,timeout=timeout)
    try:
        for case in cases:
            print('START_MEDIA62',case,e,flush=True)
            result=media.execute(e,case);out=e/case
            assert result['actual_catalog_assets']==62
            assert bool(result['injections'])==(case in INJECTED),(case,result['injections'])
            if case in ('missing-c12-saved-ack9','missing-c12-savepoint-pending9'):
                assert (out/'working9.d81').exists(),'actual second-device boundary disk'
            closure=json.loads((out/'process-closure.json').read_text())
            assert closure['PID_absent'] and closure['normal_close_requested']
            assert closure['binary_port']==8100 and 8200<=closure['text_port']<8240
            result.update(registered62_identity=identity,registered62_wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),visual_review='pending',forced_ordering=case=='missing-c12-savepoint-pending9')
            (out/'registered62-result.json').write_text(json.dumps(result,indent=2)+'\n')
            results.append(dict(case=case,status=result['status'],screens=result['screens'],pixels=result['pixels'],attributes=result['attributes'],injections=result['injections'],forced_ordering=result['forced_ordering'],ports_released=True))
            print('PASS_MEDIA62',case,result['screens'],flush=True)
    finally:
        media.own_run,media.free_ports=original_run,original_ports
    summary=dict(status='PASS',identity=identity,cases=results,screens=sum(x['screens']for x in results),pixels=sum(x['pixels']for x in results),attributes=sum(x['attributes']for x in results),visual_review='pending',scope=__doc__)
    (e/'registered62-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('MEDIA62_COMPLETE',e,flush=True)
    return e,summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,required=True);p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--case',choices=CASES,action='append');a=p.parse_args()
    if a.run:run(a.fixture.resolve(),a.project.resolve(),a.case or CASES)
    else:print(json.dumps(dict(cases=CASES,injected=sorted(INJECTED),native_run=False),indent=2))
