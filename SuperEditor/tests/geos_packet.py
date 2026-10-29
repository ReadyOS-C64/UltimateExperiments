"""Read-only GEOS FE-cache decoding and explicit legacy test-view adaptation.

raw_cache() remains authoritative. normalize_legacy() returns a detached Python
byte string, never writes machine RAM/REU, and never changes glyphs or maps. It
only relocates ABI2 arrays into ABI1 offsets for existing <=160-glyph oracles.
ABI3 derives its declared implicit affinities from FIRST+index; it never reads
the obsolete stored arrays. The original version header is retained.
Use decode_row() on RAW packets, not on an already normalized legacy test view.
"""
from dataclasses import dataclass

HEADER_SIZE=64
SLOT_BASE=0x200
SLOT_SIZE=0x800
MAX_LINES=22
VERSION_OFFSET=3


@dataclass(frozen=True)
class Layout:
    version:int
    max_glyphs:int
    chars:int
    styles:int
    roles:int
    x:int
    left:int
    right:int
    used:int


VERSION1=Layout(1,160,32,192,352,512,834,1317,1800)
VERSION2=Layout(2,161,32,194,356,518,842,1328,1814)
VERSION3=Layout(3,161,32,194,356,518,0,0,842)


class LegacyCapacityError(ValueError):
    """An ABI2 row cannot be represented by a160-glyph legacy test oracle."""


def layout(version):
    if version==1:return VERSION1
    if version==2:return VERSION2
    if version==3:return VERSION3
    raise ValueError(('unsupported GEOS cache ABI',version))


def raw_layout(cache):
    if len(cache)<HEADER_SIZE:raise ValueError('truncated GEOS header')
    return layout(cache[VERSION_OFFSET])


def _integer(data,at,size,signed=False):
    return int.from_bytes(data[at:at+size],'little',signed=signed)


def decode_row(packet,version):
    """Exact raw slot arrays; source affinities remain full canonical24bit."""
    offsets=layout(version)
    if len(packet)<offsets.used:raise ValueError('truncated GEOS slot')
    count=_integer(packet,12,2)
    if count>offsets.max_glyphs:raise ValueError(('glyph count exceeds ABI',count,version))
    first=_integer(packet,9,3)
    if version==3 and first+count>0xFFFFFF:raise ValueError('implicit canonical overflow')
    return dict(version=version,count=count,prefix=bytes(packet[:32]),
        start=_integer(packet,0,3),end=_integer(packet,3,3),next=_integer(packet,6,3),
        first=_integer(packet,9,3),height=packet[14],top=packet[15],kind=packet[16],
        reason=packet[17],caret_valid=packet[18],caret_x=_integer(packet,19,2),
        raster_x=_integer(packet,24,2,True),member=packet[26],tail_valid=packet[27],
        tail_x=_integer(packet,28,2,True),
        chars=bytes(packet[offsets.chars:offsets.chars+count]),
        styles=bytes(packet[offsets.styles:offsets.styles+count]),
        roles=bytes(packet[offsets.roles:offsets.roles+count]),
        x=tuple(_integer(packet,offsets.x+i*2,2) for i in range(count+1)),
        left=tuple(first+i if version==3 else _integer(packet,offsets.left+i*3,3) for i in range(count+1)),
        right=tuple(first+i if version==3 else _integer(packet,offsets.right+i*3,3) for i in range(count+1)))


def rows(cache):
    """Decode only published active rows; unused slot bytes are not metadata."""
    offsets=raw_layout(cache)
    count=cache[1]
    if count>MAX_LINES:raise ValueError(('GEOS row count',count))
    if len(cache)<SLOT_BASE+count*SLOT_SIZE:raise ValueError('truncated GEOS bank')
    return tuple(decode_row(cache[SLOT_BASE+i*SLOT_SIZE:SLOT_BASE+(i+1)*SLOT_SIZE],
                            offsets.version) for i in range(count))


