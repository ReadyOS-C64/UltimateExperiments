"""Score generated C64PROGINFO responses on previously unseen question wordings."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import re

import numpy as np
import torch

from tools.oracle import Network
from training.codec import END, display, prompt_tokens
from training.train import load_checkpoint, load_examples


def normalize(text):
    return '\n'.join(re.sub(r'\s+', ' ', line.strip()).lower().rstrip('.')
                     for line in text.strip().splitlines())


def exact(actual, expected):
    return normalize(actual) == normalize(expected)


def stratified(examples, per_category, seed=64):
    groups = defaultdict(list)
    for row in examples:
        key = row['kind'] if row['kind'] != 'fact' else row['category']
        groups[key].append(row)
    rng = random.Random(seed)
    return [row for key in sorted(groups)
            for row in rng.sample(groups[key], min(per_category, len(groups[key])))]


def load_independent(path):
    rows = []
    for line in path.read_text().splitlines():
        if line and not line.startswith('#'):
            category, kind, prompt, answer = line.split('|')
            rows.append({'category': category, 'kind': kind, 'prompt': prompt,
                         'answer': answer.replace('\\n', '\n')})
    return rows


@torch.no_grad()
def rollout(model, prompts, *, temperature=0., limit=112):
    """Generate independently for each right-padded prompt with causal masking."""
    device = next(model.parameters()).device
    rows = [prompt_tokens(text) for text in prompts]
    ids = torch.zeros((len(rows), model.cfg.ctx_len), device=device, dtype=torch.long)
    lengths = np.array([len(row) for row in rows])
    for i, row in enumerate(rows):
        ids[i, :len(row)] = torch.tensor(row, device=device)
    sample_rows = torch.arange(len(rows), device=device)
    pending = lengths < model.cfg.ctx_len
    answers = [[] for _ in rows]
    for _ in range(limit):
        if not pending.any():
            break
        width = min(model.cfg.ctx_len, (int(lengths.max()) + 15) // 16 * 16)
        last = torch.from_numpy(lengths - 1).to(device)
        scores = model(ids[:, :width])[sample_rows, last].float()
        if temperature:
            chosen = torch.multinomial(torch.softmax(scores / temperature, dim=-1), 1)[:, 0]
        else:
            chosen = scores.argmax(dim=-1)
        next_ids = chosen.cpu().tolist()
        write_pos = torch.from_numpy(np.minimum(lengths, model.cfg.ctx_len - 1)).to(device)
        ids[sample_rows, write_pos] = chosen
        for i in np.flatnonzero(pending):
            answers[i].append(next_ids[i])
        lengths += pending
        pending &= (lengths < model.cfg.ctx_len) & (np.array(next_ids) != END)
    return answers


def evaluate(rows, predict, output=None, batch_size=32):
    scores = defaultdict(lambda: {'exact': 0, 'total': 0})
    results = []
    for first in range(0, len(rows), batch_size):
        batch = rows[first:first + batch_size]
        replies = predict([row['prompt'] for row in batch])
        for row, actual in zip(batch, replies, strict=True):
            correct = exact(actual, row['answer'])
            key = row['kind'] if row['kind'] != 'fact' else row['category']
            for group in ('all', key):
                scores[group]['exact'] += int(correct)
                scores[group]['total'] += 1
            results.append({**row, 'actual': actual, 'exact': correct})
    result = {'scores': dict(sorted(scores.items())), 'responses': results}
    if output:
        output.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    questions = parser.add_mutually_exclusive_group(required=True)
    questions.add_argument('--validation', type=Path)
    questions.add_argument('--independent', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--per-category', type=int, default=20)
    parser.add_argument('--batch', type=int, default=32)
    parser.add_argument('--integer', action='store_true')
    parser.add_argument('--device', default='mps' if torch.backends.mps.is_available() else 'cpu')
    args = parser.parse_args()
    rows = (load_independent(args.independent) if args.independent else
            stratified(load_examples(args.validation), args.per_category))
    if args.integer:
        model = Network(args.model.read_bytes())

        def predict(prompts):
            return [model.answer(prompt, multiline=True) for prompt in prompts]
    else:
        model, _ = load_checkpoint(args.model, args.device)
        model.eval()

        def predict(prompts):
            return list(map(display, rollout(model, prompts)))

    result = evaluate(rows, predict, args.out, args.batch)
    print(json.dumps(result['scores'], indent=2))


if __name__ == '__main__':
    main()
