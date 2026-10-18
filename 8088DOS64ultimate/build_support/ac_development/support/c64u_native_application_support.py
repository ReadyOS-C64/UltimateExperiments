"""Read-only native DOS acceptance oracles. Importing performs no hardware action."""
import hashlib
from pathlib import Path
import re
import sys
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dos_image import Fat12Image

SOURCE_SHA='bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb'
KEYS={'\r':0x1c0d,'V':0x2f56,'E':0x1245,'R':0x1352,'D':0x2044,
      'I':0x1749,' ':0x3920,'/':0x352f,'P':0x1950}

def sha(value):return hashlib.sha256(value).hexdigest()

def verified_media(record,source):
    data=Path(source).read_bytes()
    required={'status':'verified','source_sha256':SOURCE_SHA,'source_bytes':368640,
              'created_directory':True,'remote_readback_bytes':368640,
              'remote_readback_sha256':SOURCE_SHA,'original_source_unchanged':True}
    if any(record.get(key)!=value for key,value in required.items()):
        raise ValueError('Media manifest is not an actually verified fresh source fixture')
    if len(data)!=368640 or sha(data)!=SOURCE_SHA or zlib.crc32(data)!=record.get('source_crc32'):
        raise ValueError('Independent original image size/hash/CRC mismatch')
    path=record.get('native_path','')
    if not re.fullmatch(r'/usb1/DOS64_TEST/[a-z0-9][a-z0-9_-]{0,63}/DOS33A\.IMG',path):
        raise ValueError('Native path must identify the fresh owned fixture image')
    if record.get('remote_directory')!=path.rsplit('/',1)[0]:raise ValueError('Fixture directory identity mismatch')
    if not re.fullmatch(r'[0-9a-f]{64}',record.get('marker_sha256','')):raise ValueError('Fresh ownership marker hash missing')
    return data,path


def patch_config(prg,config_address,fields,path,crc):
    """Only path length/body, expectedCRC and enabled byte may change."""
    if len(prg)<3 or prg[:2]!=b'\x01\x08':raise ValueError('Unexpected native runtime PRG header')
    base=config_address-0x801+2
    end=base+fields['size']
    if base<2 or end>len(prg):raise ValueError('Cold config is outside the uploaded PRG')
    if prg[base:base+4]!=b'D64N':raise ValueError('Cold config signature mismatch')
    if prg[base+fields['enabled']]!=0:raise ValueError('Source runtime must have disabled cold config')
    raw=path.encode('ascii')+b'\0'
    if not 1<=len(raw)<=fields['path_capacity']:raise ValueError('Native path exceeds owned config capacity')
    if not isinstance(crc,int) or not 0<=crc<=0xffffffff:raise ValueError('Invalid source CRC32')
    out=bytearray(prg)
    changes={fields['enabled']:b'\xa5',fields['path_length']:bytes([len(raw)]),
             fields['expected_crc']:crc.to_bytes(4,'little'),
             fields['path']:raw+bytes(fields['path_capacity']-len(raw))}
    occupied=set()
    for offset,body in changes.items():
        span=set(range(offset,offset+len(body)))
        if offset<4 or offset+len(body)>fields['size'] or occupied&span:raise ValueError('Overlapping or invalid config fields')
        occupied|=span;out[base+offset:base+offset+len(body)]=body
    allowed={base+i for i in occupied}
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(prg,out))):raise AssertionError('Patch escaped owned config')
    if len(out)!=len(prg):raise AssertionError('Patch changed runtime layout')
    return bytes(out),{'base_prg_sha256':sha(prg),'patched_prg_sha256':sha(out),
                       'config_address':config_address,'path':path,'path_bytes_including_nul':len(raw),
                       'source_crc32':crc,'changed_offsets':[i for i,(a,b) in enumerate(zip(prg,out)) if a!=b]}


