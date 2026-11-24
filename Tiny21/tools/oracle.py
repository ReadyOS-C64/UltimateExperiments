"""Integer transformer reference for the 6510 port.

Working tensors and logits use signed Q16.16. Dense operands are rounded to
signed int16 using a shared power-of-two shift, then dotted with the original
int8 weights. The CPU oracle uses Python integers to expose overflow bounds
when selecting the target implementation widths.
"""
import argparse
from dataclasses import dataclass
import math
from operator import mul
from pathlib import Path
import struct

from tools.model import BASE_CONTEXT, decode

Q = 1 << 16
SCALE_Q = 1 << 24
GAIN_Q = 1 << 12
EPSILON = round(1e-5 * Q * Q)
INVERSE_SQRT_HEAD = round(SCALE_Q / math.sqrt(24))
EXP_TABLE = tuple(round(SCALE_Q * math.exp(-i / 64)) for i in range(1025))


def round_div(n, d):
    magnitude = (abs(n) + d // 2) // d
    return -magnitude if n < 0 else magnitude


def input_tokens(line, context=BASE_CONTEXT):
    text = "".join(c for c in line if " " <= c <= "~")[:context - 56].rstrip(" ")
    if text.isupper():
        text = text.lower()
    return [ord(c) - 30 for c in text]


def dense_input(values):
    peak = max(map(abs, values))
    shift = max(0, peak.bit_length() - 15)
    if round_div(peak, 1 << shift) > 32767:
        shift += 1
    return [round_div(value, 1 << shift) for value in values], shift


def normalize(values, gains):
    # Keep 8 fractional guard bits in the RMS root.
    energy = sum(value * value for value in values) + len(values) * EPSILON
    root = math.isqrt((energy << 16) // len(values))
    divisor = root * GAIN_Q
    return [round_div(value * gain * (Q << 8), divisor)
            for value, gain in zip(values, gains)]


def exp_delta(delta):
    if delta >= 16 * Q:
        return 0
    index, fraction = divmod(delta, Q // 64)
    left, right = EXP_TABLE[index:index + 2]
    return left + round_div((right - left) * fraction, Q // 64)


def cache_vector(values):
    peak = max(map(abs, values))
    if not peak:
        return [0] * len(values), 0
    return [round_div(value * 127, peak) for value in values], peak


@dataclass
class Projection:
    weights: list[tuple]
    scales: list[int]

    def embedding(self, index):
        scale = self.scales[index]
        return [round_div(weight * scale, SCALE_Q // Q) for weight in self.weights[index]]

    def apply(self, values):
        inputs, shift = dense_input(values)
        return [round_div((sum(map(mul, weights, inputs)) * scale) << shift, SCALE_Q)
                for weights, scale in zip(self.weights, self.scales)]


class Network:
    def __init__(self, checkpoint, project=None):
        matrices, gains = decode(checkpoint)
        self.context = matrices["position"].rows
        self.matrices = {
            name: Projection([struct.unpack(f"<{m.cols}b", row) for row in m.weights],
                             [round(scale * SCALE_Q) for scale in m.scales])
            for name, m in matrices.items()
        }
        self.gains = {name: [round(value * GAIN_Q) for value in vector]
                      for name, vector in gains.items()}
        self.project = project
        self.reset()

    def reset(self):
        self.keys = [[] for _ in range(4)]
        self.values = [[] for _ in range(4)]
        self.position = 0

    def step(self, token, logits=True, trace=None):
        if not (0 <= token < 97 and self.position < self.context):
            raise ValueError("token/position outside checkpoint geometry")
        matrices = self.matrices
        residual = [a + b for a, b in zip(matrices["embedding"].embedding(token),
                                          matrices["position"].embedding(self.position))]
        if trace is not None:
            trace["embedding"] = residual
        for layer in range(4):
            prefix = str(layer) + "."
            normalized = normalize(residual, self.gains[prefix + "g1"])
            query = self.dense(prefix + "q", normalized)
            key = self.dense(prefix + "k", normalized)
            value = self.dense(prefix + "v", normalized)
            self.keys[layer].append(cache_vector(key))
            self.values[layer].append(cache_vector(value))
            attention = self.attend(layer, query)
            projected = self.dense(prefix + "o", attention)
            residual = [a + b for a, b in zip(residual, projected)]
            normalized_ff = normalize(residual, self.gains[prefix + "g2"])
            hidden = [max(0, value) for value in self.dense(prefix + "f1", normalized_ff)]
            projected_ff = self.dense(prefix + "f2", hidden)
            residual = [a + b for a, b in zip(residual, projected_ff)]
            if trace is not None:
                trace.update({prefix + name: tensor for name, tensor in (
                    ("norm1", normalized), ("q", query), ("k", key), ("v", value),
                    ("attention", attention), ("o", projected), ("norm2", normalized_ff),
                    ("relu", hidden), ("f2", projected_ff), ("residual", residual))})
        self.position += 1
        if logits:
            result = self.dense("embedding", normalize(residual, self.gains["final"]))
            if trace is not None:
                trace["logits"] = result
            return result
        return None

    def dense(self, name, values):
        if self.project is not None:
            return self.project(name, values)
        return self.matrices[name].apply(values)

    def attend(self, layer, query):
        result = []
        for start in range(0, 96, 24):
            stop = start + 24
            head = query[start:stop]
            scores = [round_div(sum(map(mul, head, key[start:stop])) *
                                peak * INVERSE_SQRT_HEAD, 127 * Q * SCALE_Q)
                      for key, peak in self.keys[layer]]
            maximum = max(scores)
            factors = [exp_delta(maximum - value) for value in scores]
            denominator = 127 * sum(factors)
            weighted = [0] * 24
            for factor, (vector, peak) in zip(factors, self.values[layer]):
                coefficient = factor * peak
                for i, value in enumerate(vector[start:stop]):
                    weighted[i] += coefficient * value
            result.extend(round_div(value, denominator) for value in weighted)
        return result

    def answer(self, question):
        self.reset()
        for token in input_tokens(question, self.context):
            self.step(token, logits=False)
        scores = self.step(1)
        output = []
        while self.position < self.context:
            token = max(range(97), key=scores.__getitem__)
            if token <= 1:
                break
            output.append(chr(token + 30))
            scores = self.step(token)
        return "".join(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("questions", nargs="+")
    args = parser.parse_args()
    network = Network(args.checkpoint.read_bytes())
    for question in args.questions:
        print(network.answer(question), flush=True)
