"""Independent GEOS rendered-source mapping oracle; no literal oracle changes.

Default is a host specification gate, not editor integration acceptance.  The
actual product gate will be enabled only after the streamed C26/C20 contract is
released.  Canonical source bytes, including hidden delimiters, remain intact.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import random
import zipfile

import test_geos_semantic_editor as semantic
from supermark_model import inline

ROOT = semantic.ROOT


@dataclass(frozen=True)
class Projection:
    raw: bytes
    origin: int
    hidden: bytes
    glyphs: bytes
    anchors: tuple
    source_boundaries: tuple
    left: tuple
    right: tuple
    styles: bytes
    roles: bytes
    reverse: bytes
    code: bytes

    def from_source(self, source):
        """Raw hidden positions still have a deterministic visible boundary."""
        if not self.origin <= source <= self.origin + len(self.raw):
            raise ValueError('source boundary outside canonical document')
        return self.source_boundaries[source - self.origin]

    def from_visible(self, boundary, affinity):
        if affinity not in ('left', 'right') or not 0 <= boundary <= len(self.glyphs):
            raise ValueError('invalid visible boundary or affinity')
        return (self.left if affinity == 'left' else self.right)[boundary]

    def selected(self, start, end):
        """Selection stays one contiguous canonical half-open interval."""
        lo, hi = sorted((start, end))
        return tuple(i for i, at in enumerate(self.anchors) if lo <= at < hi)

    def deletion_target(self, boundary, backwards=False):
        """Only the adjacent displayed byte; never an implicit hidden range."""
        index = boundary - int(backwards)
        return self.anchors[index] if 0 <= index < len(self.anchors) else None

    def reconstruct(self):
        visible = iter(self.glyphs)
        return bytes(v if hidden else next(visible)
                     for v, hidden in zip(self.raw, self.hidden))


def project(data, *, origin=0, block_prefixes=True):
    """Full logical-line proof, independent of transport32/display160 packets.

    Matched PAIR markers hide; confirmed ESCAPE hides pound only. Code lines
    and fences keep bytes literal. Heading/list prefixes START..BODY hide by the root contract; no empty BODY inference hides a
    fence/region line. No parser-emitted product maps are consumed.
    """
    data = bytes(data)
    if origin < 0 or origin + len(data) > 0xFFFFFF:
        raise ValueError('24-bit canonical boundary overflow')
    classes = semantic.classify(data)
    hidden = bytearray(len(data))
    for event in classes.events:
        kind, a, b, body = (event[k] for k in ('kind', 'start', 'end', 'body'))
        if kind not in (0, 1, 2, 3):
            continue
        if block_prefixes and kind in (2, 3):
            hidden[a:body] = bytes([1]) * (body - a)
        for token, style, width, opened, closed in inline(
                data[body:b], body, body_column=(body-a) or None):
            if token == 1:
                hidden[opened:opened+width] = bytes([1]) * width
                hidden[closed:closed+width] = bytes([1]) * width
            elif token == 2:
                assert width == 1 and closed == opened + 1
                hidden[opened] = 1
            else:
                raise AssertionError(('unknown host inline event', token))
    visible = tuple(i for i, flag in enumerate(hidden) if not flag)
    prefix = [0]
    for flag in hidden:
        prefix.append(prefix[-1] + int(not flag))
    left = [None] * (len(visible) + 1)
    right = list(left)
    for raw, boundary in enumerate(prefix):
        if left[boundary] is None:
            left[boundary] = origin + raw
        right[boundary] = origin + raw
    pick = lambda field: bytes(field[i] for i in visible)
    return Projection(data, origin, bytes(hidden), bytes(data[i] for i in visible),
                      tuple(origin+i for i in visible), tuple(prefix),
                      tuple(left), tuple(right), pick(classes.styles),
                      pick(classes.roles), pick(classes.reverse), pick(classes.code))


def expected(f, data, fonts, *, block_prefixes=True):
    """Projected pixel oracle, with source-aware selection and real raw chrome.

    Product GPR/GL maps never choose expected glyphs/metrics/affinities. The
    caller may compare emitted maps separately to this independently built p.
    """
    assert not f.get('se_l_mode', 1), 'initial rendered pixel oracle covers wrap; signed-pan extension pending'
    p = project(data, block_prefixes=block_prefixes)
    caret = p.from_source(f.get('se_hot_caret'))
    anchor = p.from_source(f.get('se_sel_anchor')) if f.get('se_sel_mark', 1) else None
    bits, attrs, rows = semantic.raster(p.glyphs, fonts,
        top=p.from_source(f.get('se_v_top')), caret=caret, anchor=anchor,
        styles=p.styles, roles=p.roles, reverse=p.reverse, code=p.code,
        nowrap=bool(f.get('se_l_mode', 1)), pan=f.get('se_l_pan'))
    # Preserve the independently documented aligned native8 cell FG contract.
    attrs = bytearray(attrs)
    pan = f.get('se_l_pan') if f.get('se_l_mode', 1) else 0
    if pan % 8 == 0:
        for row in rows:
            if row.height != 8:
                continue
            for index in range(row.start, row.end):
                x = (index-row.start)*8-pan
                if 0 <= x < 320:
                    attrs[(row.top//8)*40+x//8] = (semantic.PALETTE[p.roles[index]] << 4) | 6
    matrix, colors, popup = semantic.geos.grid.logical_ui(f, data)
    bits, attrs = semantic.geos.with_chrome(bits, bytes(attrs), matrix, colors,
                                          fonts['native8.bin'], popup)
    return bits, attrs, rows, p


def baseline_probe(out, previous):
    """Historical accepted literal build proves the new requirement is absent.

    This is an expected-failure characterization, never acceptance and never a
    reason to weaken the prior literal-mode regression. No shared build/make.
    """
    geos = semantic.geos
    frozen, identity = geos.freeze(out, Path(previous))
    fonts = {n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    fixture = geos.Fixture(out, frozen, geos.grid.runner(out), True)
    data = geos.native_text('**Bold** *italic* @@code@@\rTail.\r')
    try:
        fixture.source(data)
        fixture.command(99)
        fixture.render()
        assert fixture.merged() == data
        cache, bank = fixture.cache()
        count = int.from_bytes(cache[0x200+12:0x200+14], 'little')
        actual = cache[0x200+32:0x200+32+count]
        p = project(data)
        assert actual == data.split(b'\r')[0], 'baseline is not the accepted literal presentation'
        assert actual != p.glyphs.split(b'\r')[0]
        bits, attrs, rows, p = expected(fixture, data, fonts)
        actual_bits = fixture.read(0x6000, 8000)
        (out/'baseline-actual-bitmap.bin').write_bytes(actual_bits)
        (out/'rendered-expected-bitmap.bin').write_bytes(bits)
        geos.png(actual_bits, fixture.read(0x4000,1000), out/'baseline-literal.png')
        geos.png(bits, attrs, out/'rendered-proposed.png')
        assert actual_bits != bits
        assert fixture.read(0xC600,1024) == fixture.shim
        return dict(status='expected-baseline-literal', identity=identity,
                    raw=data.hex(), emitted_first_row=actual.hex(),
                    expected_first_row=p.glyphs.split(b'\r')[0].hex(),
                    scope='Historical accepted literal product; hidden rendering is not yet integrated. Source unchanged.')
    finally:
        fixture.m.close()


def capacity_probe(out, previous):
    """Actual accepted literal controller:161 clipped glyphs at2px/pan1.

    The non-menu pan1 value is an explicit legal view-state fixture condition;
    rendering and all worker scheduling use the public resident entry. No maps,
    source reader outputs, pixel writes, or job results are synthesized.
    """
    geos = semantic.geos
    frozen, identity = geos.freeze(out, Path(previous))
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = geos.grid.runner(out)
    records = []
    widths = (frozen/'fonts/bsw9-widths.bin').read_bytes()
    for name, value in [('period', b'.'), ('native-i', geos.native_text('i'))]:
        f = geos.Fixture(out, frozen, dll, True)
        data = value*200
        try:
            advance = widths[geos.native(value[0])]
            f.source(data); f.command(99); f.render()
            f.command(77); f.render()
            # Legal settings fixture, not a claim that20px menu pan produces1.
            f.put('se_l_pan', 1); f.put('se_l_manual', 1, 1)
            before_source = f.merged(); before_catalog = f.catalog()
            before_reu = f.reu()
            failure = None
            try:
                f.render()
            except AssertionError as exc:
                failure = str(exc)
            (out/(name+'-ram.bin')).write_bytes(f.read(0,65536))
            (out/(name+'-reu.bin')).write_bytes(f.reu())
            (out/(name+'-source.bin')).write_bytes(data)
            assert f.merged() == before_source == data
            assert f.catalog() == before_catalog
            cache, bank = f.cache()
            after_reu = f.reu(); cursor = 0; base = bank*65536
            for a,b in [(base,base+64)]+[(base+0x200+i*0x800,base+0x200+(i+1)*0x800) for i in range(22)]:
                assert before_reu[cursor:a] == after_reu[cursor:a]
                cursor=b
            assert before_reu[cursor:] == after_reu[cursor:]
            assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks'))
            assert f.read(0xC600,1024) == f.shim
            intersects = sum(i*advance < 321 and (i+1)*advance > 1
                             for i in range(len(data)))
            record = dict(case=name, byte=value.hex(), advance=advance,
                          independent_intersecting_glyphs=intersects,
                          retained_GL_map_count=int.from_bytes(f.read(0x8D00+50,2),'little'),
                          whole16MiB_outside_declared_FE_unchanged=True,
                          pan=f.get('se_l_pan'), error=f.get('se_e_error',1),
                          owner=f.get('se_f_owner',1), job=f.get('se_e_job',1),
                          exception=failure, source_unchanged=True,
                          shim_unchanged=True, catalog_unchanged=True)
            records.append(record)
            (out/'progress.json').write_text(json.dumps(records,indent=2)+'\n')
            print('CAPACITY',json.dumps(record),flush=True)
        finally:
            f.m.close()
    return dict(status='capacity-characterized', identity=identity, cases=records,
                scope='Actual public render under legal pan1 fixture; historical failure retained, not acceptance.')


def capacity_accept(out, previous=None):
    """Actual161-glyph public editor acceptance at the frozen producer's ABI.

    Pan1 is a declared legal view-state fixture, not a fake key route. Source,
    map buffers and pixels are generated by the unmodified resident workers.
    """
    from geos_packet import raw_layout, rows as decode_rows, LegacyCapacityError
    from test_geos_nowrap_editor import nowrap_expected
    geos = semantic.geos
    frozen, identity = geos.freeze(out, Path(previous) if previous else None)
    # ABI3 stores affinities implicitly; decode_rows reconstructs the declared
    # FIRST+index mapping. Require the exact frozen producer's version, rather
    # than relabeling its packet or silently accepting an unknown layout.
    with zipfile.ZipFile(frozen/'product-sources.zip')as archive:
        contract=archive.read('src/render/geos/editor.inc').decode()
    import re
    packet_version=int(re.search(r'^GP_CACHE_VERSION=(\d+)',contract,re.M).group(1))
    assert packet_version in(2,3)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    dll=geos.grid.runner(out); records=[]
    for name,value in [('period',b'.'),('native-i',geos.native_text('i'))]:
        assert fonts['bsw9-widths.bin'][geos.native(value[0])]==2
        for caret,anchor in [(0,None),(1,None),(160,None),(161,None),(200,None),(1,163)]:
            f=geos.Fixture(out,frozen,dll,True);data=value*200
            tag=name+'-'+str(caret)+('-marked' if anchor is not None else '')
            try:
                f.source(data)
                if anchor is not None:f.position(anchor);f.command(68)
                f.position(caret);f.command(99);f.render();f.command(77);f.render()
                f.put('se_l_pan',1);f.put('se_l_manual',1,1)
                before=(f.canonical(),f.catalog(),f.reu())
                f.render()
                assert f.get('se_e_error',1)==0 and f.merged()==data
                assert f.canonical()==before[0] and f.catalog()==before[1]
                cache,bank=f.raw_cache()
                assert raw_layout(cache).version==packet_version and raw_layout(cache).max_glyphs==161 and cache[0]==1 and cache[1]==1
                row=decode_rows(cache)[0]
                assert (row['start'],row['end'],row['next'],row['first'])==(0,200,200,0)
                assert row['count']==161 and row['chars']==value*161
                assert row['styles']==bytes(161) and row['roles']==bytes(161)
                assert row['x']==tuple(max(0,min(320,i*2-1)) for i in range(162))
                assert row['left']==row['right']==tuple(range(162))
                assert row['raster_x']==-1 and row['member']==1
                visible=0<=caret*2-1<320
                assert row['caret_valid']==int(visible)
                assert row['caret_x']==(caret*2-1 if visible else 0)
                assert cache[41]==1 and cache[45]==int(visible)
                try:f.cache()
                except LegacyCapacityError:pass
                else:raise AssertionError('legacy cache view silently truncated161 glyphs')
                bits,attrs,_,_,_=nowrap_expected(f,data,fonts)
                actual=f.read(0x6000,8000);actual_attrs=f.read(0x4000,1000)
                for suffix,raw in [('raw-cache',cache),('actual-bitmap',actual),
                    ('expected-bitmap',bits),('actual-attrs',actual_attrs),('expected-attrs',attrs)]:
                    (out/(tag+'-'+suffix+'.bin')).write_bytes(raw)
                geos.png(actual,actual_attrs,out/(tag+'-cpu.png'))
                assert actual==bits,(tag,'all8000bitmapbytes',next((i,a,b) for i,(a,b) in enumerate(zip(actual,bits)) if a!=b))
                assert actual_attrs==attrs,(tag,'all1000attributes')
                after=f.reu();cursor=0;base=bank*65536
                for a,b in [(base,base+64)]+[(base+0x200+i*0x800,base+0x200+(i+1)*0x800) for i in range(22)]:
                    assert before[2][cursor:a]==after[cursor:a];cursor=b
                assert before[2][cursor:]==after[cursor:]
                assert f.read(0xC600,1024)==f.shim
                assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks'))
                records.append(dict(tag=tag,caret=caret,anchor=anchor,glyphs=161,
                                    caret_visible=visible,all_pixels=True,all_attrs=True,
                                    precise16MiB_guard=True))
                (out/'progress.json').write_text(json.dumps(records,indent=2)+'\n')
                print('CAPACITY_ACCEPT',tag,'PASS',flush=True)
            finally:f.m.close()
    return dict(status='passed',identity=identity,frames=records,screens=len(records),
                pixels=len(records)*64000,attributes=len(records)*1000,
                packet_version=packet_version,
                scope='Actual public161-glyph render/pan1 at exact frozen cache ABI; all chars/styles/roles/X/affinities/pixels preserved. No hidden-markup/native/timing claim.')


def validate(p):
    assert p.reconstruct() == p.raw
    assert all(0 <= at <= 0xFFFFFF for at in p.anchors+p.left+p.right)
    assert len(p.anchors) == len(p.glyphs)
    for boundary, (left, right) in enumerate(zip(p.left, p.right)):
        assert left <= right
        assert p.from_source(left) == p.from_source(right) == boundary
        assert p.from_visible(boundary, 'left') == left
        assert p.from_visible(boundary, 'right') == right
        if boundary < len(p.glyphs):
            target = p.deletion_target(boundary)
            assert target == p.anchors[boundary] and not p.hidden[target-p.origin]
            assert p.deletion_target(boundary+1, True) == target
    assert p.deletion_target(0, True) is None
    assert p.deletion_target(len(p.glyphs)) is None
    # Every hidden byte maps to the boundary before the next displayed byte;
    # forward and reverse selection have identical displayed membership.
    for at, flag in enumerate(p.hidden):
        if flag:
            assert p.from_source(p.origin+at) == p.from_source(p.origin+at+1)
    return len(p.raw)+1


def model_check():
    cases = []; boundaries = 0
    def check(data, **kw):
        nonlocal boundaries
        p = project(data, **kw); boundaries += validate(p)
        cases.append(dict(bytes=len(data), glyphs=len(p.glyphs),
                          hidden=sum(p.hidden), origin=p.origin,
                          block_prefixes=kw.get('block_prefixes', True)))
        return p
    p = check(b'**abc**')
    assert p.glyphs == b'abc' and p.anchors == (2, 3, 4)
    assert p.styles == bytes([1])*3 and p.from_source(0) == p.from_source(2) == 0
    assert p.from_source(5) == p.from_source(7) == 3
    assert tuple(zip(p.left, p.right)) == ((0, 2), (3, 3), (4, 4), (5, 7))
    # Inserting at either side of the final hidden run preserves all delimiters.
    assert p.raw[:p.left[-1]]+b'X'+p.raw[p.left[-1]:] == b'**abcX**'
    assert p.raw[:p.right[-1]]+b'X'+p.raw[p.right[-1]:] == b'**abc**X'
    assert p.selected(1, 6) == p.selected(6, 1) == (0, 1, 2)
    assert p.selected(0, 2) == () and p.selected(5, 7) == ()
    check(b'**outer *inner* outer**\r@@*literal*@@\r')
    p = check(b'\\*literal\\* \\@ \\5')
    assert p.glyphs == b'*literal* @ \\5'
    p = check(b'*unclosed **open @@open\r****four**** @@@@four@@@@')
    assert p.glyphs == p.raw
    p = check(b':::BASIC\r10 PRINT "**literal**":REM *literal*\r:::\r')
    assert p.glyphs == p.raw and any(p.code)
    p = check(b'# **Title**\r  - *item*\r12. @@code@@\r', block_prefixes=True)
    assert p.glyphs == b'Title\ritem\rcode\r'
    # Prefix hiding is proposed independently; fence/region markers stay raw.
    p = check(b':::REGION Name\r# Title\r:::END\r', block_prefixes=True)
    assert p.glyphs == b':::REGION Name\rTitle\r:::END\r'
    for width in (1, 2, 3):
        for opened in (0, 29, 30, 31, 32, 125, 127, 128):
            check(b'A'*opened + b'*'*width + b'Wim'*60 + b'*'*width + b'Z', origin=0xFFF0)
    # True large offsets plus logical lines longer than any display packet.
    large = b'Plain.\r'*9400 + b'# **Across**\r- *last*\r'
    p = check(large, block_prefixes=True)
    assert p.anchors[-1] > 65536 and p.glyphs.endswith(b'Across\rlast\r')
    check(b'**x**', origin=0xFFFFFA)
    for data in (b'', b'\r', bytes(range(256)).replace(b'\r', b'\x00')):
        check(data)
    rng = random.Random(0x52454E44)
    atoms = [b'plain', b'*a*', b'**b**', b'***c***', b'@@*x*@@', b'\\*', b'\\5', b'*open', b'\r']
    for _ in range(80):
        check(b' '.join(rng.choice(atoms) for _ in range(15)), origin=0x10020)
    return dict(status='model-passed', cases=len(cases), canonical_boundaries=boundaries,
                fixtures=cases, scope='Host specification only; no actual editor/CPU/native acceptance.',
                block_prefix_policy='Heading/list START..BODY hidden; fence/region rows remain literal.',
                affinity='LEFT=min canonical preimage;RIGHT=max; raw hidden carets map prefix count; deletions exact displayed byte only.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-only', action='store_true', help='explicit default: independent contract tests')
    parser.add_argument('--baseline', type=Path, help='characterize a frozen historical literal fixture only')
    parser.add_argument('--capacity', type=Path, help='actual2px/pan1 historical glyph-capacity characterization')
    parser.add_argument('--capacity-accept', action='store_true', help='run actualABI2 capacity acceptance after stable build')
    parser.add_argument('--fixture', type=Path, help='immutable fixture for acceptance; default freezes current stable build')
    args = parser.parse_args()
    out = ROOT/'build/geos-rendered-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    result = capacity_accept(out, args.fixture) if args.capacity_accept else capacity_probe(out, args.capacity) if args.capacity else baseline_probe(out, args.baseline) if args.baseline else model_check()
    result['verifier_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'fixtures'}, indent=2))
    print(out)


if __name__ == '__main__':
    main()
