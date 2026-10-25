"""Read native VICE PNG pixels for assertions, without an imaging dependency."""
import struct
import zlib


def read_png(path):
    data=path.read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    cursor=8
    compressed=bytearray()
    palette=None
    while cursor<len(data):
        size=struct.unpack_from('>I',data,cursor)[0]
        kind=data[cursor+4:cursor+8]
        body=data[cursor+8:cursor+8+size]
        assert zlib.crc32(kind+body)==struct.unpack_from('>I',data,cursor+8+size)[0]
        if kind==b'IHDR':
            width,height,depth,color,_,_,interlace=struct.unpack('>IIBBBBB',body)
            assert depth==8 and interlace==0
        elif kind==b'PLTE':
            palette=[tuple(body[i:i+3]) for i in range(0,len(body),3)]
        elif kind==b'IDAT':
            compressed.extend(body)
        cursor+=size+12
    channels={0:1,2:3,3:1,4:2,6:4}[color]
    stride=width*channels
    raw=zlib.decompress(compressed)
    assert len(raw)==height*(stride+1)
    previous=bytearray(stride)
    pixels=[]
    for y in range(height):
        offset=y*(stride+1)
        mode=raw[offset]
        row=bytearray(raw[offset+1:offset+1+stride])
        for i in range(stride):
            left=row[i-channels] if i>=channels else 0
            up=previous[i]
            upper_left=previous[i-channels] if i>=channels else 0
            if mode==1:
                predictor=left
            elif mode==2:
                predictor=up
            elif mode==3:
                predictor=(left+up)//2
            elif mode==4:
                base=left+up-upper_left
                distances=[abs(base-left),abs(base-up),abs(base-upper_left)]
                predictor=[left,up,upper_left][distances.index(min(distances))]
            else:
                assert mode==0
                predictor=0
            row[i]=(row[i]+predictor)&255
        for x in range(width):
            value=row[x*channels:(x+1)*channels]
            pixels.append(palette[value[0]] if color==3 else tuple(value[:3]) if color in (2,6)
                          else (value[0],)*3)
        previous=row
    return width,height,pixels
