"""Train C64PROGINFO with the response-only objective from c64-dungeon.

The optimizer schedule and masked loss are adapted from c64-dungeon's
python/train.py, copyright (c) 2026 jaydarkseed757. See LICENSE.c64-dungeon.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

import numpy as np
import torch
import torch.nn.functional as F

from training.codec import CONTEXT, VOCAB, answer_tokens, prompt_tokens
from training.model import ModelConfig, ProgInfoModel


def load_examples(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def encode_examples(examples, context):
    tokens = np.zeros((len(examples), context), dtype=np.uint8)
    starts = np.empty(len(examples), dtype=np.int64)
    lengths = np.empty(len(examples), dtype=np.int64)
    for i, example in enumerate(examples):
        prompt = prompt_tokens(example['prompt'])
        ids = prompt + answer_tokens(example['answer'])
        if len(ids) > context or len(prompt) > context - 55:
            raise ValueError(f'example exceeds the console context {example!r}')
        tokens[i, :len(ids)] = ids
        starts[i], lengths[i] = len(prompt), len(ids)
    return tokens, starts, lengths


def training_weights(examples, balance=0.5):
    """Keep generated address tables from dominating the training batches."""
    counts = Counter(ex['category'] for ex in examples)
    weights = np.array([(3.0 if ex['fact'].startswith(('factual.', 'example.')) else 1.0)
                        / counts[ex['category']] ** balance for ex in examples])
    return weights / weights.sum()


def batch(data, indices, device):
    tokens, starts, lengths = data
    n = lengths[indices]
    width = min(tokens.shape[1], (int(n.max()) + 15) // 16 * 16)
    return tuple(torch.as_tensor(item, dtype=torch.long, device=device)
                 for item in (tokens[indices, :width], starts[indices], n))


def response_loss(model, ids, starts, lengths):
    logits = model(ids[:, :-1])
    targets = ids[:, 1:]
    positions = torch.arange(1, ids.shape[1], device=ids.device)[None, :]
    mask = (positions >= starts[:, None]) & (positions < lengths[:, None])
    losses = F.cross_entropy(logits.transpose(1, 2).float(), targets, reduction='none')
    return (losses * mask).sum(), mask.sum()


@torch.no_grad()
def validation_loss(model, data, indices, device, batch_size):
    model.eval()
    total, count = 0., 0
    for start in range(0, len(indices), batch_size):
        loss, n = response_loss(model, *batch(data, indices[start:start + batch_size], device))
        total += float(loss)
        count += int(n)
    model.train()
    return total / count


def learning_rate(step, steps, peak):
    warmup = min(300, max(1, steps // 10))
    if step < warmup:
        return peak * (step + 1) / warmup
    progress = (step - warmup) / max(1, steps - warmup)
    return peak * (0.1 + 0.45 * (1 + math.cos(math.pi * progress)))


def load_checkpoint(path, device='cpu', qat=None):
    payload = torch.load(path, weights_only=True, map_location=device)
    config = ModelConfig(**payload['model_config'])
    if qat is not None:
        config.qat = qat
    model = ProgInfoModel(config).to(device)
    model.load_state_dict(payload['model'])
    return model, payload


def atomic_save(payload, path):
    temporary = path.with_suffix('.tmp')
    torch.save(payload, temporary)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=12000)
    parser.add_argument('--batch', type=int, default=64)
    parser.add_argument('--eval-every', type=int, default=750)
    parser.add_argument('--lr', type=float, default=0.001)
    parser.add_argument('--context', type=int, default=CONTEXT)
    parser.add_argument('--seed', type=int, default=64)
    parser.add_argument('--device', default='mps' if torch.backends.mps.is_available() else 'cpu')
    parser.add_argument('--init', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--qat', action='store_true')
    parser.add_argument('--boost-fact', help='increase the sample rate of one new fact during a short fine-tune')
    parser.add_argument('--category-balance', type=float, default=0.5,
                        help='category sampling exponent, from 0 (by size) to 1 (equal categories)')
    parser.add_argument('--language-share', type=float, default=0.08,
                        help='fraction of batch samples reserved for supplemental language and logic')
    args = parser.parse_args()
    if args.resume and args.init:
        parser.error('--resume and --init are mutually exclusive')
    if not 0 <= args.category_balance <= 1:
        parser.error('--category-balance must be between zero and one')
    if not 0 <= args.language_share < 1:
        parser.error('--language-share must be at least zero and below one')
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    latest = args.out / 'latest.pt'
    if args.resume or args.init:
        model, payload = load_checkpoint(latest if args.resume else args.init, args.device, args.qat)
    else:
        model = ProgInfoModel(ModelConfig(VOCAB, ctx_len=args.context, qat=args.qat)).to(args.device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.01)
    start, best = 0, float('inf')
    if args.resume:
        optimizer.load_state_dict(payload['optimizer'])
        start, best = payload['step'], payload['best_loss']
        rng.bit_generator.state = payload['rng']
    examples = load_examples(args.data / 'train.jsonl')
    train = encode_examples(examples, model.cfg.ctx_len)
    weights = training_weights(examples, args.category_balance)
    support = np.array([row['fact'].startswith(('language.', 'logic.')) for row in examples])
    if support.any():
        if support.all():
            raise ValueError('language and logic examples require a C64 technical corpus')
        weights[support] *= args.language_share / weights[support].sum()
        weights[~support] *= (1 - args.language_share) / weights[~support].sum()
    if args.boost_fact:
        selected = np.array([row['fact'] == args.boost_fact for row in examples])
        if not selected.any():
            raise ValueError(f'no training examples for {args.boost_fact}')
        # Reserve one eighth of the batch distribution for the new example.
        weights *= 0.875
        weights[selected] += 0.125 / selected.sum()
    valid = encode_examples(load_examples(args.data / 'validation.jsonl'), model.cfg.ctx_len)
    indices = np.random.default_rng(args.seed).permutation(len(valid[0]))[:768]
    n_train = len(train[0])
    print(f'{model.param_count():,} parameters, {n_train:,} train sequences, '
          f'{len(valid[0]):,} validation, device={args.device}, qat={args.qat}', flush=True)
    started = time.monotonic()
    with (args.out / 'log.jsonl').open('a') as log:
        for step in range(start + 1, args.steps + 1):
            lr = learning_rate(step - 1, args.steps, args.lr)
            optimizer.param_groups[0]['lr'] = lr
            indices_train = rng.choice(n_train, size=args.batch, p=weights)
            loss, n = response_loss(model, *batch(train, indices_train, args.device))
            loss = loss / n
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            if step % 100 == 0 or step == 1:
                print(f'{step}: train={float(loss):.4f} elapsed={time.monotonic() - started:.1f}s', flush=True)
            if step % args.eval_every == 0 or step == args.steps:
                val = validation_loss(model, valid, indices, args.device, args.batch)
                improved = val < best
                best = min(best, val)
                report = {'step': step, 'train_loss': float(loss), 'validation_loss': val, 'lr': lr}
                print(json.dumps(report), flush=True)
                log.write(json.dumps(report) + '\n')
                log.flush()
                state = {'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                         'model_config': model.cfg.to_dict(), 'step': step, 'best_loss': best,
                         'rng': rng.bit_generator.state}
                atomic_save(state, latest)
                if improved:
                    atomic_save(state, args.out / 'best.pt')


if __name__ == '__main__':
    main()
