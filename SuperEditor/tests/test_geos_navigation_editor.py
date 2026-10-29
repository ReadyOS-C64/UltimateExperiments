"""Independent actual-editor proportional navigation gate; prepare by default.

Canonical PETSCII and reference advances determine every expected target. The
oracle never reads product row/map/X records to choose where a command lands.
No shared make, native VICE or physical keyboard claim belongs to this script.
"""
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime,timezone
import argparse,hashlib,json,sys,zipfile
import test_geos_editor as geos
from test_geos_line import oracle as line_break
from redraw_model import native_text

ROOT=geos.ROOT
VERTICAL={36:-1,37:1,38:-19,39:19}
SAMPLE=native_text('WWWW iii. mixed\rI\r\r'+('Wim. narrow i broad W '*8)+
                   '\rAfter a wrapped logical line\rShort\r'+('tail line\r'*24))


@dataclass(frozen=True)
class MetricLine:
    start:int
    end:int
    next:int
    reason:int
    boundaries:tuple


def lines(data,widths,*,width=320):
    """Complete source layout, retaining CR and an exact-width EOF row."""
    advances=[widths[geos.native(v)] for v in data]
    result=[];start=0
    while True:
        row=line_break(data,advances,start,width,0,0,-1,0)
        result.append(MetricLine(start,row['end'],row['next'],row['reason'],tuple(row['maps'])))
        if row['reason']==2:return tuple(result)
        assert row['next']>start,(start,row)
        start=row['next']


def caret_row(rows,caret):
    for i,row in enumerate(rows):
        if row.start<=caret<row.end or caret==row.end and row.reason in (1,2):return i
    raise AssertionError(('caret has no canonical visual row',caret))


def hit(row,x,*,clamp_soft_end=True):
    """Nearest source boundary, tie toward the higher canonical position.

    A soft row's exclusive end is the next row's opener. Excluding that alias
    keeps a vertical target on the requested visual row. CR/EOF owns its end.
    """
    count=len(row.boundaries)
    if clamp_soft_end and row.reason not in (1,2) and count>1:count-=1
    index=min(range(count),key=lambda i:(abs(row.boundaries[i]-min(320,max(0,x))),-i))
    return row.start+index


def move(rows,caret,command,preferred=None):
    assert command in VERTICAL
    current=caret_row(rows,caret);line=rows[current]
    x=line.boundaries[caret-line.start] if preferred is None else preferred
    target=max(0,min(len(rows)-1,current+VERTICAL[command]))
    return hit(rows[target],x),x,target


def viewport(rows,top,target):
    """Twenty intersecting9px rows; off-page motion anchors at target start."""
    first=next(i for i,row in enumerate(rows) if row.start==top)
    return top if first<=target<min(len(rows),first+20) else rows[target].start