def normalize_legacy(cache):
    """Detached ABI1-offset view, only for active rows with count<=160.

    Header VERSION remains unchanged. Prefixes/source anchors/glyph bytes/values
    are copied exactly; ABI3 declared implicit affinities alone are expanded.
    No clipping, glyph substitution or pixel computation occurs. Count161 refuses so a
    legacy oracle cannot accidentally accept a truncated real row. Inactive
    slots remain byte-for-byte raw, as their counts/arrays are not published.
    """
    original=bytes(cache)
    offsets=raw_layout(original)
    if offsets.version==1:return original
    decoded=rows(original)
    for index,row in enumerate(decoded):
        if row['count']>160:
            raise LegacyCapacityError(('use raw_cache for ABI2 count161',index,row['count']))
    result=bytearray(original)
    for i in range(len(decoded)):
        base=SLOT_BASE+i*SLOT_SIZE
        for field,size in [('chars',160),('styles',160),('roles',160),
                           ('x',161*2),('left',161*3),('right',161*3)]:
            target=base+getattr(VERSION1,field)
            if offsets.version==3 and field in ('left','right'):
                values=decoded[i][field];raw=b''.join(v.to_bytes(3,'little')for v in values)
                result[target:target+len(raw)]=raw
            else:
                source=base+getattr(offsets,field)
                result[target:target+size]=original[source:source+size]
    assert result[:HEADER_SIZE]==original[:HEADER_SIZE]
    return bytes(result)


def self_test():
    cache=bytearray((i*73+29)&255 for i in range(65536))
    cache[1]=1;cache[VERSION_OFFSET]=2;slot=SLOT_BASE
    cache[slot+12:slot+14]=(160).to_bytes(2,'little')
    before=bytes(cache);normalized=normalize_legacy(cache)
    assert bytes(cache)==before and normalized[:64]==before[:64] and normalized[3]==2
    old=decode_row(normalized[slot:slot+SLOT_SIZE],1)
    new=decode_row(before[slot:slot+SLOT_SIZE],2)
    for field in ('chars','styles','roles','x','left','right','prefix'):
        assert old[field]==new[field],field
    cache[slot+12:slot+14]=(161).to_bytes(2,'little')
    assert len(decode_row(cache[slot:slot+SLOT_SIZE],2)['chars'])==161
    try:normalize_legacy(cache)
    except LegacyCapacityError:pass
    else:raise AssertionError('161-glyph normalization must refuse')
    cache[3]=1;assert normalize_legacy(cache)==bytes(cache)
    # ABI3 must ignore poisoned legacy arrays, retain 24bit canonical offsets,
    # and refuse arithmetic overflow rather than silently wrapping affinities.
    cache[3]=3
    cache[slot+9:slot+12]=(0x10000).to_bytes(3,'little')
    cache[slot+12:slot+14]=(160).to_bytes(2,'little')
    before=bytes(cache);first=decode_row(before[slot:slot+SLOT_SIZE],3)
    cache[slot+842:slot+1814]=bytes([0xA5])*972
    second=decode_row(cache[slot:slot+SLOT_SIZE],3)
    assert first==second and first['left']==first['right']==tuple(range(0x10000,0x100A1))
    normalized=normalize_legacy(cache)
    legacy=decode_row(normalized[slot:slot+SLOT_SIZE],1)
    for field in ('chars','styles','roles','x','left','right','prefix'):
        assert legacy[field]==second[field],field
    cache[slot+9:slot+12]=(0xFFFFF0).to_bytes(3,'little')
    try:decode_row(cache[slot:slot+SLOT_SIZE],3)
    except ValueError:pass
    else:raise AssertionError('implicit affinity overflow must refuse')
    return dict(status='passed',versions=(1,2,3),pure_read_only=True,refuses161=True,
                implicit_dead_arrays_ignored=True,refuses24bitOverflow=True)


if __name__=='__main__':print(self_test())
