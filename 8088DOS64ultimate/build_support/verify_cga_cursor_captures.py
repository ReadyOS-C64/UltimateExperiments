"""Read-only full-frame cross-check of actual Peddle capture bytes."""
import sys
sys.dont_write_bytecode=True
sys.pycache_prefix='/nonexistent/dos64-cursor-source-only'
import argparse, hashlib, json
from pathlib import Path
import cga_cursor_oracle as oracle

def verify(directory,native,expected):
    actual=hashlib.sha256(native.read_bytes()).hexdigest()
    if actual!=expected:raise ValueError('Native pair changed since explicit pin')
    receipts=[]
    for p in sorted(directory.glob('cursor-capture-*.bin')):
        raw=p.read_bytes()
        if len(raw)!=28735:raise ValueError('Wrong capture size')
        bda=raw[:256];cga=raw[256:16640];narrow=raw[16640:17664];wide=raw[17664:19712]
        registers=raw[19712:19730];control,cv,pv,phase,blink=raw[19730:19735]
        result=oracle.render_text_capture(bda,cga,narrow,wide,registers=registers,control=control,control_valid=cv,phase_valid=pv,field_phase=phase,blink_visible=blink,native_sha256=actual,expected_native_sha256=expected)
        if raw[19735:27735]!=result['bitmap']:raise ValueError(f'{p}: full8000bitmap mismatch')
        if raw[27735:]!=result['matrix']:raise ValueError(f'{p}: full1000matrix mismatch')
        receipts.append({'capture':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bitmap_bytes':8000,'matrix_bytes':1000,**result['metadata']})
    if len(receipts)<4:raise ValueError('Four actual width/blink/intensity captures required')
    return {'status':'PASS','native':actual,'captures':receipts}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--capture-dir',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--expected-sha256',required=True);a=p.parse_args();print(json.dumps(verify(a.capture_dir,a.native,a.expected_sha256),indent=2))
