"""Disposable DOS1 demo media: original boot/core plus byte-exact supplied BASIC.

Only named unused utility files are removed. Original images are never written.
The independent strict FAT12 reader validates all allocation and kept payloads.
"""
import argparse,json,struct
from pathlib import Path
from dos_disk_inspect import Volume,sha
SOURCE_SHA='bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb'
BASIC_DISK_SHA='c69238c738bab18db840b5ae72b2470c0d594832d91103573a6d8273dce300e9'
REMOVE=('FDISK.COM','4201.CPI','GRAPHICS.COM')

def derive(source,basic_disk,game):
    if sha(source)!=SOURCE_SHA or sha(basic_disk)!=BASIC_DISK_SHA: raise ValueError('source identity')
    if not game or len(game)>8192 or b'\x00' in game or b'\n' in game.replace(b'\r\n',b''): raise ValueError('ASCII CRLF BASIC source required')
    game.decode('ascii')
    v=Volume(source);bv=Volume(basic_disk);program=bv.payloads['GWBASIC.EXE']
    raw=bytearray(source);bps,spc,reserved,fats,roots,total,media,spf=struct.unpack_from('<HBHBHHBH',source,11)
    fs=reserved*bps;root=v.root_sector*bps
    def setfat(c,value):
        for m in range(fats):
            at=fs+m*spf*bps+c+c//2;word=int.from_bytes(raw[at:at+2],'little')
            word=(word&15)|(value<<4) if c&1 else (word&0xf000)|value
            raw[at:at+2]=word.to_bytes(2,'little')
    removed=[]
    for name in REMOVE:
        f=next(f for f in v.files if f['name']==name)
        short=(name.split('.')[0].ljust(8)+name.split('.')[1].ljust(3)).encode()
        slots=[root+i*32 for i in range(roots) if raw[root+i*32:root+i*32+11]==short]
        if len(slots)!=1:raise ValueError('removal root identity')
        raw[slots[0]]=0xe5
        for c in f['clusters']:setfat(c,0)
        removed.append(dict(name=name,sha256=f['sha256'],bytes=f['bytes'],clusters=f['clusters']))
    clean=Volume(bytes(raw));chains={}
    for name,payload in [('GWBASIC.EXE',program),('HANGMAN.BAS',game)]:
        if name in clean.payloads: raise ValueError('duplicate added file')
        free=[c for c in range(2,v.clusters+2) if Volume(bytes(raw)).entry(c)==0]
        need=(len(payload)+spc*bps-1)//(spc*bps)
        if len(free)<need:raise ValueError('insufficient free clusters')
        chain=free[:need]
        slot=next((root+i*32 for i in range(roots) if raw[root+i*32] in (0,0xe5)),None)
        if slot is None:raise ValueError('root full')
        for n,c in enumerate(chain):
            setfat(c,chain[n+1] if n+1<len(chain) else 0xfff)
            at=(v.data_sector+(c-2)*spc)*bps;chunk=payload[n*spc*bps:(n+1)*spc*bps]
            raw[at:at+spc*bps]=chunk+bytes(spc*bps-len(chunk))
        ent=bytearray(32);base,ext=name.split('.');ent[:11]=(base.ljust(8)+ext.ljust(3)).encode();ent[11]=0x20
        struct.pack_into('<HI',ent,26,chain[0],len(payload));raw[slot:slot+32]=ent
        chains[name]=chain
    result=bytes(raw);out=Volume(result)
    if set(out.payloads)!=(set(v.payloads)-set(REMOVE))|{'GWBASIC.EXE','HANGMAN.BAS'}:raise ValueError('unexpected payload set')
    kept=[]
    for name,payload in v.payloads.items():
        if name not in REMOVE:
            if out.payloads[name]!=payload:raise ValueError('kept payload changed')
            kept.append(dict(name=name,bytes=len(payload),sha256=sha(payload)))
    if out.payloads['GWBASIC.EXE']!=program or out.payloads['HANGMAN.BAS']!=game:raise ValueError('new payload changed')
    if result[:512]!=source[:512]:raise ValueError('boot changed')
    return result,dict(source_sha256=sha(source),basic_disk_sha256=sha(basic_disk),fixture_sha256=sha(result),program_sha256=sha(program),program_bytes=len(program),game_sha256=sha(game),game_bytes=len(game),removed=removed,kept=kept,added_clusters=chains,free_bytes=out.free_clusters*spc*bps,changed_sectors=[n for n in range(total) if source[n*bps:(n+1)*bps]!=result[n*bps:(n+1)*bps]],scope='Disposable demo media only; real DOS owns boot, files, EXE loading, and BASIC execution.')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--basic-disk',type=Path,required=True);p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.resolve() in (a.source.resolve(),a.basic_disk.resolve()) or a.output.exists() or a.output.with_suffix('.json').exists():p.error('new disposable output required')
 source=a.source.read_bytes();basic=a.basic_disk.read_bytes();game=a.game.read_text().replace('\r\n','\n').replace('\n','\r\n').encode('ascii')
 fixture,report=derive(source,basic,game)
 if a.source.read_bytes()!=source or a.basic_disk.read_bytes()!=basic:raise ValueError('source changed')
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(fixture);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['fixture_sha256','program_sha256','game_sha256','free_bytes']},indent=2))
if __name__=='__main__':main()
