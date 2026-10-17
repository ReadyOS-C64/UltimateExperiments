import hashlib,zlib
BASE_SHA="38806976236c39df7b392b8dbf5312adb92c4ac4f9ac60460f664a3eb61e905b"
SIZE=4194304
OFFSET=0x1985-0x801+2
CONFIG_SIZE=138
DYNAMIC=(0x12b9,0x135f)
sha=lambda b:hashlib.sha256(b).hexdigest()

def configure(base,data,path):
    if not isinstance(base,bytes) or sha(base)!=BASE_SHA:raise ValueError('Unreviewed base restore PRG')
    if not isinstance(data,bytes) or len(data)!=SIZE:raise ValueError('Exact immutable4MiB backup required')
    encoded=path.encode('ascii')+b'\0'
    if not 2<=len(encoded)<=128 or any(b<32 or b>126 for b in encoded[:-1]):raise ValueError('Invalid bounded ASCII restore path')
    result=bytearray(base)
    result[OFFSET+4:OFFSET+CONFIG_SIZE]=bytes([0xa5,len(encoded)])+(zlib.crc32(data)&0xffffffff).to_bytes(4,'little')+encoded+bytes(128-len(encoded))
    return bytes(result)

def resident_identity(ram,configured,terminal=False):
    if not isinstance(ram,bytes) or len(ram)!=65536:raise ValueError('Native identity requires full exact C64 RAM capture')
    for address in DYNAMIC:
        value=int.from_bytes(ram[address:address+2],'little')
        window=(0xc100,0xc47f) if address==DYNAMIC[0] else (0xc480,0xc7ff)
        # Pause may land between low/high STA operands. First upload can
        # temporarily retain FFhigh (path command<=131bytes); first drain
        # FF80 and C4FF->C500 low-first seam C400 are also known publications.
        transient=(value==0xffff or (address==DYNAMIC[0] and 0xff00<=value<=0xff00+configured[OFFSET+5]+2) or (address==DYNAMIC[1] and value in (0xff80,0xc400)))
        if terminal and value!=(0xc101 if address==DYNAMIC[0] else 0xc67f):raise ValueError('Native final CLOSE/512byte READ operand identity mismatch')
        if not (window[0]<=value<=window[1] or (not terminal and transient)):raise ValueError('Native dynamic UCI operand escaped expected buffer')
    ignored={a+i for a in DYNAMIC for i in (0,1)}
    for offset,expected in enumerate(configured[2:]):
        address=0x801+offset
        if address not in ignored and ram[address]!=expected:raise ValueError(f'Native resident PRG differs at${address:04X}')

def done_mailbox(raw,data):
    if len(raw)!=32 or raw[:4]!=b'DRF1' or raw[4]!=0xa5:raise ValueError('Native restore did not publish fresh DONE')
    crc=(zlib.crc32(data)&0xffffffff).to_bytes(4,'little')
    if raw[5:7]!=bytes(2) or raw[7]!=6 or raw[8:12]!=bytes(4) or raw[16:20]!=crc or raw[20:24]!=crc or raw[28:30]!=b'\0\x20' or int.from_bytes(raw[24:28],'little')>=144323:raise ValueError('Native DONE lacks exact4MiB/CRC/known-CLOSE counters')
