# Independent reduced-REU stress on the private C19 fixture

Run:

```sh
python3 tests/test_retention_grammar_16.py
```

Input is the unchanged sealed private59 fixture at
`build/retention-grammar/20261026T200015684677Z/link/fixture`; PRG938321/binding7abb,
D81 `f1146a8fa4a95387987fa018f5c7aa7ffab4404dbe42a4e73d8c928cffc2cc93`.
Only C19 differs from the committed R16 input. No shared build, product source,
Git, native emulator, or physical Ultimate is used by this qualification.

Actual provider capacity is16 physical banks (one controlbank,15 usable), with
a one-bank document quota and all59 checked catalog assets. The released
independent workload and exact capacity/source/history/pixel/typed-DMA checks are
reused unchanged through its existing16-bank profile. No host-created capability
or semantic-valid flag is used. The profile builds a genuine53 baseline (15 CR
records for869 initial bytes), then allocates three actual A5 foreign banks,
frees alternating handles13/15, and preserves retained logical/physical14.

The completed run is `build/retention-grammar16/20261026T202315370747Z`.
It passes96 mixed public edit groups plus a32-key insertion group:291 modeled
mutation/Undo/Redo operations,122 canonical/history checkpoints,73 independent
fullpixel/attribute frames, all four editable modes, preview, selection/copy/paste,
and an initial700-byte long line. Final source1052 bytes has SHA256
`4899f22d8310fb2edd265ab267e98f319c69d179fadad11044c09d90b18f0f88`.
Full16MiB snapshots are checked in memory against actual checked typedDMA writes,
including foreign/unallocated tails. No per-event full dumps are retained.
No capacity refusal or altered expected-error path was necessary.

The legacy checkpoint statistic reports15 nonzero/nonFF physical-owner entries,
which includes reserved controlbank0; it is not a saturation or minimum-headroom
claim. Maximum checkpoint object count is6. The raw instruction-level owner-STA
monitor includes provider/source reset initialization and reports40 transient
table values, so that number is explicitly NOT a live16-bank allocation peak.

This bounded profile intentionally leaves stored-fold objects unallocated and
omits its separate far-offset phase to retain a real COW workspace bank. It does
not independently exercise the new action6 branch, establish a maximum document
size, qualify16-bank native latency, or replace the separate32-bank C19/far/fold
proof. Its source1052B/one-bank quota result cannot be generalized to all1MiB
workloads. The supported limits and prior pressure refusal evidence remain
separate. No physical OS/suspend/resume/hardware claim is made.
