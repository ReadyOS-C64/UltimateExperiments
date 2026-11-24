# English to Japanese in C64 LLM v0.8

**F5** selects the Japanese model. Type an English sentence directly and press
**RETURN**. The reply uses polite, spaced romaji. For example, type
`i ate an apple` to get `watashi wa ringo o tabemashita`.
**F1** selects Tiny 2.1 and **F3** selects C64PROGINFO.

The model uses **375,744 parameters** with 224 learned positions. It uses the
same character-token geometry and integer inference engine as C64PROGINFO.
The C64 console reads PETSCII-compatible input and displays romaji with its
normal character set. Inside the model, each character uses the existing
ASCII-derived token ID mapping. English case is normalized before inference.
The model outputs ASCII-compatible lowercase romaji and spaces. Long vowels
use letter pairs such as `ou`, `uu`, `oo`, and `ee`.

## Scope

Original sentence pairs cover polite present and past forms, negation,
desire, ability, ongoing actions, requests, permission, and obligation.
They also cover `kore/sore/are`, `kono/sono/ano`, `koko/soko/asoko`,
locatives, possessives, counters, prices, times, i- and na-adjectives,
comparison, introductions, and everyday questions. A deliberately limited
learner vocabulary combines food, ordinary objects, people, rooms, places,
and travel. English number is conveyed when explicitly counted. A plain
noun such as `ringo` can mean an apple or apples.

The beginner scope draws on the Japan Foundation's A1/A2 teaching sequence.
The vocabulary and paired sentences are generated in this project.
[Irodori](https://www.irodori.jpf.go.jp/en/about.html) ·
[Marugoto](https://www.marugoto.jpf.go.jp/en/teacher/feature/)

## Generate, train, and export

The generator creates a reproducible corpus with a hash-based holdout.
Within a verb family it keeps the same English subject, verb and object
combination on one side of the split across tenses and surface forms.
All first-person `eat` plus `apple` pairs are deliberately held out.
The held-out groups test new combinations of vocabulary in the learner set.
The label file also covers ordinary phrases and novel wordings.

From Tiny21, install the [training dependencies](requirements.txt) and run:

```sh
python3 -m training.japanese --out build/japanese/corpus
python3 -m training.train --data build/japanese/corpus --out build/japanese/base \
  --context 224 --steps 22000 --batch 48 --eval-every 1500 --lr .0014 --seed 804
python3 -m training.japanese --extended --out build/japanese/corpus-extended
python3 -m training.train --data build/japanese/corpus-extended --out build/japanese/qat \
  --init build/japanese/base/best.pt --steps 6300 --batch 40 --eval-every 900 \
  --lr .00032 --category-balance .8 --seed 805 --qat
python3 -m training.export CHECKPOINT.pt --name E2JROMAJI --out build/japanese/export
python3 -m training.japanese_eval build/japanese/export/E2JROMAJI.tny2 --integer \
  --train build/japanese/corpus-extended/train.jsonl --out build/japanese/quality.json
```

The second stage adds alternative word orders and everyday topics such as
residence, transport and clock times. Its category sampler gives infrequent
patterns more training time. Choose a checkpoint using generated translations
from the exported integer model in addition to teacher-forced validation loss.

The model is intended for short sentences with familiar vocabulary. Compare
translations before using them for study. [Example prompts and targets](japanese_checks.txt)
