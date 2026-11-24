"""Generate sourced C64 facts, original questions, and short code exercises."""
import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import random

from training.codec import CONTEXT, answer_tokens, prompt_tokens

SOURCE_DIR = Path(__file__).resolve().parent
PRG = 'Commodore 64 Programmer\'s Reference Guide (1982)'
VIC = 'VIC-II register specification and documented memory geometry'
SID = 'SID datasheet oscillator equation and equal temperament (A4=440 Hz)'
CPU = 'MOS 6502 official instruction table, PRG Appendix L'
MODES = ('immediate', 'zero page', 'zero page x', 'zero page y', 'absolute',
         'absolute x', 'absolute y', 'indirect x', 'indirect y', 'accumulator',
         'implied', 'relative', 'indirect')

# Each metadata token contains opcode, mode index, and base cycles. A plus
# marks a read with a page-crossing cost. Branches have separate timing.
OPCODES = '''
ADC 69/0/2 65/1/3 75/2/4 6D/4/4 7D/5/4+ 79/6/4+ 61/7/6 71/8/5+
AND 29/0/2 25/1/3 35/2/4 2D/4/4 3D/5/4+ 39/6/4+ 21/7/6 31/8/5+
ASL 06/1/5 16/2/6 0E/4/6 1E/5/7 0A/9/2
BCC 90/11/2
BCS B0/11/2
BEQ F0/11/2
BIT 24/1/3 2C/4/4
BMI 30/11/2
BNE D0/11/2
BPL 10/11/2
BRK 00/10/7
BVC 50/11/2
BVS 70/11/2
CLC 18/10/2
CLD D8/10/2
CLI 58/10/2
CLV B8/10/2
CMP C9/0/2 C5/1/3 D5/2/4 CD/4/4 DD/5/4+ D9/6/4+ C1/7/6 D1/8/5+
CPX E0/0/2 E4/1/3 EC/4/4
CPY C0/0/2 C4/1/3 CC/4/4
DEC C6/1/5 D6/2/6 CE/4/6 DE/5/7
DEX CA/10/2
DEY 88/10/2
EOR 49/0/2 45/1/3 55/2/4 4D/4/4 5D/5/4+ 59/6/4+ 41/7/6 51/8/5+
INC E6/1/5 F6/2/6 EE/4/6 FE/5/7
INX E8/10/2
INY C8/10/2
JMP 4C/4/3 6C/12/5
JSR 20/4/6
LDA A9/0/2 A5/1/3 B5/2/4 AD/4/4 BD/5/4+ B9/6/4+ A1/7/6 B1/8/5+
LDX A2/0/2 A6/1/3 B6/3/4 AE/4/4 BE/6/4+
LDY A0/0/2 A4/1/3 B4/2/4 AC/4/4 BC/5/4+
LSR 46/1/5 56/2/6 4E/4/6 5E/5/7 4A/9/2
NOP EA/10/2
ORA 09/0/2 05/1/3 15/2/4 0D/4/4 1D/5/4+ 19/6/4+ 01/7/6 11/8/5+
PHA 48/10/3
PHP 08/10/3
PLA 68/10/4
PLP 28/10/4
ROL 26/1/5 36/2/6 2E/4/6 3E/5/7 2A/9/2
ROR 66/1/5 76/2/6 6E/4/6 7E/5/7 6A/9/2
RTI 40/10/6
RTS 60/10/6
SBC E9/0/2 E5/1/3 F5/2/4 ED/4/4 FD/5/4+ F9/6/4+ E1/7/6 F1/8/5+
SEC 38/10/2
SED F8/10/2
SEI 78/10/2
STA 85/1/3 95/2/4 8D/4/4 9D/5/5 99/6/5 81/7/6 91/8/6
STX 86/1/3 96/3/4 8E/4/4
STY 84/1/3 94/2/4 8C/4/4
TAX AA/10/2
TAY A8/10/2
TSX BA/10/2
TXA 8A/10/2
TXS 9A/10/2
TYA 98/10/2
'''


