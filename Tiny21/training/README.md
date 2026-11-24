# C64PROGINFO training

C64PROGINFO is a 375,744-parameter decoder for Commodore 64 programming
questions. It has four layers, four attention heads, 96 channels, a
256-wide feed-forward layer and 224 learned positions. The exporter produces
a 390,499-byte T64M image with row-wise int8 weights and the name
`C64PROGINFO` in header bytes 53–63. Token 0 is an output line break in this
model. Token 1 separates the prompt and answer and ends a response.

The PyTorch decoder and response-only training loop were adapted from
[jaydarkseed757's c64-dungeon](https://github.com/jaydarkseed757/c64-dungeon/tree/60a5b6c36db41a5c74fa3b7efea15ba235b27546/python).
The original copyright and MIT notice are in [LICENSE.c64-dungeon](LICENSE.c64-dungeon).
Our fake quantization uses the Tiny21 engine's shared 96-lane key/value peak
and Q0.24 per-row scales.

## Corpus

`facts.txt` contains original summaries of C64 hardware, VIC-II and SID,
BASIC V2, 6502/6510, interrupt, CIA and KERNAL facts. `corpus.py` adds
explicit register and opcode records, calculated screen and bitmap addresses,
SID note words, and comment-free BASIC and assembler examples. `augment.py`
adds author-supplied paraphrases and controlled variants and keeps the
independent check prompts outside training. The packaged model's corpus has
3,507 fact and example records, 114,255 training wordings and 3,506 held-out
wordings. This includes calculated register and memory-address cases, so the
fact count combines reference material and derived facts.

Primary references include the [Commodore 64 Programmer's Reference Guide](https://www.commodore.ca/commodore-manuals/)
and the original [MOS 6510, VIC-II, SID and CIA datasheets](https://www.zimmers.net/anonftp/pub/cbm/documents/chipdata/index.html).
The computed bitmap and screen records use the addressing geometry in the VIC
specification. SID note words use the standard PAL and NTSC clocks with
A4 at 440 Hz. Facts are written in our own words. The examples use BASIC V2
and ca65-compatible NMOS 6502 assembly. `verify_corpus` checks splits,
compiles every assembler example, checks the 151 official opcode encodings
against ca65, and checks the BASIC examples against their supported patterns.

## Train, score and export

From Tiny21, install `training/requirements.txt` in a Python virtual
environment. Run these commands using that environment. The trainer selects
Apple MPS when available, and supports `--device cpu`.

```sh
python -m training.corpus --out build/corpus
python -m training.augment --data build/corpus --out build/corpus-expanded
python -m training.verify_corpus build/corpus-expanded
python -m training.train --data build/corpus --out build/proginfo-base
python -m training.train --data build/corpus --out build/proginfo-quantized \
  --steps 1800 --init build/proginfo-base/best.pt --lr .00018 --qat
python -m training.train --data build/corpus-expanded --out build/proginfo-qat \
  --steps 5200 --init build/proginfo-quantized/best.pt --lr .0004 --qat
python -m training.reinforce build/proginfo-qat/best.pt \
  --data build/corpus-expanded --out build/proginfo-rl --steps 200 --temperature 1.2
python -m training.train --data build/corpus-expanded --out build/proginfo-sprite \
  --steps 450 --init build/proginfo-rl/latest.pt --lr .00012 --qat --boost-fact example.34
python -m training.export build/proginfo-sprite/latest.pt --out build/proginfo-export
python -m training.evaluate build/proginfo-export/C64PROGINFO.tny2 --integer \
  --independent training/independent_checks.txt --out build/programmer-checks.json
```

The reinforcement step samples several completions per prompt and rewards a
correct answer that ends cleanly. It keeps a supervised loss on the expected
response. Review the independent and held-out wording scores before choosing
which checkpoint to export. The integer oracle scores the same quantized
checkpoint used in the console. Generated answers can contain factual or
code errors, especially for unfamiliar phrasing.

## Verification of the packaged checkpoint

The corpus audit checked 151 opcode encodings, assembled 180 original
snippets with ca65, and checked 175 BASIC snippets against the supported
BASIC V2 patterns. The final reward pass ran 200 updates and had 279
question groups with differing completion rewards. The sprite example
received a short final supervised pass to cover a ten-line answer.

The quantized model matched all 11 answers in the supported-prompt smoke
suite and 63 of 64 sampled held-out wordings from the same question families.
The QAT model matched 245 of 252 on a larger held-out sample. On 33 more
independently written prompts, the quantized model matched 7 answers. This checkpoint works best with the
examples and familiar wordings. Check unfamiliar answers and generated code
against the relevant hardware or language reference.

`native_checks.txt` and `independent_checks.txt` provide the two explicit
suites. Use `--independent` to select either one. For native inference and
formatting, use `tools.run_peddle --verify` and `probe.check_models`.

The final bundle ran on the physical C64 Ultimate at 64 MHz with a 16 MB REU.
F3 loaded C64PROGINFO through Ultimate DOS and displayed the two-line assembly
and BASIC examples. F1 returned to Tiny 2.1 and answered the arithmetic
prompt. F3 then reused the resident C64PROGINFO image. The native Peddle
console also generated and displayed the ten-line sprite example.
[Physical assembler output](../screenshots/proginfo-assembler.png).

## Expanded C64 wording and English-language experiment

The original 3,507 C64 fact and example records yield 360,987 technical
training wordings after lexical substitutions and question reframing.
The control and mixed runs both use those C64 wordings, initialized from
the same C64PROGINFO checkpoint. The mixed run reserves 8% of its sampling
probability for 6,096 additional English and C64 logic wordings.

`tiny21_language.tsv` contains 79 selected English relations from WollyMonjac's
Tiny 2.1 `lang.tsv` and `words2.tsv`. They cover opposites, synonyms, plurals
and verb forms useful to C64 questions. The import excludes geography,
translations and other trivia. The C64 logic examples derive their answers
from byte operations, bit masks and the 6510 branch conditions. The
experiment starts from our C64PROGINFO weights.
[MIT notice](LICENSE.tiny21-language) · [Upstream data licenses](https://github.com/WollyMonjac/Tiny-2.1/blob/49348445661ffc9106f243afb4eafe499a51e286/DATA_LICENSES.md)

```sh
python -m training.language_mix --data build/corpus-expanded --out build/language
python -m training.verify_corpus build/language/mixed
for variant in control mixed; do
  python -m training.train --data "build/language/$variant" \
    --out "build/language/$variant-weights" --init build/proginfo-sprite/latest.pt \
    --steps 3600 --eval-every 600 --batch 64 --seed 91 --lr .00024 --qat
done
```

The original independent C64 prompts and the 36 new prompts in
`language_transfer_checks.txt` stay outside both training sets. Baseline,
control and mixed evaluations measure supported prompts, the two independent
sets and held-out English and logic wordings separately.

| Check | Released checkpoint | Expanded C64 control | Expanded C64 + English and logic |
| --- | ---: | ---: | ---: |
| Supported C64 prompts, QAT | 11/11 | 11/11 | 11/11 |
| Familiar-family C64 wordings, QAT | 245/252 | 248/252 | 240/252 |
| Independent C64 wordings, exported integer model | 11/69 | 10/69 | 8/69 |
| Held-out English and logic wordings, QAT | 0/90 | 0/90 | 25/90 |
| Alternate branch wording and unseen byte operands, QAT | 0/36 | 0/36 | 2/36 |

The auxiliary training helped on examples of the auxiliary tasks. The
mixed checkpoint scored lower on both C64 wording checks, so the release
uses the prior checkpoint. Peddle ran the experimental image from the
C64PROGINFO slot and matched all checked logits on the CPU identification
prompt.
