"""Exercise model switching and multiline rendering in the native Peddle console."""
import argparse
from pathlib import Path

from probe.check_console import screen, set_keys, type_chars
from probe.check_local import check_uci, load_native, seed_pal_clock
from tools.peddle import BUILD, Machine
from tools.run_peddle import STEP_LIMIT

TINY = 0
PROGRAMMER = 0x100000
JAPANESE = 0x200000
CRC_LIMIT = 12_000_000


def key(machine, matrix, row, expected):
    set_keys(matrix, (0, row))
    machine.run('keyboard_input')
    machine.run('keyboard_input')
    assert machine.accumulator == expected
    flags = machine.run('console_edit', expected, instruction_limit=CRC_LIMIT)[4]
    assert not flags & 1
    set_keys(matrix)
    machine.run('keyboard_input')
    machine.run('keyboard_input')


def check_ten_lines(machine):
    machine.run('clear_answer')
    machine.put('answer_cursor', 0x0400 + 40*12 + 1, 2)
    machine.put('answer_column', 1)
    lines = ['LDA #$30', 'STA $07F8', 'LDA #$40', 'STA $D000', 'LDA #$50',
             'STA $D001', 'LDA #$00', 'STA $D010', 'LDA #$01', 'STA $D015']
    for char in '\r'.join(lines):
        machine.put('question_char', ord(char))
        machine.run('render_answer_char')
    for index, line in enumerate(lines):
        start = 0x0400 + 40*(12 + index) + (index == 0)
        assert bytes(machine.ram[start:start + len(line)]) == line.encode('ascii')
    assert bytes(machine.ram[0x0400 + 40*22:0x0400 + 40*23]) == b' ' * 40


def check_japanese(machine, matrix, data, prompt, expected):
    machine.preload(data, JAPANESE)
    machine.reu[JAPANESE + len(data) - 1] ^= 1
    key(machine, matrix, 6, 0x87)
    assert machine.get('active_model', 1) == 1
    assert machine.get('model_bank', 1) == 0x10
    assert screen(machine, 10).startswith('Load failed.')
    machine.reu[JAPANESE + len(data) - 1] ^= 1

    key(machine, matrix, 6, 0x87)
    assert machine.get('active_model', 1) == 2
    assert machine.get('model_bank', 1) == 0x20
    assert machine.get('model_context', 1) == data[52]
    assert machine.get('token_pos', 1) == 0
    assert screen(machine, 5).startswith('Model: English to Japanese (romaji)')
    assert screen(machine, 6).startswith('Type an English sentence to translate')
    assert type_chars(machine, matrix, prompt + '\r')
    machine.run('run_answer', instruction_limit=STEP_LIMIT * data[52])
    actual = screen(machine, 12, 399)
    if '\n' in expected:  # A fixture image can contain C64PROGINFO code.
        lines = [actual[:39].strip()]
        lines.extend(actual[i:i+40].strip() for i in range(39, len(actual), 40))
        actual = '\n'.join(lines).strip()
    assert screen(machine, 10).startswith('Answer complete.')
    assert actual.rstrip() == expected, (actual.rstrip(), expected)
    assert bytes(machine.reu[JAPANESE:JAPANESE + len(data)]) == data
    print('F5, third-slot CRC recovery, and the native translation screen verified.')


