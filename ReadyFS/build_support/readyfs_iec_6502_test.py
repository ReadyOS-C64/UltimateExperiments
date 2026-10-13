#!/usr/bin/env python3
"""Execute the linked native partition parser against captured directory bytes.

Uses py65; KERNAL I/O and conio are boundary mocks, while production native
sidecar code and resident cc65 stack/runtime instructions execute unchanged.
This catches code/RODATA interleaving that host C tests cannot detect.
"""
from pathlib import Path
import argparse, hashlib, json, re
from py65.devices.mpu6502 import MPU

ROOT = Path(__file__).resolve().parent.parent
RAW = bytes.fromhex('0104010101001222534432494543202020202020202020202220494b20324100010100002020202253595354454d2220202020202020202020205359532020000101010020202022626f6f7422202020202020202020202020204e41542020000000')

def run(artifacts):
    labels = {name:int(address,16) for address,name in re.findall(r'^al ([0-9A-Fa-f]+) \.([^\s]+)', (artifacts/'readyfs-overlay.lbl').read_text(), re.M)}
    m = MPU()
    for name in ('readyfs-overlay.prg','readyfs-native.prg'):
        data=(artifacts/name).read_bytes(); start=int.from_bytes(data[:2],'little')
        m.memory[start:start+len(data)-2]=data[2:]
    def word(address):return m.memory[address] | m.memory[address+1]<<8
    def text(address):
        out=bytearray()
        while m.memory[address]:out.append(m.memory[address]);address+=1
        return bytes(out)
    def drop(size):
        value=word(2)+size;m.memory[2]=value&255;m.memory[3]=value>>8
    def ret(value=0):
        m.a=value&255;m.x=value>>8;m.pc=(m.stPopWord()+1)&65535
    call=0xC700
    m.memory[call+3]=10;m.memory[call+4]=4
    m.memory[call+11:call+15]=[0x80,0xC7,0xF0,0xC7]
    m.memory[2:4]=[0,0xD0]
    m.a=call&255;m.x=call>>8;m.pc=labels['_readyfs_iec_execute']
    m.sp=255;m.stPushWord(0x01FF)
    offset=0;opened=False;output=bytearray()
    for instructions in range(150000):
        pc=m.pc
        if pc==0x0200:break
        if pc==labels['_cbm_open']:
            sp=word(2)
            assert (m.memory[sp+2],m.memory[sp+1],m.memory[sp])==(2,10,0)
            assert text(m.a | m.x<<8)==b'$=P'
            assert not opened;opened=True;drop(3);ret()
        elif pc==labels['_cbm_read']:
            sp=word(2);dest=word(sp);size=m.a | m.x<<8
            assert opened and m.memory[sp+2]==2
            data=RAW[offset:offset+size];m.memory[dest:dest+len(data)]=data
            offset+=len(data);drop(3);ret(len(data))
        elif pc==labels['_cbm_close']:
            assert opened and m.a==2;opened=False;ret()
        elif pc==0xFFCC:ret()
        elif pc==labels['_cputs']:
            output.extend(text(m.a | m.x<<8));ret()
        elif pc==labels['_cputc']:
            output.append(m.a);ret()
        elif pc==labels['_cputhex8']:
            output.extend(f'{m.a:02X}'.encode());ret()
        else:
            assert m.memory[pc]!=0, f'BRK at ${pc:04X}: compiler data at executable entry'
            m.step()
    else:raise AssertionError('6502 instruction bound exceeded')
    assert m.a==1 and m.x==0 and not opened and offset==len(RAW)
    assert word(2)==0xD000, 'software stack unbalanced'
    assert b'$0000' in output and b'SYSTEM' in output and b'boot' in output
    result={'result':'PASS','instructions':instructions,'directory_bytes':offset,
            'native_sha256':hashlib.sha256((artifacts/'readyfs-native.prg').read_bytes()).hexdigest(),
            'output':output.decode('ascii')}
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--artifacts',type=Path,default=ROOT/'artifacts/readyfs')
    run(parser.parse_args().artifacts)
