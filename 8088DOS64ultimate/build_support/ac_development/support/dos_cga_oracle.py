"""Independent decoded-pixel oracle for retained genuine guest CGA captures."""
from pathlib import Path
import argparse,json,re,hashlib
RGBI_TO_VIC=(0,6,5,3,2,4,9,15,12,14,13,3,10,4,7,1)
def source(mode):
    if mode not in (4,5,6): raise ValueError('mode')
    data=bytearray((i^(i>>8)^(mode*17))&255 for i in range(16384))
    data[0x3ff0:0x3ffa]=b'DOS64CGA'+bytes((mode,0xa5))
    return bytes(data)
def expected(mode):
    raw=source(mode)
    palette=(0,15,0,0) if mode==6 else ((0,11,12,15) if mode==5 else (0,11,13,15))
    palette=tuple(RGBI_TO_VIC[c] for c in palette)
    bitmap=bytearray(8000);pairs=set()
    # Decode every source pixel first, then perform the documented lossy
    # horizontal reduction. This does not call native renderer/test code.
    for y in range(200):
        offset=(y&1)*8192+(y//2)*80
        row=[]
        for value in raw[offset:offset+80]:
            row.extend(((value>>bit)&1 for bit in range(7,-1,-1)) if mode==6 else ((value>>bit)&3 for bit in (6,4,2,0)))
        reduced=[]
        for x in range(0,len(row),2):
            a,b=row[x:x+2];pairs.add((a,b))
            reduced.append((a|b) if mode==6 else (a if a else b))
        bits=1 if mode==6 else 2
        per_byte=8//bits
        for cell in range(40):
            packed=0
            for pixel in reduced[cell*per_byte:(cell+1)*per_byte]:packed=(packed<<bits)|pixel
            bitmap[(y//8)*320+cell*8+y%8]=packed
    matrix=bytes([(palette[1]<<4) if mode==6 else ((palette[1]<<4)|palette[2])])*1000
    colors=None if mode==6 else bytes([palette[3]])*1000
    if len(pairs)!=(4 if mode==6 else 16):raise ValueError('pattern fails complete pixel-pair coverage')
    return raw,bytes(bitmap),matrix,colors,pairs

def code_identity(directory,ram):
    prg=(directory/'dos64-tests.prg').read_bytes()
    memory=json.loads((directory/'dos64-tests.memory.json').read_text())
    labels={m[2]:int(m[1],16) for line in (directory/'dos64-tests.labels').read_text().splitlines() if (m:=re.fullmatch(r'al ([0-9A-Fa-f]+) \.(\S+)',line))}
    mutable=[]
    for operand,buffer,opcode in (('dos64_uci_upload_operand','dos64_uci_command',0xad),('dos64_uci_drain_operand','dos64_uci_data',0x8d)):
        at=labels[operand];base=labels[buffer];pointer=int.from_bytes(ram[at:at+2],'little')
        if ram[at-1]!=opcode or not base<=pointer<base+896:raise ValueError('invalid UCI self-modification')
        mutable.extend((at,at+1))
    normalized=bytearray(ram)
    for at in mutable:normalized[at]=prg[at-0x801+2]
    result=[]
    for segment in memory['segments']:
        name=segment['name']
        if name not in ('BASIC','CODE','RODATA','DEVICECODE','HDBIOS'):continue
        at=segment['start'];size=3584 if name=='HDBIOS' else segment['bytes'];source=0xa000 if name=='HDBIOS' else at
        wanted=prg[source-0x801+2:source-0x801+2+size];actual=bytes(normalized[at:at+size])
        if actual!=wanted:raise ValueError(f'captured immutable native segment {name} mismatch')
        result.append(dict(name=name,bytes=size,sha256=hashlib.sha256(actual).hexdigest()))
    if len(result)!=5 or ram[labels['hdb_extension_ready']]!=0xa5:raise ValueError('incomplete immutable identity')
    for name,at,size in (('cp437-narrow4x8.bin',0x4400,1024),('cp437-unscii8.bin',0x4800,2048)):
        if ram[at:at+size]!=(directory.parent/'assets/native-text'/name).read_bytes():raise ValueError('immutable font changed')
    return {'segments':result,'only_mutable_bytes':mutable,'shadow_guard':165,'fonts_exact':True,'prg_sha256':hashlib.sha256(prg).hexdigest()}

def verify(directory):
    report={};checks=0
    for mode in (4,5,6):
        raw,bitmap,matrix,colors,pairs=expected(mode)
        for kind,wanted in (('cga',raw),('bitmap',bitmap),('matrix',matrix),('colors',colors)):
            if wanted is None:continue
            actual=(directory/f'cga-{mode}-{kind}.bin').read_bytes()
            if actual!=wanted:
                at=next((i for i,(a,b) in enumerate(zip(actual,wanted)) if a!=b),min(len(actual),len(wanted)))
                raise ValueError(f'mode{mode}/{kind} first difference {at}')
            checks+=len(wanted)
        bda=(directory/f'cga-{mode}-bda.bin').read_bytes()
        if (len(bda)!=256 or bda[0x49]!=mode
                or int.from_bytes(bda[0x4a:0x4c],'little')!=(80 if mode==6 else 40)
                or int.from_bytes(bda[0x4c:0x4e],'little')!=0x4000
                or int.from_bytes(bda[0x4e:0x50],'little')!=0
                or bda[0x62]!=0
                or bda[0x66]!=(0x3f if mode==6 else 0x30)):
            raise ValueError('BDA geometry or CGA palette shadow')
        host=(directory/f'cga-{mode}-host.bin').read_bytes()
        if len(host)!=65536 or host[0x6000:0x7f40]!=bitmap or host[0x4000:0x43e8]!=matrix:raise ValueError('host capture identity')
        identity=code_identity(directory,host)
        report[str(mode)]={'immutable_identity':identity,'source_pixels':640*200 if mode==6 else 320*200,'all_pixel_pairs':sorted(pairs),'source_bytes':len(raw),'bitmap_bytes':len(bitmap),'matrix_bytes':len(matrix),'color_bytes':None if colors is None else len(colors),'mode6_color_ram':'unused and unconstrained' if mode==6 else None}
    return {'status':'passed','byte_comparisons':checks,'modes':report,'scope':'Raw guest VRAM and lossy C64 representation only; no external display, physical timing or artifact-color fidelity claim.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture_directory',type=Path);a=p.parse_args();print(json.dumps(verify(a.capture_directory),indent=2))
if __name__=='__main__':main()
