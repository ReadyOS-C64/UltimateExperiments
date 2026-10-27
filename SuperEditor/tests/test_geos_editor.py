"""Live GEOS editor acceptance, prepared before the integrated product exists.

The model consumes canonical bytes and reference expanded GEOS glyphs; it never
uses the product's emitted line table, source-to-X maps, or strip packets to
construct its expected output. Default invocation is preparation only. CPU
screens here cannot prove VIC banking, real IRQ timing, or physical key chords.
"""
from pathlib import Path
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,shutil,struct,sys,zipfile,zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import test_grid_modes as grid
import test_fold_retention as retention
from redraw_model import native_text
from test_geos_glyphs import native
from test_geos_line import oracle as line_break

PALETTE=(1,3,7,10,12,12,12,7,13,5,15,7,3,1)
PRIORITY=(0,6,7,8,0,0,0,5,3,4,1,5,2,0)
TINY=native_text('Wim. Mixed UPPER/lower\rgjpqy descenders\rLast line.')
GEOS_FONTS=('bsw9.bin','bsw9-widths.bin','bsw9-original.bin')


@dataclass(frozen=True)
class Line:
    start:int
    end:int
    next:int
    top:int
    height:int
    reason:int
    x:int


def source_lines(data,widths,*,top=0,styles=None,code=None,nowrap=False,
                 prose_width=320,limit=22):
    """Independent canonical line breaks and mixed-pitch viewport geometry.

    styles/code are canonical-byte arrays, not projected product row buffers.
    Terminal EOF is an actual empty logical row. A full-width soft boundary
    belongs to the following row; CR/EOF belongs to the current row.
    """
    assert 0<=top<=len(data) and len(widths)==128
    styles=bytes(len(data)) if styles is None else bytes(styles)
    code=bytes(len(data)) if code is None else bytes(code)
    assert len(styles)==len(code)==len(data)
    assert all(s<4 for s in styles) and all(k in (0,1) for k in code)
    advance=[8 if k else widths[native(v)]+(s&1)+(s&2)
             for v,s,k in zip(data,styles,code)]
    lines=[];at=top;y=16
    while y<192 and len(lines)<limit:
        mono=bool(code[at]) if at<len(data) else False
        if mono:y=(y+7)&~7
        if y>=192:break
        result=line_break(data,advance,at,320 if mono else prose_width,
                          int(nowrap),0,-1,0)
        lines.append(Line(at,result['end'],result['next'],y,8 if mono else 9,
                          result['reason'],0))
        y+=8 if mono else 9
        if result['reason']==2:break
        assert result['next']>at,(at,result)
        at=result['next']
    return tuple(lines)


