"""Tiny21-compatible transformer adapted from c64-dungeon's PyTorch decoder.

Copyright (c) 2026 jaydarkseed757. See LICENSE.c64-dungeon.

Matches Tiny21's four pre-normalized blocks and tied output embedding:
  - learned token and absolute position embeddings
  - pre-RMSNorm blocks: multi-head causal attention, ReLU feed-forward
  - no biases anywhere
  - final RMSNorm; output head tied to the token embedding

With qat=True (Milestone 8) the forward pass rounds like the C64 engine, so
training learns weights that survive the conversion (quantization-aware
training, straight-through gradients):
  - every weight matrix and embedding to int8 per row
  - keys and values to signed int8 using a single Q16.16 peak per token
The other integer steps (15-bit packing, Q16.16 outputs, the exp table) are
far finer and are not modelled.
"""
from dataclasses import dataclass, asdict

import torch
import torch.nn as nn
import torch.nn.functional as F

@dataclass
class ModelConfig:
    vocab_size: int
    ctx_len: int = 224
    d_model: int = 96
    n_layers: int = 4
    n_heads: int = 4
    d_ff: int = 256
    rms_eps: float = 1e-5
    dropout: float = 0.0
    qat: bool = False

    @property
    def head_dim(self):
        return self.d_model // self.n_heads

    def validate(self):
        geometry = (self.vocab_size, self.d_model, self.n_layers, self.n_heads, self.d_ff)
        if geometry != (97, 96, 4, 4, 256) or not 128 <= self.ctx_len <= 255:
            raise ValueError("model geometry must match the Tiny21 integer engine")
        return self

    def to_dict(self):
        return asdict(self)


def fake_quant_rows(w):
    """int8 per row, symmetric (scale max|w| / 127); straight-through gradient."""
    scale = (w.detach().abs().amax(dim=1, keepdim=True) / 127 * (1 << 24)).round()
    scale = scale.clamp_min(1) / (1 << 24)
    q = torch.round(w / scale).clamp(-127, 127) * scale
    return w + (q - w).detach()


def fake_quant_kv(x):
    """Simulate Tiny21's Q16.16 output and the shared peak over all 96 lanes."""
    fixed = (x.detach() * 65536).round()
    peak = fixed.abs().amax(dim=-1, keepdim=True)
    scaled = fixed * 127 / peak.clamp_min(1)
    packed = scaled.sign() * (scaled.abs() + 0.5).floor()
    q = packed * peak / (127 * 65536)
    return x + (q - x).detach()


def qweight(layer, qat):
    return fake_quant_rows(layer.weight) if qat else layer.weight


class RMSNorm(nn.Module):
    def __init__(self, d, eps):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d))

    def forward(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps) * self.weight


class Block(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        d = cfg.d_model
        self.cfg = cfg
        self.attn_norm = RMSNorm(d, cfg.rms_eps)
        self.wq = nn.Linear(d, d, bias=False)
        self.wk = nn.Linear(d, d, bias=False)
        self.wv = nn.Linear(d, d, bias=False)
        self.wo = nn.Linear(d, d, bias=False)
        self.ffn_norm = RMSNorm(d, cfg.rms_eps)
        self.w1 = nn.Linear(d, cfg.d_ff, bias=False)
        self.w2 = nn.Linear(cfg.d_ff, d, bias=False)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x):
        b, t, d = x.shape
        h, hd = self.cfg.n_heads, self.cfg.head_dim
        qat = self.cfg.qat
        lin = lambda layer, inp: F.linear(inp, qweight(layer, qat))  # noqa: E731
        n = self.attn_norm(x)
        q = lin(self.wq, n).view(b, t, h, hd).transpose(1, 2)
        k = lin(self.wk, n)
        v = lin(self.wv, n)
        if qat:
            k, v = fake_quant_kv(k), fake_quant_kv(v)
        k = k.view(b, t, h, hd).transpose(1, 2)
        v = v.view(b, t, h, hd).transpose(1, 2)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True,
                                           dropout_p=self.cfg.dropout if self.training else 0.0)
        x = x + self.drop(lin(self.wo, a.transpose(1, 2).reshape(b, t, d)))
        x = x + self.drop(lin(self.w2, F.relu(lin(self.w1, self.ffn_norm(x)))))
        return x


class ProgInfoModel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg.validate()
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.pos_emb = nn.Embedding(cfg.ctx_len, cfg.d_model)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.n_layers))
        self.final_norm = RMSNorm(cfg.d_model, cfg.rms_eps)
        self.apply(self._init)

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)

    def forward(self, ids):
        t = ids.shape[1]
        if t > self.cfg.ctx_len:
            raise ValueError(f"sequence length {t} exceeds ctx_len {self.cfg.ctx_len}")
        if self.cfg.qat:
            tok, pos = fake_quant_rows(self.tok_emb.weight), fake_quant_rows(self.pos_emb.weight)
        else:
            tok, pos = self.tok_emb.weight, self.pos_emb.weight
        x = F.embedding(ids, tok) + pos[:t]
        for block in self.blocks:
            x = block(x)
        return self.final_norm(x) @ tok.T

    def param_count(self):
        return sum(p.numel() for p in self.parameters())


@torch.no_grad()
def generate(model, prompt_ids, max_new=120, temperature=0.0, top_k=0, eos_id=2,
             banned=(), generator=None):
    """Float reference generation. Returns the new token ids (stops at EOS)."""
    model.eval()
    device = next(model.parameters()).device
    ids = list(prompt_ids)
    out = []
    while len(out) < max_new and len(ids) < model.cfg.ctx_len:
        logits = model(torch.tensor([ids], device=device))[0, -1].float()
        if banned:
            logits[list(banned)] = float("-inf")
        if temperature <= 0:
            nxt = int(torch.argmax(logits))
        else:
            logits = logits / temperature
            if top_k:
                kth = torch.topk(logits, top_k).values[-1]
                logits[logits < kth] = float("-inf")
            nxt = int(torch.multinomial(torch.softmax(logits, -1), 1, generator=generator))
        ids.append(nxt)
        out.append(nxt)
        if nxt == eos_id:
            break
    return out
