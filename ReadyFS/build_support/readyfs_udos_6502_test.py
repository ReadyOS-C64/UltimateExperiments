#!/usr/bin/env python3
"""Execute the linked four-phase gateway, real REU DMA assembly, and DOS leaves.

Only the UltimateDOS device and REU register transfers are simulated. This
executes cc65 frames, shared-window replacement, complete payload caching,
PETSCII literals, and resident handoffs; host tests cover directory callbacks.
"""
from pathlib import Path
import hashlib, json, re
from py65.devices.mpu6502 import MPU
ROOT=Path(__file__).resolve().parent.parent
ART=ROOT/'artifacts/readyfs'
labels={n:int(a,16) for a,n in re.findall(r'^al ([0-9A-F]{6}) \.([^\s]+)',(ART/'readyfs-overlay.lbl').read_text(),re.M)}
phases=('prepare','lookup','execute','name')
cache={}; transfers=[]
for i,name in enumerate(phases):
    data=(ART/f'readyfs-udos-{name}.prg').read_bytes();assert data[:2]==b'\x00\xb6'
    cache[(1,(i+5)*4096)]=data[2:]
cache[(2,0)]=(ART/'readyfs-match.prg').read_bytes()[2:]
class Memory(list):
    def __setitem__(self,address,value):
        super().__setitem__(address,value)
        if address==0xdf01:
            assert value==0x91, 'Only cache fetches are expected'
            dest=self[0xdf02] | self[0xdf03]<<8
            offset=self[0xdf04] | self[0xdf05]<<8
            bank=self[0xdf06];size=self[0xdf07] | self[0xdf08]<<8
            payload=cache[(bank,offset)]
            assert dest==0xb600 and size==len(payload), ('DMA must include CODE/RODATA/BSS exactly',hex(dest),bank,hex(offset),size,len(payload))
            self[dest:dest+size]=payload;transfers.append((bank,offset,size))
m=Memory([0]*65536);cpu=MPU(memory=m)
data=(ART/'readyfs-overlay.prg').read_bytes();start=int.from_bytes(data[:2],'little');m[start:start+len(data)-2]=data[2:]
CALL,STATUS,LIVE,ACCESS,NAME,WIRE,STREAM,OTHER,RETURN=0xc680,0xc6c0,0xc6c1,0xc700,0xc750,0xc764,0xc800,0xca00,0xfff0

def word(a,v=None):
    if v is None:return m[a] | m[a+1]<<8
    m[a:a+2]=[v&255,v>>8]
def string(a):
    out=bytearray()
    while m[a]:out.append(m[a]);a+=1
    return bytes(out)
def put(a,b):m[a:a+len(b)+1]=b+b'\0'
def drop(n):word(2,word(2)+n)
def ret(v=0):cpu.a=v&255;cpu.x=v>>8;cpu.pc=(cpu.stPopWord()+1)&65535

def stream(address,path):
    m[address:address+274]=[0]*274;m[address]=2
    put(address+7,path);word(address+263,address+7);word(address+265,address+9)

def parsed(raw):
    raw=raw.upper();type=0
    if raw[-4:] in (b'.SEQ',b'.PRG',b'.USR',b'.REL'):
        type=16+(b'.SEQ',b'.PRG',b'.USR',b'.REL').index(raw[-4:]);raw=raw[:-4]
    if raw.startswith(b'{') and raw.endswith(b'}'):raw=bytes.fromhex(raw[1:-1].decode())
    return raw,type
files={};handles={1:None,2:None};calls=[];output=bytearray();bad_close=False

def dos():
    sp=word(2);n=word(sp);cmd=bytes(m[word(sp+2):word(sp+2)+n]);x=cpu.a | cpu.x<<8
    target,op=cmd[:2];assert target in (1,2);calls.append(cmd)
    status=b'00,OK\0';data=b''
    def info(name,type,attr=0):return bytes(8)+(b'SEQ',b'PRG',b'USR',b'REL')[type-16]+bytes([attr])+name
    if op==0x11:assert cmd[-1]==0
    elif op==0x08:
        raw=cmd[2:-1];assert cmd[-1]==0
        if raw.lower()==b'disk.d64':data=info(b'disk.d64',16)
        else:
            name,type=parsed(raw);match=next(((a,b) for a,b in files if a==name and (not type or b==type)),None)
            if match:data=info(*match)
            else:status=b'82,FILE NOT FOUND\0'
    elif op==0x13:
        # The bare-name case below is a hidden leaf, omitted by firmware DIR.
        assert all(name.startswith(b'.') for name,type in files)
        status=b'01,DIRECTORY EMPTY\0'
    elif op==0x02:
        assert handles[target] is None and cmd[-1]==0
        name,type=parsed(cmd[3:-1]);match=next(((a,b) for a,b in files if a==name and (not type or b==type)),None)
        if cmd[2]==6:
            assert not match;match=(name,type or 17);files[match]=b'new'
        if match:handles[target]=match
        else:status=b"FILE DOESN'T EXIST\0"
    elif op==0x07:
        assert handles[target];data=info(*handles[target])
    elif op==0x03:
        if bad_close:status=b'DISK ERROR\0'
        else:assert handles[target];handles[target]=None
    elif op==0x0a:
        left,right=cmd[2:].split(b'\0')[:2];a=parsed(left);b=parsed(right);assert a in files and b not in files
        files[b]=files.pop(a)
    else:raise AssertionError(('DOS opcode',cmd))
    assert len(data)<=word(x+2) and len(status)<=word(x+8)
    m[word(x):word(x)+len(data)]=data;word(x+4,len(data))
    m[word(x+6):word(x+6)+len(status)]=status;word(x+10,len(status))
    drop(4);ret(1)

