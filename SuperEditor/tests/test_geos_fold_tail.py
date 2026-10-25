"""Isolated actual R25 fold-summary/virtual-CR policy CPU acceptance.

Builds an unchanged frozen copy of the parent's module against the current
generated resident API. No shared build, production edit, fake overlay callback,
pixels, editor integration, native IRQ/VIC or timing claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,random,re,shutil,subprocess,sys,zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_row as row
from peddle import Machine
S=0x8B40
END=S+0x23;NEXT=S+0x26;PREFIX_FLAGS=S+0x36;REASON=S+0x31;VISIBLE=S+0x3B
SOURCE=S+0x42;CARET=S+0x45;LOW=S+0x48;HIGH=S+0x4B;MARK=S+0x4E
CHAR=S+0x5D;ROLE=S+0x5E;ANCHOR=S+0x6C;WANT=S+0x9E;FLAGS=S+0x9F


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out):
    frozen=out/'fixture';frozen.mkdir()
    files=['src/render/geos/tail-entry.s','src/render/geos/tail-policy.inc','src/render/geos/editor.inc',
        'src/render/geos/page-paint.inc','src/document/math24.inc',
        'build/editor-api.inc','build/editor-report.json','cfg/overlay-r.cfg']
    hashes={}
    for name in files:
        target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,target);hashes[name]=sha(target)
    # Include directives are resolved only against frozen input, not a parent
    # build that may be changing while this independent lane executes.
    subprocess.run(['ca65','-g','-I',str(frozen/'src'),'-I',str(frozen/'build'),
        '-o',str(out/'tail.o'),'-l',str(out/'tail.lst'),str(frozen/'src/render/geos/tail-entry.s')],check=True,cwd=ROOT)
    subprocess.run(['ld65','-C',str(frozen/'cfg/overlay-r.cfg'),'-o',str(out/'tail.bin'),
        '-Ln',str(out/'tail.lbl'),'-m',str(out/'tail.map'),str(out/'tail.o')],check=True,cwd=ROOT)
    symbols={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'tail.lbl').read_text())}
    api=(frozen/'build/editor-api.inc').read_text()
    symbols.update({n:int(a,16) for n,a in re.findall(r'^(se_f_owner|se_overlay_frame) = \$([0-9A-Fa-f]+)',api,re.M)})
    dump=subprocess.check_output(['od65','--dump-segments',str(out/'tail.o')],text=True)
    sizes={n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',dump,re.S)}
    assert all(not sizes.get(n,0) for n in ('BSS','DATA','ZEROPAGE'))
    assert len((out/'tail.bin').read_bytes())<=4096
    report=json.loads((frozen/'build/editor-report.json').read_text())
    assert (out/'tail.bin').read_bytes()[:16]==bytes.fromhex(report['resident_binding']['digest'])
    assert symbols['entry']==0xA010
    (out/'sources.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return symbols,sizes,hashes


def run(out):
    out.mkdir(parents=True);symbols,sizes,hashes=build(out)
    row.OUT=out;dll=row.runner();m=Machine()
    m.load(0,bytes((i*73+19)&255 for i in range(65536)));m.load(0xA000,(out/'tail.bin').read_bytes())
    report=json.loads((out/'fixture/build/editor-report.json').read_text())
    count=bounds_count=owner_count=0;peak=0;coverage=set()
    def read(start,n):
        b=C.create_string_buffer(n);dll.gr_read(m.handle,start,n,b);return b.raw
    def reu():
        b=C.create_string_buffer(16*1024*1024);dll.gr_reu(m.handle,len(b),b);return b.raw
    def put24(address,value):m.load(address,value.to_bytes(3,'little'))
    def invoke(operation,expected,owner=4):
        nonlocal peak,count
        m.write(symbols['se_f_owner'],owner);m.write(symbols['se_overlay_frame'],operation)
        m.write(0x1FE,0xFE);m.write(0x1FF,2)
        before=read(0,65536)
        for key,value in [('pc',symbols['entry']),('sp',0xFD),('p',0x24),('a',0xD3),('x',0xA5),('y',0x5A)]:
            getattr(m.lib,'zeropage_peddle_set_'+key)(m.handle,value)
        steps=dll.gr_run(m.handle,1000);assert steps,('nonreturn',operation,hex(m.regs().pc))
        peak=max(peak,steps);count+=1;regs=m.regs()
        target=bytearray(before)
        for address,data in expected.items():target[address:address+len(data)]=data
        after=read(0,65536)
        assert after==target,('fullRAMguard',operation,owner,
            next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,target)) if a!=b))
        assert regs.a==(0 if owner==4 else 0xB2) and bool(regs.p&1)==(owner!=4),(regs.a,regs.p,owner)
    def tail(end,next_,folded,lo,hi,visible=1,reason=1,want=None):
        assert 0<=lo<=hi<=0xFFFFFF and 0<=end<=next_<=0xFFFFFF
        if want is None:want=int(lo!=hi)
        # Poison the complete prefix+private frame, then provide only actual
        # documented inputs. No serialized source/map bytes are synthesized.
        m.load(S,bytes((i*29+end+hi)&255 for i in range(192)))
        put24(END,end);put24(NEXT,next_);put24(LOW,lo);put24(HIGH,hi)
        m.write(PREFIX_FLAGS,0x80 if folded else 0);m.write(VISIBLE,visible)
        m.write(REASON,reason);m.write(WANT,want)
        # A normalCR represents exactly its source byte; a summary represents
        # the half-open canonical range beginning at thatCR throughfoldEND.
        selected=bool(want and visible and reason==1 and
            ((lo<next_ and end<hi) if folded else lo<=end<hi))
        paint_folded=bool(folded and visible)
        flags=int(paint_folded)|(2 if selected else 0)
        invoke(0,{SOURCE:end.to_bytes(3,'little'),CHAR:bytes([43 if paint_folded else 32]),
            ROLE:bytes([2 if paint_folded else 0]),FLAGS:bytes([flags])})
    def bounds(caret,anchor,mark):
        nonlocal bounds_count
        m.load(S,bytes((i*41+caret+anchor)&255 for i in range(192)))
        for address in (CARET,LOW,HIGH):put24(address,caret)
        put24(ANCHOR,anchor);m.write(MARK,mark)
        lo,hi=sorted((caret,anchor)) if mark else (caret,caret)
        invoke(1,{LOW:lo.to_bytes(3,'little'),HIGH:hi.to_bytes(3,'little')});bounds_count+=1
    try:
        old_reu=reu()
        # Precise boundaries include low-byte,64KiB and24-bit transitions.
        for end,next_ in [(0,1),(7,41),(255,256),(65535,65536),(65536,131072),
            (0x123456,0x234567),(0xFFFFFE,0xFFFFFF)]:
            points=sorted({0,max(0,end-1),end,min(0xFFFFFF,end+1),
                max(0,next_-1),next_,min(0xFFFFFF,next_+1),0xFFFFFF})
            for lo in points:
                for hi in points:
                    if lo>hi:continue
                    for folded in (0,1):
                        for visible in (0,1):
                            for reason in range(7):tail(end,next_,folded,lo,hi,visible,reason)
            coverage.add('halfopen_CR_foldend_ties_24bit')
        rng=random.Random(0xF01D25)
        for _ in range(384):
            begin=rng.randrange(0xFFFF00);end=rng.randrange(begin,0xFFFFFF)
            next_=rng.randrange(end,0x1000000);lo,hi=sorted((rng.randrange(0x1000000),rng.randrange(0x1000000)))
            tail(end,next_,rng.randrange(2),lo,hi,rng.randrange(2),rng.randrange(7))
        # Nested summaries use the caller-certified outer interval. A marked
        # endpoint wholly inside a hidden child must still select its ancestor.
        for cr,end in [(10,200),(65530,131090),(0xFE0000,0xFFFFF0)]:
            for lo,hi in [(cr+5,cr+6),(cr+50,cr+90),(end-1,end),(end,end+1)]:
                tail(cr,end,1,lo,hi)
            coverage.add('nested_hidden_intersection')
        points=[0,1,255,256,65535,65536,0x123456,0xFFFFFE,0xFFFFFF]
        for caret in points:
            for anchor in points:
                for mark in (0,1):bounds(caret,anchor,mark)
        for _ in range(128):bounds(rng.randrange(0x1000000),rng.randrange(0x1000000),rng.randrange(2))
        coverage.add('forward_reverse_marked_caret24_sorted_bounds')
        for owner in [v for v in range(256) if v!=4]:
            for operation in (0,1):
                m.load(S,bytes(rng.randrange(256) for _ in range(192)))
                invoke(operation,{},owner);owner_count+=1
        coverage.add('all255_foreignowners_opaque_phase')
        assert reu()==old_reu,'whole16MiB REU changed'
        result=dict(status='passed',calls=count,tail_cases=count-bounds_count-owner_count,
            bounds_cases=bounds_count,foreignowner_cases=owner_count,peak_instructions=peak,
            payload_bytes=(out/'tail.bin').stat().st_size,segments=sizes,resident_BSS=0,ZP=0,
            fullRAMguard_bytes_per_call=65536,wholeREUguard_bytes=16*1024*1024,
            shim_bytes_per_call=1024,source_sha256=hashes,resident_sha256=report['sha256'],
            binding=report['resident_binding'],coverage=sorted(coverage),
            limits='Isolated actual R25 helper only; no root/C22 missing-leaf behavior, glyph/pixel/selection-caret compositor, folding tree validity, native or cycle claim. Opcode1 requires caller initializes lo/hi=caret; want denotes a nonempty selection.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    except BaseException:
        (out/'failure-ram.bin').write_bytes(read(0,65536));raise
    finally:m.close()


if __name__=='__main__':
    out=ROOT/'build/geos-fold-tail'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    print('RUN',out,flush=True);result=run(out)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','binding')},indent=2));print(out)