def body_model(data,fonts,*,top=0,caret=None,anchor=None,styles=None,roles=None,
               reverse=None,code=None,nowrap=False,pan=0,prose_width=320):
    """All 320x200 pixels +1000 attributes from reference glyph ink votes.

    Prose uses the expanded 128x9 GEOS reference, independent of packed decoder.
    Bold dilates right once; italic shears upper/middle thirds. Selection/caret
    invert once as a union, after reverse-video ink voting. Empty CR/EOF caret
    is a space with the reference space advance. Chrome is painted separately.
    """
    widths=fonts['bsw9-widths.bin'];font=fonts['bsw9.bin'];native8=fonts['native8.bin']
    assert len(font)==128*18 and len(widths)==128 and len(native8)==1024
    n=len(data)
    styles=bytes(n) if styles is None else bytes(styles)
    roles=bytes(n) if roles is None else bytes(roles)
    reverse=bytes(n) if reverse is None else bytes(reverse)
    code=bytes(n) if code is None else bytes(code)
    assert all(len(a)==n for a in (styles,roles,reverse,code))
    assert all(r<14 for r in roles) and all(v in (0,1) for v in reverse)
    lines=source_lines(data,widths,top=top,styles=styles,code=code,
                       nowrap=nowrap,prose_width=prose_width)
    pixels=bytearray(8000);attrs=bytearray([0x16])*1000
    weights=[[[0]*14 for _ in range(40)] for _ in range(25)]
    lo,hi=sorted((caret,anchor)) if caret is not None and anchor is not None else (0,0)
    def draw(value,style,role,inverse,selected,x,y,height):
        sc=native(value);advance=8 if height==8 else widths[sc]+(style&1)+(style&2)
        cell=((1<<advance)-1)<<(16-advance)
        for gy in range(height):
            sy=y+gy
            if not 16<=sy<192:continue
            if height==8:word=native8[sc*8+gy]<<8
            else:
                word=int.from_bytes(font[sc*18+gy*2:sc*18+gy*2+2],'big')
                if style&1:word|=word>>1
                if style&2:word>>=2 if gy<3 else 1 if gy<6 else 0
            if inverse:word^=cell
            for gx in range(advance):
                px=x+gx
                if not 0<=px<320:continue
                ink=bool(word&(1<<(15-gx)));row=sy//8;tile=px//8
                weights[row][tile][role]=min(255,weights[row][tile][role]+ink)
                if ink^selected:pixels[row*320+tile*8+sy%8]|=128>>(px&7)
        return advance
    for line in lines:
        x=line.x-(pan if nowrap else 0)
        for at in range(line.start,line.end):
            x+=draw(data[at],styles[at],roles[at],reverse[at],
                    lo<=at<hi or at==caret,x,line.top,line.height)
        if line.reason in (1,2) and (line.end==caret or lo<=line.end<hi):
            draw(32,0,0,False,True,x,line.top,line.height)
    for row in range(2,24):
        for tile,votes in enumerate(weights[row]):
            role=max(range(14),key=lambda r:(votes[r],PRIORITY[r] if votes[r] else 0,-r))
            attrs[row*40+tile]=(PALETTE[role]<<4)|6
    return bytes(pixels),bytes(attrs),lines


def with_chrome(bitmap,attributes,matrix,colors,font,popup=None):
    """Paint shared native8 header/status and the exact visible popup rectangle."""
    bits=bytearray(bitmap);attrs=bytearray(attributes)
    for row in range(25):
        for col in range(40):
            if row not in (0,1,24) and not (popup and popup[0]<=col<popup[0]+popup[2]
                    and popup[1]<=row<popup[1]+popup[3]):continue
            at=row*40+col;code=matrix[at];glyph=font[(code&127)*8:(code&127)*8+8]
            bits[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in glyph)
            attrs[at]=((colors[at]&15)<<4)|6
    return bytes(bits),bytes(attrs)


def expected(f,data,fonts,**options):
    """Live chrome comes from the independent existing native40 UI oracle."""
    bits,attrs,lines=body_model(data,fonts,top=f.get('se_v_top'),
        caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor')
        if f.get('se_sel_mark',1) else None,**options)
    matrix,colors,popup=grid.logical_ui(f,data)
    bits,attrs=with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
    return bits,attrs,lines


