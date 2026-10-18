"""Pure independent capture oracle for the reviewed standalone IEC binaries."""
import argparse,hashlib,json,zlib
from pathlib import Path
from build_iec_standalone import EXPECTED,check_build
DOS_SHA='bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def seed():return bytes(range(256))*2
def pattern():return bytes((i^(i>>8)^(i>>16)^0xa7)&255 for i in range(4194304))
def derived(base,case):
    if case=='original' or case=='missing':return base
    if case=='short':return base[:-1]
    if case=='long':return base+b'\xff'
    if case=='crc':return base[:123]+bytes([base[123]^0x80])+base[124:]
    raise ValueError('Unsupported IEC case')
def verify(run,project,expected_d81_sha=None):
    check_build(project)
    data=json.loads((run/'result.json').read_text());digest=data['prg_sha256']
    kind=next((k for k,v in EXPECTED.items() if v==digest),None)
    if kind is None:raise ValueError('Unreviewed IEC executable')
    base=seed() if kind=='small' else next((project/'reference').glob('*1 of 3.img')).read_bytes()
    if kind=='full' and sha(base)!=DOS_SHA:raise ValueError('Original DOS image changed')
    case=data['case'];payload=derived(base,case)
    if (run/'input.img').read_bytes()!=payload:raise ValueError('Unexpected derived input')
    if data['payload_sha256']!=sha(payload) or data['payload_bytes']!=len(payload):raise ValueError('Fixture digest mismatch')
    if data['source_sha256']!=sha(base) or data['source_bytes']!=len(base):raise ValueError('Source digest mismatch')
    stem=project/'build'/('dos64-iec-standalone'+('-small' if kind=='small' else ''))
    prg=Path(str(stem)+'.prg').read_bytes()
    if sha(prg)!=digest:raise ValueError('Current IEC binary changed')
    symbols={v.split()[2].lstrip('.'):int(v.split()[1],16) for v in Path(str(stem)+'.labels').read_text().splitlines() if v.startswith('al ')}
    ram=(run/'ram.bin').read_bytes();reu=(run/'reu.img').read_bytes()
    if len(ram)!=65536 or len(reu)!=4194304:raise ValueError('Truncated RAM/REU capture')
    mb=ram[0x6000:0x6020]
    if data['mailbox_hex']!=mb.hex():raise ValueError('Mailbox disagrees with full RAM capture')
    start=int.from_bytes(prg[:2],'little');expected=bytearray(prg[2:]);expected[symbols['started']-start]=1
    if ram[start:start+len(expected)]!=expected:raise ValueError('Executable capture differs')
    if ram[0xf000:0xfe00]!=bytes((i&255)^0xa5 for i in range(3584)) or ram[0xbfff]!=0xa7 or ram[0xc200]!=0x5a:raise ValueError('Host shadow/buffer guard changed')
    error={'original':0,'short':4,'long':4,'crc':6,'missing':3}[case]
    count=0 if case=='missing' else len(base)-1 if case=='short' else len(base)
    chunks=0 if case=='missing' else (len(base)//512-1 if case in ('long','short') else len(base)//512)
    if (mb[0],mb[1],mb[13])!=((0xe1 if error else 0xa5),error,0 if error else 1):raise ValueError('Wrong native error/publication')
    if int.from_bytes(mb[4:7],'little')!=count or int.from_bytes(mb[7:9],'little')!=chunks:raise ValueError('Wrong receive/DMA counts')
    if mb[15]!=(0 if case in ('long','missing') else 1) or mb[2]!=(0x42 if case=='missing' else 0 if case=='long' else 0x40):raise ValueError('Wrong final-byte EOI/status')
    if count and mb[16]!=payload[count-1]:raise ValueError('Wrong returned final byte')
    if mb[3]!=(0 if case=='missing' else 1) or ram[0x98]!=0 or mb[17]!=0 or mb[18]!=0:raise ValueError('Wrong close/owned-channel state')
    if case=='missing':
        if mb[2]!=0x42 or ram[0x2005:0x2007]!=b'62':raise ValueError('Missing-file primary status lost')
    elif mb[20:22]!=b'00':raise ValueError('Drive close status is not 00')
    if not error and (mb[14]!=1 or mb[19]!=5 or int.from_bytes(mb[9:13],'little')!=zlib.crc32(base)):raise ValueError('CRC or entry guard failed')
    expected_reu=bytearray(pattern());expected_reu[0x100000:0x100000+chunks*512]=payload[:chunks*512]
    if reu!=expected_reu:raise ValueError('Complete 4 MiB REU comparison failed')
    d81=(run/'container.d81').read_bytes()
    if len(d81)!=819200 or sha(d81)!=data.get('d81_sha256',expected_d81_sha):raise ValueError('D81 changed/truncated')
    wanted={'REU':1,'REUsize':4096,'Drive8Type':1581,'Drive8TrueEmulation':int(kind=='small'),'TrapDevice8':int(kind=='full'),'MachineVideoStandard':1}
    if any(data['resources'].get(k)!=v for k,v in wanted.items()):raise ValueError('Wrong VICE configuration')
    return {'schema':1,'status':'passed','standalone_only':True,'case':case,'kind':kind,'prg_sha256':digest,'received_bytes':count,'dma_chunks':chunks,'native_error':error,'loaded':mb[13],'all_4_mib_equal':True,'executable_equal':True,'shadow_guards_equal':True,'source_sha256':sha(base),'known_closed':mb[3],'result_sha256':sha((run/'result.json').read_bytes())}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('run',type=Path);args=ap.parse_args();print(json.dumps(verify(args.run.resolve(),Path(__file__).resolve().parents[1]),indent=2))
