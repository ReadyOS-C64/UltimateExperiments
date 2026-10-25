"""Real emitted 6510 provider with an independent, deliberately small ROM/DOS
boundary model. This is not native IEC, a disk-full proof, or a VICE substitute.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from peddle import Machine

ROM = {0xFFBD, 0xFFBA, 0xFFC0, 0xFFC3, 0xFFC6, 0xFFC9,
       0xFFB7, 0xFFCF, 0xFFD2, 0xFFCC}

class FileIOFixture:
    def __init__(self):
        self.s = {}
        for line in (ROOT / 'build/fileio/provider.lbl').read_text().splitlines():
            _, value, name = line.split()
            self.s[name.lstrip('.')] = int(value, 16)
        self.m = Machine()
        self.m.load(0x1000, (ROOT / 'build/fileio/provider.bin').read_bytes())
        self.fs = {}
        self.channels = {}
        self.trace = []
        self.selected_in = self.selected_out = None
        self.st = 0
        self.dos = b'00, OK,00,00\r'
        self.directory = b''
        self.inject = {}
        self.shim = bytes((i * 43 + 17) & 255 for i in range(1024))
        self.m.load(0xC600, self.shim)
        self.call('se_io_init')

    def read(self, name, n=1):
        a = self.s[name] if isinstance(name, str) else name
        return bytes(self.m.read(a+i) for i in range(n))

    def set(self, name, data):
        self.m.load(self.s[name], bytes([data]) if isinstance(data, int) else data)

    def name(self, data, other=False):
        stem = 'se_io_other' if other else 'se_io_name'
        self.set(stem, data)
        self.set(stem+'_len', len(data))

    def call(self, name, a=0, error=None):
        m = self.m
        for k, v in [('pc', self.s[name]), ('a', a), ('x', 0), ('y', 0),
                     ('sp', 0xFD), ('p', 0x24)]:
            getattr(m.lib, 'zeropage_peddle_set_'+k)(m.handle, v)
        m.write(0x1FE, 0xFE); m.write(0x1FF, 0x02)
        steps = 0
        start = m.regs().instructions
        while m.regs().pc != 0x02FF:
            if m.regs().pc in ROM:
                self.rom()
            else:
                m.lib.zeropage_peddle_step_instruction(m.handle)
            steps += 1
            assert steps < 1_000_000, (name, hex(m.regs().pc))
        r = m.regs()
        if error is None:
            assert not r.p & 1 and r.a == 0, (name, hex(r.a), hex(r.p))
        else:
            assert r.p & 1 and r.a == error, (name, hex(r.a), hex(r.p), error)
        assert self.read(0xC600, 1024) == self.shim
        return r.instructions - start

    def rom(self):
        m = self.m; r = m.regs(); pc = r.pc
        self.trace.append(pc)
        a, x, y, p = r.a, r.x, r.y, r.p & ~1
        failure = self.inject.get(pc)
        if failure:
            self.inject.pop(pc)
            self.st = failure
            p |= 1
        elif pc == 0xFFBD:
            self.filename = self.read(x | (y << 8), a)
        elif pc == 0xFFBA:
            self.lfn, self.device, self.sa = a, x, y
        elif pc == 0xFFC0:
            assert self.device in (8, 9)
            self.st = 0
            if self.sa == 15:
                if self.filename:
                    self.command(self.filename)
                self.channels[self.lfn] = dict(data=self.dos, pos=0)
            elif self.filename.startswith(b'$'):
                self.channels[self.lfn] = dict(data=self.directory, pos=0)
                self.dos = b'00, OK,00,00\r'
            else:
                assert self.filename.startswith(b'0:')
                name, kind, mode = self.filename[2:].rsplit(b',', 2)
                assert kind == b'S'
                if mode == b'W':
                    if name in self.fs:
                        self.dos = b'63, FILE EXISTS,00,00\r'
                    else:
                        self.fs[name] = bytearray()
                        self.channels[self.lfn] = dict(write=name)
                        self.dos = b'00, OK,00,00\r'
                else:
                    assert mode == b'R'
                    if name not in self.fs:
                        self.dos = b'62, FILE NOT FOUND,00,00\r'
                    else:
                        self.channels[self.lfn] = dict(data=bytes(self.fs[name]), pos=0)
                        self.dos = b'00, OK,00,00\r'
        elif pc == 0xFFC3:
            self.channels.pop(a, None)
        elif pc == 0xFFC6:
            if x not in self.channels:
                p |= 1
            else:
                self.selected_in = x
                self.st = 0
        elif pc == 0xFFC9:
            if x not in self.channels:
                p |= 1
            else:
                self.selected_out = x
                self.st = 0
        elif pc == 0xFFCC:
            self.selected_in = self.selected_out = None
        elif pc == 0xFFB7:
            a = self.st
        elif pc == 0xFFCF:
            ch = self.channels[self.selected_in]
            assert ch['pos'] < len(ch['data']), 'Read beyond modeled stream'
            a = ch['data'][ch['pos']]; ch['pos'] += 1
            self.st = 64 if ch['pos'] == len(ch['data']) else 0
        elif pc == 0xFFD2:
            ch = self.channels[self.selected_out]
            self.fs[ch['write']].append(a)
            self.st = 0
        p = (p & ~0x82) | (a & 0x80) | (2 if a == 0 else 0)
        sp = r.sp
        ret = (m.read(0x100+((sp+1)&255)) |
               (m.read(0x100+((sp+2)&255)) << 8)) + 1
        for k, v in [('a', a), ('x', x), ('y', y), ('p', p),
                     ('sp', (sp+2)&255), ('pc', ret & 65535)]:
            getattr(m.lib, 'zeropage_peddle_set_'+k)(m.handle, v)

    def command(self, command):
        if command.startswith(b'R0:'):
            dest, src = command[3:].split(b'=')
            if dest in self.fs:
                self.dos = b'63, FILE EXISTS,00,00\r'
            elif src not in self.fs:
                self.dos = b'62, FILE NOT FOUND,00,00\r'
            else:
                self.fs[dest] = self.fs.pop(src)
                self.dos = b'00, OK,00,00\r'
        elif command.startswith(b'S0:'):
            src = command[3:]
            if src in self.fs:
                del self.fs[src]
                self.dos = b'01, FILES SCRATCHED,01,00\r'
            else:
                self.dos = b'62, FILE NOT FOUND,00,00\r'
        else:
            raise AssertionError(command)

    def close(self):
        self.m.close()
