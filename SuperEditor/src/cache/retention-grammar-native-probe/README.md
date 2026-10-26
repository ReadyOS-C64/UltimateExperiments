# Native private C19 incomplete-region recovery

Source: `tests/test_retention_grammar_vice.py`. This qualifies only the coherent
private fix from the CPU release, not a later canonical/hardware build.

```sh
python3 tests/test_retention_grammar_vice.py --run
python3 tests/test_retention_grammar_vice.py --verify EVIDENCE_DIRECTORY
```

Input fixture:
`build/retention-grammar/20261026T200015684677Z/link/fixture`.
Resident SHA256 `93832107be6bca207087516304249b5de8b567143528ddcc132befdba64dd76b`,
private D81 `f1146a8fa4a95387987fa018f5c7aa7ffab4404dbe42a4e73d8c928cffc2cc93`.
Actual59 catalog; only C19 differs from the committed R16 fixture. C19 payload
1555B, SEO SHA `53884af91475602c11020180c519e10f36fc59df83d0489286f6c21fa92a318b`.

The run owns8100/text8200..8239, a private disk, unique runtime/REU files, and
normal CLI process lifetime with `--close-vice`. Fresh free-port checks use
SO_REUSEADDR solely to tolerate closed TIME_WAIT sockets; live listeners refuse.
It never kills unrelated processes. The physical Ultimate is untouched.

## Real input and independent checks

Real cold D81 boot, File/Open valid48-byte REGION, actual sourceGEOS publication
to establish the real semantic baseline, then source40. Real typed Fold All,
Unfold All and GOTO3, RIGHT twice, native Q into the closing marker, LEFT,
Undo/Redo. The pending49-byte source is captured before flush, then the committed
49-byte source in40/60/80/GEOS. Continued native Z, Undo/Redo and return40 produce
the final50 bytes. All input uses the original IRQ event runner; no source,
fold, caret, frame, PC, status, or semantic-valid metadata is inserted by debugger.

Nine frames pass all independent native VIC pixels (576,000), attributes (9,000),
canonical/pending source reconstruction, caret and selection, exact journal
records/CRCs/inserted reference bytes, clipboard, names/device, channels/leases,
1024-byte reserved shim, full59 sealed catalog and genuine fontpack/settings.
Four cross-mode read-only intervals preserve the whole16MiB except declared,
authenticated FE spans. The entire authenticated type53 allocation is separately
byte-identical across all nine captures, including after the edit; it is never
masked. Fold46, source/history, foreign and unused FE tail bytes remain exact.

Explicit malformed Fold All B5 and missing-reader error17 remain CPU-negative
controls from the prior release. This native run does not inject either fault.
Native IRQ byte events are not a physical key-chord, hardware latency, ReadyOS,
physical RESTORE, suspend/resume or final canonical release claim.

## Evidence and review

`agentsworking/evidence/M8/20261026T201841433009Z-retention-grammar-native`.
Actual native plan:450 steps,126 IRQ bytes; all complete. CLI closed its owned
VICE before final sharing; all owned ports are free and no runtime process remains.
All nine images reviewed in `gallery/contact.png`; full repaired80 and repaired
GEOS also opened directly. The unfinished marker is visible, caret/status remain
coherent, and no error obscures the source.

The first offline verifier omitted the grid FE packet extent in its cross-mode
union. Its traceback is preserved. Exact diff proof showed all3652 changed bytes
inside the same authenticated FE bank's frozen `GRID_CACHE_ROWS=22` ×
`GRID_CACHE_PACKET=240` layout and existing GEOS extents. Only that source-declared
extent was added, followed by offline re-verification of the same captures.
No native rerun, error waiver, whole-bank mask, or type53 exception was used.

`tools/closed_runtime_copy.py` is included in the final verifier source archive.
Its only modification is the final host copy, after native Status=success and
--close-vice: owned closed runtime files are hardlinked with exact SHA/size/inode
receipts. Failed runs retain their original logs. There are505 sharing receipts;
no capture source is deleted and no live backing file is linked by this helper.