def freeze(out,previous=None):
    """Freeze linked identities before the parent may rebuild shared products."""
    frozen,identity=retention.freeze(out,previous)
    if previous:
        assert all((frozen/'fonts'/n).exists() for n in GEOS_FONTS)
    else:
        for name in GEOS_FONTS:
            src=ROOT/'assets/fonts/generated'/name
            shutil.copy2(src,frozen/'fonts'/name)
            identity['fonts'][name]=grid.sha(src)
        raw_outputs={}
        for path in (ROOT/'build').rglob('*.bin'):
            if path.with_suffix('.lbl').exists() and path.with_suffix('.map').exists():
                raw_outputs.setdefault(grid.sha(path),[]).append(path)
        for name in identity['names']:
            image=(frozen/f'build/overlays/{name}.seo').read_bytes()
            candidates=raw_outputs.get(hashlib.sha256(image[36:]).hexdigest(),[])
            assert candidates,(name,'no source-matched linked bin/lbl/map')
            source=sorted(candidates,key=lambda p:(p.stem!=name,len(str(p)),str(p)))[0]
            for suffix in ('.bin','.lbl','.map'):
                linked=source.with_suffix(suffix)
                standard=frozen/f'build/overlays/{name}{suffix}'
                shutil.copy2(linked,standard)
                # Some production capsules are linked in dedicated stage/worker
                # directories and their native profilers consume those exact
                # paths.  Preserve both the catalog-normalized copy and the
                # source-matched linked path in the immutable fixture.
                original=frozen/linked.relative_to(ROOT)
                if original!=standard:
                    original.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(linked,original)
            assert (frozen/f'build/overlays/{name}.bin').read_bytes()==image[36:]
        # The code/style typing capsules deliberately have a staged entry and
        # worker.  CPU instrumentation binds to those source-matched labels,
        # so keep their production linked outputs rather than reconstructing
        # paths from catalog aliases.
        for stage_dir in ('code-typing','style-typing'):
            source_dir=ROOT/'build/geos-prod'/stage_dir
            target_dir=frozen/'build/geos-prod'/stage_dir
            target_dir.mkdir(parents=True,exist_ok=True)
            for linked in source_dir.iterdir():
                if linked.suffix in ('.bin','.lbl','.map'):
                    shutil.copy2(linked,target_dir/linked.name)
        for name in ('supereditor.d81','disk-manifest.json'):
            shutil.copy2(ROOT/'build'/name,frozen/'build'/name)
        catalog=frozen/'build/geos-font-catalog'
        catalog.mkdir(parents=True,exist_ok=True)
        for name in ('font-pack.bin','catalog.json'):
            shutil.copy2(ROOT/'build/geos-font-catalog'/name,catalog/name)
        identity['disk_sha256']=grid.sha(frozen/'build/supereditor.d81')
        # A CPU oracle can otherwise pass new SEO bytes with an old disk.
        # Refuse fresh product freezes until all packaged bytes are coherent.
        from d81_image import D81Image
        disk=D81Image((frozen/'build/supereditor.d81').read_bytes())
        assert disk.read(b'SUPEREDITOR',kind=2).data==(frozen/'build/editor.prg').read_bytes(), 'stale packaged resident: make build/supereditor.d81'
        assert disk.read(b'GEOSFONTS',kind=1).data==(ROOT/'build/geos-font-catalog/font-pack.bin').read_bytes(), 'stale packaged font pack: make build/supereditor.d81'
        for name in identity['names']:
            assert disk.read(name.upper().encode(),kind=1).data==(frozen/f'build/overlays/{name}.seo').read_bytes(), (name,'stale packaged overlay: make build/supereditor.d81')
        source_files=[ROOT/'Makefile',Path(__file__)]+sorted(p for directory in ('src','cfg')
            for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in ('.s','.inc','.cfg','.py'))
        source_files+=sorted(p for p in (ROOT/'tools').glob('*.py') if p.is_file())
        identity['sources']={str(p.relative_to(ROOT)):grid.sha(p) for p in source_files}
        with zipfile.ZipFile(frozen/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for path in source_files:archive.write(path,path.relative_to(ROOT))
        (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
    for name,h in identity['fonts'].items():assert grid.sha(frozen/'fonts'/name)==h
    assert grid.sha(frozen/'build/supereditor.d81')==identity['disk_sha256']
    return frozen,identity


class Fixture(grid.Fixture):
    def render(self):
        # Run actual root jobs. No controller/line-worker/row leaf is called
        # directly, no emitted map or pixel result is seeded by the host.
        for _ in range(16):
            sequence=self.get('se_e_draw_sequence',2)
            regs=self.call('se_editor_render')
            assert not regs.p&1,('render',hex(regs.a),self.debug())
            job=self.get('se_e_job',1)
            if not job:return regs
            assert job in (7,10,11),('unexpected render job',job,self.debug())
            self.settle()
            if self.get('se_e_draw_sequence',2)!=sequence:
                assert not self.get('se_e_draw_busy',1)
                return regs #job11 includes the actual page/UI publication
        raise AssertionError(('GEOS public render did not converge',self.debug()))

    def cache(self):
        # Existing literal oracles retain ABI1 offsets, with VERSION2 disclosed.
        # A161-glyph active row refuses normalization; new gates use raw_cache.
        from geos_packet import normalize_legacy
        raw,physical=self.raw_cache()
        return normalize_legacy(raw),physical

    def raw_cache(self):
        """Exact owned FEbank bytes; no relocation, mutation or substitution."""
        handle=self.get('se_gc_handle',1)
        assert handle and self.get('se_gc_epoch',2)==self.get('se_reu_epoch',2)
        assert self.m.read(self.s['se_reu_logical_owner']+handle)==0xFE
        physical=self.m.read(self.s['se_reu_map']+handle)
        assert physical and self.m.read(self.s['se_reu_physical_owner']+physical)==0xFE
        return self.reu()[physical*65536:(physical+1)*65536],physical


def png(bitmap,attrs,path):
    """CPU memory visualization only; native VICE screenshots are separate."""
    palette=[(0,0,0),(255,255,255),(136,0,0),(170,255,238),(204,68,204),
             (0,204,85),(0,0,170),(238,238,119),(221,136,85),(102,68,0),
             (255,119,119),(51,51,51),(119,119,119),(170,255,102),
             (0,136,255),(187,187,187)]
    raw=bytearray()
    for y in range(200):
        raw.append(0)
        for x in range(320):
            attribute=attrs[(y//8)*40+x//8]
            ink=bitmap[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8))
            raw.extend(palette[attribute>>4 if ink else attribute&15])
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xFFFFFFFF)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,200,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))


