"""Verify corpus identities, splits, and the machine encodings with ca65."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from training.codec import CONTEXT, answer_tokens, prompt_tokens
from training.corpus import OPCODES
from training.train import load_examples

OPERANDS = ('#$42', '$42', '$42,X', '$42,Y', '$2345', '$2345,X', '$2345,Y',
            '($42,X)', '($42),Y', 'A', '', '*', '($2345)')


def verify_assembly(facts):
    text = ['.setcpu "6502"', '.segment "CODE"']
    expected = []
    for line in OPCODES.strip().splitlines():
        op, *encoded = line.split()
        for entry in encoded:
            byte, mode, _ = entry.split('/')
            marker = f'op_{byte}'
            text.extend([f'{marker}: {op} {OPERANDS[int(mode)]}', f'.res 4-(*-{marker}),$EA'])
            expected.append(int(byte, 16))
    assert len(expected) == len(set(expected)) == 151
    snippets = [fact['answer'] for fact in facts if fact['kind'] == 'assembler']
    for index, answer in enumerate(snippets):
        assert 2 <= len(answer.splitlines()) <= 10 and ';' not in answer
        text.extend([f'.scope snippet_{index}', answer, '.endscope'])
    with tempfile.TemporaryDirectory(prefix='proginfo-corpus-') as folder:
        path = Path(folder)
        source = path / 'test.s'
        obj = path / 'test.o'
        binary = path / 'test.bin'
        source.write_text('\n'.join(text) + '\n')
        subprocess.run(['ca65', '-o', obj, source], check=True)
        subprocess.run(['ld65', '-t', 'none', '-o', binary, obj], check=True)
        data = binary.read_bytes()
        assert list(data[:4*len(expected):4]) == expected
    return len(expected), len(snippets)


def verify_basic(facts):
    patterns = [r'10 POKE (\d+),(\d+)', r'10 PRINT PEEK\(\d+\)( AND 15)?',
                r'10 PRINT (CHR\$\(147\)\n20 PRINT "READY"|TI|INT\(RND\(1\)\*6\)\+1)',
                r'10 SYS 49152', r'10 INPUT A\n20 PRINT A\*A', r'LOAD "\$",8\nLIST',
                r'10 GET A\$:IF A\$="" THEN 10\n20 PRINT A\$',
                r'10 FOR I=(1 TO 10|10 TO 1 STEP -1):PRINT I:NEXT I',
                r'10 FOR I=1024 TO 2023:POKE I,32:NEXT I',
                r'10 IF \(PEEK\(56320\) AND 16\)=0 THEN PRINT "FIRE"',
                r'10 DATA 3,5,7\n20 FOR I=1 TO 3:READ A:PRINT A:NEXT I']
    snippets = [fact['answer'] for fact in facts if fact['kind'] == 'basic']
    for text in snippets:
        assert any(re.fullmatch(pattern, text) for pattern in patterns), text
        poke = re.fullmatch(patterns[0], text)
        if poke:
            assert 0 <= int(poke[1]) < 65536 and 0 <= int(poke[2]) <= 255
    return len(snippets)


def verify(data):
    facts, train, valid = [load_examples(data / f'{name}.jsonl')
                           for name in ('facts', 'train', 'validation')]
    by_id = {fact['id']: fact for fact in facts}
    assert len(by_id) == len(facts) >= 3500
    train_prompts = {row['prompt'] for row in train}
    valid_prompts = {row['prompt'] for row in valid}
    assert len(train_prompts) == len(train) and len(valid_prompts) == len(valid)
    assert not train_prompts & valid_prompts
    for row in train + valid:
        assert row['answer'] == by_id[row['fact']]['answer']
        assert len(prompt_tokens(row['prompt']) + answer_tokens(row['answer'])) <= CONTEXT
    opcode, assembly = verify_assembly(facts)
    return {'facts': len(facts), 'training_wordings': len(train), 'held_out_wordings': len(valid),
            'verified_opcodes': opcode, 'assembled_snippets': assembly,
            'basic_pattern_checks': verify_basic(facts)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.data), indent=2))