def invoke(op,type=16,target=1,expected=1):
    m[CALL:CALL+23]=[0]*23
    for offset,value in ((0,STREAM),(2,OTHER),(6,ACCESS),(8,ACCESS),(10,NAME),(12,WIRE),(16,STATUS),(18,LIVE)):word(CALL+offset,value)
    m[CALL+20:CALL+23]=[op,target,type]
    word(2,0xd000);cpu.pc=labels['_readyfs_overlay_udos'];cpu.a=CALL&255;cpu.x=CALL>>8;cpu.sp=255;cpu.p=0x21;cpu.stPushWord(RETURN-1)
    for steps in range(500000):
        pc=cpu.pc
        if pc==RETURN:break
        if pc==labels['_readyfs_uci_command']:dos()
        elif pc==labels['_cputs']:output.extend(string(cpu.a | cpu.x<<8));ret()
        elif pc==labels['_cputc']:output.append(cpu.a);ret()
        else:
            assert m[pc]!=0,f'BRK at ${pc:04X} (phase BSS/RODATA or bad return)'
            cpu.step()
    else:raise AssertionError('6502 did not return')
    assert cpu.a==expected and cpu.x==0,(op,cpu.a,bytes(output),calls[-8:])
    assert word(2)==0xd000 and cpu.sp==255, 'Unbalanced cc65 or CPU stack'
    assert m[1]==0x37, 'CPU port was not restored'
    assert bytes(m[0xb600:0xb600+len(cache[(2,0)])])==cache[(2,0)], 'Matcher not restored'

m[1]=0x37
m[labels['_readyfs_reu_history_bank_value']]=1
m[labels['_readyfs_reu_overlay_bank_value']]=2
checks=0
for type,suffix in ((16,b'.seq'),(17,b'.prg'),(18,b'.usr')):
    files.clear();files[(b'NOTE',type)]=b'old';m[LIVE]=0
    stream(STREAM,b'u:/usb1/disk.d64/NOTE'+suffix);stream(OTHER,b'u:/usb1/disk.d64/DEST'+suffix)
    invoke(2);assert m[STREAM+270]==type and string(ACCESS).upper().endswith(suffix.upper())
    invoke(3);assert m[LIVE]==1 and m[STREAM+271]==1
    invoke(5);assert m[LIVE]==0 and m[STREAM+271]==0
    invoke(2);invoke(6);assert (b'DEST',type) in files and (b'NOTE',type) not in files
    stream(STREAM,b'u:/usb1/disk.d64/STAGE'+suffix)
    invoke(4,type);assert handles[1]==(b'STAGE',type);invoke(5)
    checks+=7
files.clear();files[(b'NOTE',16)]=b'alias';stream(STREAM,b'u:/usb1/disk.d64/NOTE.seq')
stream(OTHER,b'u:/USB1/DISK.D64/{4e4f5445}');m[OTHER+270]=16
invoke(2);invoke(9,expected=2);assert len(files)==1;checks+=2
files.clear();files[(b'.NOTE',16)]=b'hidden';stream(STREAM,b'u:/usb1/disk.d64/.NOTE')
invoke(2);assert m[STREAM+270]==16 and not m[LIVE];checks+=1
files[(b'.NOTE',18)]=b'ambiguous';invoke(2,expected=2);assert not m[LIVE];checks+=1
stream(STREAM,b'u:/usb1/disk.d64/.NOTE.seq');invoke(3);bad_close=True
invoke(5,expected=2);assert m[LIVE]==1 and m[STREAM+271]==1
before=len(calls);invoke(2,expected=2);assert len(calls)==before
checks+=3
print(json.dumps({'result':'PASS','cases':checks,'dma_transfers':len(transfers),'scope':'actual linked gateway, all four leaves, real REU DMA assembly, whole payload, CPU port/stack/typed metadata/rename/hidden ambiguity/failed close','artifacts':{n:hashlib.sha256((ART/f'readyfs-udos-{n}.prg').read_bytes()).hexdigest() for n in phases}},indent=2))
