"""Export a compatible trained network as TNY2 and a named T64M image."""
import argparse
import json
from pathlib import Path
import struct

import torch

from tools.model import image
from training.train import load_checkpoint


@torch.no_grad()
def checkpoint_bytes(model):
    result = bytearray(struct.pack('<4s4H', b'TNY2', 96, 4, 4, 256))

    def rows(matrix):
        matrix = matrix.detach().cpu()
        scale = (matrix.abs().amax(dim=1) / 127 * (1 << 24)).round().clamp_min(1)
        scale = scale / (1 << 24)
        values = (matrix / scale[:, None]).round().clamp(-127, 127).to(torch.int8).numpy()
        for value, row in zip(scale.tolist(), values):
            result.extend(struct.pack('<f', value))
            result.extend(row.tobytes())

    def gain(norm):
        values = norm.weight.detach().cpu()
        if not torch.isfinite(values).all() or torch.any((values * 4096).round().abs() >= 32768):
            raise ValueError('RMS gain overflows Q4.12')
        result.extend(values.numpy().astype('<f4').tobytes())

    rows(model.tok_emb.weight)
    rows(model.pos_emb.weight)
    for block in model.blocks:
        gain(block.attn_norm)
        for layer in (block.wq, block.wk, block.wv, block.wo):
            rows(layer.weight)
        gain(block.ffn_norm)
        rows(block.w1.weight)
        rows(block.w2.weight)
    gain(model.final_norm)
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--name', default='C64PROGINFO', help='short model name stored in the REU image')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    model, _ = load_checkpoint(args.checkpoint)
    raw = checkpoint_bytes(model)
    name = args.name.upper()
    payload, manifest = image(raw, 'group8-context', model_name=name)
    (args.out / f'{name}.tny2').write_bytes(raw)
    (args.out / f'{name}.BIN').write_bytes(payload)
    (args.out / f'{name}.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{model.param_count():,} parameters, {len(payload):,} bytes')


if __name__ == '__main__':
    main()
