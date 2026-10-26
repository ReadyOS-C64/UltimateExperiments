# Automatic fold-retention grammar recovery (private)

This is a source-only private C19 replacement. It does not modify the canonical
build, resident ABI, parser, folding commands, or physical hardware.

## Defect and exact scope

A public edit that changes `:::end` to `::Q:end` leaves an ordinary unfinished
region. After a valid fold map has been built, the automatic ordered-retention
rebuild (action6) returned builder B5 through job10 and prevented painting.
The identical 49-byte repro fails on both released946 and committed R16 inputs.
Source bytes, history, and leases remained intact, so this is an automatic
rebuild/paint policy defect, rather than a source corruption or R16 defect.

`coordinator.s` changes only `ec_abort`. Recovery requires all of:

- Primary B5, internal action6, and EC_BUILD.
- Builder B5, stopped builder, and a recognized grammar-failure state.
- EOF with outstanding code/region nesting; or an unmatched code/region closing
  event with no corresponding open nesting.

It invokes the existing resident emergency cleanup, which releases only owned
resources, invalidates the map and every derived projection, disarms retention,
and leaves the original target/canonical source intact. It then returns A0/Cclear
so the root paints expanded source. The builder's other B5 use (a stalled source
read in FB_PARSE) remains an error. Explicit user Fold All is action3 and retains
its original B5 error. Other errors, phases, and actions retain the primary error.

The control reassembles byte-for-byte to the frozen C19 (1469 bytes). Candidate
C19 is 1555 bytes (+86), with no new resident state, ZP, assets, or dependencies.
Only this assembler file is the possible production promotion boundary.

## Reproduce

From the repository root:

```sh
python3 tests/test_retention_grammar.py
python3 tests/test_retention_grammar_stress.py --fixture PRIVATE_FIXTURE --rounds 96
```

The first command extracts the immutable product sources, checks exact control
reassembly, links and seals a private C19, packages a copied D81, and verifies
that every other D81 file's bytes and sector chain are unchanged. It prints the
private fixture path for the second command. No shared output is rebuilt.

Pinned input: `build/normal-row80-committed/20261026T193357856684Z/fixture`.
PRG `93832107be6bca207087516304249b5de8b567143528ddcc132befdba64dd76b`;
D81 `446a5fa688886d7065b1da21491cf75c76f497bc111c37b83c3673c1a930171e`.

Public reproduction: valid region source48 bytes; Fold All/render, Unfold
All/render; typed GOTO3, RIGHT twice, native Q, LEFT, Undo, Redo, render.
The candidate renders the exact resulting49 bytes. The regression then proves
normal typing/Undo/Redo/mode change with independent all-four-mode pixels and
full16MiB checked typed-DMA guards. Actual missing R14 remains error17.

The stress wrapper changes only authentication of the coherent private D81;
its source/history/clipboard/pixel/REU assertions are unchanged. Tests use the
existing CPU/ROM transport seams. They make no native IRQ/VIC, physical latency,
ReadyOS lifecycle, or physical Ultimate claim. Any final stress limit is recorded
in the accompanying immutable result; a partial run is not called a pass.

## Qualified result (immutable private release)

Regression run: `build/retention-grammar/20261026T200015684677Z`.
Candidate SEO SHA256:
`53884af91475602c11020180c519e10f36fc59df83d0489286f6c21fa92a318b`.
Candidate source SHA is recorded in the release manifest. Seven groups pass:
unchanged control failure, four repaired modes with continued editing, explicit
Fold All B5, and actual missing-reader error17.

Stress run: `build/retention-grammar-stress/20261026T200102181699Z`.
All actual workload assertions passed: 96 mixed edit groups, a32-native-key
group, four above64KiB edit/Undo/Redo sequences, 303 modeled mutation/history
operations, 148 canonical/history checkpoints and87 independent fullpixel/attr
checks. The real32-bank profile includes a retained genuinely allocated foreign
bank with alternating freed holes, stored folds, preview and long lines.
Checkpoint highwater is16 banks/6 objects, not a complete worst-case bound.
The raw owner-STA monitor includes source-reset initialization (40 transitional
table values) and is explicitly NOT reported as a32-bank capacity highwater.

After the completed workload printed/wrote its passing result, the original
registered decorator attempted to attach metadata to a legacy None return.
That host TypeError is retained in the log. The new wrapper now reads the already
written result. Its `--finalize RUN_DIRECTORY` mode sealed `result-final.json`
offline, without rerunning any editor operation or changing the original result.
No old test source or product error/pixel/source guard was weakened.

The16-bank stress profile and native repeated-key latency are not qualified by
this release. Prior independent pressure/capacity evidence remains separate.
