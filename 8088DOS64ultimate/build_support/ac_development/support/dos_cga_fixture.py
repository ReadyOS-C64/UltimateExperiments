"""Derive a disposable DOS floppy by adding one original-8088 CGAPROBE.COM.

No boot or existing file changes; both FAT12 mirrors, allocation, root and every
original payload are independently validated by dos_disk_inspect.Volume.
"""
from pathlib import Path
import argparse, json, struct, subprocess
from dos_disk_inspect import Volume, sha
SOURCE_SHA = 'bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb'
NAME = b'CGAPROBECOM'

def derive(source: bytes, program: bytes):
    if sha(source) != SOURCE_SHA: raise ValueError('source identity')
    if not 0 < len(program) <= 1024: raise ValueError('probe size')
    original = Volume(source)
    if original.width != 12 or 'CGAPROBE.COM' in original.payloads: raise ValueError('fixture precondition')
    bps,spc,reserved,fats,roots,total,media,spf=struct.unpack_from('<HBHBHHBH',source,11)
    start=reserved*bps; fat=source[start:start+spf*bps]
    def value(n):
        p=n+n//2; w=int.from_bytes(fat[p:p+2],'little'); return (w>>4 if n&1 else w)&4095
    free=[n for n in range(2,original.clusters+2) if value(n)==0]
    need=(len(program)+spc*bps-1)//(spc*bps)
    if len(free)<need: raise ValueError('insufficient free space')
    chain=free[:need]; raw=bytearray(source)
    root=original.root_sector*bps
    slot=next((root+i*32 for i in range(roots) if source[root+i*32] in (0,0xe5)),None)
    if slot is None: raise ValueError('root full')
    for mirror in range(fats):
        fs=start+mirror*spf*bps
        for index,cluster in enumerate(chain):
            successor=chain[index+1] if index+1<len(chain) else 0xfff
            at=fs+cluster+cluster//2
            word=int.from_bytes(raw[at:at+2],'little')
            word=(word&0x000f)|(successor<<4) if cluster&1 else (word&0xf000)|successor
            raw[at:at+2]=word.to_bytes(2,'little')
    entry=bytearray(32);entry[:11]=NAME;entry[11]=0x20
    struct.pack_into('<H',entry,26,chain[0]);struct.pack_into('<I',entry,28,len(program))
    raw[slot:slot+32]=entry
    for index,cluster in enumerate(chain):
        at=(original.data_sector+(cluster-2)*spc)*bps
        chunk=program[index*spc*bps:(index+1)*spc*bps]
        raw[at:at+spc*bps]=chunk+bytes(spc*bps-len(chunk))
    result=bytes(raw); final=Volume(result)
    if final.payloads.get('CGAPROBE.COM')!=program: raise ValueError('probe extraction')
    if set(final.payloads)!=set(original.payloads)|{'CGAPROBE.COM'}: raise ValueError('unexpected new file')
    for name,payload in original.payloads.items():
        if final.payloads[name]!=payload: raise ValueError('existing file changed')
    if result[:512]!=source[:512]: raise ValueError('boot sector changed')
    return result,dict(source_sha256=sha(source),fixture_sha256=sha(result),program_sha256=sha(program),program_bytes=len(program),clusters=chain,root_slot=(slot-root)//32,changed_sectors=[i for i in range(total) if source[i*512:(i+1)*512]!=result[i*512:(i+1)*512]],original_files_preserved=len(original.payloads),scope='Validated disposable FAT12 addition only; genuine DOS must load CGAPROBE.COM normally.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--nasm',default='nasm');a=p.parse_args()
    source=a.source.resolve(); output=a.output.resolve()
    if output==source or output.exists(): p.error('output must be a new disposable file')
    program=output.with_suffix('.com')
    if program.exists() or output.with_suffix('.json').exists(): p.error('derived output already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    asm=Path(__file__).parent/'dos_fixture_assets/cgaprobe.asm'
    subprocess.run([a.nasm,'-f','bin',str(asm),'-o',str(program)],check=True,timeout=10)
    original=source.read_bytes(); fixture,report=derive(original,program.read_bytes())
    if source.read_bytes()!=original: raise ValueError('source changed')
    output.write_bytes(fixture);report.update(assembly_sha256=sha(asm.read_bytes()),builder_sha256=sha(Path(__file__).read_bytes()),source=str(source),output=str(output))
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
