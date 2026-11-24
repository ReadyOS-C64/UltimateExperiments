"""Evaluate unprefixed English prompts with the trainer or the integer oracle."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random

from tools.oracle import Network
from training.codec import display
from training.evaluate import load_independent, rollout
from training.train import load_checkpoint, load_examples


def normalized(text):
    return ' '.join(text.lower().rstrip('.?!').split())


def choose_examples(path, count, seed):
    grouped = defaultdict(list)
    for row in load_examples(path):
        if row['prompt'][-1] not in '.?':
            grouped[row['category'].split('.', 1)[0]].append(row)
    rng = random.Random(seed)
    remaining = []
    for key in sorted(grouped):
        candidates = grouped[key]
        remaining.extend(rng.sample(candidates, min(count, len(candidates))))
    return remaining


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('--suite', type=Path, default=Path(__file__).with_name('japanese_checks.txt'))
    parser.add_argument('--validation', type=Path)
    parser.add_argument('--train', type=Path, action='append', default=[],
                        help='tag prompts present in a training file (can be repeated)')
    parser.add_argument('--per-domain', type=int, default=12)
    parser.add_argument('--seed', type=int, default=804)
    parser.add_argument('--device', default='mps')
    parser.add_argument('--integer', action='store_true')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rows = choose_examples(args.validation, args.per_domain, args.seed) if args.validation else load_independent(args.suite)

    known = set()
    if args.train:
        wanted = {normalized(row['prompt']) for row in rows}
        for path in args.train:
            with path.open() as stream:
                for line in stream:
                    prompt = normalized(json.loads(line)['prompt'])
                    if prompt in wanted:
                        known.add(prompt)

    if args.integer:
        model = Network(args.model.read_bytes())
        responses = (model.answer(row['prompt'], multiline=True) for row in rows)
    else:
        model, _ = load_checkpoint(args.model, args.device)
        model.eval()
        responses = (display(tokens) for start in range(0, len(rows), 64)
                     for tokens in rollout(model, [row['prompt'] for row in rows[start:start + 64]]))
    groups = defaultdict(Counter)
    report = []
    for row, answer in zip(rows, responses, strict=True):
        seen = normalized(row['prompt']) in known
        correct = normalized(answer) == normalized(row['answer'])
        for group in ('all', row['category'], 'seen' if seen else 'unseen') if args.train else ('all', row['category']):
            groups[group]['total'] += 1
            groups[group]['exact'] += correct
        report.append({**row, 'actual': answer, 'exact': correct, 'seen_in_training': seen})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w') as destination:
        json.dump({'scores': dict(groups), 'responses': report}, destination, indent=2)
        destination.write('\n')
    print(json.dumps({k: dict(v) for k, v in sorted(groups.items()) if v}, indent=2))


if __name__ == '__main__':
    main()
