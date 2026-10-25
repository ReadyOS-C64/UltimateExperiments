# Editor fold integration

The standalone source editor exposes F7 `fold`, `fold all`, `unfold all` and
Block/F, Block/L, Block/E in40/60/80 columns. Command IDs112..117 are toggle,
collapse, expand, collapse-all, expand-all and canonical-position reveal.
The first UI increment commits a pending typing group before beginning a fold
operation; document bytes remain unchanged. Heading, fenced-code and explicit
region records use the checked type$46 logical REU object and existing builder.

The resident dispatcher enters C19 and, after its return, executes any requested
C17 parse or C18 finish slice. Those leaves use R14 merged-source and R18 checked
fold primitives sequentially. There is no command-to-command nesting. Each
successful controller call returns A0 complete or A1 pending with carry clear;
failures retain the original error and run resident, ownership-checked cleanup.
Default capacity is one logical bank,2016records; allocation/capacity failure
preserves source, history, selection and foreign allocations.

Persistent fold state is121B, plus20B for edit provenance:45B descriptor,66B row paint ends,
3B fold row bits,2B projection generation,4B checked motion and1B modal suspension.
The journal uses15B VIEWSTATE and5B BSS. Current BSS is1531B, endingC5FA; C600–C9FF stays wholly reserved. No new ZP is
used. Disposable foundation/builder/controller state shares owner3 phase8D00–917F.
Every phase claim first revokes sparse-index publication. Modal/file owner1 and
style owner2 remain distinct; the source key and published row metadata can be
checked without inspecting their phase bytes.

C11 publishes canonical row starts/bottom, separate paint ends and a fold bitset.
The folded opener retains every wrapped glyph. Its final CR blank shows an
inverse `+`; the next row starts at the fold's exclusive canonical end. R1 and
C16 consume these published maps without a nested fold query. Paint ends are
inactive when the fold descriptor is invalid.

C6 records each visible one-byte edit before mutation. C4/C5 record successful
committed splice tuples; a hot flush advances the generation witness without
recording those same edits twice. R19 stores up to112 ordered9B events in the
last1024 bytes of the existing fold object. No separate journal object or
physical REU bank is assumed. Observer failures disarm retention while source
editing still succeeds.

Internal action6 reads that witnessed log, invokes R20 to transform hints into
a distinct typed object, and freshly parses into a separate candidate. Only
matching ranges/kind/level transfer COLLAPSED; saved caret/motion is cleared and
the fresh tree supplies ancestry/line counts. Opener edits drop the affected
record and descendants; unaffected siblings survive. Old map, hints and fresh
candidate fit the8-object table with document/history/clipboard. No transformed
hint is ever published as a fold map. Final parse success retires old/hint maps;
resident cancellation releases only owned disposable objects.

A witnessed zero-event hot flush can rekey/reuse the same map. This also works
when FileUI temporarily invalidated it. Motion-serial wrap disarms retention and
invalidates the full painted projection, preventing ancient saved-caret reuse.

Ordinary canonical movement advances a32-bit serial and opens enclosing hidden
regions before painting. A controlled collapse/expand does not advance it;
expansion restores an inner caret only at the matching summary and serial.
Selections retain canonical endpoints, so copying/cutting across hidden source
includes its bytes. Highlighting a partially selected hidden interval in its
summary is represented by its highlighted `+`: selection must intersect the
nonempty canonical interval from that CR to the next visible row anchor. Both
wrap/no-wrap and40/60/80 use the same resident published-row query, including
marker/caret union and exact end-boundary exclusion.

While FileUI owns the phase, the modal helper temporarily suspends the projection
and displays ordinary source rows. Closing/cancelling/saving restores the same
fold map if its full source key still matches; opening a different document
discards its stale edit journal before a fresh build. Failed controller or C11 admission revokes the projection and
render/style caches, releases only owned leases, and allows ordinary source to
paint without the missing fold leaf. Resident cancellation never requires a
successful overlay reload.

`tests/test_fold_controller.py`, `test_fold_projection.py` and
`test_fold_editor_vice.py`, `test_fold_retention.py` and
`test_fold_retention_vice.py` exercise the actual dispatcher and independent
storage/pixel models. The native test uses the existing.NET VICE automation,
owned monitor ports, warp/traps and disposable disks. It does not prove physical
key chords or PAL/NTSC latency. GEOS editing and ReadyOS integration remain later.
