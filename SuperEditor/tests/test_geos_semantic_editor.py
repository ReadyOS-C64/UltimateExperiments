"""Independent canonical SuperMark/lexer oracle for styled GEOS integration.

Default invocation prepares only; --run freezes the actual linked editor integration.
No emitted product class/map is used to choose glyph metrics or semantic roles.
Raw prefixes/delimiters remain source-visible; inline emphasis is not enabled.
"""
from pathlib import Path
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,sys,zipfile
import test_geos_editor as geos
from supermark_model import blocks,inline,lex

ROOT=geos.ROOT
PALETTE=(1,3,7,10,14,1,1,7,13,5,15,7,3,1)
FIXTURE=geos.native_text('# GEOS heading\rWim. prose and gjpqy.\r- A PETSCII bullet\r:::basic\r'
    '10 PRINT "'+('ABcd'*12)+'":REM '+('tail '*7)+'\r'
    '20 DATA 1,2,"a:b":PRINT 42\r:::\r:::asm\r'
    'start: lda #$2A ; comment crossing forty columns and more\r'
    ' .byte "long string crossing a forty-column boundary",$FF\r:::\rEnd.\r')

INLINE_FIXTURE=geos.native_text('# **Strong** *italic* @@code@@\r'
    'Plain **bold** and *italic* plus ***both***.\r'
    '- **item *nested* words** then @@lda #$01@@.\r'
    'Escaped \\*literal\\* and **unclosed plus @@open\r'
    'Wide '+('Wim *a* '*18)+' **across last close** end.\r'
    ':::basic\r10 PRINT "**literal in code**":REM *plain*\r:::\rEnd.\r')


@dataclass(frozen=True)
class Semantic:
    styles:bytes
    roles:bytes
    reverse:bytes
    code:bytes
    events:tuple
    eof_kind:int
    eof_language:int


def classify(data):
    """Source byte classes are a whole-input independent dialect interpretation."""
    n=len(data);styles=bytearray(n);roles=bytearray(n);reverse=bytearray(n);code=bytearray(n)
    events=tuple(blocks(data))
    for event in events:
        a,b,kind=event['start'],event['end'],event['kind']
        stop=b+int(b<n and data[b]==13)
        role=2 if kind==2 else 1 if kind==3 else 4 if kind in (4,5,6) else 0
        roles[a:stop]=bytes([role])*(stop-a)
        reverse[a:stop]=bytes([int(kind==2)])*(stop-a)
        code[a:stop]=bytes([int(kind==5)])*(stop-a)
        if kind in (0,1,2,3):
            exclusive=set()
            for token,style,width,opened,closed in inline(data[event['body']:b],event['body'],body_column=(event['body']-a) or None):
                if token!=1:continue #escaped source and all delimiters stay literal
                interior=range(opened+width,closed)
                if style==4:
                    exclusive.update(interior)
                    for at in interior:styles[at]=0;roles[at]=4
                else:
                    gg=(1 if style&2 else 0)|(2 if style&1 else 0)
                    for at in interior:
                        if at not in exclusive:styles[at]|=gg
            # Inline-code exclusivity is order-independent under outer pairs.
            for at in exclusive:styles[at]=0;roles[at]=4
        if kind==5:
            # Lex full logical source, not a 40-column clipped packet. A quote
            # or REM beyond the first physical row still controls its suffix.
            for start,end,token_role in lex(data[a:b],event['language'],start=a):
                assert 7<=token_role<=13
                roles[start:end]=bytes([token_role])*(end-start)
    fence=events[-1]['fence'] if events else 0
    language=events[-1]['language'] if fence else 0
    return Semantic(bytes(styles),bytes(roles),bytes(reverse),bytes(code),events,
                    5 if fence else 1,language)


