# Tiny21 v0.7 research comparison with c64-dungeon

Compared on 2026-11-23. The Tiny21 baseline is the released v0.6 source at
`30089f7858bbb0f9bed199bffd67a8f256855171`. The c64-dungeon snapshot is
`60a5b6c36db41a5c74fa3b7efea15ba235b27546`.

This review reads source and the shipped model package. Its numerical
inventory and source comparisons run on the host. Dungeon's runtime
correctness and hardware timings are author-reported.

## Design lineage and assembly overlap

Dungeon explicitly credits Tiny21. Its reference research pins our v0.6
commit, records reading the integer oracle, converter and selected assembly
modules, and identifies our arithmetic and verification approach as its
starting point. It also studies llama2.c64. The authors describe their ACME
engine as an independent implementation. [Reference research](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/docs/REFERENCE_IMPLEMENTATIONS.md)

A source comparison covered our 14 inference assembly files and nine native
probe assembly files against Dungeon's 12 engine assembly files. There were
zero byte-identical files. After stripping comments and whitespace, the
longest matching run of literal opcodes and operands was five instructions,
such as four shifts followed by TAX. Those are ordinary indexing operations.
When operands were discarded, the longest matching run contained 23 opcodes
in REU setup, which writes the same hardware registers.

This provides no evidence of a substantial verbatim assembly routine in the
compared source. The comparison examines source instructions before macro
expansion. It cannot determine authorship or rule out adaptation expressed
through renamed operands or different macro structure. The quarter-square
equation, fixed-point formats and subset-sum equations are shared, while the
assembly implementing them differs. [Our compact multiplier](../src/dot.s),
[Dungeon multiplier](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/engine/source/ai_math.asm)

## Model and forward pass

| Property | Tiny21 v0.6 | Shipped Dungeon v3q model |
| --- | --- | --- |
| Layers / attention heads | 4 / 4 | 4 / 4 |
| Channels / head width | 96 / 24 | 64 / 16 |
| Feed-forward width / activation | 256 / ReLU | 256 / ReLU |
| Positions | 128 learned absolute | 128 learned absolute |
| Vocabulary | 97 character tokens | 256 ids including characters, letter groups and controls |
| Parameter count | 366,528 | 221,760 |
| Converted image | 380,995 bytes | 237,312 bytes |
| Final projection | Tied token embedding | Tied token embedding |
| Generation | Greedy | Greedy or top-k with temperature and seeded RNG |

The shipped Dungeon image's length and SHA-256 matched its distribution
manifest. The model uses four pre-RMSNorm transformer blocks with the same
overall ordering as Tiny21. Each performs normalization, Q/K/V, cache append,
causal attention, output projection/residual, normalization, ReLU feed-forward
and residual. Both skip the output head for prompt positions whose logits
would be discarded. Their model weights and token ids are different.
[Dungeon manifest](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/dist/MANIFEST.JSON),
[forward pass](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/engine/source/ai_model.asm)

## Fixed-point arithmetic

Both retain signed Q16.16 activations and logits, signed int8 row weights,
Q0.24 row scales, Q4.12 normalization gains, and int16 dot inputs packed with
a shared shift. Both use widened accumulators, integer square roots with
eight guard bits, and nearest rounding with ties away from zero. These are
specific numerical design choices Dungeon's reference research attributes
to Tiny21.

Their arithmetic is not bit-compatible with ours. Dungeon rounds the mean
square before its RMS square root, while our oracle floors the scaled
division used to construct that root. Dungeon folds the attention factor
1/sqrt(head width) into Q weights before quantization, while our attention
path applies its fixed-point factor during score evaluation. Dungeon also
changes cache scaling, described below. These changes require its own
integer oracle and model conversion. [Our oracle](../tools/oracle.py),
[Dungeon arithmetic contract](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/docs/INFERENCE.md)

## Multiplication and lookup tables

Both compact multiplication paths use the quarter-square identity and
page-aligned byte planes. Our tables are assembled as constants and accessed
with indirect zero-page pointers. Dungeon builds its tables at initialization
under BASIC ROM and patches absolute indexed operands for its multiply
helper.

Both fast matrix paths use the same group-eight subset-sum principle.
For eight activations, build all 256 sums. A weight bitplane mask selects one
sum. Add the seven positive planes and subtract the sign plane to reconstruct
an exact signed dot. Dungeon's format document explicitly identifies our
`mask_row_group8` as the source of this idea.

The organization is substantially different. Our engine prepares 9 KiB of
tables for the full 96-input vector and shares them across Q/K/V. We stream
16-row tiles, retaining group-four for O and the compact sparse path for F2.
Dungeon streams blocks of up to 64 rows by 64 columns, builds one 768-byte
subset table at a time, and applies it to all rows in the block through a
generated kernel. It uses this layout for all matrices except the position
embedding, including F2 and the tied output head. Its matrix calls rebuild
the tables for each Q/K/V projection. [Our kernel](../src/dot_group8.s),
[Dungeon matrix kernel](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/engine/source/ai_matvec.asm)