def decode_screen(bda,video):
    if len(bda)!=256:raise ValueError('Truncated BDA snapshot')
    mode=bda[0x49];cols=int.from_bytes(bda[0x4a:0x4c],'little');page=bda[0x62]
    offset=int.from_bytes(bda[0x4e:0x50],'little')
    if mode not in (0,1,2,3) or cols not in (40,80) or page>7 or offset+cols*25*2>0x4000:
        raise ValueError('Unsupported or inconsistent actual text BDA')
    if len(video)!=cols*25*2:raise ValueError('Truncated active text VRAM')
    col=bda[0x50+page*2];row=bda[0x51+page*2]
    if col>=cols or row>=25:raise ValueError('Invalid active cursor position')
    chars=video[::2]
    rows=[chars[i*cols:(i+1)*cols].decode('cp437') for i in range(25)]
    return {'mode':mode,'columns':cols,'page':page,'page_offset':offset,'cursor_row':row,'cursor_column':col,
            'text':'\n'.join(rows),'prompt':rows[row][:col].endswith('A>')}


class Builtins:
    """Genuine DOS VER then DIR /P; all input uses native queue requests."""
    def __init__(self,source):
        image=Fat12Image(source)
        self.entries={bytes.fromhex(e.raw_hex)[:8].decode('cp437')+' '+bytes.fromhex(e.raw_hex)[8:11].decode('cp437'):e.size
                      for e in image.entries if not e.attributes&0x1e}
        self.expected_free=sum(image.bpb['sectors_per_cluster']*512 for c in range(2,image.cluster_count+2) if image.fat_entry(c)==0)
        self.stage='date';self.seen=set();self.version=False;self.header=False;self.summary=False
        self.pages=0;self.history=[];self.screens=[];self.initial_prompt=False;self.pagination_screens=set()
    def observe(self,screen):
        text=screen['text'];self.screens.append(screen)
        keys=''
        if self.stage=='date' and 'Enter new date (mm-dd-yy):' in text:keys='\r';self.stage='time'
        elif self.stage=='time' and 'Enter new time:' in text:keys='\r';self.stage='initial_prompt'
        elif self.stage=='initial_prompt' and screen['prompt']:
            self.initial_prompt=True;keys='VER\r';self.stage='ver'
        elif self.stage=='ver':
            self.version|='MS-DOS Version 3.30' in text
            if self.version and screen['prompt']:keys='DIR /P\r';self.stage='dir'
        elif self.stage=='dir':
            self.header|='Directory of  A:' in text
            if self.header:
                for line in text.splitlines():
                    name=line[:12]
                    if name in self.entries:
                        fields=line[12:].split()
                        if fields and fields[0].isdigit() and int(fields[0])==self.entries[name]:self.seen.add(name)
                    match=re.fullmatch(r'\s*(\d+)\s+File\(s\)\s+(\d+)\s+bytes free\s*',line)
                    if match and int(match[1])==len(self.entries) and int(match[2])==self.expected_free:self.summary=True
                if self.summary and len(self.seen)==len(self.entries) and self.pages>0 and screen['prompt']:self.stage='done'
                elif 'Strike a key when ready . . .' in text.splitlines()[screen['cursor_row']][:screen['cursor_column']] and text not in self.pagination_screens:
                    # Only the cursor-local prompt is active. Old prompt text
                    # can remain on screen while the next page is printed.
                    if self.pages>=4:raise ValueError('Unexpected extra genuine DOS pagination pages')
                    keys=' ';self.pages+=1;self.pagination_screens.add(text)
        result=[KEYS[k] for k in keys]
        self.history.extend(result)
        return result
    def result(self):
        return {'accepted':self.stage=='done','stage':self.stage,'initial_prompt':self.initial_prompt,
                'version_3_30':self.version,'directory_header':self.header,'directory_summary':self.summary,
                'expected_free_bytes':self.expected_free,'expected_entries':self.entries,
                'seen_entries':sorted(self.seen),'pagination_keys':self.pages,'input_key_words':self.history,
                'script':'CR, CR, VER CR, DIR /P CR, SPACE per actual DOS pagination prompt',
                'screens':self.screens}
