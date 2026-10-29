"""Audit packed startup names against an independent frozen three-table build.

This compares emitted address/length bytes and actual packaged files. Native
startup/import is a separate gate; no emulated startup behavior is replaced.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from d81_image import D81Image


def run(out, baseline, current):
    old=json.loads((baseline/'build/editor-report.json').read_text())
    new=json.loads((current/'editor-report.json').read_text())
    a=(baseline/'build/editor.prg').read_bytes();b=(current/'editor.prg').read_bytes()
    os,ns=old['symbols'],new['symbols']
    def read(raw,at,count):
        start=at-int.from_bytes(raw[:2],'little')+2
        assert 2<=start<=len(raw)-count
        return raw[start:start+count]
    names=json.loads((baseline/'freeze.json').read_text())['names']
    span=ns['file_catalog_end']-ns['file_catalog'];assert span%2==0
    count=span//2;assert count==len(names)==54
    table=read(b,ns['file_catalog'],2*count)
    disk=D81Image((current/'supereditor.d81').read_bytes());items=[]
    for i,asset in enumerate(names):
        before_at=read(a,os['file_low']+i,1)[0]+256*read(a,os['file_high']+i,1)[0]
        before_len=read(a,os['file_length']+i,1)[0]
        at=table[2*i]+256*(table[2*i+1]>>4);length=table[2*i+1]&15
        before=read(a,before_at,before_len);after=read(b,at,length)
        assert after==before==asset.upper().encode('ascii'),(i,asset,before,after)
        image=(current/'overlays'/(asset+'.seo')).read_bytes()
        assert disk.read(after).data==image,(asset,'D81 exact filename/payload')
        items.append(dict(index=i,name=after.decode('ascii'),length=length,address=at,payload_sha256=hashlib.sha256(image).hexdigest()))
    cold=lambda r:next(x for x in r['segments']if x['name']=='COLD')
    recovered=cold(old)['size']-cold(new)['size'];assert recovered==47
    tutorial=read(a,os['sample'],os['sample_end']-os['sample'])
    assert tutorial==read(b,ns['sample'],ns['sample_end']-ns['sample'])
    for name,at in os.items():
        if at>=0x1000:assert ns.get(name)==at,('warm address moved',name)
    # Only the initial JSR to the moved cold REU probe and the ABI seal
    # may change in warm code. Compare all other emitted bytes to the control.
    warm=bytearray(read(a,0x1000,0x3000));now=read(b,0x1000,0x3000)
    call=b'\x20'+os['se_reu_probe'].to_bytes(2,'little')
    pos=warm.find(call,0,80);assert pos>=0 and warm.find(call,pos+1,80)<0
    assert now[pos:pos+3]==b'\x20'+ns['se_reu_probe'].to_bytes(2,'little')
    warm[pos:pos+3]=now[pos:pos+3]
    seal=ns['se_overlay_binding_digest']-0x1000
    warm[seal:seal+16]=now[seal:seal+16];assert warm==now
    assert new['state_bytes']==old['state_bytes']==1534
    assert next(x for x in new['segments']if x['name']=='ZEROPAGE')['size']==24
    result=dict(status='PASS',resident=new['sha256'],baseline=old['sha256'],catalog=count,
                items=items,recovered_cold_bytes=recovered,
                cold_free_before_0F00=0x0f00-cold(new)['end']-1,
                tutorial_bytes=len(tutorial),warm_delta='cold REU probe JSR relocation and seal only',
                warm_addresses_unchanged=True,BSS=1534,ZP=24,scope=__doc__)
    out.mkdir(parents=True);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',out,'54 exact native names/files; recovered',recovered,'COLD bytes')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--current',type=Path,default=ROOT/'build')
    a=p.parse_args();out=ROOT/'build/cold-catalog'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run(out,a.baseline.resolve(),a.current.resolve())