def check(bundle, prompt, expected, *, japanese_prompt='i eat an apple',
          japanese_expected='watashi wa ringo o tabemasu'):
    machine = Machine(BUILD / 'group8')
    try:
        program = load_native(machine, bundle)
        tiny = (bundle / 'MODEL.BIN').read_bytes()
        prog = (bundle / 'C64PROGINFO.BIN').read_bytes()
        machine.put('reu_banks', 32)
        machine.preload(tiny, TINY)
        machine.preload(prog, PROGRAMMER)
        assert machine.reu[PROGRAMMER + 53:PROGRAMMER + 64] == list(b'C64PROGINFO')
        assert not machine.run('check_resident_model', instruction_limit=CRC_LIMIT)[4] & 1
        assert machine.get('active_model', 1) == 0
        matrix = machine.keyboard_matrix()
        machine.run('screen_init')
        assert screen(machine, 1).startswith('C64 LLM - Little Language Model')
        prompt_color = 0xD800 + 40*7
        assert all(color & 15 == 7 for color in machine.ram[prompt_color:prompt_color+80])
        machine.run('console_prepare')
        seed_pal_clock(machine)
        assert screen(machine, 5).startswith('Model: Tiny 2.1')
        assert screen(machine, 10).startswith('Model ready.')

        machine.reu[PROGRAMMER + len(prog) - 1] ^= 1
        key(machine, matrix, 5, 0x86)
        assert machine.get('active_model', 1) == 0
        assert machine.get('model_bank', 1) == 0
        assert screen(machine, 10).startswith('Load failed.')
        machine.reu[PROGRAMMER + len(prog) - 1] ^= 1

        key(machine, matrix, 5, 0x86)
        assert screen(machine, 5).startswith('Model: C64PROGINFO')
        assert machine.get('active_model', 1) == 1
        assert machine.get('model_bank', 1) == 0x10
        assert machine.get('model_context', 1) == prog[52]
        assert machine.get('token_pos', 1) == 0
        assert type_chars(machine, matrix, prompt + '\r')
        machine.run('run_answer', instruction_limit=STEP_LIMIT * prog[52])
        assert screen(machine, 10).startswith('Answer complete.'), (
            screen(machine, 10), screen(machine, 12), machine.get('token_pos', 1)
        )
        for index, text in enumerate(expected.splitlines()):
            start = 0x0400 + 40*(12 + index) + (index == 0)
            actual = ''.join(chr(code + 96 if 1 <= code <= 26 else code)
                             for code in machine.ram[start:start + len(text)])
            assert actual == text, (index, actual, text)
        assert screen(machine, 22).startswith('Elapsed ')
        machine.run('render_prompt')
        assert screen(machine, 7, 79) == prompt[-72:].ljust(79)
        assert not type_chars(machine, matrix, '\r\b')
        assert screen(machine, 7, 79) == prompt[-72:].ljust(79)
        assert not type_chars(machine, matrix, 'n')
        assert screen(machine, 7, 79) == 'n' + chr(0xA0) + ' ' * 77
        check_ten_lines(machine)
        third = bundle / 'E2JROMAJI.BIN'
        if third.is_file():
            japanese = third.read_bytes()
            check_japanese(machine, matrix, japanese, japanese_prompt, japanese_expected)
        key(machine, matrix, 4, 0x85)
        assert screen(machine, 5).startswith('Model: Tiny 2.1')
        assert machine.get('model_context', 1) == 128
        assert machine.get('token_pos', 1) == machine.get('active_model', 1) == 0
        assert bytes(machine.reu[TINY:TINY + len(tiny)]) == tiny
        assert bytes(machine.reu[PROGRAMMER:PROGRAMMER + len(prog)]) == prog
        print('F3 and F1, wrong CRC recovery, distinct REU slots and multiline display verified.')
        check_uci(bundle, machine.symbols, program, len(prog), slot=1)
        if third.is_file():
            check_uci(bundle, machine.symbols, program, len(japanese), slot=2)
    finally:
        machine.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--prompt', default='show assembler code to set border to red')
    parser.add_argument('--expected', default='LDA #$02\nSTA $D020')
    parser.add_argument('--japanese-prompt', default='i eat an apple')
    parser.add_argument('--japanese-expected', default='watashi wa ringo o tabemasu')
    args = parser.parse_args()
    check(args.bundle, args.prompt, args.expected, japanese_prompt=args.japanese_prompt,
          japanese_expected=args.japanese_expected)
