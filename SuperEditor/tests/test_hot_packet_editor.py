"""Actual C4 W_PACKET against an independent logical gap/source oracle.

Isolates the packet producer's phase/frame boundary; does not pretend these
synthetic continuation frames are a completed history transaction.
"""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture

OUT=ROOT/'build/hot-packet-editor-result.json'
OUT.unlink(missing_ok=True)
f=EditorFixture();cases=packets=refusals=0;max_instructions=0
immutable_hot={n:w for n,w in [
 ('se_hot_ready',1),('se_hot_phase',1),('se_hot_pending',1),('se_hot_fault',1),
 ('se_hot_owned',1),('se_hot_original',5),('se_hot_append',5),
 ('se_hot_generation',2),('se_hot_epoch',2),('se_hot_position',3),
 ('se_hot_base',3),('se_hot_caret',3),('se_hot_before',3),('se_hot_group',1),
 ('se_hot_byte',1),('se_hot_old_length',2),('se_hot_length',2),
 ('se_hot_left',2),('se_hot_right',2),('se_hot_prefix',2),('se_hot_suffix',2),
 ('se_hot_loaded',2),('se_hot_target',2),('se_hot_delete',1),('se_hot_command',1)]}
immutable_source={n:w for n,w in [
 ('se_doc_original',5),('se_doc_append',5),('se_doc_epoch',2),
 ('se_doc_generation',2),('se_doc_length',3),('se_doc_roots',256),
 ('se_doc_read_locks',1),('se_doc_busy',1),('se_h_token',5),
 ('se_h_service_epoch',2),('se_h_ready',1),('se_h_phase',1),
 ('se_h_original',5),('se_h_append',5),('se_h_generation',2),
 ('se_h_current',4),('se_h_saved',4),('se_h_counter',4),
 ('se_h_end',2),('se_h_cursor',2),('se_h_fault',1),
 ('se_h_owned_lease',1),('se_h_owned_capture',1),('se_h_owned_splice',1)]}
def snap(fields):return {n:f.read(f.s[n],w) for n,w in fields.items()}
def same(fields,before):
    for n,b in before.items():assert f.read(f.s[n],fields[n])==b,n
def reu():
    return bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,i) for i in range(8*65536))
def invoke(error=None):
    global packets,refusals,max_instructions
    f.put('se_overlay_frame',0x81,1)
    r,used=f.m.call(f.s['se_overlay_call'],a=4,x=1,limit=200_000)
    max_instructions=max(max_instructions,used)
    if error is None:
        assert not r.p&1 and r.a==0,('W_PACKET',hex(r.a),hex(r.p))
        packets+=1
    else:
        assert r.p&1 and r.a==error,('W_PACKET refusal',hex(r.a),error)
        refusals+=1
    assert f.read(0xC600,1024)==f.shim
    assert f.read(f.s['se_overlay_busy'],2)==b'\0\0'

def frame(data,split,start=0,count=None):
    n=len(data);right=split+2048-n
    assert 0<=split<=right<=2048
    raw=data[:split]+bytes([0xBC])*(right-split)+data[split:]
    assert len(raw)==2048
    f.m.load(0x9200,raw)
    f.put('se_hot_phase',2,1);f.put('se_h_phase',4,1)
    f.put('se_hot_length',n,2);f.put('se_hot_left',split,2)
    f.put('se_hot_right',right,2);f.put('se_hot_feed',start,2)
    f.put('se_hot_feed_left',n-start if count is None else count,2)
    return raw

def valid(n,split,start=0,count=None):
    global cases
    data=bytes((i*73+(i>>8)*11+n)&255 for i in range(n))
    raw=frame(data,split,start,count)
    hot=snap(immutable_hot);source=snap(immutable_source)
    end=start+(n-start if count is None else count);pos=start
    sentinel=bytes((i*29+17)&255 for i in range(1024))
    while pos<end:
        f.m.load(0x8000,sentinel)
        expected=min(128,end-pos,split-pos if pos<split else end-pos)
        invoke()
        assert f.get('se_doc_count',2)==expected,(n,split,pos,expected)
        assert f.get('se_doc_c64',2)==0x8000
        assert f.get('se_hot_count',1)==expected
        assert f.get('se_hot_feed',2)==pos+expected
        assert f.get('se_hot_feed_left',2)==end-pos-expected
        assert f.read(0x8000,expected)==data[pos:pos+expected],(n,split,pos)
        assert f.read(0x8000+expected,1024-expected)==sentinel[expected:],(n,split,'overrun')
        assert f.read(0x9200,2048)==raw
        same(immutable_hot,hot);same(immutable_source,source)
        pos+=expected
    cases+=1

