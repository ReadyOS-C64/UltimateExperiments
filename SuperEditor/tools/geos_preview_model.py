"""Independent canonical-source/font-bit oracle for read-only GEOS preview.

No emitted C24/C26 class, glyph frame, row/X map, bitmap or attributes choose the
expected result. Source events use the independent SuperMark host grammar. The
font decoder reads native packed bits; it does not call the executable raster.
Body-only output is full8000/1000 bytes; optional independent logical chrome
covers physical rows0,1,24. This model does not enable editable rendered source.
"""
from dataclasses import dataclass,replace
from pathlib import Path
import hashlib,json,struct
from supermark_model import blocks,inline,lex

ROOT=Path(__file__).resolve().parents[1]
PALETTE=(1,3,7,10,14,1,1,7,13,5,15,7,3,1)
HEADER=b'SEST'+bytes((1,64,8,7))


@dataclass(frozen=True)
class Profile:
    origin:int
    family:int
    point:int
    foreground:int
    background:int
    styles:int


def profiles(settings):
    settings=bytes(settings)
    if len(settings)!=64 or settings[:8]!=HEADER:raise ValueError('settings64 header')
    result=[]
    for p in range(8,64,7):
        origin,lo,hi,point,fg,bg,style=settings[p:p+7]
        if origin>1 or not point or fg>15 or bg>15 or style>7:raise ValueError('settings profile')
        result.append(Profile(origin,lo+256*hi,point,fg,bg,style))
    return tuple(result)


def screen(value):
    if value<32 or 128<=value<160:return 63
    if value<64:return value
    if value<96:return value-64
    if value<128:return value-96+64
    if 192<=value<224:return value-192+64
    if value==255:return 94
    return (value&63)|96


def ascii_for_screen(code):
    if code==0:return 64
    if 1<=code<=26:return code+96
    if code in (27,29):return code+64
    if 32<=code<=63 or 65<=code<=90:return code
    return None


@dataclass(frozen=True)
class Glyph:
    width:int
    advance:int
    baseline:int
    height:int
    rows:tuple