Both softmax implementations use 1,025 samples of exp(-i/64), linear
interpolation, and a delta cutoff of 16. Comparing the generated numerical
entries found 1,024 identical values. The first differs because ours handles
exact 2^24 separately, while Dungeon caps it to 2^24-1. Equal values from the
same formula establish numerical agreement for those entries.

Our exp table stays in resident memory. Dungeon places its initial table in
vector RAM, copies it to REU at initialization, then fetches two entries with
a six-byte DMA for each evaluation. Its generated arithmetic kernels occupy
`$9C00–$9DFF`. This trades small transfers and initialization work for free
CPU RAM. [Our exponential](../src/attention_exp.s),
[Dungeon exponential and table](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/engine/source/ai_math.asm)

## REU and attention cache

| Property | Tiny21 v0.6 | Dungeon engine |
| --- | --- | --- |
| Model base | REU zero | REU zero |
| KV base / layer stride | $080000 / $8000 | $100000 / $10000 |
| KV record | K8 + peak32, V8 + peak32 | K8, V8, per-head key/value exponents |
| Baseline bytes per position/layer | 200 | 136 |
| Actual 128-position KV bytes | 102,400 | 69,632 |
| Runtime minimum / documented user setting | 16 MB release target | 2 MB engine minimum / 16 MB player setting |
| Transfer policy | Owned CPU windows and model/cache regions | General fetch/stash with caller-selected CPU buffers |
| Bank boundaries | Split at 512 KiB | Split at 512 KiB |

Our cache scales all 96 channels of a key or value with one absolute peak.
Dungeon packs each 16-channel head with a power-of-two shift and stores one
exponent per head. This replaces peak multiplications/divisions with shifts
and changes the quantization. Its training fine-tunes the model with weight
and K/V quantization simulated.

Both attend to positions zero through the current position, append current
K/V first, and reset context validity for a new request. Our attention code
processes all heads across a tile, then reuses the final key-pass tile during
the value pass. Dungeon loops over heads and fetches cache tiles again for
each score/value pass. Its design favors simpler head-local arithmetic and
different scaling. [Our cache](../src/cache.s),
[our attention](../src/attention.s),
[Dungeon attention](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/engine/source/ai_attn.asm)

Both configure the 17xx REU registers for DMA, split the 512 KiB counter wrap,
and use model integrity checks. Dungeon explicitly cites Tiny21 for the
counter behavior. Both support a preloaded image and a USB/UCI fallback.
Dungeon's driver uses different counters and general addresses, while ours
checks particular CPU windows and capacity spans. The routines have different
source and validation responsibilities. [Our REU driver](../src/reu.s),
[Dungeon REU driver](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/engine/source/hw_reu.asm)

## Model flexibility and multiple-model implications

Our v0.6 model admission pins the Tiny 2.1 checkpoint hash, dimensions, exact
matrix directory and image size. Its image versions select packing layouts
for one checkpoint. Dungeon uses a new D64AI header with tensor kinds,
dimensions, offsets, tokenizer, vocabulary identity and header/payload CRCs.
Its engine reads model geometry at runtime within compiled limits, including
d <= 128, heads/layers <= 8, feed-forward <= 256 and context <= 128.

That permits sequential replacement of compatible Dungeon models. The
current code still maps one image at REU zero and one active context. It does
not provide a registry of several models concurrently resident in REU.
The terminal/game also use model-specific vocabulary identities and scene
tokens. Arbitrary tokenizers cannot be exchanged without checking the host.
[Dungeon loader](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/engine/source/ai_load.asm),
[model format](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/docs/MODEL_FORMAT.md)

For v0.7, distinguish selecting several checkpoints of the same Tiny21
geometry from supporting different geometries and tokenizers. The former can
preserve the proven arithmetic. The latter needs format, workspace, cache,
tokenizer, and model-admission decisions. Dungeon's metadata and tokenizer
contract are relevant references. Adopting its cache exponents would change
our numeric profile and needs a separate accuracy evaluation.

