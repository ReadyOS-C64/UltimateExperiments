"""Build a bounded data-only GEOS D81/VLIR bitmap-font inventory.

No font scaling, name substitution, synthetic family, or guessed point size.
The GEOS size is the actual VLIR index and packed info-sector identifier; the
raster height/baseline come from its native eight-byte font header. ASCII32..127
indices are retained, with no implicit PETSCII fallback. Source media unchanged.
"""
from pathlib import Path
import argparse, hashlib, json, re, struct, zlib
from d81_image import D81Image
from fonts import png

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_MEDIA=ROOT.parent.parent/'GEOS20/media'
DEFAULT_BSW=ROOT.parent.parent/'GEOS20/reference/geos/kernal/bswfont/bswfont.s'
MAX_RECORD_BYTES=16384
sha=lambda b:hashlib.sha256(b).hexdigest()


def font(raw):
    if len(raw)<10 or len(raw)>MAX_RECORD_BYTES:raise ValueError('font record length')
    baseline,stride,height,index,bits=struct.unpack('<BHBHH',raw[:8])
    if not (1<=height<=64 and baseline<height and 1<=stride<=512 and index==8 and 10<=bits<=520 and (bits-index)%2==0):raise ValueError('font header geometry')
    if len(raw)!=bits+stride*height:raise ValueError('font raster extent')
    offsets=[int.from_bytes(raw[i:i+2],'little') for i in range(index,bits,2)]
    if not (2<=len(offsets)<=257 and offsets[0]==0 and offsets[-1]<=stride*8 and all(a<=b for a,b in zip(offsets,offsets[1:]))):raise ValueError('font index ordering/range')
    widths=[b-a for a,b in zip(offsets,offsets[1:])]
    if max(widths)>255:raise ValueError('font glyph width')
    return dict(baseline=baseline,height=height,stride=stride,index_offset=index,bitmap_offset=bits,
                first_character=32,glyphs=len(widths),minimum_advance=min(widths),maximum_advance=max(widths),
                raw_bytes=len(raw),raw_header_hex=raw[:8].hex(),width_bytes=len(widths),
                monospace=len(set(widths))==1,monospace_advance=widths[0] if len(set(widths))==1 else None,
                raw_row_plane_bytes=(max(widths)+7)//8,
                maximum_GG_bold_italic_width=max(widths)+3,
                maximum_GG_bold_italic_row_plane_bytes=(max(widths)+3+7)//8,
                underline_row=baseline+1,underline_within_native_height=baseline+1<height,
                widths=widths,offsets=offsets)


def chain(disk,position):
    result=bytearray();visited=set()
    while position[0]:
        if position in visited or len(visited)>=3200:raise ValueError('cyclic/oversize font chain')
        visited.add(position);block=disk.sector(*position)
        count=254 if block[0] else block[1]-1
        if not 0<=count<=254:raise ValueError('invalid terminal sector')
        if len(result)+count>MAX_RECORD_BYTES:raise ValueError('font exceeds bounded record budget')
        result+=block[2:2+count];position=tuple(block[:2])
    return bytes(result),sorted(visited)