@dataclass(frozen=True)
class Fact:
    id: str
    category: str
    subject: str
    answer: str
    prompts: tuple[str, ...]
    source: str
    kind: str = 'fact'


def question_forms(question):
    forms = [question, question + '?', 'c64: ' + question, 'on the c64, ' + question,
             question + ' on a c64']
    for old, new in (('assembler', '6502 assembly'), ('assembler', 'asm'),
                     ('basic', 'basic v2'), ('color', 'colour'), ('zero page', 'zeropage')):
        if old in question:
            forms.append(question.replace(old, new))
    return list(dict.fromkeys(forms))


def curated():
    for line in (SOURCE_DIR / 'facts.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            category, subject, answer, first, second = line.split('|')
            yield Fact(f'factual.{category}.{subject}', category, subject, answer,
                       (first, second, f'tell me about {subject}', f'c64 reference for {subject}',
                        f'what is the {subject}', f'explain the {subject}'), PRG)


def opcodes():
    for line in OPCODES.strip().splitlines():
        instruction, *entries = line.split()
        name = instruction.lower()
        for entry in entries:
            code, mode_idx, duration = entry.split('/')
            mode_idx = int(mode_idx)
            mode = MODES[mode_idx]
            subject = f'{name} {mode}'
            answer = f'${code}.'
            yield Fact(f'opcode.{code}.encoding', 'asm', subject, answer,
                       (f'what is the opcode for {subject}', f'hex opcode of {subject}',
                        f'encode {subject} on the 6510', f'give the machine code byte for {subject}'), CPU)
            hex_byte = f'${code.lower()}'
            yield Fact(f'opcode.{code}.decode', 'asm', subject, f'{instruction} {mode}.',
                       (f'which instruction is opcode {hex_byte}', f'what does opcode {hex_byte} decode to',
                        f'decode the 6510 opcode {hex_byte}', f'what instruction and mode is {hex_byte}'), CPU)
            if mode_idx == 11:
                cycles = '2 cycles, 3 taken, or 4 taken across a page.'
            elif duration.endswith('+'):
                cycles = f'{duration[0]} cycles, plus one on a page crossing.'
            else:
                cycles = f'{duration} cycles.'
            yield Fact(f'opcode.{code}.cycles', 'asm', subject, cycles,
                       (f'how many cycles for {subject}', f'cycle count for {subject}',
                        f'how long does {subject} take', f'give 6510 timing for {subject}'), CPU)


def address_fact(id_, group, subject, value, prompts, source=PRG):
    return Fact(id_, group, subject, f'${value:04X}.', tuple(prompts), source)


def address_tables():
    port_names = ('port a data', 'port b data', 'port a direction', 'port b direction',
                  'timer a low byte', 'timer a high byte', 'timer b low byte', 'timer b high byte',
                  'tod tenths', 'tod seconds', 'tod minutes', 'tod hours', 'serial data',
                  'interrupt control', 'control a', 'control b')
    for chip in (1, 2):
        for offset, name in enumerate(port_names):
            subject = f'cia {chip} {name}'
            yield address_fact(f'cia.{chip}.{offset}', 'cia', subject, 0xDB00 + 256*chip + offset,
                               (f'where is {subject}', f'what is the address of {subject}',
                                f'give the register location of {subject}', f'what address holds {subject}'))
    voice_names = ('frequency low byte', 'frequency high byte', 'pulse width low byte',
                   'pulse width high nibble', 'control', 'attack and decay', 'sustain and release')
    for voice in (1, 2, 3):
        for offset, name in enumerate(voice_names):
            subject = f'sid voice {voice} {name}'
            yield address_fact(f'sid.voice.{voice}.{offset}', 'sid', subject, 0xD400 + (voice-1)*7 + offset,
                               (f'where is {subject}', f'what address controls {subject}',
                                f'find the register for {subject}', f'give register address for {subject}'))
    for sprite in range(8):
        for name, address in (('x position', 0xD000 + sprite*2), ('y position', 0xD001 + sprite*2),
                              ('individual color', 0xD027 + sprite), ('default pointer', 0x07F8 + sprite)):
            subject = f'sprite {sprite} {name}'
            yield address_fact(f'sprite.reg.{sprite}.{name}', 'sprite', subject, address,
                               (f'where is {subject}', f'what address controls {subject}',
                                f'find the address for {subject}', f'give register address for {subject}'), VIC)
    for row in range(25):
        for col in range(40):
            for region, base in (('screen ram', 0x0400), ('color ram', 0xD800)):
                if (row + col) % 4 == 0 and 0 < col < 39:
                    continue
                subject = f'{region} row {row} column {col}'
                yield address_fact(f'cell.{region}.{row}.{col}', 'screen map', subject, base + row*40 + col,
                                   (f'what is the address for {subject}', f'{region} address at x {col} y {row}',
                                    f'where is {subject} with zero based coordinates',
                                    f'map {region} x {col} y {row} to a byte address'), VIC)
    for bank in range(4):
        for pointer in range(0, 256, 4):
            subject = f'vic bank {bank} sprite pointer {pointer}'
            yield address_fact(f'sprite.data.{bank}.{pointer}', 'sprite map', subject,
                               bank*0x4000 + pointer*64,
                               (f'what pixel data address does {subject} select',
                                f'where is sprite data with pointer {pointer} in vic bank {bank}',
                                f'convert sprite pointer {pointer} in bank {bank} to a data address',
                                f'give the sprite buffer address for bank {bank} pointer {pointer}'), VIC)
    for mode, base in (('upper graphics', 0xD000), ('lower upper', 0xD800)):
        for glyph in range(0, 128, 2):
            subject = f'{mode} character rom glyph {glyph}'
            yield address_fact(f'character-rom.{mode}.{glyph}', 'character map', subject, base + glyph*8,
                               (f'where does {subject} start when char rom is mapped',
                                f'cpu address of glyph {glyph} in the {mode} character rom',
                                f'find the first byte of {subject}', f'char rom location for {subject}'), VIC)
    for bank in range(4):
        for screen in range(16):
            subject = f'vic bank {bank} screen block {screen}'
            yield address_fact(f'vic.screen.{bank}.{screen}', 'vic layout', subject,
                               0x4000*bank + 0x400*screen,
                               (f'where is {subject}', f'screen base for block {screen} in vic bank {bank}',
                                f'give the address of {subject}', f'locate {subject} from d018'), VIC)
        for charset in range(8):
            subject = f'vic bank {bank} character block {charset}'
            yield address_fact(f'vic.charset.{bank}.{charset}', 'vic layout', subject,
                               0x4000*bank + 0x800*charset,
                               (f'where is {subject}', f'charset base for block {charset} in vic bank {bank}',
                                f'give the address of {subject}', f'locate {subject} from d018'), VIC)
    for y in range(0, 200, 5):
        for x in (0, 8, 80, 160, 240, 319):
            address = 0x2000 + (y // 8)*320 + (x // 8)*8 + y % 8
            subject = f'hires bitmap pixel x {x} y {y}'
            yield address_fact(f'bitmap.{x}.{y}', 'bitmap map', subject, address,
                               (f'which byte at base $2000 contains {subject}',
                                f'give bitmap byte address for x {x} y {y} with base $2000',
                                f'locate pixel {x} {y} in a hires bitmap at $2000',
                                f'what byte holds {subject} if the bitmap starts at $2000'), VIC)


def sid_notes():
    names = ('c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b')
    for standard, clock in (('pal', 985248), ('ntsc', 1022727)):
        for octave in range(1, 8):
            for note, name in enumerate(names):
                midi = (octave + 1)*12 + note
                word = round((2**24)*440*2**((midi-69)/12) / clock)
                subject = f'{standard} sid note {name}{octave}'
                yield Fact(f'sid.note.{standard}.{midi}', 'sid pitch', subject,
                           f'${word:04X}.',
                           (f'what frequency word plays {subject}', f'what sid pitch word is {name}{octave} on {standard}',
                            f'convert {subject} to a frequency value', f'give the oscillator word for {subject}'), SID)


def code_facts():
    colors = ('black', 'white', 'red', 'cyan', 'purple', 'green', 'blue', 'yellow',
              'orange', 'brown', 'light red', 'dark gray', 'gray', 'light green', 'light blue', 'light gray')
    for use, register in (('border', 0xD020), ('background', 0xD021),
                          *((f'sprite {i} color', 0xD027+i) for i in range(8))):
        for color, name in enumerate(colors):
            subject = f'{use} to {name}'
            for kind, answer in (('basic', f'10 POKE {register},{color}'),
                                 ('assembler', f'LDA #${color:02X}\nSTA ${register:04X}')):
                yield Fact(f'code.{kind}.{use}.{color}', 'examples', subject, answer,
                           (f'show {kind} code to set {subject}', f'how do i set {subject} in {kind}',
                            f'write a short {kind} example setting {subject}',
                            f'what is the {kind} snippet to change {subject}'), PRG, kind)
    examples = [
        ('basic', 'clear the screen and print ready', '10 PRINT CHR$(147)\n20 PRINT "READY"'),
        ('basic', 'wait for a keypress', '10 GET A$:IF A$="" THEN 10\n20 PRINT A$'),
        ('basic', 'print the numbers 1 to 10', '10 FOR I=1 TO 10:PRINT I:NEXT I'),
        ('basic', 'count down from 10 to 1', '10 FOR I=10 TO 1 STEP -1:PRINT I:NEXT I'),
        ('basic', 'blank every visible screen cell', '10 FOR I=1024 TO 2023:POKE I,32:NEXT I'),
        ('basic', 'display the current border color', '10 PRINT PEEK(53280) AND 15'),
        ('basic', 'run assembly at decimal 49152', '10 SYS 49152'),
        ('basic', 'display the directory on drive 8 in direct mode', 'LOAD "$",8\nLIST'),
        ('basic', 'test fire on joystick port 2', '10 IF (PEEK(56320) AND 16)=0 THEN PRINT "FIRE"'),
        ('basic', 'show the time in jiffies', '10 PRINT TI'),
        ('basic', 'read a number and print its square', '10 INPUT A\n20 PRINT A*A'),
        ('basic', 'store 1 in the first screen cell', '10 POKE 1024,1'),
        ('basic', 'print the value in memory location 49152', '10 PRINT PEEK(49152)'),
        ('basic', 'print random integers from 1 to 6', '10 PRINT INT(RND(1)*6)+1'),
        ('basic', 'store and read three data values', '10 DATA 3,5,7\n20 FOR I=1 TO 3:READ A:PRINT A:NEXT I'),
        ('assembler', 'add the bytes at $02 and $03 into $04', 'CLD\nCLC\nLDA $02\nADC $03\nSTA $04'),
        ('assembler', 'subtract the byte at $03 from $02 into $04', 'CLD\nSEC\nLDA $02\nSBC $03\nSTA $04'),
        ('assembler', 'save and restore a around a subroutine at $c000', 'PHA\nJSR $C000\nPLA'),
        ('assembler', 'poll the fire button on port 2', 'WAIT: LDA $DC00\nAND #$10\nBNE WAIT'),
        ('assembler', 'print a using kernal chrout', 'LDA #$41\nJSR $FFD2'),
        ('assembler', 'clear the screen using kernal chrout', 'LDA #$93\nJSR $FFD2'),
        ('assembler', 'write screen code 1 into the first screen cell', 'LDA #$01\nSTA $0400'),
        ('assembler', 'fill the first screen page with spaces', 'LDX #$00\nLDA #$20\nFILL: STA $0400,X\nINX\nBNE FILL'),
        ('assembler', 'copy the first screen page to $c000', 'LDX #$00\nCOPY: LDA $0400,X\nSTA $C000,X\nINX\nBNE COPY'),
        ('assembler', 'wait for low raster byte 100', 'WAIT: LDA $D012\nCMP #100\nBNE WAIT'),
        ('assembler', 'acknowledge the vic raster interrupt', 'LDA #$01\nSTA $D019'),
        ('assembler', 'mask and acknowledge all cia1 interrupt sources', 'LDA #$7F\nSTA $DC0D\nLDA $DC0D'),
        ('assembler', 'enable sprite zero while preserving other enables', 'LDA $D015\nORA #$01\nSTA $D015'),
        ('assembler', 'disable sprite zero while preserving other enables', 'LDA $D015\nAND #$FE\nSTA $D015'),
        ('assembler', 'set sprite zero color to white and enable it', 'LDA #$01\nSTA $D027\nLDA $D015\nORA #$01\nSTA $D015'),
        ('assembler', 'make the sid volume 15 while preserving filter flags', 'LDA $D418\nAND #$F0\nORA #$0F\nSTA $D418'),
        ('assembler', 'write 440 hz sid voice 1 frequency on pal', 'LDA #$44\nSTA $D400\nLDA #$1D\nSTA $D401'),
        ('assembler', 'select vic bank one while preserving cia2 port bits', 'LDA $DD02\nORA #$03\nSTA $DD02\nLDA $DD00\nAND #$FC\nORA #$02\nSTA $DD00'),
        ('assembler', 'turn on standard hires bitmap mode', 'LDA $D011\nAND #$BF\nORA #$20\nSTA $D011\nLDA $D016\nAND #$EF\nSTA $D016'),
        ('assembler', 'start only sprite 0 at x 64 y 80 using data at 3072 on the default screen',
         'LDA #$30\nSTA $07F8\nLDA #$40\nSTA $D000\nLDA #$50\nSTA $D001\nLDA #$00\nSTA $D010\nLDA #$01\nSTA $D015'),
    ]
    for i, (kind, subject, answer) in enumerate(examples):
        yield Fact(f'example.{i}', 'examples', subject, answer,
                   (f'show {kind} code to {subject}', f'how do i {subject} in {kind}',
                    f'write {kind} to {subject}', f'give me a {kind} example to {subject}'), PRG, kind)


def all_facts():
    return [fact for section in (curated, opcodes, address_tables, sid_notes, code_facts) for fact in section()]


def generate(out):
    out.mkdir(parents=True, exist_ok=True)
    facts = all_facts()
    if len({fact.id for fact in facts}) != len(facts):
        raise ValueError('duplicated fact identity')
    owners = {}
    train, valid = [], []
    for fact in facts:
        seed = int.from_bytes(hashlib.blake2s(fact.id.encode('ascii'), digest_size=2).digest(), 'little')
        first_holdout = 2 if fact.id.startswith(('factual.', 'example.')) else 0
        held = first_holdout + seed % (len(fact.prompts) - first_holdout)
        for i, base in enumerate(fact.prompts):
            forms = question_forms(base)
            # Hold out a complete wording for each fact. Other facts expose the
            # shared question grammar without leaking this prompt/answer pair.
            variants = forms if i != held else [forms[1]]
            for prompt in variants:
                tokens = prompt_tokens(prompt) + answer_tokens(fact.answer)
                if len(tokens) > CONTEXT:
                    raise ValueError(f'over context for {fact.id}: {prompt}')
                owner = owners.get(prompt)
                if owner is not None:
                    if owner.answer != fact.answer:
                        raise ValueError(f'contradictory prompt {prompt}: {owner.id} / {fact.id}')
                    continue
                owners[prompt] = fact
                target = train if i != held else valid
                target.append(dict(fact=fact.id, category=fact.category, kind=fact.kind,
                                   prompt=prompt, answer=fact.answer))
    rng = random.Random(64)
    for name, rows in (('facts', [asdict(f) for f in facts]), ('train', train), ('validation', valid)):
        if name != 'facts':
            rng.shuffle(rows)
        with (out / f'{name}.jsonl').open('w') as file:
            for row in rows:
                file.write(json.dumps(row) + '\n')
    summary = {'facts': len(facts), 'train': len(train), 'validation': len(valid),
               'categories': dict(sorted(Counter(f.category for f in facts).items())),
               'kinds': dict(Counter(f.kind for f in facts))}
    (out / 'stats.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.out), indent=2))
