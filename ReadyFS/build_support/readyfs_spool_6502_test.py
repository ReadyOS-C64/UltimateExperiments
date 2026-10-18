#!/usr/bin/env python3
"""Execute the built spool machine code against modeled REU DMA registers.

Requires py65==1.2.0. Run after make readyfs. This verifies actual 6502 branch,
carry and ABI behavior; it does not claim physical REU timing coverage.
"""
from pathlib import Path
import hashlib
import json
import re
from py65.devices.mpu6502 import MPU

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / 'artifacts/readyfs'
labels = {name: int(address, 16) for address, name in re.findall(
    r'^al ([0-9A-F]{6}) \.([^\s]+)', (ART/'readyfs-overlay.lbl').read_text(), re.M)}
binary = (ART/'readyfs-tape.prg').read_bytes()
CALL, STATE, DATA, RETURN = 0x8000, 0x8100, 0x8200, 0xFFF0


class Memory:
    def __init__(self):
        self.ram = bytearray(65536)
        self.reu = bytearray(16 * 65536)
        self.transfers = []

    def __getitem__(self, address):
        return self.ram[address]

    def __setitem__(self, address, value):
        self.ram[address] = value
        if address == 0xDF01 and value in (0x90, 0x91):
            cpu = int.from_bytes(self.ram[0xDF02:0xDF04], 'little')
            reu = int.from_bytes(self.ram[0xDF04:0xDF07], 'little')
            count = int.from_bytes(self.ram[0xDF07:0xDF09], 'little') or 65536
            assert reu + count <= 12 * 65536, 'DMA touched reserved console/cache bank'
            assert cpu + count <= 65536
            self.transfers.append((value, reu, count))
            if value == 0x90:
                self.reu[reu:reu+count] = self.ram[cpu:cpu+count]
            else:
                self.ram[cpu:cpu+count] = self.reu[reu:reu+count]


mem = Memory()
load = int.from_bytes(binary[:2], 'little')
mem.ram[load:load+len(binary)-2] = binary[2:]
mem.ram[labels['_readyfs_reu_console_bank_value']] = 12
mem.reu[12*65536:] = bytes([0xA7]) * (4*65536)
mpu = MPU(memory=mem)


def word(address, value):
    mem.ram[address:address+2] = value.to_bytes(2, 'little')


def cursor(total_bank, total_lo, replay_bank, replay_lo):
    word(STATE, total_lo)
    mem.ram[STATE+2] = total_bank
    word(STATE+3, replay_lo)
    mem.ram[STATE+5] = replay_bank


def invoke(operation, length):
    mem.ram[CALL] = operation
    word(CALL+5, DATA)
    word(CALL+7, length)
    word(CALL+9, STATE)
    mpu.pc = labels['_readyfs_tape_spool_dispatch']
    mpu.a, mpu.x, mpu.sp, mpu.p = CALL & 255, CALL >> 8, 0xFF, 0x20
    mpu.stPushWord(RETURN-1)
    for _ in range(2000):
        if mpu.pc == RETURN:
            assert mpu.x == 0, 'cc65 return high byte'
            return mpu.a, int.from_bytes(mem.ram[CALL+7:CALL+9], 'little')
        mpu.step()
    raise AssertionError('spool routine did not return')


assert invoke(10, 1) == (1, 0)
assert mem.ram[STATE:STATE+6] == bytes(6)
cursor(10, 0xFFF0, 10, 0xFFF0)
mem.ram[DATA:DATA+32] = bytes(range(32))
assert invoke(11, 17)[0] == 0 and not mem.transfers
assert invoke(11, 16)[0] == 1
assert mem.ram[STATE:STATE+3] == b'\0\0\x0B'
assert invoke(11, 1)[0] == 0
mem.ram[DATA:DATA+32] = bytes([0xCC])*32
assert invoke(12, 32) == (1, 16), 'cap final read at adjacent-bank EOF'
assert mem.ram[DATA:DATA+32] == bytes(range(16)) + bytes([0xCC])*16
assert invoke(12, 32) == (1, 0)
cursor(1, 0x0010, 0, 0xFFF0)
mem.reu[0x1FFF0:0x20010] = bytes(range(32))
assert invoke(12, 64) == (1, 32), 'cap across a nonzero adjacent-bank end'
assert mem.ram[DATA:DATA+32] == bytes(range(32))
cursor(1, 0x0010, 1, 0x0011)
assert invoke(12, 32) == (1, 0), 'cursor beyond end returns EOF'
cursor(2, 0x0010, 0, 0xFFF0)
assert invoke(12, 64) == (1, 64), 'full chunk when more than a bank remains'
assert mem.reu[12*65536:] == bytes([0xA7]) * (4*65536)
print(json.dumps({'result': 'PASS', 'artifact': str(ART/'readyfs-tape.prg'),
                  'sha256': hashlib.sha256(binary).hexdigest(),
                  'dma_transfers': mem.transfers}, indent=2))
