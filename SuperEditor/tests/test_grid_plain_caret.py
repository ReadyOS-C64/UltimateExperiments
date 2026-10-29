"""Private C33/R25 dependency boundary; no parser activation for Plain caret."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,importlib.util,inspect,json,shutil,zipfile
import test_cache_hotpath_profile as profile
import test_geos_fold_editor as fold
import test_grid_caret_candidate_faults as transport
ROOT=profile.ROOT
D=ROOT/'src/render/grid/probes/plain-caret'

def matrix(out,fixture,modes=(1,2),actions=('right','down','up','insert')):
    source=inspect.getsource(profile.run)
    needle='for mode in ([2]if smoke else(0,2,3)):';assert source.count(needle)==1
    source=source.replace(needle,'for mode in MODES:')
    needle="for action in ('right','down','up','insert'):";assert source.count(needle)==1
    source=source.replace(needle,'for action in ACTIONS:')
    assert source.count('out.mkdir(parents=True)')==1
    source=source.replace('out.mkdir(parents=True)','out.mkdir(parents=True,exist_ok=True)')
    out.mkdir();(out/'executed-profile.py').write_text(source)
    ns=dict(profile.__dict__,MODES=modes,ACTIONS=actions);exec(compile(source,str(out/'executed-profile.py'),'exec'),ns)
    return ns['run'](out,fixture)

def faults(out,base):
    out.mkdir();g=profile.observer.Gate(out,base);f=g.f;cases=[];data=profile.observer.geos.native_text('# Heading\rPlain mixedCase prose.\rSecond row.\r')
    def setup(width,caps=0):
        f.source(data,physical=256);f.typed(profile.observer.geos.native_text('syntax '+('plain'if caps==0 else'full')));f.command(97 if width==60 else 98);profile.drain(f)
        f.typed(profile.observer.geos.native_text('goto 2'));f.key(0x1d);profile.drain(f)
    def slot(ident,kind):return next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==kind)
    def header():
        raw,bank=f.raw_cache();return raw[0x1500:0x1600],bank
    def store(raw,offset=0x1500):
        f.m.load(0x8880,raw);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8880,2);f.put('se_reu_length',len(raw),2);assert not f.call('se_reu_copy',0).p&1
    def invoke():
        f.put('se_overlay_frame',1,1);return f.fast_call(f.s['se_overlay_call'],a=33,x=1)
    def snapshot():return(g.reu(),f.canonical(),f.read(0x6000,8000)+f.read(0x4000,1000),f.read(0x8d00,1152))
    def refused(tag):
        before=snapshot();r,n=invoke();assert not r.p&1 and r.a==2,(tag,r.a,r.p)
        assert snapshot()==before,(tag,'refusal changed source/history/pixels/phase/16MiB')
        assert not f.get('se_doc_read_locks',1) and f.read(0xc600,1024)==f.shim
        return n
    try:
        for width in (60,80):
            for action in ('missing-C14-caret-allowed','missing-R14-caret-allowed','missing-R25','wrong-R25-CRC','foreign-owner','bad-header-CRC','bad-row-packet-CRC','validCRC-row22','font-CRC','missing-C14-typing','missing-R14-typing'):
                typing=action.endswith('typing');setup(width,3 if typing else 0)
                h,bank=header();assert h[:4]==b'NC\1\xa5'and binascii.crc_hqx(h[:254],65535)==int.from_bytes(h[254:],'little')
                restores=[];owner=0
                if action.startswith('missing-'):
                    ident,kind=(14,1)if'C14'in action else(14,0)if'R14'in action else(25,0)
                    idx=slot(ident,kind);a=f.s['se_overlay_ids']+idx;restores.append((a,f.m.read(a)));f.m.write(a,0)
                if action=='wrong-R25-CRC':
                    a=f.s['image_crc_lo']+slot(25,0);restores.append((a,f.m.read(a)));f.m.write(a,f.m.read(a)^1)
                if action=='font-CRC':
                    a=f.s['image_crc_lo']+slot(17 if width==60 else 16,0);restores.append((a,f.m.read(a)));f.m.write(a,f.m.read(a)^1)
                if action=='foreign-owner':f.put('se_f_owner',1,1);owner=1
                if action=='bad-header-CRC':bad=bytearray(h);bad[4]^=1;store(bad)
                if action=='validCRC-row22':bad=bytearray(h);bad[200]=22;bad[254:]=binascii.crc_hqx(bad[:254],65535).to_bytes(2,'little');store(bad)
                if action=='bad-row-packet-CRC':
                    row=h[200];raw,_=f.raw_cache();bad=bytes((raw[row*240]^1,));store(bad,row*240)
                if typing:
                    # Actual checked C6 mutation, not host revision/certificate
                    # fabrication; then direct optional TRY before full repaint.
                    f.put('se_hot_byte',profile.observer.Q,1);assert not f.call('se_hot_call',3).p&1
                    assert f.get('se_r_revision',4)!=f.get('se_l_revision',4)
                allowed=action.endswith('caret-allowed')
                if allowed:
                    before=g.reu();canonical=f.canonical();bits=f.read(0x6000,8000)+f.read(0x4000,1000);r,n=invoke()
                    assert not r.p&1 and r.a==0,(action,r.a,r.p)
                    assert f.canonical()==canonical,(action,'canonical')
                    assert f.read(0x6000,8000)+f.read(0x4000,1000)==bits,(action,'unchanged-caret pixels')
                    # A0 stages the next publication sequence in the NC header;
                    # the real root (covered by the paired matrix) then INCs it.
                    after=g.reu();want=bytearray(before);lo=bank*65536+0x1500
                    want[lo:lo+256]=after[lo:lo+256]
                    assert after==want,(action,'16MiB outside exact NC header')
                    future=after[lo:lo+256];assert int.from_bytes(future[202:204],'little')==(f.get('se_e_draw_sequence',2)+1)&65535
                    assert binascii.crc_hqx(future[:254],65535)==int.from_bytes(future[254:],'little')
                else:n=refused(action)
                assert f.get('se_f_owner',1)==owner
                for a,v in restores:f.m.write(a,v)
                f.put('se_f_owner',0,1)
                item=dict(width=width,action=action,allowed=allowed,instructions=n);cases.append(item);print('FAULT PASS',item,flush=True)
                (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
        (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases),indent=2)+'\n');return cases
    finally:f.close()

def run(out,base):
    out.mkdir(parents=True);spec=importlib.util.spec_from_file_location('plain_caret_build',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);candidate,budget=b.build(out/'pair',base)
    old=matrix(out/'control',base);new=matrix(out/'candidate',candidate)
    assert len(old['cases'])==len(new['cases'])==16
    for a,c in zip(old['cases'],new['cases']):
        assert a['tag']==c['tag']and a['pixels_sha256']==c['pixels_sha256']and a['caret']==c['caret']and a['top']==c['top']
        if c['caps']==0 and c['action']=='right':assert 'gridedit'not in c['entries']and c['settled_instructions']<a['settled_instructions']//2
    zero=matrix(out/'source40',candidate,(0,),('right',))
    assert all(c['loads']==0 for c in zero['cases'])
    fault_cases=faults(out/'faults',candidate)
    t=out/'transport';t.mkdir();transport_result=transport.run(t,candidate)
    result=dict(status='PASS',budget=budget,cases=[dict(control=a,candidate=c)for a,c in zip(old['cases'],new['cases'])],source40=zero['cases'],faults=fault_cases,transport=transport_result,scope=__doc__)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=profile.BASE);a=p.parse_args();out=ROOT/'build/grid-plain-caret'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve())