The v0.7 console keeps two compatible Tiny21 model images in separate REU
slots. F1 selects the original Tiny 2.1 and F3 selects C64PROGINFO.
[Release model slots and cache layout](TECHNICAL.md#model-and-resident-6510-engine)

## Performance interpretation

Dungeon reports 563 ms per generated token and 2.29 characters/s over its
five-minute shipped-model benchmark. Our published standard prompts measured
0.795–0.829 characters/s from first output through ready. The scopes differ.
Dungeon's 64-wide model performs 212,992 dense MACs per full step versus our
353,376, about 40% less work before attention. Its letter-group tokens can emit
multiple characters and its scene prompts use a few control tokens. Those
factors affect throughput alongside the optimized kernel.

Its figures support treating the implementation as promising. They do not
isolate an engine-only speed ratio. Such a comparison requires matched model
geometry, tokenization, prompts, arithmetic contract, and timing boundaries.
The reported five-minute run includes an integer-reference token checksum,
which is stronger evidence than a single narrative screenshot. This review
has not rerun that benchmark. [Dungeon hardware results](https://github.com/jaydarkseed757/c64-dungeon/blob/60a5b6c36db41a5c74fa3b7efea15ba235b27546/docs/HW_RESULTS.md)

## Engine efficiency and optimization priorities

A fresh Peddle measurement of our v0.6 group-eight binary took 49,333,722 CPU
cycles for position zero with output logits. Dungeon documents 28,730,682
cycles for its smaller model at position zero in VICE. Dividing whole-step
cycles by dense MAC count gives approximately 140 for Tiny21 and 135 for
Dungeon. This rough normalization puts their efficiencies much closer than
their raw output-character rates suggest. It includes normalization,
attention, scales and control overhead in the numerator and counts only dense
MACs in the denominator. The models, numeric contracts and simulation backends
differ, so it is an indicator, rather than a matched kernel benchmark.

The strongest candidate to measure first is a row-block bitplane kernel with
patched absolute addressing. It could reduce pointer and loop overhead and
extend exact lookup arithmetic to the F2 and output projections. A useful
experiment should retain our Q/K/V table sharing, sparse F2 fallback, and
existing all-head attention tile reuse. Compare full-prompt cycles, table
setup, DMA traffic and exact logits on the same model.

Specialized scale products and divisions are another candidate where
proved width bounds permit them. Per-head exponent caches and folding the
attention scale into weights are separate numeric-profile experiments,
because they alter model quantization. Moving the exponential table into REU
is a RAM tradeoff that adds transfers; it needs a workspace-driven reason and
a whole-token measurement. Multi-character tokens and short control prompts
improve text throughput through model/tokenizer design and should be measured
separately from assembly improvements.

## Changes measured for v0.7

The ca65 group-eight dot now uses unrolled, directly indexed lookups into
the existing fixed table pages. Q/K/V still share the prepared table.
Sparse F2, the compact output projection and the resident exponential
table use their existing arithmetic. Cache slot addresses and attention
tile lengths now use the existing quarter-square multiplier in place of
repeated addition. Attention still processes all heads in each 40-record
tile and retains the last key tile for the value pass.

| Same Tiny21 model and workload | v0.6 Peddle cycles | v0.7 Peddle cycles | Reduction |
| --- | ---: | ---: | ---: |
| Position zero, token `w`, with logits | 49,333,722 | 42,262,117 | 14.3% |
| `what is 7 times 8` | 2,061,063,646 | 1,820,409,164 | 11.7% |
| `what is the capital of peru` | 1,951,929,113 | 1,718,359,946 | 12.0% |

The prompt measurements include prefill and generation through end of
response. Both answers and all checked logits matched the integer oracle,
with the same DMA byte counts and transfer counts in the two builds.
Generation-only rates were 1.03 and 0.98 characters/s at an idealized 64 MHz.
Peddle counts CPU cycles and verifies DMA data; physical DMA and video timing
are outside the rate calculation.

The context layout raises the engine's limit from 128 to 255 positions.
The current upstream checkpoint continues to supply 128 learned positions.
The extended test checkpoint reuses existing position rows to exercise
the format and arithmetic. A full run ingested 154 prompt characters before
the delimiter and matched every generation logit to the Python oracle. The
final-position test verified all 97 logits, all four newly appended cache
records and clean rejection at the limit. The attention test verified exact
outputs on a full 255-position prefix, including a head with equal weights
at every position. [Build and model format](BUILD.md).

### Measured on the C64 Ultimate

The 2026-11-23 A/B run used the same physical C64 Ultimate, a 16 MB REU, the
same preloaded model (CRC32 `557003c0`), and the same two scripted prompts.
Both builds verified 64 MHz. The probe measured PAL CIA2 PHI2 ticks at
985,248 Hz. Response time excludes model loading and validation.

| Prompt | v0.6 first character | v0.7 first character | v0.6 total | v0.7 total | Total time reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| `what is 7 times 8` | 17.012 s | 14.959 s | 36.322 s | 32.442 s | 10.68% |
| `what is the capital of peru` | 28.148 s | 24.956 s | 34.441 s | 30.678 s | 10.93% |

Both answers matched. Combined response time fell from 70.763 s to
63.120 s, a 10.80% reduction. Output-phase rates rose from 0.829 to 0.915
and from 0.795 to 0.874 character tokens per second, respectively.
