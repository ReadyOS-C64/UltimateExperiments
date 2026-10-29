"""Independent canonical GEOS fold projection and literal-source pixel model.

No emitted editor row, source map, or fold record is consulted to choose pixels.
Callers supply host-derived fold intervals (start/hidden/end/flags). Full source
semantics are classified before projection, so a hidden closing fence still
determines the language of later visible source. Preview is a separate contract.
"""
from dataclasses import dataclass
from supermark_model import blocks, inline, lex

PALETTE=(1,3,7,10,14,1,1,7,13,5,15,7,3,1)
PRIORITY=(0,6,7,8,0,0,0,5,3,4,1,5,2,0)


def native(v):
    if v<32 or 128<=v<160:return 63
    if v<64:return v
    if v<96:return v&63
    if v<128:return (v&31)|64
    if 192<=v<224:return (v&63)|64
    if v==255:return 94
    return (v&63)|96


def classify(data):
    """Whole-source literal styles; deliberately keeps controls source-visible."""
    n=len(data);styles=bytearray(n);roles=bytearray(n);reverse=bytearray(n);code=bytearray(n)
    events=tuple(blocks(data))
    for e in events:
        a,b,k=e['start'],e['end'],e['kind'];stop=b+int(b<n and data[b]==13)
        role=2 if k==2 else 1 if k==3 else 4 if k in (4,5,6) else 0
        roles[a:stop]=bytes([role])*(stop-a)
        reverse[a:stop]=bytes([int(k==2)])*(stop-a)
        code[a:stop]=bytes([int(k==5)])*(stop-a)
        if k in (0,1,2,3):
            exclusive=set()
            for token,style,width,opened,closed in inline(data[e['body']:b],e['body'],body_column=(e['body']-a) or None):
                if token!=1:continue
                if style==4:exclusive.update(range(opened+width,closed))
                else:
                    gg=int(bool(style&2))|2*int(bool(style&1))
                    for at in range(opened+width,closed):styles[at]|=gg
            for at in exclusive:styles[at]=0;roles[at]=4
        if k==5:
            for start,end,role in lex(data[a:b],e['language'],start=a):roles[start:end]=bytes([role])*(end-start)
    return bytes(styles),bytes(roles),bytes(reverse),bytes(code)


def collapsed(data,folds):
    """Outermost active intervals, rejecting malformed/crossing host input."""
    active=[]
    for f in sorted((f for f in folds if f.flags&1),key=lambda f:(f.start,-f.end)):
        assert 0<=f.start<f.hidden<f.end<=len(data),("fold bounds",f)
        assert data[f.hidden-1]==13,("summary requires actual opener CR",f)
        if active and f.start<active[-1].end:
            assert active[-1].hidden<=f.start and f.end<=active[-1].end,("crossing folds",f)
            continue
        active.append(f)
    return tuple(active)


def normalize_top(data,folds,top):
    assert 0<=top<=len(data)
    return next((f.start for f in collapsed(data,folds) if f.hidden<=top<f.end),top)


def selected_summary(anchor,caret,cr,after):
    if anchor is None or caret is None:return False
    lo,hi=sorted((anchor,caret))
    return lo<hi and lo<after and cr<hi


@dataclass(frozen=True)
class Row:
    start:int
    end:int
    next:int
    top:int
    height:int
    reason:int
    marker:bool=False


def _line(data,advances,start,nowrap):
    at=start;x=0;space=None
    while at<len(data):
        if data[at]==13:return at,at+1,1
        width=advances[at]
        if not nowrap and x+width>320:
            if at==start:return at+1,at+1,6
            if space is not None:return space,space,4
            return at,at,5
        x+=width;at+=1
        if data[at-1]==32:space=at
        if not nowrap and x==320:return at,at,3
    return at,at,2


def rows(data,fonts,folds,*,top=0,nowrap=False,all_rows=False):
    styles,roles,reverse,code=classify(data);widths=fonts['bsw9-widths.bin']
    advances=[8 if code[i] else widths[native(v)]+(styles[i]&1)+(styles[i]&2) for i,v in enumerate(data)]
    summaries={f.hidden-1:f for f in collapsed(data,folds)}
    at=normalize_top(data,folds,top);y=16;result=[]
    while all_rows or (y<192 and len(result)<22):
        mono=bool(code[at]) if at<len(data) else False
        if mono:y=(y+7)&~7
        if not all_rows and y>=192:break
        end,nxt,reason=_line(data,advances,at,nowrap)
        marker=reason==1 and end in summaries
        if marker:nxt=summaries[end].end
        result.append(Row(at,end,nxt,y,8 if mono else 9,reason,marker))
        if reason==2:break
        assert nxt>at,(at,end,nxt,reason)
        at=nxt;y+=8 if mono else 9
    return tuple(result),(styles,roles,reverse,code)