try:
    committed=bytes((i*37+(i>>8)*7)&255 for i in range(2048))
    f.source(committed,banks=1,physical=8)
    original_reu=reu()
    original_identity={n:f.read(f.s[n],w) for n,w in immutable_hot.items() if n in
                       ('se_hot_original','se_hot_append','se_hot_generation')}
    # Every possible complete RAM span; midpoint gap creates both prefix and
    # suffix packets, including odd spans and page boundaries.
    for n in range(1,2049):valid(n,n//2)
    # Pure prefix/suffix, exact packet edges and disjoint subranges.
    for n in [1,2,127,128,129,255,256,257,511,512,513,1023,1024,1025,2047,2048]:
        valid(n,0);valid(n,n)
    for split in [1,127,128,129,255,256,257,511,512,1023,1024,2047]:
        valid(2048,split)
        for start,count in [(max(0,split-1),min(129,2048-max(0,split-1))),
                            (split,min(128,2048-split))]:
            valid(2048,split,start,count)

    def refusal(changes,error=0x70):
        frame(bytes(range(128)),64)
        for n,data in original_identity.items():f.m.load(f.s[n],data)
        for n,value,width in changes:f.put(n,value,width)
        f.m.load(0x8000,bytes([0xA7])*1024)
        f.put('se_doc_count',0x55AA,2);f.put('se_doc_c64',0x80FF,2)
        hot=snap(immutable_hot);source=snap(immutable_source)
        feed=(f.get('se_hot_feed',2),f.get('se_hot_feed_left',2))
        raw=f.read(0x9200,2048)
        invoke(error)
        assert f.read(0x8000,1024)==bytes([0xA7])*1024,'failed packet wrote output'
        assert f.get('se_doc_count',2)==0x55AA and f.get('se_doc_c64',2)==0x80FF
        assert feed==(f.get('se_hot_feed',2),f.get('se_hot_feed_left',2))
        assert f.read(0x9200,2048)==raw
        same(immutable_hot,hot);same(immutable_source,source)
        # Only malformed request values are restored; source bytes never change.
        for n in ['se_h_ready','se_h_fault']:
            f.put(n,1 if n=='se_h_ready' else 0,1)
        f.m.load(f.s['se_h_generation'],f.read(f.s['se_doc_generation'],2))

    for phase in [0,1,3,255]:refusal([('se_hot_phase',phase,1)])
    for phase in [0,1,2,3,5,255]:refusal([('se_h_phase',phase,1)])
    for n in ['se_hot_original','se_hot_append']:
        for offset in range(5):
            value=bytearray(original_identity[n]);value[offset]^=0x80
            refusal([(n,int.from_bytes(value,'little'),5)],0x74)
    for offset in range(2):
        value=bytearray(original_identity['se_hot_generation']);value[offset]^=0x80
        refusal([('se_hot_generation',int.from_bytes(value,'little'),2)],0x74)
    malformed=[
        [('se_hot_length',2049,2)], [('se_hot_length',65535,2)],
        [('se_hot_feed_left',0,2)], [('se_hot_feed',128,2)],
        [('se_hot_feed',127,2),('se_hot_feed_left',2,2)],
        [('se_hot_feed',0xFF80,2),('se_hot_feed_left',128,2)],
        [('se_hot_right',2049,2)], [('se_hot_right',65535,2)],
        [('se_hot_left',1985,2)], [('se_hot_left',65535,2)],
        [('se_hot_length',127,2),('se_hot_feed_left',127,2)],
        # Original confirmed bug: otherwise individually valid fields read
        # DOCSTATE at9A00 because suffix0 and logical128 disagree.
        [('se_hot_length',128,2),('se_hot_left',0,2),('se_hot_right',2048,2)],
        [('se_hot_length',2048,2),('se_hot_left',2048,2),('se_hot_right',2048,2),
         ('se_hot_feed',2048,2),('se_hot_feed_left',1,2)],
        [('se_hot_length',0,2),('se_hot_left',0,2),('se_hot_right',2048,2),
         ('se_hot_feed',0,2),('se_hot_feed_left',1,2)]
    ]
    for changes in malformed:refusal(changes)
    refusal([('se_h_ready',0,1)],0x60)
    refusal([('se_h_fault',1,1)],0x65)
    refusal([('se_h_generation',f.get('se_doc_generation',2)^0x80,2)],0x64)
    assert reu()==original_reu,'packet mutated source/journal/asset or unowned REU'
    assert f.document()==committed,'packet published source changes'
    result=dict(status='passed',valid_spans=cases,packets=packets,refusals=refusals,
                complete_lengths='all1..2048',reu_bytes_unchanged=8*65536,
                shim_bytes_per_call=1024,max_call_instructions=max_instructions,
                resident_sha256=f.report['sha256'],
                eedit_sha256=hashlib.sha256(f.assets['eedit']).hexdigest(),
                scope='Actual C4 W_PACKET, synthetic bounded continuation frames, no history publication/native timing claim')
    OUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:f.close()