def raster(data,fonts,*,top=0,caret=None,anchor=None,styles=None,roles=None,
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
    lines=geos.source_lines(data,widths,top=top,styles=styles,code=code,
                       nowrap=nowrap,prose_width=prose_width)
    pixels=bytearray(8000);attrs=bytearray([0x16])*1000
    weights=[[[0]*14 for _ in range(40)] for _ in range(25)]
    lo,hi=sorted((caret,anchor)) if caret is not None and anchor is not None else (0,0)
    def draw(value,style,role,inverse,selected,x,y,height):
        sc=geos.native(value);advance=8 if height==8 else widths[sc]+(style&1)+(style&2)
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
            role=max(range(14),key=lambda r:(votes[r],geos.PRIORITY[r] if votes[r] else 0,-r))
            attrs[row*40+tile]=(PALETTE[role]<<4)|6
    return bytes(pixels),bytes(attrs),lines


def body(data,fonts,*,top=0,caret=0,anchor=None):
    semantic=classify(data)
    # The reference raster receives only independently derived canonical arrays.
    # Its explicit CR/EOF tail is a normal role0 virtual cell; only caret/
    # selection invert it. Heading reversal belongs to real source glyphs.
    bitmap,attrs,rows=raster(data,fonts,top=top,caret=caret,anchor=anchor,
        styles=semantic.styles,roles=semantic.roles,reverse=semantic.reverse,code=semantic.code)
    assert not (semantic.eof_kind==5 and any(row.start==len(data) for row in rows)), 'empty code EOF needs a local virtual-cell metric extension'
    # Aligned native code has one glyph per physical color tile. Its actual
    # cell writer sets the semantic foreground even when a space has no ink;
    # proportional strips use ink voting, which intentionally defaults empty
    # tiles to normal white. Do not conflate those attribute contracts.
    attributes=bytearray(attrs)
    for row in rows:
        if row.height!=8:continue
        assert row.top%8==0 and row.x==0
        for col,at in enumerate(range(row.start,row.end)):
            assert col<40
            attributes[(row.top//8)*40+col]=(PALETTE[semantic.roles[at]]<<4)|6
    return bitmap,bytes(attributes),rows,semantic


def global_rows(data,widths):
    """Canonical document geometry from y16, independent of viewport phase.

    Reanchoring a viewport at16 can change the following ceil8 code alignment.
    PAGE decisions therefore use these full-document origins, never cached
    viewport-local TOP values. Prefixes remain literal and source-affine.
    """
    semantic=classify(data)
    advances=[8 if semantic.code[i] else widths[geos.native(v)]+(semantic.styles[i]&1)+(semantic.styles[i]&2)
              for i,v in enumerate(data)]
    rows=[];at=0;y=16
    while True:
        mono=semantic.code[at] if at<len(data) else semantic.eof_kind==5
        if mono:y=(y+7)&~7
        result=geos.line_break(data,advances,at,320,0,0,-1,0)
        rows.append(geos.Line(at,result['end'],result['next'],y,
                              8 if mono else 9,result['reason'],0))
        if result['reason']==2:return tuple(rows)
        assert result['next']>at,(at,result)
        at=result['next'];y+=8 if mono else 9


def row_for_caret(rows,caret):
    for i,row in enumerate(rows):
        if row.start<=caret<row.end or (caret==row.end and row.reason in (1,2)):
            return i
    raise AssertionError(('canonical caret has no semantic row',caret))


def navigation(data,widths,caret,command,preferred=None):
    rows=global_rows(data,widths);index=row_for_caret(rows,caret);row=rows[index]
    semantic=classify(data)
    def advance(at):return 8 if semantic.code[at] else widths[geos.native(data[at])]+(semantic.styles[at]&1)+(semantic.styles[at]&2)
    if preferred is None:preferred=sum(advance(at) for at in range(row.start,caret))
    if command in (36,37):target=max(0,min(len(rows)-1,index+(-1 if command==36 else 1)))
    elif command==39:
        target=next((i for i in range(index+1,len(rows)) if rows[i].top>=row.top+171),len(rows)-1)
    elif command==38:
        target=next((i for i in range(index-1,-1,-1) if rows[i].top<=row.top-171),0)
    else:raise AssertionError(('unsupported vertical command',command))
    hit=rows[target];boundaries=[0]
    for at in range(hit.start,hit.end):boundaries.append(boundaries[-1]+advance(at))
    choice=min(range(len(boundaries)),key=lambda i:(abs(boundaries[i]-preferred),-i))
    result=hit.start+choice
    if result==hit.end and hit.reason not in (1,2):result=max(hit.start,hit.end-1)
    return result,preferred,target,rows


def expected(f,data,fonts):
    bits,attrs,rows,semantic=body(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),
        anchor=f.get('se_sel_anchor') if f.get('se_sel_mark',1) else None)
    matrix,colors,popup=geos.grid.logical_ui(f,data)
    bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
    return bits,attrs,rows,semantic


def model_check():
    fonts={n:(ROOT/'assets/fonts/generated'/n).read_bytes()
           for n in geos.GEOS_FONTS+('native8.bin',)}
    bits,attrs,rows,semantic=body(FIXTURE,fonts)
    assert len(bits)==8000 and len(attrs)==1000
    heading=semantic.events[0];assert heading['kind']==2
    assert semantic.roles[0]==2 and semantic.reverse[0]==1
    assert any(e['kind']==3 for e in semantic.events)
    assert {e['language'] for e in semantic.events if e['kind']==5}=={1,2}
    assert all(r.height==8 and r.top%8==0 for r in rows if r.start<len(FIXTURE) and semantic.code[r.start])
    assert all(r.height==9 for r in rows if r.start<len(FIXTURE) and not semantic.code[r.start])
    assert all(len(semantic.styles)==len(x)==len(FIXTURE) for x in (semantic.roles,semantic.reverse,semantic.code))
    basic=next(e for e in semantic.events if e['kind']==5 and e['language']==1)
    quote=FIXTURE.index(b'"',basic['start']);closing=FIXTURE.index(b'"',quote+1)
    assert closing-basic['start']>40 and set(semantic.roles[quote:closing+1])=={9}
    rem=FIXTURE.index(geos.native_text('REM'),closing)
    assert rem-basic['start']>40 and set(semantic.roles[rem:basic['end']])=={10}
    assert any(r.start>basic['start'] and r.start<basic['end'] for r in rows)
    asm=next(e for e in semantic.events if e['kind']==5 and e['language']==2)
    assert semantic.roles[asm['start']]==12 and 7 in semantic.roles[asm['start']:asm['end']]
    page_data=geos.native_text('before\rcurrent\rplain\r:::basic\r'+''.join('10 PRINT 1\r' for _ in range(14))+':::\rone\rtwo\rthree\r')
    page_caret=page_data.index(geos.native_text('current'))
    page_target,_,_,all_rows=navigation(page_data,fonts['bsw9-widths.bin'],page_caret,39)
    assert page_target==len(page_data),('global PAGE must choose EOF',page_target)
    _,_,local_rows,_=body(page_data,fonts,top=page_caret,caret=page_caret)
    local_target=next((r.start for r in local_rows if r.top>=local_rows[0].top+171),local_rows[-1].start)
    assert local_target!=page_target,('fixture must distinguish cached local vs canonical global origins',local_target,page_target)
    styled=classify(INLINE_FIXTURE)
    assert set(styled.styles)=={0,1,2,3}
    for word,style in (('Strong',1),('italic',2),('both',3),('nested',3)):
        at=INLINE_FIXTURE.index(geos.native_text(word));assert styled.styles[at:at+len(word)]==bytes([style])*len(word)
    at=INLINE_FIXTURE.index(geos.native_text('@@code@@'))+2
    assert styled.styles[at:at+4]==bytes(4) and styled.roles[at:at+4]==bytes([4])*4
    at=INLINE_FIXTURE.index(geos.native_text('literal'))
    assert styled.styles[at:at+7]==bytes(7),'escaped literal asterisks must not become italic'
    code_event=next(e for e in styled.events if e['kind']==5)
    assert not any(styled.styles[code_event['start']:code_event['end']])
    long_event=max(styled.events,key=lambda e:e['end']-e['start']);assert long_event['end']-long_event['start']>128
    return dict(status='model-prepared',source_bytes=len(FIXTURE),semantic_events=len(semantic.events),
        page_global_target=page_target,page_cached_local_target=local_target,inline_bytes=len(INLINE_FIXTURE),inline_styles=sorted(set(styled.styles)),
        visible_rows=[asdict(r) for r in rows],roles=sorted(set(semantic.roles)),
        bitmap_sha256=hashlib.sha256(bits).hexdigest(),
        scope='Host canonical source/block/whole-linelexer/mixedfont oracle; no actual C24/C25 editor run yet.')


def run(out,previous=None,smoke=False,io_reveal=False,io_selection=False,io_tails=False,io_pending=False,inline_case=False):
    frozen,identity=geos.freeze(out,previous)
    assert len(identity['names'])>=31,'C24/C25 product integration not frozen yet'
    geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
    geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
    paths=[Path(__file__),ROOT/'tools/supermark_model.py',ROOT/'tests/test_geos_editor.py',
           ROOT/'tests/test_geos_line.py',ROOT/'tests/test_grid_modes.py']
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in paths:z.write(path,path.relative_to(ROOT))
    fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);frames=[];data=INLINE_FIXTURE if inline_case else FIXTURE
    def check(tag,require_caret=False):
        canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();used=f.total_instructions
        f.render()
        assert f.get('se_mode',1)==3 and f.canonical()==canonical and f.catalog()==catalog,(tag,'render mutated canonical/catalog')
        assert f.merged()==data,(tag,'exact canonical source')
        bits,attrs,rows,semantic=expected(f,data,fonts)
        actual_bits,actual_attrs=f.read(0x6000,8000),f.read(0x4000,1000)
        for suffix,raw in [('actual-bitmap',actual_bits),('actual-attributes',actual_attrs),
                           ('expected-bitmap',bits),('expected-attributes',attrs),('source',data)]:
            (out/(tag+'-'+suffix+'.bin')).write_bytes(raw)
        geos.png(actual_bits,actual_attrs,out/(tag+'-cpu.png'))
        if require_caret:assert f.get('se_v_seen',1)==1,(tag,'actual canonical caret hidden after publication',f.get('se_hot_caret'),f.get('se_v_top'),f.get('se_v_bottom'))
        cache,bank=f.cache()
        assert cache[0]==1 and cache[1]==len(rows),(tag,'published mixed page')
        for i,row in enumerate(rows):
            base=0x200+i*0x800;record=cache[base:base+32]
            mono=int(row.start<len(data) and semantic.code[row.start])
            role=semantic.roles[row.start] if row.start<len(data) else 0
            rev=semantic.reverse[row.start] if row.start<len(data) else 0
            assert tuple(int.from_bytes(record[j:j+3],'little') for j in (0,3,6))==(row.start,row.end,row.next),(tag,'canonicalanchors',i)
            assert tuple(record[j] for j in (14,15,16,17))==(row.height,row.top,mono,row.reason),(tag,'independentheight/alignment/kind',i,record.hex(),row)
            assert record[22]&1==rev,(tag,'headinginverseflag',i)
            count=int.from_bytes(record[12:14],'little');assert count==row.end-row.start,(tag,'glyphcount',i)
            assert cache[base+32:base+32+count]==data[row.start:row.end],(tag,'rawvisibleprefixes/glyphs',i)
            assert cache[base+192:base+192+count]==semantic.styles[row.start:row.end],(tag,'canonical GG inline styles',i)
            assert cache[base+352:base+352+count]==semantic.roles[row.start:row.end],(tag,'wholelogicallexer roles',i,
                cache[base+352:base+352+count].hex(),semantic.roles[row.start:row.end].hex())
        assert actual_bits==bits,(tag,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(actual_bits,bits)) if a!=b))
        assert actual_attrs==attrs,(tag,'tilecolors',next((i,a,b) for i,(a,b) in enumerate(zip(actual_attrs,attrs)) if a!=b))
        after=f.reu();start=bank*65536;cursor=0
        # Optional unselected bitmap/attribute base for R27 caret moves occupies
        # B200..D527 after ABI2 packets; R28 additionally owns D528..E567
        # for its sealed old/new row transaction when present in this build.
        for a,b in ([(start,start+64)]+
                    [(start+0x200+i*0x800,start+0x200+(i+1)*0x800) for i in range(22)]+
                    [(start+0xB200,start+(0xEA88 if 'gfont' in f.assets else 0xE568 if 'geosdelta' in f.assets else 0xD528))]):
            assert after[cursor:a]==reu[cursor:a],(tag,'otherREUchanged',cursor,a);cursor=b
        assert after[cursor:]==reu[cursor:],(tag,'cachetail/otherREUchanged')
        assert f.read(0xC600,1024)==f.shim and not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks','se_fs_owned'))
        frames.append(dict(tag=tag,source_bytes=len(data),caret=f.get('se_hot_caret'),top=f.get('se_v_top'),
            pending=f.get('se_hot_pending',1),rows=[asdict(row) for row in rows],
            roles=sorted(set(semantic.roles)),instructions=f.total_instructions-used))
        (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
    def position(p):
        line=data[:p].count(b'\r')+1;column=p-(data.rfind(b'\r',0,p)+1)
        f.typed(geos.native_text('goto '+str(line)))
        for _ in range(column):f.command(2)
        assert f.get('se_hot_caret')==p,('public GOTO+RIGHT source target',p,f.get('se_hot_caret'))
    try:
        f.source(data);f.m.load(0x8300,bytes((i*73+29)&255 for i in range(160)))
        f.command(99);check('all-blocks');frozen_catalog=f.catalog()
        if inline_case and not smoke:
            initial=INLINE_FIXTURE
            p=data.index(geos.native_text('Strong'));position(p);check('inline-bold-caret',True)
            value=geos.native_text('Q');f.key(value[0]);data=data[:p]+value+data[p:]
            assert f.get('se_hot_pending',1);check('inline-pending-bold',True)
            f.command(16);data=initial;assert f.merged()==data;check('inline-undo-bold',True)
            p=data.index(b'**',p+2);position(p);f.command(4);data=data[:p]+data[p+1:]
            check('inline-unmatched-close',True)
            f.command(16);data=initial;assert f.merged()==data;check('inline-undo-close',True)
            start=data.index(geos.native_text('Plain'));stop=data.index(geos.native_text('italic'),start)+3
            position(start);f.command(68)
            for _ in range(stop-start):f.command(2)
            check('inline-marked-across-styles',True)
            f.command(50);f.command(68)
            for _ in range(stop-start):f.command(1)
            check('inline-reverse-across-styles',True);f.command(50)
            before=f.canonical()
            for command,mode in ((96,0),(97,1),(98,2),(99,3)):
                f.command(command);f.render();assert f.get('se_mode',1)==mode and f.canonical()==before and f.merged()==data
            check('inline-mode-return',True)
            position(start+5);preferred=None
            for serial,command in enumerate((37,37,37,36,36,39,38)):
                wanted,preferred,_,_=navigation(data,fonts['bsw9-widths.bin'],f.get('se_hot_caret'),command,preferred)
                f.command(command)
                assert f.get('se_hot_caret')==wanted and f.get('se_l_preferred')==preferred and f.get('se_n_preferred_valid',1)==2,('inline preferred metric navigation',serial,command,wanted,f.get('se_hot_caret'),preferred)
                check('inline-nav-'+str(serial),True)
            f.key(0x85);f.key(geos.native_text('f')[0]);check('inline-File-menu');f.key(3)
            f.key(0x8B);check('inline-help');f.key(0x8B);check('inline-popup-restore',True)
        if io_reveal or io_selection:
            position(15);f.command(68)
            for _ in range(62):f.command(2)
            assert f.get('se_hot_caret')==77 and f.get('se_sel_anchor')==15
            if io_selection:
                check('io-marked-through-code',True)
                f.command(50);f.command(68)
                for _ in range(62):f.command(1)
                assert f.get('se_hot_caret')==15 and f.get('se_sel_anchor')==77
                check('io-reversed-through-code',True)
            f.command(69);assert f.get('se_clip_length')==62
            f.command(50);f.command(35);assert f.get('se_hot_caret')==len(FIXTURE)
            f.command(71);data=FIXTURE+FIXTURE[15:77]
            assert f.merged()==data and f.get('se_hot_caret')==len(data)
            check('io-pasted-eof',True)
            f.command(16);data=FIXTURE;assert f.merged()==data
            check('io-undo-shorter',True)
            f.command(17);data=FIXTURE+FIXTURE[15:77];assert f.merged()==data
            check('io-redo-longer',True)
            for command in (96,99):f.command(command);f.render()
            check('io-mode-return-eof',True)
        if io_tails:
            for label,source,at in (
                ('heading-CR',FIXTURE,14),('code-CR',FIXTURE,164),
                ('prose-CR',FIXTURE,36),('heading-EOF',geos.native_text('# Last'),5),
                ('code-EOF',geos.native_text(':::basic\r10 PRINT 1'),18),
                ('plain-EOF',geos.native_text('Last'),3)):
                data=source;f.source(data);f.command(99);position(at);f.command(68);f.command(2)
                assert f.get('se_hot_caret')==at+1
                check('tail-'+label,True)
        if io_pending:
            data=FIXTURE;f.source(data);f.command(99);f.command(35);check('pending-start-EOF',True)
            flushes=[]
            def object_bytes(token,offset,count,reu):
                identity=token[0];assert token[3:]==f.read(f.s['se_object_epoch'],2)
                assert int.from_bytes(token[1:3],'little')==f.read(f.s['object_gen_lo']+identity,1)[0]+256*f.read(f.s['object_gen_hi']+identity,1)[0]
                result=bytearray()
                while count:
                    logical=f.read(f.s['object_extents']+identity*16+(offset>>16),1)[0]
                    physical=f.read(f.s['se_reu_map']+logical,1)[0]
                    assert logical and physical and f.read(f.s['se_reu_logical_owner']+logical,1)==f.read(f.s['se_reu_physical_owner']+physical,1)
                    take=min(count,65536-(offset&65535));result+=reu[physical*65536+(offset&65535):physical*65536+(offset&65535)+take];offset+=take;count-=take
                return bytes(result)
            for i,value in enumerate(geos.native_text('A \rB \rC \rD \rE')):
                p=f.get('se_hot_caret');f.key(value);data=data[:p]+bytes([value])+data[p:]
                before=dict(pending=f.get('se_hot_pending',1),generation=f.get('se_doc_generation',2),
                    node=f.get('se_h_current',4),saved=f.get('se_h_saved',4),counter=f.get('se_h_counter',4),end=f.get('se_h_end',2),
                    position=f.get('se_hot_base'),delete=f.get('se_hot_old_length',2),insert=f.get('se_hot_length',2),caret_before=f.get('se_hot_before'))
                committed=f.document()
                old_reu=f.reu();tokens=f.read(f.s['se_doc_meta'],15);clip=f.read(f.s['se_clip_token'],5)+f.read(f.s['se_clip_length'],3)
                selection=f.read(f.s['se_sel_mark'],1)+f.read(f.s['se_sel_anchor'],3)
                old_state=f.canonical();f.render()
                bits,attrs,_,_=expected(f,data,fonts)
                assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,('pending first publication pixels',i)
                assert f.get('se_v_seen',1)==1 and f.get('se_hot_caret')==p+1 and f.merged()==data,('pending first publication visible source/caret',i)
                assert clip==f.read(f.s['se_clip_token'],5)+f.read(f.s['se_clip_length'],3) and selection==f.read(f.s['se_sel_mark'],1)+f.read(f.s['se_sel_anchor'],3)
                if f.canonical()!=old_state:
                    assert before['pending']==1 and f.get('se_hot_pending',1)==0 and f.get('se_doc_generation',2)==before['generation']+1
                    assert tokens==f.read(f.s['se_doc_meta'],15) and f.get('se_doc_length')==len(data)
                    assert f.get('se_h_counter',4)==before['counter']+1 and f.get('se_h_current',4)==f.get('se_h_counter',4) and f.get('se_h_saved',4)==before['saved']
                    length=f.get('se_h_end',2)-before['end'];record=object_bytes(f.read(f.s['se_h_token'],5),before['end'],length,f.reu());head=record[:64]
                    assert head[:5]==b'SEH1\x01' and int.from_bytes(head[6:8],'little')==len(record)
                    assert binascii.crc_hqx(head[:58]+head[60:],0xFFFF)==int.from_bytes(head[58:60],'little') and binascii.crc_hqx(record[64:],0xFFFF)==int.from_bytes(head[56:58],'little')
                    editpos,deleted,inserted_bytes=(int.from_bytes(head[a:a+3],'little') for a in (26,29,32))
                    assert before['position']<=editpos<=editpos+deleted<=before['position']+before['delete']
                    assert len(data)==len(committed)-deleted+inserted_bytes
                    assert tuple(int.from_bytes(head[a:a+3],'little') for a in (39,42))==(before['caret_before'],p+1)
                    removed=int.from_bytes(head[35:37],'little');inserted=int.from_bytes(head[37:39],'little');newbytes=bytearray();oldbytes=bytearray()
                    for j in range(removed):
                        ref=record[64+j*9:64+(j+1)*9];oldbytes+=object_bytes(ref[:3]+f.read(f.s['se_object_epoch'],2),int.from_bytes(ref[3:6],'little'),int.from_bytes(ref[6:9],'little'),f.reu())
                    for j in range(removed,removed+inserted):
                        ref=record[64+j*9:64+(j+1)*9];newbytes+=object_bytes(ref[:3]+f.read(f.s['se_object_epoch'],2),int.from_bytes(ref[3:6],'little'),int.from_bytes(ref[6:9],'little'),f.reu())
                    assert oldbytes==committed[editpos:editpos+deleted] and len(oldbytes)==deleted
                    assert newbytes==data[editpos:editpos+inserted_bytes] and len(newbytes)==inserted_bytes
                    assert committed[:editpos]+newbytes+committed[editpos+deleted:]==data
                    # The authorized canonical publication may write only its
                    # authenticated metadata/append/history objects and FE cache.
                    allowed=set()
                    for token in (tokens[:5],tokens[10:15],f.read(f.s['se_h_token'],5)):
                        for j in range(16):
                            logical=f.read(f.s['object_extents']+token[0]*16+j,1)[0]
                            if logical:allowed.add(f.read(f.s['se_reu_map']+logical,1)[0])
                    _,physical=f.cache();allowed.add(physical);new_reu=f.reu()
                    for bank in range(len(old_reu)//65536):
                        if bank not in allowed:assert old_reu[bank*65536:(bank+1)*65536]==new_reu[bank*65536:(bank+1)*65536],('pending publication other REU bank',bank)
                    flushes.append(dict(step=i,record_bytes=len(record),generation=f.get('se_doc_generation',2),allowed_typed_object_banks=sorted(allowed)))
                else:
                    new_reu=f.reu();_,physical=f.cache();start=physical*65536;cursor=0
                    for a,b in [(start,start+64)]+[(start+0x200+j*0x800,start+0x200+(j+1)*0x800) for j in range(22)]:
                        assert new_reu[cursor:a]==old_reu[cursor:a],('pending uncommitted other REU changed',i,cursor,a);cursor=b
                    assert new_reu[cursor:]==old_reu[cursor:]
                check('pending-bottom-'+str(i),True)
            assert flushes,'fixture must force real pending canonical publication'
            (out/'pending-publications.json').write_text(json.dumps(flushes,indent=2)+'\n')
            f.command(16);data=f.merged();check('pending-undo',True)
        if not smoke and not (io_reveal or io_selection or io_tails or io_pending or inline_case):
            # Pending edit inside a quoted BASIC string after physical column40
            # must still be styled from its canonical logical-line opener.
            p=data.index(geos.native_text('ABcd'))+42;position(p)
            check('cross40-string-caret')
            raw=geos.native_text('Q');f.key(raw[0]);data=data[:p]+raw+data[p:]
            assert f.get('se_hot_pending',1);check('pending-cross40-string')
            f.command(16);data=FIXTURE;assert f.merged()==data;check('undo-pending')
            # Removing the closing quote makes REM part of an unfinished
            # string. It remains editable and source-exact until undo.
            quote=data.index(b'"',data.index(geos.native_text('ABcd')))
            position(quote);f.command(4);data=data[:quote]+data[quote+1:]
            check('unfinished-string-rem')
            f.command(16);data=FIXTURE;assert f.merged()==data;check('undo-unfinished-string')
            canonical=f.canonical()
            for command,mode in ((96,0),(97,1),(98,2),(99,3)):
                f.command(command);f.render()
                assert f.get('se_mode',1)==mode and f.canonical()==canonical and f.merged()==data,('mode source/history preservation',mode)
            check('four-mode-return')
            f.key(0x85);f.key(geos.native_text('f')[0]);check('File-menu');f.key(3)
            f.key(0x8B);check('help');f.key(0x8B);check('popup-restore')
            position(5);preferred=None
            for serial,command in enumerate((37,37,37,37,37,36,39,38)):
                old_top=f.get('se_v_top');old_caret=f.get('se_hot_caret')
                wanted,preferred,target,document_rows=navigation(data,fonts['bsw9-widths.bin'],old_caret,command,preferred)
                _,_,visible,_=body(data,fonts,top=old_top,caret=old_caret)
                wanted_top=old_top if document_rows[target].start in {r.start for r in visible} else document_rows[target].start
                f.command(command)
                assert f.get('se_hot_caret')==wanted,('mixed global semantic navigation target',serial,command,wanted,f.get('se_hot_caret'))
                assert f.get('se_l_preferred')==preferred and f.get('se_n_preferred_valid',1)==2,('proportional preferred X',serial,preferred)
                assert f.get('se_v_top')==wanted_top,('mixed page viewport preservation/reanchor',serial,wanted_top,f.get('se_v_top'))
                assert f.merged()==data and f.catalog()==frozen_catalog,('navigation preserves canonical/catalog',serial)
                check('mixed-nav-'+str(serial))
        result=dict(status='passed',identity=identity,frames=frames,pixels_checked=len(frames)*64000,
            attributes_checked=len(frames)*1000,verification_sha256=source_hashes,
            scope='Actual public editor GEOS blocks/lexer/pending/history/modes/UI withcanonicalmixedfontoracle. '+('Matched inline GGbold/italic/nested/code enabled. ' if inline_case else '')+'CPUonly; no markerhiding/nativeVIC/timingclaim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
    finally:f.close()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model-check',action='store_true')
    ap.add_argument('--run',action='store_true');ap.add_argument('--fixture',type=Path);ap.add_argument('--smoke',action='store_true');ap.add_argument('--io-reveal',action='store_true');ap.add_argument('--io-selection',action='store_true');ap.add_argument('--io-tails',action='store_true');ap.add_argument('--io-pending',action='store_true');ap.add_argument('--inline',action='store_true');args=ap.parse_args()
    if args.model_check:print(json.dumps(model_check(),indent=2));return
    if args.run:
        out=ROOT/'build/geos-semantic-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
        print('RUN '+str(out),flush=True)
        try:run(out,args.fixture,args.smoke,args.io_reveal,args.io_selection,args.io_tails,args.io_pending,args.inline)
        except BaseException as error:
            (out/'failure.json').write_text(json.dumps(dict(error=repr(error)),indent=2)+'\n');raise
        return
    print('Prepared canonical styled GEOS oracle; wait for stable integrated C24/C25 build before actual CPU gate.')


if __name__=='__main__':main()