def atlas(path,raw,meta):
    cell_w=max(meta['maximum_advance']+4,12);cell_h=meta['height']+5
    width=16*cell_w;height=((meta['glyphs']+15)//16)*cell_h
    pixels=bytearray([20])*(width*height)
    for c,(a,b) in enumerate(zip(meta['offsets'],meta['offsets'][1:])):
        ox=(c%16)*cell_w+2;oy=(c//16)*cell_h+2
        for y in range(meta['height']):
            for x in range(b-a):
                bit=a+x
                if raw[meta['bitmap_offset']+y*meta['stride']+bit//8]&(128>>(bit%8)):pixels[(oy+y)*width+ox+x]=240
        # Baseline witness outside the glyph; no alteration to extracted ink.
        pixels[(oy+meta['baseline'])*width+ox-1]=100
    png(path,width,height,pixels)
    return dict(width=width,height=height,columns=16,first_character=32,cell_width=cell_w,cell_height=cell_h)


def media_fonts(path):
    data=path.read_bytes();disk=D81Image(data)
    for entry in disk.entries():
        if entry.raw[24]!=8:continue # GEOS FONT, not DOS kind.
        if not entry.closed or entry.raw[23]!=1:raise ValueError('FONT must be closed VLIR')
        info=disk.sector(*entry.raw[21:23]);family=int.from_bytes(info[128:130],'little')
        identifiers=[int.from_bytes(info[i:i+2],'little') for i in range(130,190,2)]
        identifiers=identifiers[:next((i for i,v in enumerate(identifiers) if not v),len(identifiers))]
        if not identifiers or any(v>>6!=family for v in identifiers):raise ValueError('font family identifier mismatch')
        sizes={v&63 for v in identifiers};index=disk.sector(*entry.first);found=set()
        for size in range(127):
            pos=tuple(index[2+2*size:4+2*size])
            if not pos[0]:
                if pos[1] not in (0,255):raise ValueError('invalid absent VLIR record')
                continue
            if size not in sizes:raise ValueError('VLIR size not certified by info header')
            found.add(size);raw,sectors=chain(disk,pos);meta=font(raw)
            yield dict(family=entry.name.decode('ascii'),native_family_id=family,point_size=size,
                       namespace='GEOS-font-file',metrics=meta,raw=raw,
                       source=dict(path=str(path.resolve()),sha256=sha(data),file_name_hex=entry.name.hex(),
                                   info_sector=list(entry.raw[21:23]),record=size,sectors=sectors))
        if found!=sizes:raise ValueError('missing declared font size')


def bsw_font(path):
    text=path.read_text();assert text.count('\n.else\n')==1
    branch=text.split('\n.else\n')[1].split('\n.endif')[0]
    raw=bytes(int(v,16) for line in branch.splitlines() if line.lstrip().startswith('.byte') for v in re.findall(r'\$([0-9a-fA-F]{2})',line))
    return dict(family='BSW',native_family_id=None,point_size=9,namespace='GEOS-system-source',metrics=font(raw),raw=raw,
                source=dict(path=str(path.resolve()),sha256=sha(path.read_bytes()),branch='original English .else'))


def build(media,out,bsw):
    out.mkdir(parents=True,exist_ok=True);unique={};source_hashes={str(p.resolve()):sha(p.read_bytes()) for p in media+[bsw]}
    for item in [x for p in media for x in media_fonts(p)]+[bsw_font(bsw)]:
        raw=item.pop('raw');source=item.pop('source');key=(item['namespace'],item['native_family_id'],item['point_size'],sha(raw))
        if key in unique:unique[key]['sources'].append(source);continue
        slug=re.sub('[^a-z0-9]+','-',item['family'].lower())+'-'+str(item['point_size'])
        base=out/slug;base.mkdir(exist_ok=True);(base/'font.bin').write_bytes(raw)
        widths=bytes(item['metrics']['widths']);(base/'advances.bin').write_bytes(widths)
        geometry=atlas(base/'atlas.png',raw,item['metrics'])
        item.update(raw_sha256=sha(raw),advance_sha256=sha(widths),sources=[source],files={n:str((base/n).relative_to(out)) for n in ('font.bin','advances.bin','atlas.png')},atlas=geometry)
        # Variable-width indexes are the native representation, not a synthetic16px glyph expansion.
        item['metrics'].pop('offsets');item['metrics'].pop('widths');unique[key]=item
    for p in media+[bsw]:assert sha(p.read_bytes())==source_hashes[str(p.resolve())],'source media modified'
    faces=list(unique.values());result=dict(schema=1,faces=faces,face_count=len(faces),font_file_faces=sum(x['namespace']=='GEOS-font-file' for x in faces),raw_bytes=sum(x['metrics']['raw_bytes'] for x in faces),source_sha256=source_hashes,
        scope='Genuine GEOS bitmap-font records; native point IDs and raster metrics. No scaling, substitution, executable font software or original disk filesystem.')
    # One immutable logical-data pack; no per-font SEO/catalog slot. The index
    # is16B/face; callers must split logical REU transfers at64KiB boundaries.
    table=bytearray();payload=bytearray();base=32+16*len(faces)
    for f in faces:
        m=f['metrics'];offset=base+len(payload);raw=(out/f['files']['font.bin']).read_bytes()
        entry=bytes([1 if f['namespace']=='GEOS-font-file' else 2])+(f['native_family_id'] if f['native_family_id'] is not None else 65535).to_bytes(2,'little')+bytes([f['point_size'],m['baseline'],m['height']])+m['stride'].to_bytes(2,'little')+offset.to_bytes(3,'little')+len(raw).to_bytes(2,'little')+bytes([m['glyphs'],m['first_character'],m['maximum_advance']])
        assert len(entry)==16;table+=entry;payload+=raw
    header=b'GFC1'+bytes([1,len(faces),16,0])+(32).to_bytes(2,'little')+base.to_bytes(3,'little')+(base+len(payload)).to_bytes(3,'little')+bytes(16)
    assert len(header)==32
    pack=header+table+payload;(out/'font-pack.bin').write_bytes(pack)
    result['pack']=dict(path='font-pack.bin',sha256=sha(pack),bytes=len(pack),index_bytes=base,logical_64KiB_banks=(len(pack)+65535)//65536,format='GFC1 header32 + ordered16Bentries + exactnativefontrecords; namespace1GEOSfile/2systemsource; systemfamilyFFFF')
    (out/'catalog.json').write_text(json.dumps(result,indent=2)+'\n');return result


def self_test(result,out):
    assert result['font_file_faces']==42 and result['face_count']==43
    pack=(out/result['pack']['path']).read_bytes()
    assert len(pack)==result['pack']['bytes'] and sha(pack)==result['pack']['sha256']
    for i,f in enumerate(result['faces']):
        entry=pack[32+i*16:48+i*16];offset=int.from_bytes(entry[8:11],'little');size=int.from_bytes(entry[11:13],'little')
        assert pack[offset:offset+size]==(out/f['files']['font.bin']).read_bytes()
    sizes={}
    for f in result['faces']:
        raw=(out/f['files']['font.bin']).read_bytes();m=font(raw)
        assert sha(raw)==f['raw_sha256'] and m['raw_bytes']==len(raw)
        # Independent pixel reconstruction directly from original bit columns.
        reconstructed=[]
        for a,b in zip(m['offsets'],m['offsets'][1:]):
            for y in range(m['height']):reconstructed.extend((raw[m['bitmap_offset']+y*m['stride']+x//8]>>(7-x%8))&1 for x in range(a,b))
        assert len(reconstructed)==m['height']*sum(m['widths'])
        # Decode the generated PNG independently and compare every pixel to a
        # second source-bit model (including untouched atlas gutters).
        png_data=(out/f['files']['atlas.png']).read_bytes();at=8;compressed=bytearray()
        while at<len(png_data):
            length=int.from_bytes(png_data[at:at+4],'big');kind=png_data[at+4:at+8];payload=png_data[at+8:at+8+length]
            if kind==b'IDAT':compressed+=payload
            at+=12+length
        a=f['atlas'];decoded=zlib.decompress(compressed);expected=bytearray([20])*(a['width']*a['height'])
        for c,(left,right) in enumerate(zip(m['offsets'],m['offsets'][1:])):
            ox=c%16*a['cell_width']+2;oy=c//16*a['cell_height']+2
            for y in range(m['height']):
                row=int.from_bytes(raw[m['bitmap_offset']+y*m['stride']:m['bitmap_offset']+(y+1)*m['stride']],'big')
                for x in range(right-left):
                    if row&(1<<(m['stride']*8-1-left-x)):expected[(oy+y)*a['width']+ox+x]=240
            expected[(oy+m['baseline'])*a['width']+ox-1]=100
        assert decoded==b''.join(b'\0'+expected[y*a['width']:(y+1)*a['width']] for y in range(a['height']))
        for altered in (raw[:7],raw+b'\0',bytes([255])+raw[1:],raw[:8]+b'\xff\xff'+raw[10:]):
            try:font(altered)
            except ValueError:pass
            else:raise AssertionError('malformed font accepted')
        sizes.setdefault(f['family'],[]).append(f['point_size'])
    bsw=next(f for f in result['faces'] if f['family']=='BSW');assert (out/bsw['files']['font.bin']).read_bytes()==(ROOT/'assets/fonts/generated/bsw9-original.bin').read_bytes()
    # Synthetic malformed chain is refused within its first repeated sector.
    class Cyclic:
        def sector(self,*position):return bytes([1,0])+bytes(254)
    try:chain(Cyclic(),(1,0))
    except ValueError:pass
    else:raise AssertionError('cyclic VLIR chain accepted')
    result=dict(status='passed',atlas_pixels_checked=sum(f['atlas']['width']*f['atlas']['height'] for f in result['faces']),cyclic_chain_refused=True,faces=result['face_count'],font_file_faces=42,malformed_header_refusals=4*result['face_count'],families=sizes,source_immutable=True,existing_BSW9_byteidentical=True)
    (out/'proof.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--media',action='append',type=Path);p.add_argument('--bsw-source',type=Path,default=DEFAULT_BSW);p.add_argument('--out',type=Path,default=ROOT/'build/geos-font-catalog');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    media=a.media or [DEFAULT_MEDIA/'geos20-original.d81',DEFAULT_MEDIA/'geos-system.d81']
    result=build(media,a.out,a.bsw_source)
    if a.self_test:print(json.dumps(self_test(result,a.out),indent=2))
    else:print(json.dumps(dict(face_count=result['face_count'],raw_bytes=result['raw_bytes'],catalog=str(a.out/'catalog.json')),indent=2))

if __name__=='__main__':main()
