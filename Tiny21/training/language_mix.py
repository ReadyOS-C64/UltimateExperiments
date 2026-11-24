"""Expand C64 questions and add a small English and logic curriculum."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import shutil

from training.codec import CONTEXT, answer_tokens, prompt_tokens

ROOT = Path(__file__).resolve().parent
LEXICON = ROOT / 'tiny21_language.tsv'

# Keep the meaning of the source question. Terms like C64 register names,
# flag polarity, numbers, address literals, and CPU mode names stay intact.
REWRITES = {
    'c64': ('commodore 64', 'c-64'),
    'assembler': ('assembly', '6502 asm', 'machine language'),
    'basic': ('commodore basic', 'basic v2'),
    'where is': ('what address holds', 'where do i find', 'give the location of'),
    'how many': ('what is the number of', 'give the count of'),
    'what does': ('explain what', 'tell me what'),
    'how do i': ('how can i', 'what is the way to'),
    'what is the': ('tell me the', 'give me the', 'identify the'),
    'bit number': ('bit position', 'numbered bit'),
    'color': ('colour',),
    'vic ii': ('vic-ii', 'vic2'),
    'zero page': ('zeropage', 'page zero'),
    'cpu': ('processor', 'microprocessor'),
    'sprites': ('hardware sprites',),
    'high resolution': ('hires', 'high-resolution'),
    'memory location': ('ram address', 'memory address'),
    'multicolor': ('multicolour',),
    'low byte': ('least significant byte', 'lower byte'),
    'high byte': ('most significant byte', 'upper byte'),
}
FRAMES = (
    '{question}', 'could you tell me {question}', 'on a stock machine, {question}',
    'for a commodore 64 program, {question}', 'in c64 terms, {question}',
    'i need to know {question}', 'in a c64 programming reference, {question}',
    'when working on a c64, {question}', '{question} on original c64 hardware',
    'can you explain {question}', 'for this machine, {question}',
    'in the c64 manual, {question}', '{question} on my commodore 64',
    'while writing c64 code, {question}', 'for the commodore 64, {question}',
    'i am writing a c64 program and want to know {question}',
)
TOPICS = {
    'architecture': 'memory and cpu', 'vic': 'vic ii video', 'sprite': 'sprites',
    'interrupt': 'interrupts', 'cia': 'cia registers', 'sid': 'sid audio',
    'basic': 'basic v2', 'asm': '6510 assembler', 'kernal': 'kernal routines',
}
ENGLISH = {
    'opposite': ('what is the opposite of {word}', 'which word means the reverse of {word}',
                 'replace {word} with a word that reverses its meaning', 'give the antonym of {word}',
                 'which word expresses the inverse of {word}'),
    'synonym': ('what is another word for {word}', 'give a synonym for {word}',
                'which word can stand in for {word}', 'express {word} using a similar word',
                'which word has a similar meaning to {word}'),
    'plural': ('what is the plural of {word}', 'give the plural form of {word}',
               'change one {word} to the plural', 'make the word {word} plural',
               'how do you write {word} when there is more than one'),
    'past': ('what is the past tense of {word}', 'write the past tense of {word}',
             'change the verb {word} to past tense', 'give the past form of {word}',
             'which form of {word} describes an action in the past'),
}


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_rows(path, rows):
    with path.open('w') as out:
        for row in rows:
            out.write(json.dumps(row) + '\n')


def canonical(prompt):
    return ' '.join(prompt.lower().rstrip(' ?!.').split())


def record(fact, prompt):
    return {'fact': fact['id'], 'category': fact['category'], 'kind': fact.get('kind', 'fact'),
            'answer': fact['answer'], 'prompt': prompt}


def english_facts():
    for line in LEXICON.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        relation, word, answer = line.split('\t')
        stems = [frame.format(word=word) for frame in ENGLISH[relation]]
        yield {'id': f'language.{relation}.{word}', 'category': f'english {relation}',
               'answer': answer.capitalize() + '.', 'source': 'Tiny 2.1 English subset'}, stems


def logic_facts():
    # Restrict the operands to a byte so BASIC and the 6510 agree on AND/OR.
    for op, compute, description in (('and', int.__and__, 'both bits set'),
                                     ('or', int.__or__, 'either bit set'),
                                     ('eor', int.__xor__, 'exactly one bit set')):
        for a in (0, 1, 3, 15, 16, 32, 65, 127, 128, 255):
            for b in (0, 1, 2, 4, 7, 15, 31, 64, 128, 255):
                result = compute(a, b)
                yield ({'id': f'logic.{op}.{a}.{b}', 'category': 'c64 bit logic',
                        'answer': f'${result:02X}.', 'source': 'C64 6510 byte arithmetic'},
                       [f'what byte does 6510 {op} produce for ${a:02x} and ${b:02x}',
                        f'on the c64 use {op} on ${a:02x} with ${b:02x} and give the result',
                        f'after {op} #${b:02x} with a holding ${a:02x} what byte remains',
                        f'combine ${a:02x} and ${b:02x} using {op} ({description}) on the 6510'])
    for value in range(0, 256, 17):
        for bit in range(8):
            for action in ('set', 'clear'):
                mask = 1 << bit
                result = value | mask if action == 'set' else value & ~mask
                alternative = 'turn on' if action == 'set' else 'turn off'
                yield ({'id': f'logic.{action}.{value}.{bit}', 'category': 'c64 bit logic',
                        'answer': f'${result:02X}.', 'source': 'C64 6510 byte arithmetic'},
                       [f'c64 byte ${value:02x} with bit {bit} {action} gives what byte',
                        f'{action} bit {bit} of ${value:02x} and give the result in hex',
                        f'in 6510 code {alternative} bit {bit} in ${value:02x}',
                        f'what is the result when i {action} bit {bit} in ${value:02x}'])
    for branch, flag, when_set in (('beq', 'zero', True), ('bne', 'zero', False),
                                   ('bcs', 'carry', True), ('bcc', 'carry', False),
                                   ('bmi', 'negative', True), ('bpl', 'negative', False),
                                   ('bvs', 'overflow', True), ('bvc', 'overflow', False)):
        for state in ('set', 'clear'):
            taken = (state == 'set') == when_set
            equivalent = 'one' if state == 'set' else 'zero'
            yield ({'id': f'logic.{branch}.{state}', 'category': 'c64 branch logic',
                    'answer': 'Branch taken.' if taken else 'Branch not taken.', 'source': 'MOS 6502 instruction set'},
                   [f'does {branch} jump when the 6510 {flag} flag is {state}',
                    f'if the {flag} flag is {equivalent} will {branch} branch',
                    f'for {branch} with {flag} {state} is the branch taken',
                    f'decide whether {branch} branches if the {flag} flag is {state}'])


def generate(source, output, checks):
    base = read_rows(source / 'train.jsonl')
    facts = read_rows(source / 'facts.jsonl')
    valid = read_rows(source / 'validation.jsonl')
    reserved = {canonical(row['prompt']) for row in valid}
    for file in checks:
        for line in file.read_text().splitlines():
            if line and not line.startswith('#'):
                reserved.add(canonical(line.split('|')[2]))
    initial = {canonical(row['prompt']) for row in base}
    new = {}
    conflicts = set()

    def add(fact, prompt):
        key = canonical(prompt)
        if key in reserved or key in initial:
            return
        if len(prompt_tokens(prompt)) > CONTEXT - 55 or len(prompt_tokens(prompt) + answer_tokens(fact['answer'])) > CONTEXT:
            return
        if key in new and new[key]['answer'] != fact['answer']:
            conflicts.add(key)
        new[key] = record(fact, prompt)

    preferred = {word: answer for relation, word, answer in (
        line.split('\t') for line in LEXICON.read_text().splitlines() if line and not line.startswith('#')
    ) if relation == 'synonym' and word in {'build', 'choose', 'close', 'fast', 'fix', 'nearly'}}
    rewrite = {**REWRITES, **{word: (alt,) for word, alt in preferred.items()}}
    lex_patterns = [(re.compile(r'(?<![\w$])' + pattern + r'(?![\w])'), choices)
                    for pattern, choices in rewrite.items()]
    for fact in facts:
        seed = int.from_bytes(hashlib.sha256(fact['id'].encode()).digest()[:8], 'little')
        rng = random.Random(seed)
        stems = [canonical(stem) for stem in fact['prompts'] if canonical(stem) not in reserved]
        for stem in stems:
            # Keep a mixture of genuinely reworded questions and changed contexts.
            variants = [stem]
            for pattern, choices in lex_patterns:
                if pattern.search(stem):
                    variants.extend(pattern.sub(choice, stem) for choice in choices)
            for _ in range(3):
                combined = stem
                for pattern, choices in lex_patterns:
                    if rng.random() < 0.4:
                        combined = pattern.sub(rng.choice(choices), combined)
                variants.append(combined)
            for index, variant in enumerate(dict.fromkeys(variants)):
                frames = FRAMES if index == 0 else rng.sample(FRAMES, 4)
                for frame in frames:
                    add(fact, frame.format(question=variant))
                if fact['category'] in TOPICS:
                    add(fact, f'in {TOPICS[fact["category"]]} programming, {variant}')

    expanded = base + [row for key, row in new.items() if key not in conflicts]
    support, support_valid, extra_facts = [], [], []
    prompts = {canonical(row['prompt']) for row in expanded}
    for fact, stems in (*english_facts(), *logic_facts()):
        extra_facts.append({**fact, 'kind': 'fact'})
        held = int.from_bytes(hashlib.blake2s(fact['id'].encode(), digest_size=2).digest(), 'little') % len(stems)
        for i, stem in enumerate(stems):
            for prompt in ([stem + '?'] if i == held else [stem, stem + '?', 'for c64 programming, ' + stem]):
                if canonical(prompt) in reserved or prompt in prompts:
                    continue
                prompts.add(prompt)
                (support_valid if i == held else support).append(record(fact, prompt))
    rng = random.Random(612)
    for rows in (expanded, support, support_valid):
        rng.shuffle(rows)
    for name, include_support in [('control', False), ('mixed', True)]:
        out = output / name
        out.mkdir(parents=True, exist_ok=True)
        write_rows(out / 'train.jsonl', expanded + (support if include_support else []))
        shutil.copyfile(source / 'validation.jsonl', out / 'validation.jsonl')
        write_rows(out / 'facts.jsonl', facts + (extra_facts if include_support else []))
    write_rows(output / 'language-validation.jsonl', support_valid)
    stats = {'technical_facts': len(facts), 'original_technical_questions': len(base),
             'expanded_technical_questions': len(expanded), 'english_relations': len(list(english_facts())),
             'logic_records': len(list(logic_facts())), 'auxiliary_questions': len(support),
             'auxiliary_held_out': len(support_valid), 'rejected_conflicting_rewordings': len(conflicts)}
    (output / 'stats.json').write_text(json.dumps(stats, indent=2) + '\n')
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    checks = ('independent_checks.txt', 'native_checks.txt', 'language_transfer_checks.txt',
              'novel_logic_checks.txt')
    print(json.dumps(generate(args.data, args.out, [ROOT / name for name in checks]), indent=2))
