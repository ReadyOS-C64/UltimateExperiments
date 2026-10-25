"""Actual C22 dirty-band compositor over real C21 pages, isolated owner seam.

The C22 candidate is substituted only in a private fixture. Cached source,
layout and styles come from the real editor. Full-source pixel oracle is
independent; outside-band poison detects unintended repaint or attr changes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,subprocess,hashlib
import test_geos_semantic_editor as semantic
from overlays import wrap
geos=semantic.geos;ROOT=geos.ROOT
BASE=ROOT/'build/geos-semantic-editor/20261025T075329265974Z/fixture'

def command(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True,capture_output=True)
def run(out,previous):
    frozen,identity=geos.freeze(out,previous);r=json.loads((frozen/'build/editor-report.json').read_text());s=r['symbols']
    geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
    geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
    for n in ('page-paint','cache-paint'):
        command('ca65','-g','-I','build/geos-prod','-I','src','-o',out/(n+'.o'),'src/render/geos/'+n+'.s')
    objects=[ROOT/'build/geos-prod/page-paint-entry.o',out/'page-paint.o',ROOT/'build/geos-prod/native-pan.o',out/'cache-paint.o']
    command('python3','tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',out/'aliases.s',*objects)
    command('ca65','-o',out/'aliases.o',out/'aliases.s');command('ld65','-C','cfg/geos-editor-page.cfg','-o',out/'paint.bin',*objects,out/'aliases.o')
    raw=(out/'paint.bin').read_bytes();assert len(raw)==4096 and raw[:16]==bytes.fromhex(r['resident_binding']['digest'])
    image=wrap(raw,1,22,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=raw[:16])
    dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);f.assets['geospaint']=image
    fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    data=semantic.FIXTURE;cases=[]
    def invoke(op):
        f.put('se_overlay_frame',op,1);regs,n=f.fast_call(s['se_overlay_call'],a=22,x=1)
        assert not regs.p&1,(op,regs.a,regs.p);return regs.a,n
    try:
        f.source(data);f.command(99);f.render();eb,ea,_,_=semantic.expected(f,data,fonts)
        assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea
        variants=[(2,start,start+1,start,start+1) for start in range(2,24)]
        variants += [(2,2,6,2,6),(2,2,24,2,24),(0,3,4,2,24)]
        variants += [(2,a,b,2,24) for a,b in [(0,2),(1,3),(24,25),(3,25),(4,4),(7,3)]]
        for no,(flag,first,end,want_first,want_end) in enumerate(variants):
            bits=bytearray(eb);attrs=bytearray(ea)
            for i in range(640,7680):bits[i]^=(i*13+37)&255
            for i in range(80,960):attrs[i]^=0xEF
            f.m.load(0x6000,bits);f.m.load(0x4000,attrs)
            f.m.write(0x9134+20,flag);f.m.write(0x9149+5,first);f.m.write(0x9149+6,end)
            f.put('se_f_owner',4,1);f.m.load(0x8B40,b'\0\0')
            canonical=f.canonical();reu=f.reu();a,used=invoke(0);steps=0
            while a:
                assert a==1 and steps<5000
                a,n=invoke(1);used+=n;steps+=1
            wanted_bits=bytearray(bits);wanted_attrs=bytearray(attrs)
            wanted_bits[want_first*320:want_end*320]=eb[want_first*320:want_end*320]
            wanted_attrs[want_first*40:want_end*40]=ea[want_first*40:want_end*40]
            actual=f.read(0x6000,8000);actual_attrs=f.read(0x4000,1000)
            assert actual==wanted_bits,(no,'pixels',first,end,next((i,a,b)for i,(a,b)in enumerate(zip(actual,wanted_bits))if a!=b))
            assert actual_attrs==wanted_attrs,(no,'attrs',first,end)
            assert f.canonical()==canonical and f.reu()==reu and f.read(0xC600,1024)==f.shim
            f.put('se_f_owner',0,1)
            cases.append(dict(flag=flag,first=first,end=end,actual_first=want_first,actual_end=want_end,steps=steps,instructions=used))
        result=dict(status='passed',cases=cases,payload_bytes=len(raw),pixels_checked=len(cases)*64000,attributes_checked=len(cases)*1000,
            identity=identity,scope='Actual C22 and R21 over real C21 packets; owner/dirty-range inputs are explicit component seams. Independent fullpixel/attr reference, poisoned outside bands, entire16MiB read-only, canonical/shim; no new C21/R28 integration or timing claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='identity'},indent=2))
    finally:f.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-dirty-bands'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
