#!/usr/bin/env python3
"""Differential execution of the built checksum overlay against binascii.

Uses py65 (same environment as the spool machine-code test); no hardware I/O.
Checks the C one-pointer gateway, actual machine code, count carry, chunking,
zero-length handling, register return convention, and measured CPU cycles.
"""
from pathlib import Path
import binascii
import hashlib
import json
import random
import re
from py65.devices.mpu6502 import MPU
ROOT=Path(__file__).resolve().parent.parent
ART=ROOT/'artifacts/readyfs'
labels={n:int(a,16) for a,n in re.findall(r'^al ([0-9A-F]{6}) \.([^\s]+)',(ART/'readyfs-overlay.lbl').read_text(),re.M)}
m=bytearray(65536)
for name in ['readyfs-overlay.prg','readyfs-tape.prg']:
    raw=(ART/name).read_bytes();start=int.from_bytes(raw[:2],'little');m[start:start+len(raw)-2]=raw[2:]
CALL,SIG,DATA,RETURN=0xC700,0xC740,0xC7F0,0xFFF0
cpu=MPU(memory=m)
def word(a,n):m[a:a+2]=n.to_bytes(2,'little')
def invoke(data,total=0,crc=65535,null_data=False):
    m[CALL:CALL+32]=bytes(32);m[SIG:SIG+6]=total.to_bytes(4,'little')+crc.to_bytes(2,'little')
    word(2,0xD000);m[CALL]=2;word(CALL+1,SIG);word(CALL+5,0 if null_data else DATA);word(CALL+7,len(data));m[DATA:DATA+len(data)]=data
    cpu.pc=labels['_readyfs_tape_dispatch'];cpu.a=CALL&255;cpu.x=CALL>>8;cpu.sp=255;cpu.p=0x21;cpu.stPushWord(RETURN-1)
    before=cpu.processorCycles
    for _ in range(1000000):
        if cpu.pc==RETURN:break
        cpu.step()
    else:raise AssertionError('Checksum did not return: '+hex(cpu.pc))
    assert cpu.a==1 and cpu.x==0 and m[CALL+11]==1
    got_total=int.from_bytes(m[SIG:SIG+4],'little');got_crc=int.from_bytes(m[SIG+4:SIG+6],'little')
    assert got_total==(total+len(data))&0xffffffff,(got_total,total,len(data))
    assert got_crc==binascii.crc_hqx(data,crc),(hex(got_crc),data[:10])
    assert int.from_bytes(m[2:4],'little')==0xD000,'software stack not balanced'
    return got_total,got_crc,cpu.processorCycles-before
rng=random.Random(6410)
cases=0
for size in (0,1,2,31,32,33,255,256,257,511,1025):
    for total in (0,0xfff0,0xffff,0xffffffff):
        data=bytes(rng.randrange(256) for _ in range(size));invoke(data,total,rng.randrange(65536),null_data=not size);cases+=1
assert invoke(b'123456789')[1]==0x29B1
payload=bytes(rng.randrange(256) for _ in range(1025));total=crc=0
crc=65535
for pos in range(0,len(payload),32):total,crc,_=invoke(payload[pos:pos+32],total,crc)
assert total==len(payload) and crc==binascii.crc_hqx(payload,65535)
cycles=invoke(bytes(range(32)))[2]
assert cycles<12000,'Hot checksum regressed to slow C implementation'
report={'result':'PASS','cases':cases+2,'artifact_sha256':hashlib.sha256((ART/'readyfs-tape.prg').read_bytes()).hexdigest(),'cycles_per_32_byte_sample':cycles,'previous_cycles_same_sample':52570,'speedup_sample':52570/cycles,'estimated_signature_only_seconds_for_174848_bytes_at_1mhz':cycles*(174848/32)/1000000,'scope':'CPU sample excludes REU overlay switching and device I/O; no end-to-end timing claim'}
print(json.dumps(report,indent=2))