class Face:
    def __init__(self,raw=None,*,native=None):
        self.native=native
        if raw is None:
            self.raw=None;self.baseline=6;self.height=8;self.stride=0;self.offsets=()
        else:
            raw=bytes(raw)
            if len(raw)<8:raise ValueError('font header')
            baseline,stride,height,index,bits=struct.unpack('<BHBHH',raw[:8])
            if not (1<=height<=24 and baseline<height and index==8 and bits in (202,204) and stride>0 and len(raw)==bits+stride*height):raise ValueError('font geometry')
            offsets=struct.unpack('<'+str((bits-index)//2)+'H',raw[index:bits])
            if offsets[0] or any(a>b for a,b in zip(offsets,offsets[1:])) or offsets[-1]>stride*8:raise ValueError('font offsets')
            self.raw=raw;self.baseline=baseline;self.height=height;self.stride=stride;self.bits=bits;self.offsets=offsets
        if native is None or len(native)!=1024:raise ValueError('explicit128x8 fallback required')

    def glyph(self,value,style=0,*,fixed=False):
        code=screen(value);char=ascii_for_screen(code)
        packed=self.raw is not None and char is not None
        if packed:
            a,b=self.offsets[char-32:char-30];width=b-a
        else:a=0;width=8
        if width>24 or style>7:raise ValueError('font glyph/style range')
        advance=width+(style&1)+(style&2)
        if self.raw is None or fixed:advance=width
        # LSB is rightmost local cell pixel; rows are not limited to16bits.
        rows=[]
        for y in range(self.height):
            if packed:
                row=0
                for x in range(width):
                    bit=a+x
                    if self.raw[self.bits+y*self.stride+bit//8]&(128>>(bit%8)):row|=1<<(31-x)
            else:row=(self.native[code*8+y]<<24) if y<8 else 0
            if style&1:row|=row>>1
            if style&2:row>>=2 if 3*y<self.height else 1 if 3*y<2*self.height else 0
            if style&4 and y==self.baseline+1:row=((1<<advance)-1)<<(32-advance)
            row&=(((1<<advance)-1)<<(32-advance)) if advance else 0
            rows.append(row)
        return Glyph(width,advance,self.baseline,self.height,tuple(rows))


class FontCatalog:
    def __init__(self,path=None,*,native=None):
        path=Path(path or ROOT/'build/geos-font-catalog/catalog.json')
        native=bytes(native) if native is not None else (ROOT/'assets/fonts/generated/native8.bin').read_bytes()
        self.native=native;self.faces={(0,1,8):Face(native=native)}
        manifest=json.loads(path.read_text())
        for item in manifest['faces']:
            data=(path.parent/item['files']['font.bin']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=item['raw_sha256']:raise ValueError('font hash')
            if item['namespace']=='GEOS-system-source':key=(0,0,item['point_size'])
            elif item['namespace']=='GEOS-font-file':key=(1,item['native_family_id'],item['point_size'])
            else:raise ValueError('font namespace')
            if key in self.faces:raise ValueError('duplicate font identity')
            self.faces[key]=Face(data,native=native)
    def get(self,profile):
        try:return self.faces[profile.origin,profile.family,profile.point]
        except KeyError as e:raise ValueError('unavailable genuine font') from e


@dataclass(frozen=True)
class PreviewRow:
    start:int
    end:int
    next:int
    top:int
    height:int
    baseline:int
    profile:int
    glyph_sources:tuple


@dataclass(frozen=True)
class Preview:
    bitmap:bytes
    attrs:bytes
    bottom:int
    anchors:tuple
    rows:tuple


def _events(data):
    events=list(blocks(data))
    if not data or data[-1]==13:
        last=events[-1] if events else {}
        events.append(dict(kind=5 if last.get('fence') else 1,start=len(data),end=len(data),body=len(data),level=0,language=last.get('language',0),fence=last.get('fence',0)))
    return events


def _inline(data,event):
    a,b,body=(event[k] for k in ('start','end','body'))
    hidden=set();styles={};roles={};exclusive=set()
    if event['kind']==5:
        for start,end,role in lex(data[a:b],event['language'],start=a):
            for at in range(start,end):roles[at]=role
        return hidden,styles,roles
    if event['kind'] not in (0,1,2,3,7):return hidden,styles,roles
    for token,kind,width,opened,closed in inline(data[body:b],body,body_column=(body-a) or None):
        if token==2:hidden.add(opened);continue
        if token!=1:raise ValueError('host inline event')
        hidden.update(range(opened,opened+width));hidden.update(range(closed,closed+width))
        if kind==4:
            exclusive.update(range(opened+width,closed))
        else:
            gg=(1 if kind&2 else 0)|(2 if kind&1 else 0)
            for at in range(opened+width,closed):styles[at]=styles.get(at,0)|gg
    for at in exclusive:styles[at]=0;roles[at]=4
    return hidden,styles,roles


def with_chrome(bitmap,attrs,matrix,colors,native):
    """Paint only shared40-column header/rule/status from independent UI cells."""
    if len(bitmap)!=8000 or len(attrs)!=1000 or len(matrix)!=1000 or len(colors)!=1000 or len(native)!=1024:raise ValueError('chrome extent')
    bits=bytearray(bitmap);attributes=bytearray(attrs)
    for row in (0,1,24):
        for col in range(40):
            index=row*40+col;value=matrix[index];glyph=native[(value&127)*8:(value&127)*8+8]
            bits[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if value&128 else 0) for v in glyph)
            attributes[index]=(colors[index]&15)*16+6
    return bytes(bits),bytes(attributes)


def render(data,settings,*,catalog=None,native=None,top=0,keep_list_prefix=True,chrome=None):
    """Character-wrap320, aligned bands16..192, exact canonical bottom/anchors.

    Heading/region title prefixes and closed inline markers disappear. List
    hyphen/number prefixes remain by default; False characterizes the historical
    initial preview. Fence open/close and region close consume source but no band.
    Conservative inline-capable line height reserves CODE metrics when the raw
    logical line contains'*' or'@', including escaped or unmatched occurrences.
    Foreground is first ink per8x8 tile; background is the entire block band.
    """
    data=bytes(data)
    if len(data)>0x100000 or not 0<=top<=len(data):raise ValueError('canonical source/top range')
    ps=profiles(settings)
    fonts=catalog if isinstance(catalog,FontCatalog) else FontCatalog(catalog,native=native)
    for profile in ps:fonts.get(profile)
    bitmap=bytearray(8000);attrs=bytearray([0x16])*1000;rows=[];position=top;y=16
    full=False
    def start_row(anchor,height,baseline,pindex):
        if len(rows)>=22 or y+height>192:return False
        rows.append(dict(start=anchor,end=anchor,next=anchor,top=y,height=height,baseline=baseline,profile=pindex,glyph_sources=[]))
        base=ps[pindex]
        for tr in range(y//8,(y+height)//8):attrs[tr*40:(tr+1)*40]=bytes([base.foreground*16+base.background])*40
        return True
    for event in _events(data):
        a,b,kind,body=(event[k] for k in ('start','end','kind','body'))
        if b<position:continue
        if kind in (4,6,8):
            position=b+int(b<len(data) and data[b]==13)
            if position==len(data) and b==len(data):break
            continue
        pindex=7 if kind==5 else event['level'] if kind==2 else 0
        base=ps[pindex];baseface=fonts.get(base);baseline=baseface.baseline;descent=baseface.height-baseface.baseline
        if any(v in (42,64) for v in data[a:b]):
            cf=fonts.get(ps[7]);baseline=max(baseline,cf.baseline);descent=max(descent,cf.height-cf.baseline)
        height=(baseline+descent+7)//8*8
        if not start_row(position,height,baseline,pindex):full=True;break
        x=0;claimed=set();hidden,styles,roles=_inline(data,event)
        if kind==3 and keep_list_prefix:visible_start=position
        else:visible_start=max(position,body)
        position=visible_start
        for at in range(visible_start,b):
            if at in hidden:position=at+1;continue
            role=roles.get(at,4 if kind==5 else 0);selected=7 if role==4 else pindex
            profile=ps[selected];face=fonts.get(profile)
            glyph=face.glyph(data[at],profile.styles|styles.get(at,0),fixed=(kind==5 or role==4))
            if x+glyph.advance>320:
                rows[-1]['end']=at;position=at;y+=height
                if not start_row(at,height,baseline,pindex):full=True;break
                x=0;claimed=set()
            fg=PALETTE[role] if 7<=role<=13 else profile.foreground
            gy=y+baseline-glyph.baseline
            for sy,word in enumerate(glyph.rows):
                py=gy+sy
                for sx in range(glyph.advance):
                    if not word&(1<<(31-sx)):continue
                    px=x+sx;tile=(py//8)*40+px//8
                    if not (0<=px<320 and 16<=py<192):raise ValueError('glyph escaped certified band')
                    bitmap[(py//8)*320+(px//8)*8+py%8]|=128>>(px%8)
                    if tile not in claimed:attrs[tile]=fg*16+base.background;claimed.add(tile)
            x+=glyph.advance;position=at+1;rows[-1]['glyph_sources'].append(at)
        if full:break
        position=b
        rows[-1]['end']=b
        if b==len(data):break
        position=b+1;y+=height
    for i,row in enumerate(rows):row['next']=rows[i+1]['start'] if i+1<len(rows) else position
    frozen=tuple(PreviewRow(**{**row,'glyph_sources':tuple(row['glyph_sources'])}) for row in rows)
    if chrome is not None:bitmap,attrs=with_chrome(bitmap,attrs,*chrome)
    return Preview(bytes(bitmap),bytes(attrs),position,tuple(row.start for row in frozen),frozen)
