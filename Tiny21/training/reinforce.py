"""Improve C64PROGINFO with group-relative sequence rewards and a supervised anchor."""
import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from training.codec import END, display, prompt_tokens
from training.evaluate import exact, normalize, rollout
from training.train import (atomic_save, batch, encode_examples, load_checkpoint,
                            load_examples, response_loss, training_weights)


def reward(reply, expected):
    text = display(reply)
    if exact(text, expected) and reply and reply[-1] == END:
        return 1.0
    # Small shaping term rewards recoverable partial answers. Only a correct
    # finished answer gets the full reward.
    return 0.2 * SequenceMatcher(None, normalize(expected), normalize(text), autojunk=False).ratio()


def policy_loss(model, prompts, replies, advantages, device, temperature):
    prefixes = list(map(prompt_tokens, prompts))
    lengths = [len(prefix) + len(answer) for prefix, answer in zip(prefixes, replies, strict=True)]
    width = min(model.cfg.ctx_len, (max(lengths) + 15) // 16 * 16)
    padding = torch.zeros((len(lengths), width), device=device, dtype=torch.long)
    for i, (prefix, answer) in enumerate(zip(prefixes, replies, strict=True)):
        padding[i, :lengths[i]] = torch.tensor(prefix + answer, device=device)
    positions = torch.arange(1, width, device=device)[None, :]
    starts = torch.tensor([len(prefix) for prefix in prefixes], device=device)[:, None]
    ends = torch.tensor(lengths, device=device)[:, None]
    mask = (positions >= starts) & (positions < ends)
    log_prob = F.log_softmax(model(padding[:, :-1]).float() / temperature, dim=-1)
    observed = log_prob.gather(-1, padding[:, 1:, None]).squeeze(-1)
    mean = (observed * mask).sum(dim=-1) / mask.sum(dim=-1).clamp_min(1)
    return -(mean * torch.as_tensor(advantages, device=device)).mean()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--steps', default=350, type=int)
    parser.add_argument('--batch', default=12, type=int)
    parser.add_argument('--group', default=4, type=int)
    parser.add_argument('--lr', default=2e-5, type=float)
    parser.add_argument('--temperature', default=1.15, type=float)
    parser.add_argument('--seed', default=91, type=int)
    parser.add_argument('--device', default='mps' if torch.backends.mps.is_available() else 'cpu')
    args = parser.parse_args()
    if args.temperature <= 0:
        parser.error('policy sampling needs a positive temperature')
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    model, initial = load_checkpoint(args.model, args.device)
    model.eval()
    examples = load_examples(args.data / 'train.jsonl')
    data = encode_examples(examples, model.cfg.ctx_len)
    weights = training_weights(examples)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95))
    args.out.mkdir(parents=True, exist_ok=True)
    informative = 0
    with (args.out / 'rewards.jsonl').open('w') as log:
        for step in range(1, args.steps + 1):
            indices = rng.choice(len(examples), size=args.batch, p=weights)
            chosen = [examples[i] for i in indices for _ in range(args.group)]
            prompts = [ex['prompt'] for ex in chosen]
            replies = rollout(model, prompts, temperature=args.temperature, limit=112)
            rewards = np.array([reward(reply, ex['answer']) for reply, ex in zip(replies, chosen, strict=True)],
                               dtype=np.float32).reshape((args.batch, args.group))
            advantages = (rewards - rewards.mean(axis=1, keepdims=True)) / (rewards.std(axis=1, keepdims=True) + 0.02)
            informative += int((rewards.std(axis=1) > 0).sum())
            pg = policy_loss(model, prompts, replies, advantages.ravel(), args.device, args.temperature)
            ce, count = response_loss(model, *batch(data, indices, args.device))
            loss = pg + 0.35 * ce / count
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            if step % 20 == 0 or step == args.steps:
                report = {'step': step, 'reward': float(rewards.mean()),
                          'full_reward_fraction': float((rewards == 1).mean()),
                          'nonconstant_groups': int((rewards.std(axis=1) > 0).sum()),
                          'cumulative_nonconstant_groups': informative,
                          'policy_loss': float(pg.detach()), 'supervised_loss': float(ce.detach() / count)}
                print(json.dumps(report), flush=True)
                log.write(json.dumps(report) + '\n')
                log.flush()
                atomic_save({'model': model.state_dict(), 'model_config': model.cfg.to_dict(),
                             'initial_step': initial['step'], 'step': step, 'stage': 'sequence reward'},
                            args.out / 'latest.pt')


if __name__ == '__main__':
    main()
