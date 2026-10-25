"""Actual packaged R28/strip-R21 native qualification on a private owned port.

Reuse all released source/pixel/font/catalog/history/REU/D81 oracles. No image
substitution, shared build, physical-key claim or baseline timing comparison.
"""
from pathlib import Path
import argparse,json,socket
import test_geos_wrap_refusal_candidate_vice as released

original=released.original


def run(fixture,port):
    assert 1024<=port<=65395
    class Plan(original.Plan):
        def plan(self):
            p=super().plan()
            p['global_defaults']['monitor_port_start']=port
            p['global_defaults']['monitor_port_span']=1
            assert not p['global_defaults'].get('kill_stale',False)
            return p
    def ports():
        for number in [port,*range(port+100,port+140)]:
            with socket.socket()as s:s.bind(('127.0.0.1',number))
    original.Plan=Plan;original.ports=ports
    evidence,result=original.execute(fixture.resolve(),'candidate')
    result['packaged_qualification']=dict(fixture=str(fixture),requested_binary=port,
        requested_text_block=[port+100,port+139],no_initial_substitutions=True,
        limits=__doc__)
    (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PACKAGED',evidence,flush=True)
    return evidence,result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--monitor-port',type=int,default=8900);a=p.parse_args()
    run(a.fixture,a.monitor_port)
