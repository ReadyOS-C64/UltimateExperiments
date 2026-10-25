"""Writable-font aliases retain per-glyph header validation in the R21 fast path."""
from pathlib import Path
from datetime import datetime,timezone
import json
import test_geos_phase_dispatch_candidate as candidate
import test_geos_literal_byte_candidate as proof
ROOT=candidate.ROOT
out=ROOT/'build/geos-phase-dispatch-alias'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
print('RUN',out,flush=True);cases=[]
for variant in ['control','candidate']:
    target=out/variant;target.mkdir()
    d,src,s,labels,raw,image,mods=candidate.prepare(target,candidate.BASE,variant)
    f=proof.Fixture(d,candidate.BASE,src,s,labels,raw)
    try:
        packed=(candidate.BASE/'fonts/bsw9-original.bin').read_bytes()
        for map_at,font_at in [(0x9000,0x9000),(0x9010,0x9010)]:
            f.setup([proof.profile.rec(b'AA')],row=2)
            f.m.load(font_at,packed)
            f.m.load(proof.leaf.F+6,font_at.to_bytes(2,'little'))
            f.m.load(0x8d00+12,map_at.to_bytes(2,'little'))
            before=f.reu()
            # The initial boundary overwrites the writable font header. The
            # next real glyph must catch that change before painting pixels.
            f.refuse(0x94,partial=True)
            assert f.reu()==before
            cases.append(dict(variant=variant,font=hex(font_at),map=hex(map_at),error=0x94,whole_REU_guard=16777216))
        print('PASS',variant,flush=True)
    finally:f.close()
(out/'result.json').write_text(json.dumps(dict(status='passed',cases=cases,scope=__doc__),indent=2)+'\n')