def model_check():
    widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();rows=lines(SAMPLE,widths)
    caret=5;preferred=None;trace=[]
    for command in (37,37,37,37,36,36,39,38):
        caret,preferred,index=move(rows,caret,command,preferred)
        assert caret_row(rows,caret)==index
        trace.append(dict(command=command,caret=caret,pixel_x=preferred,row=index))
    # Exact-width sources put EOF on the following row; trailing CR does too.
    space=widths[geos.native(32)];assert 320%space==0
    full=lines(b' '*(320//space),widths)
    assert len(full)==2 and full[-1].start==len(b' '*(320//space))
    assert caret_row(full,full[-1].start)==1
    assert len(lines(b'\r',widths))==2 and len(lines(b'',widths))==1
    for row in rows:
        for x in (0,1,159,319,320,65535):
            p=hit(row,x);assert row.start<=p<=row.end
            assert row.reason in (1,2) or p<row.end
    return dict(status='model-prepared',source_bytes=len(SAMPLE),visual_rows=len(rows),trace=trace,
        scope='Independent host preferred-X/source-boundary oracle only; actual C23 awaits stable build.')


def preserved(f):
    """Navigation can move/reload the gap and close its group, never edit it."""
    fields=(('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),
            ('se_h_current',4),('se_h_saved',4),('se_h_end',2),
            ('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3))
    return f.read(f.s['se_doc_roots'],512)+b''.join(f.read(f.s[n],w) for n,w in fields)


class Fixture(geos.Fixture):
    def remove(self,identity,slot):
        # Catalog is six fixed arrays; search the whole declared capacity,
        # including the new C23 tail rather than an old24entry probe limit.
        for i in range(self.s['se_overlay_capacity']):
            if self.m.read(self.s['se_overlay_ids']+i)==identity and self.m.read(self.s['image_slot']+i)==slot:
                self.m.write(self.s['se_overlay_ids']+i,0)
                self.m.write(self.s['se_overlay_active']+slot,0)
                return i
        raise AssertionError(('missing fault target',identity,slot))


def run(out,previous=None,smoke=False):
    frozen,identity=geos.freeze(out,previous)
    symbols=json.loads((frozen/'build/editor-report.json').read_text())['symbols']
    assert len(identity['names'])>=29,'C23 product integration not available; preparation only'
    geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
    geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
    paths=[Path(__file__),ROOT/'tests/test_geos_editor.py',ROOT/'tests/test_geos_line.py',
           ROOT/'tests/test_grid_modes.py',ROOT/'tools/editor_fixture.py',ROOT/'tools/cpu_editor.py']
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in paths:archive.write(path,path.relative_to(ROOT))
    dll=geos.grid.runner(out)
    fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    widths=fonts['bsw9-widths.bin'];frames=[];moves=[];f=None
    def check(data,tag):
        canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();used=f.total_instructions
        f.render();assert f.get('se_mode',1)==3 and f.merged()==data,(tag,'mode/source')
        assert f.canonical()==canonical and f.catalog()==catalog,(tag,'render changed canonical state/catalog')
        bits,attrs,layout=geos.expected(f,data,fonts)
        actual_bits,actual_attrs=f.read(0x6000,8000),f.read(0x4000,1000)
        for label,raw in [('bitmap',actual_bits),('attributes',actual_attrs),('source',data)]:
            (out/(tag+'-'+label+'.bin')).write_bytes(raw)
        geos.png(actual_bits,actual_attrs,out/(tag+'-cpu.png'))
        assert actual_bits==bits,(tag,'pixels',next((i,a,b) for i,(a,b) in enumerate(zip(actual_bits,bits)) if a!=b))
        assert actual_attrs==attrs,(tag,'colors',next((i,a,b) for i,(a,b) in enumerate(zip(actual_attrs,attrs)) if a!=b))
        cache,bank=f.cache();after=f.reu();start=bank*65536;cursor=0
        allowed=[(start,start+64)]+[(start+0x200+i*0x800,start+0x200+(i+1)*0x800) for i in range(22)]
        for a,b in allowed:
            assert after[cursor:a]==reu[cursor:a],(tag,'other REU changed',cursor,a);cursor=b
        assert after[cursor:]==reu[cursor:],(tag,'REU banktail/otherbanks changed')
        assert cache[0]==1 and cache[1]==len(layout),(tag,'cache publication')
        for i,row in enumerate(layout):
            raw=cache[0x200+i*0x800:0x220+i*0x800]
            assert tuple(int.from_bytes(raw[j:j+3],'little') for j in (0,3,6))==(row.start,row.end,row.next),(tag,'canonical row anchors',i)
        assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks','se_fs_owned','se_n_owned'))
        assert f.read(0xC600,1024)==f.shim
        frames.append(dict(tag=tag,source_bytes=len(data),top=f.get('se_v_top'),caret=f.get('se_hot_caret'),
            preferred=f.get('se_l_preferred'),preferred_valid=f.get('se_n_preferred_valid',1),
            render_instructions=f.total_instructions-used,rows=len(layout)))
        (out/'progress.json').write_text(json.dumps(dict(frames=frames,moves=moves),indent=2)+'\n')
    def start(data,caret=0):
        nonlocal f
        if f:f.close()
        f=Fixture(out,frozen,dll,True);f.source(data)
        if caret:f.position(caret) #explicit initial W_LOAD fixture seed only
        f.m.load(0x8300,bytes((i*73+29)&255 for i in range(160)))
        f.command(99);check(data,'start-'+str(len(frames)))
        assert not f.get('se_n_preferred_valid',1)
    def vertical(data,command,preferred,tag):
        rows_=lines(data,widths);old=f.get('se_hot_caret');top=f.get('se_v_top')
        target,wanted_x,index=move(rows_,old,command,preferred)
        target_top=viewport(rows_,top,index)
        unchanged,reu,catalog=preserved(f),f.reu(),f.catalog();used=f.total_instructions
        f.command(command)
        assert f.get('se_hot_caret')==target,(tag,'canonical caret',old,command,target,f.get('se_hot_caret'))
        assert f.get('se_v_top')==target_top,(tag,'viewport context',top,target_top,f.get('se_v_top'))
        assert f.get('se_n_preferred_valid',1)==2 and f.get('se_l_preferred')==wanted_x,(tag,'preferred pixelX',wanted_x,f.get('se_l_preferred'))
        assert f.merged()==data and preserved(f)==unchanged and f.reu()==reu and f.catalog()==catalog,(tag,'navigation mutated source/history/clipboard/REU/catalog')
        moves.append(dict(tag=tag,command=command,before=old,target=target,row=index,top=target_top,
                          preferred=wanted_x,instructions=f.total_instructions-used))
        check(data,tag);return wanted_x
    try:
        start(SAMPLE,5);preferred=None
        for i,command in enumerate((37,37,37,37,36,36,39,38)):
            preferred=vertical(SAMPLE,command,preferred,'preferred-'+str(i))
        if not smoke:
            # Both exact-width and empty EOF have a distinct legal caret row.
            space=widths[geos.native(32)]
            for data in (b'',b'\r',b' '*(320//space),native_text('Wim.\r\rIII')):
                start(data,0);preferred=None
                for i,command in enumerate((37,37,36,39,38)):
                    preferred=vertical(data,command,preferred,'edge-'+str(len(moves)))
            # >64KiB canonical positions must survive both forward and second
            # backward scans, and source reads must not flatten/copy the doc.
            large=native_text('padding Wim. ')*5100+native_text('\rWWWWW\rI\rTail.\r')
            caret=large.rfind(native_text('WWWWW'))+3
            assert caret>65535
            start(large,caret);preferred=None
            for command in (37,37,36,38):
                preferred=vertical(large,command,preferred,'far-'+str(len(moves)))
            # Select both directions across a soft row boundary. This range
            # contains no CR, keeping the current raw-source selection contract
            # separate from future visible CR/hidden-delimiter formatting.
            paragraph=SAMPLE.index(native_text('Wim. narrow'))
            start(SAMPLE,paragraph+10);f.command(68)
            anchor=f.get('se_sel_anchor');preferred=vertical(SAMPLE,37,None,'selection-forward')
            assert f.get('se_sel_mark',1) and f.get('se_sel_anchor')==anchor
            lo,hi=sorted((anchor,f.get('se_hot_caret')));selected=SAMPLE[lo:hi]
            assert selected and 13 not in selected
            f.command(69)
            assert f.merged()==SAMPLE and f.get('se_clip_length')==len(selected)
            token=f.read(f.s['se_clip_token'],5)
            f.m.load(f.s['se_object_id'],token);assert not f.call('se_object_validate').p&1
            reu=f.reu();copied=bytearray()
            for at in range(len(selected)):
                logical=f.m.read(f.s['object_extents']+token[0]*16+(at>>16))
                physical=f.m.read(f.s['se_reu_map']+logical)
                copied.append(reu[physical*65536+(at&65535)])
            assert bytes(copied)==selected,'independent realclipboard bytes'
            check(SAMPLE,'selection-copy')
            f.command(50);position=f.get('se_hot_caret');f.command(71)
            pasted=SAMPLE[:position]+selected+SAMPLE[position:]
            assert f.merged()==pasted;check(pasted,'actual-paste')
            f.command(16);assert f.merged()==SAMPLE;check(SAMPLE,'paste-undo')
            f.command(17);assert f.merged()==pasted;check(pasted,'paste-redo')
            # Reversed source endpoints remain canonical across mode changes.
            start(SAMPLE,paragraph+80);f.command(68);anchor=f.get('se_sel_anchor')
            vertical(SAMPLE,36,None,'selection-reversed')
            assert f.get('se_hot_caret')<anchor and f.get('se_sel_anchor')==anchor
            canonical=f.canonical();f.key(0x8C)
            assert f.get('se_mode',1)==0 and f.canonical()==canonical
            f.render();f.key(0x8C,mods=4)
            assert f.get('se_mode',1)==3 and f.canonical()==canonical
            check(SAMPLE,'selected-F8-CTRL-F8')
            # Every cache-independent cold source continuation can be cancelled
            # through the actual resident queued STOP service poll.
            start(SAMPLE,5)
            before=preserved(f),f.get('se_hot_caret'),f.get('se_v_top'),f.reu(),f.catalog(),f.read(0x6000,8000),f.read(0x4000,1000)
            f.put('se_e_error',0,1);f.call('se_editor_command',37)
            assert f.get('se_e_job',1)==12
            for _ in range(400):
                if f.read(0x912D,1)==b'\1':break
                f.call('se_editor_service')
                assert f.get('se_e_job',1)==12,'navigation finished before mid-source STOP'
            else:raise AssertionError('navigation never opened actual source context')
            f.queued(3);f.call('se_editor_service')
            assert not f.get('se_e_job',1) and not f.get('se_e_redraw',1)
            assert before==(preserved(f),f.get('se_hot_caret'),f.get('se_v_top'),f.reu(),f.catalog(),f.read(0x6000,8000),f.read(0x4000,1000)), 'STOP published partial navigation/state/pixels'
            assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks','se_fs_owned'))
            f.command(0);check(SAMPLE,'STOP-navigation-recovery')
            # Actual catalog admission faults, both before BEGIN and with an
            # open counted R14 source lease. No unavailable leaf is fake-called.
            for identity_,slot,mid in ((23,1,False),(20,1,False),(14,0,True)):
                start(SAMPLE,5);before=preserved(f),f.get('se_hot_caret'),f.get('se_v_top'),f.reu()
                if mid:
                    f.put('se_e_error',0,1);f.call('se_editor_command',37)
                    for _ in range(400):
                        if f.read(0x912D,1)==b'\1':break
                        f.call('se_editor_service')
                    else:raise AssertionError('missingR14 probe never opened source')
                index=f.remove(identity_,slot)
                if not mid:f.command(37,error=0x17)
                else:f.settle(error=0x17)
                assert before==(preserved(f),f.get('se_hot_caret'),f.get('se_v_top'),f.reu()),'failed admission published navigation/source'
                assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks','se_fs_owned'))
                f.m.write(f.s['se_overlay_ids']+index,identity_)
                f.command(0);check(SAMPLE,'missing-'+str(identity_)+'-recovery')
        result=dict(status='passed',identity=identity,frames=frames,moves=moves,
            pixels_checked=len(frames)*64000,attributes_checked=len(frames)*1000,
            verification_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            scope='Actual public editor proportional navigation + independent canonical targets/preferredX/pixels. CPU only, no native timing/physical-key claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
    finally:
        if f:f.close()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model-check',action='store_true')
    ap.add_argument('--run',action='store_true');ap.add_argument('--fixture',type=Path);ap.add_argument('--smoke',action='store_true');args=ap.parse_args()
    if args.model_check:print(json.dumps(model_check(),indent=2));return
    if args.run:
        out=ROOT/'build/geos-navigation-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
        print('RUN '+str(out),flush=True)
        try:run(out,args.fixture,args.smoke)
        except BaseException as error:
            (out/'failure.json').write_text(json.dumps(dict(error=repr(error)),indent=2)+'\n');raise
        return
    print('Prepared canonical preferred-X GEOS navigation oracle. Actual public command gate awaits C23 ABI/build signal.')


if __name__=='__main__':main()