def navigation(data,fonts,folds,caret,command,preferred=None):
    """Projected canonical globalY navigation; no fixed-character heuristics."""
    lines,semantic=rows(data,fonts,folds,all_rows=True)
    styles,_,_,code=semantic;widths=fonts['bsw9-widths.bin']
    def advance(at):return 8 if code[at] else widths[native(data[at])]+(styles[at]&1)+(styles[at]&2)
    index=next(i for i,r in enumerate(lines) if r.start<=caret<r.end or (caret==r.end and r.reason in (1,2)))
    current=lines[index]
    if preferred is None:preferred=sum(advance(at) for at in range(current.start,caret))
    if command in (36,37):target=max(0,min(len(lines)-1,index+(-1 if command==36 else 1)))
    elif command==39:target=next((i for i in range(index+1,len(lines)) if lines[i].top>=current.top+171),len(lines)-1)
    elif command==38:target=next((i for i in range(index-1,-1,-1) if lines[i].top<=current.top-171),0)
    else:raise ValueError('vertical command')
    row=lines[target];positions=[0]
    for at in range(row.start,row.end):positions.append(positions[-1]+advance(at))
    picked=min(range(len(positions)),key=lambda i:(abs(positions[i]-preferred),-i))
    result=row.start+picked
    if result==row.end and row.reason not in (1,2):result=max(row.start,row.end-1)
    return result,preferred,target,lines


