"""Add semantic paraphrases and controlled wording noise to the training split."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import shutil

from training.codec import CONTEXT, answer_tokens, prompt_tokens
from training.evaluate import load_independent
from training.train import load_examples

STOP_WORDS = frozenset('on a the c64 can could would will me i my you please of for to from '
                       'in with it be is are do does what which that something tell about'.split())
ALIASES = (
    (r'\b(?:c64|commodore 64)\b', ('commodore 64', 'c64', 'the machine', 'commodore sixty four')),
    (r'\b(?:cpu|processor)\b', ('microprocessor', 'processor', 'cpu', 'central processing unit')),
    (r'\b(?:assembler|assembly)\b', ('6502 assembly', 'assembler', 'asm', 'machine code')),
    (r'\b(?:basic|basic v2)\b', ('basic', 'commodore basic', 'basic v2')),
    (r'\b(?:code|snippet|example)\b', ('example', 'code', 'snippet', 'routine')),
    (r'\b(?:set|change)\b', ('set', 'make', 'change', 'write')),
    (r'\b(?:screen|display)\b', ('screen', 'display', 'video display')),
    (r'\b(?:address|location)\b', ('address', 'location', 'memory address')),
    (r'\b(?:register|reg)\b', ('register', 'reg', 'hardware register')),
    (r'\b(?:color|colour)\b', ('colour', 'color')),
    (r'\b(?:vic ii|vic2|vic-ii|vic)\b', ('vic ii', 'vic2', 'vic-ii', 'video chip', 'vic')),
    (r'\b(?:sid)\b', ('sid', 'sound chip', 'sid chip')),
    (r'\b(?:ram)\b', ('ram', 'main memory', 'memory')),
    (r'\b(?:irq)\b', ('irq', 'interrupt request', 'maskable interrupt')),
    (r'\b(?:nmi)\b', ('nmi', 'nonmaskable interrupt', 'non maskable interrupt')),
    (r'\b(?:keyboard|keys)\b', ('keyboard', 'keys')),
    (r'\b(?:how many)\b', ('how many', 'what number of', 'number of')),
    (r'\b(?:where is|where are)\b', ('locate', 'where is', 'give the address of')),
)
def noisy_variants(prompt, n, rng):
    words = prompt.strip(' ?').split()
    keywords = [word for word in words if word not in STOP_WORDS]
    variants = []
    if len(keywords) >= 3:
        variants += [' '.join(keywords), 'c64 ' + ' '.join(keywords),
                     ' '.join(keywords) + ' information']
    wrappers = ('can you tell me {prompt}', '{prompt} on a stock c64',
                'i need to know {prompt}', 'in commodore 64 programming, {prompt}',
                'could you explain {prompt}', 'quick question: {prompt}',
                'for my c64, {prompt}', '{prompt} please')
    for i in range(n):
        text = ' '.join(words)
        for pattern, choices in ALIASES:
            if rng.random() < 0.45:
                text = re.sub(pattern, lambda match: rng.choice(choices), text)
        if i % 4 == 0 and len(keywords) >= 4:
            cut = rng.randint(1, len(keywords) - 1)
            text = ' '.join(keywords[cut:] + keywords[:cut])
        elif i % 4 != 1:
            text = rng.choice(wrappers).format(prompt=text)
        variants.append(text + ('?' if i % 2 else ''))
    return variants


def build(source, out, independent):
    facts = load_examples(source / 'facts.jsonl')
    train = load_examples(source / 'train.jsonl')
    valid = load_examples(source / 'validation.jsonl')
    forbidden = {row['prompt'].lower().rstrip('?') for row in valid + load_independent(independent)}
    original = {row['prompt']: row['answer'] for row in train}
    candidates = {}
    contested = set()
    root = Path(__file__).resolve().parent
    manual = {}
    for line in (root / 'paraphrases.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            key, *variants = line.split('|')
            manual[key] = variants

    def add(fact, prompt):
        prompt = ' '.join(prompt.split()).lower()
        if (not prompt or prompt in original or prompt.rstrip('?') in forbidden or
                len(prompt_tokens(prompt) + answer_tokens(fact['answer'])) > CONTEXT):
            return
        row = {'fact': fact['id'], 'category': fact['category'], 'kind': fact['kind'],
               'prompt': prompt, 'answer': fact['answer']}
        prior = candidates.get(prompt)
        if prior is not None and prior['answer'] != row['answer']:
            contested.add(prompt)
        candidates[prompt] = row

    for fact in facts:
        prominent = fact['id'].startswith(('factual.', 'example.'))
        practical = prominent or fact['kind'] != 'fact'
        rng = random.Random(int.from_bytes(hashlib.sha256(fact['id'].encode()).digest()[:8], 'little'))
        seeds = [prompt for prompt in fact['prompts'] if prompt in original]
        for seed in seeds[:4] if practical else seeds[:2]:
            for variant in noisy_variants(seed, 20 if prominent else 11 if practical else 2, rng):
                add(fact, variant)
        if fact['id'].startswith('factual.'):
            for prompt in manual.get(fact['subject'], []):
                for variant in [prompt, *noisy_variants(prompt, 5, rng)]:
                    add(fact, variant)
        if fact['kind'] != 'fact':
            kind = '6502 assembly' if fact['kind'] == 'assembler' else 'c64 basic'
            for stem in (f'using {kind} {fact["subject"]}',
                         f'{kind} example: {fact["subject"]}',
                         f'i need a short {kind} program to {fact["subject"]}',
                         f'write a routine in {kind} to {fact["subject"]}',
                         f'how can {kind} be used to {fact["subject"]}'):
                add(fact, stem)
    added = [row for prompt, row in candidates.items() if prompt not in contested]
    records = train + added
    random.Random(91).shuffle(records)
    out.mkdir(parents=True, exist_ok=True)
    for name in ('facts.jsonl', 'validation.jsonl'):
        shutil.copyfile(source / name, out / name)
    with (out / 'train.jsonl').open('w') as output:
        for row in records:
            output.write(json.dumps(row) + '\n')
    stats = {'facts': len(facts), 'training': len(records), 'added': len(added),
             'validation': len(valid), 'rejected_ambiguous': len(contested)}
    (out / 'stats.json').write_text(json.dumps(stats, indent=2) + '\n')
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--independent', type=Path, default=Path('training/independent_checks.txt'))
    args = parser.parse_args()
    print(json.dumps(build(args.data, args.out, args.independent), indent=2))