def run(out,previous=None):
    frozen,identity=freeze(out,previous)
    # Public product catalog can grow while this immutable run is executing.
    grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen
    grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names']
    dll=grid.runner(out);fonts={n:(frozen/'fonts'/n).read_bytes()
                               for n in GEOS_FONTS+('native8.bin',)}
    f=Fixture(out,frozen,dll,True);frames=[];data=TINY
    def check(tag):
        assert f.get('se_mode',1)==3,(tag,'not actual GEOS mode')
        canonical,catalog,reu=f.canonical(),f.catalog(),f.reu()
        before=f.total_instructions
        f.render()
        assert f.read(0x8300,160)==bytes(160),(tag,'literal style/role scratch was not completely initialized')
        assert f.canonical()==canonical and f.catalog()==catalog,(tag,'render changed source/history/selection/catalog')
        assert f.merged()==data,(tag,'canonical merged source',f.merged(),data)
        cache,bank=f.cache();after=f.reu();start=bank*65536
        # Only this authenticated logical FE cache bank can receive derived
        # data. The precise populated page spans are checked below and its
        # undeclared bank prefix/tail remain byte exact.
        allowed=[(start,start+64)]+[(start+0x200+i*0x800,start+0x200+(i+1)*0x800) for i in range(22)]
        pos=0
        for a,b in allowed:
            assert after[pos:a]==reu[pos:a],(tag,'REU outside declared GEOS cache spans',pos,a)
            pos=b
        assert after[pos:]==reu[pos:],(tag,'REU after declared GEOS cache spans')
        assert cache[0]==1 and cache[1]<=22,(tag,'page not published',cache[:64].hex())
        bits,attrs,lines=expected(f,data,fonts)
        assert cache[1]==len(lines),(tag,'logical count',cache[1],len(lines))
        for i,line in enumerate(lines):
            record=cache[0x200+i*0x800:0x200+i*0x800+32]
            actual=tuple(int.from_bytes(record[j:j+3],'little') for j in (0,3,6))
            assert actual==(line.start,line.end,line.next),(tag,'canonical row anchors',i,actual,line)
            assert tuple(record[j] for j in (14,15,16,17))==(line.height,line.top,int(line.height==8),line.reason),(tag,'line geometry',i,record.hex(),line)
        actual_bits,actual_attrs=f.read(0x6000,8000),f.read(0x4000,1000)
        (out/(tag+'-actual-bitmap.bin')).write_bytes(actual_bits)
        (out/(tag+'-actual-attributes.bin')).write_bytes(actual_attrs)
        (out/(tag+'-expected-bitmap.bin')).write_bytes(bits)
        (out/(tag+'-expected-attributes.bin')).write_bytes(attrs)
        (out/(tag+'-source.bin')).write_bytes(data)
        png(actual_bits,actual_attrs,out/(tag+'-cpu.png'))
        assert actual_bits==bits,(tag,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(actual_bits,bits)) if a!=b))
        assert actual_attrs==attrs,(tag,'tile colors',next((i,a,b) for i,(a,b) in enumerate(zip(actual_attrs,attrs)) if a!=b))
        assert f.read(0xC600,1024)==f.shim and not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks','se_fs_owned')),(tag,'shim/lease')
        frames.append(dict(tag=tag,source_bytes=len(data),caret=f.get('se_hot_caret'),
            pending=f.get('se_hot_pending',1),instructions=f.total_instructions-before,
            lines=[asdict(l) for l in lines],bitmap_sha256=hashlib.sha256(bits).hexdigest()))
        (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
    try:
        # Explicit fixture import seeds only canonical source. Every following
        # operation uses actual public editor command/input/render services.
        f.source(data)
        # Explicit legal, inactive source-I/O/page scratch fixture. Native RAM
        # is not zero-filled: C21 must initialize all160styles/roles itself.
        f.m.load(0x8300,bytes((i*73+29)&255 for i in range(160)))
        f.command(99);check('three-lines')
        f.key(native_text('Q')[0]);data=native_text('Q')+data;check('pending-type')
        f.command(2);check('right')
        f.command(1);check('left')
        f.command(16);data=TINY;check('undo')
        canonical=f.canonical();f.command(100)
        assert f.get('se_mode',1)==0 and f.canonical()==canonical,'GEOS next must preserve source and cycle to40'
        f.render()
        f.m.load(0x8300,bytes((i*31+7)&255 for i in range(160)))
        f.command(101)
        assert f.get('se_mode',1)==3 and f.canonical()==canonical,'40 previous must preserve source and cycle to GEOS'
        check('cycle-return')
        result=dict(status='passed',identity=identity,frames=frames,
            pixels_checked=len(frames)*64000,attributes_checked=len(frames)*1000,
            scope='Actual editor CPU mode3/public edits + canonical/reference-font full-pixel oracle. CPU visualizations; no native VIC/physical-key/cycle claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
        return result
    finally:f.close()


def model_check():
    """Host-model sanity only; never reported as actual editor execution."""
    fonts={n:(ROOT/'assets/fonts/generated'/n).read_bytes()
           for n in ('bsw9.bin','bsw9-widths.bin','native8.bin')}
    bits,attrs,lines=body_model(TINY,fonts,caret=0)
    assert [x.top for x in lines]==[16,25,34] and lines[-1].end==len(TINY)
    assert lines[0].end==TINY.index(13) and lines[0].next==lines[0].end+1
    assert len(bits)==8000 and len(attrs)==1000
    # Two selections whose caret union covers the same cells must match.
    a=body_model(TINY,fonts,caret=0,anchor=3)[:2]
    b=body_model(TINY,fonts,caret=2,anchor=0)[:2]
    assert a==b #caret at the upper selection boundary extends the same union
    ninth=body_model(native_text('gjpqy\rNext'),fonts,caret=None)[0]
    assert any(ninth[3*320+i*8] for i in range(40)), 'real ninth row missing'
    mixed=native_text('prose\rcode\rafter');code=bytearray(len(mixed));code[6:11]=b'\1'*5
    assert [l.top for l in source_lines(mixed,fonts['bsw9-widths.bin'],code=code)]==[16,32,40]
    empty=source_lines(b'',fonts['bsw9-widths.bin']);assert len(empty)==1 and empty[0].reason==2
    return dict(status='model-prepared',source_bytes=len(TINY),lines=[asdict(l) for l in lines],
        oracle_bitmap_sha256=hashlib.sha256(bits).hexdigest(),
        scope='Host oracle sanity only; actual mode3 production gate awaits stable integration.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model-check',action='store_true')
    ap.add_argument('--run',action='store_true');ap.add_argument('--fixture',type=Path);args=ap.parse_args()
    if args.model_check:print(json.dumps(model_check(),indent=2));return
    if args.run:
        out=ROOT/'build/geos-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
        print('RUN '+str(out),flush=True)
        try:run(out,args.fixture)
        except BaseException as error:
            (out/'failure.json').write_text(json.dumps(dict(error=repr(error)),indent=2)+'\n');raise
        return
    print('Prepared independent live GEOS editor oracle. Await integrated production ABI/build before actual CPU execution.')


if __name__=='__main__':main()