def raster(data,fonts,folds,*,top=0,caret=None,anchor=None,nowrap=False,pan=0):
    """320x200 bitmap +40x25 attrs; plus inverse precedes selection/caret union."""
    lines,semantic=rows(data,fonts,folds,top=top,nowrap=nowrap)
    styles,roles,reverse,code=semantic
    font=fonts['bsw9.bin'];widths=fonts['bsw9-widths.bin'];mono=fonts['native8.bin']
    pixels=bytearray(8000);attrs=bytearray([0x16])*1000
    weights=[[[0]*14 for _ in range(40)] for _ in range(25)]
    lo,hi=sorted((caret,anchor)) if caret is not None and anchor is not None else (0,0)
    def draw(value,style,role,inverse,selected,x,y,height):
        sc=native(value);advance=8 if height==8 else widths[sc]+(style&1)+(style&2)
        mask=((1<<advance)-1)<<(16-advance)
        for gy in range(height):
            sy=y+gy
            if not 16<=sy<192:continue
            word=mono[sc*8+gy]<<8 if height==8 else int.from_bytes(font[sc*18+gy*2:sc*18+gy*2+2],'big')
            if height!=8:
                if style&1:word|=word>>1
                if style&2:word>>=2 if gy<3 else 1 if gy<6 else 0
            if inverse:word^=mask
            for gx in range(advance):
                px=x+gx
                if not 0<=px<320:continue
                ink=bool(word&(1<<(15-gx)));tile=px//8;row=sy//8
                weights[row][tile][role]=min(255,weights[row][tile][role]+ink)
                if ink^selected:pixels[row*320+tile*8+sy%8]|=128>>(px&7)
        return advance
    for row in lines:
        x=-(pan if nowrap else 0)
        for at in range(row.start,row.end):
            x+=draw(data[at],styles[at],roles[at],reverse[at],lo<=at<hi or at==caret,x,row.top,row.height)
        if row.marker:
            draw(43,0,2,True,selected_summary(anchor,caret,row.end,row.next) or caret==row.end,x,row.top,row.height)
        elif row.reason in (1,2) and (row.end==caret or lo<=row.end<hi):
            draw(32,0,0,False,True,x,row.top,row.height)
    for row in range(2,24):
        for tile,votes in enumerate(weights[row]):
            role=max(range(14),key=lambda r:(votes[r],PRIORITY[r] if votes[r] else 0,-r))
            attrs[row*40+tile]=(PALETTE[role]<<4)|6
    # Aligned native cells explicitly publish their semantic FG even for blanks.
    for row in lines:
        if row.height!=8 or (pan if nowrap else 0)%8:continue
        for at in range(row.start,row.end):
            x=(at-row.start)*8-(pan if nowrap else 0)
            if 0<=x<320:attrs[(row.top//8)*40+x//8]=(PALETTE[roles[at]]<<4)|6
    return bytes(pixels),bytes(attrs),lines,semantic


def preview(data,settings,folds,*,catalog=None,native=None,top=0):
    """Read-only variable-font preview with canonical fold skips.

    Headings/regions retain formatted titles; collapsed fence-open source is
    literal so it still names the hidden code block. The inverse plus uses the
    containing base profile, style0/yellow7. A collapsed fence uses the CODE
    profile for both literal opener and plus. Preview has no editing selection.
    """
    from geos_preview_model import profiles,FontCatalog,Preview,PreviewRow,_events,_inline
    data=bytes(data);ps=profiles(settings)
    fonts=catalog if isinstance(catalog,FontCatalog) else FontCatalog(catalog,native=native)
    active=collapsed(data,folds);summaries={f.hidden-1:f for f in active}
    position=normalize_top(data,active,top);y=16;result=[]
    bitmap=bytearray(8000);attrs=bytearray([0x16])*1000;full=False
    def start(anchor,height,baseline,pindex):
        if len(result)>=22 or y+height>192:return False
        result.append(dict(start=anchor,end=anchor,next=anchor,top=y,height=height,
            baseline=baseline,profile=pindex,glyph_sources=[]))
        base=ps[pindex]
        for tr in range(y//8,(y+height)//8):attrs[tr*40:(tr+1)*40]=bytes([base.foreground*16+base.background])*40
        return True
    for event in _events(data):
        a,b,k,body=(event[n] for n in ('start','end','kind','body'))
        if b<position or any(f.hidden<=a<f.end for f in active):continue
        summary=summaries.get(b)
        if k in (4,6,8) and not summary:
            position=b+int(b<len(data) and data[b]==13)
            continue
        pindex=7 if k==5 or (k==4 and summary) else event['level'] if k==2 else 0
        base=ps[pindex];face=fonts.get(base);baseline=face.baseline;descent=face.height-face.baseline
        if any(v in (42,64) for v in data[a:b]):
            cf=fonts.get(ps[7]);baseline=max(baseline,cf.baseline);descent=max(descent,cf.height-cf.baseline)
        height=(baseline+descent+7)//8*8
        if not start(position,height,baseline,pindex):break
        x=0;claimed=set();hidden,styles,roles=_inline(data,event)
        visible=max(position,a if k==3 or (k==4 and summary) else body)
        position=visible
        # A source=-1 item is a virtual marker, never a fake canonical byte.
        glyphs=[(at,data[at],False) for at in range(visible,b) if at not in hidden]
        if summary:glyphs.append((-1,43,True))
        for at,value,inverse in glyphs:
            role=roles.get(at,4 if k==5 or (k==4 and summary) else 0);selected=7 if role==4 else pindex
            profile=ps[selected] if not inverse else base
            glyph=fonts.get(profile).glyph(value,0 if inverse else profile.styles|styles.get(at,0),fixed=(k==5 or role==4))
            anchor=b if inverse else at
            if x+glyph.advance>320:
                result[-1]['end']=anchor;position=anchor;y+=height
                if not start(anchor,height,baseline,pindex):full=True;break
                x=0;claimed=set()
            fg=7 if inverse else PALETTE[role] if 7<=role<=13 else profile.foreground
            gy=y+baseline-glyph.baseline
            mask=((1<<glyph.advance)-1)<<(32-glyph.advance) if glyph.advance else 0
            for sy,raw in enumerate(glyph.rows):
                word=raw^mask if inverse else raw;py=gy+sy
                for sx in range(glyph.advance):
                    if not word&(1<<(31-sx)):continue
                    px=x+sx;tile=(py//8)*40+px//8
                    assert 0<=px<320 and 16<=py<192
                    bitmap[(py//8)*320+(px//8)*8+py%8]|=128>>(px%8)
                    if tile not in claimed:attrs[tile]=fg*16+base.background;claimed.add(tile)
            x+=glyph.advance;position=b if inverse else at+1
            if not inverse:result[-1]['glyph_sources'].append(at)
        if full:break
        result[-1]['end']=b
        position=summary.end if summary else b+int(b<len(data) and data[b]==13)
        # A hidden suffix ending at EOF has no following preview event. Do
        # not synthesize an editable-source EOF caret band in read-only view.
        if b==len(data) or (summary and position==len(data)):break
        y+=height
    for i,row in enumerate(result):row['next']=result[i+1]['start'] if i+1<len(result) else position
    final=tuple(PreviewRow(**{**r,'glyph_sources':tuple(r['glyph_sources'])}) for r in result)
    return Preview(bytes(bitmap),bytes(attrs),position,tuple(r.start for r in final),final)
