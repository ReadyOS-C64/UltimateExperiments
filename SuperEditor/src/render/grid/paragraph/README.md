# Plain fixed-grid direct-row transaction

The old SP2 paragraph producer, paragraph shifter and retained-directory draft
are no longer production architecture. Plain 40/60/80-column edits now use a
bounded one-row transaction built from the edit certificate and the already
published resident row anchors. The internal `lrv3` filenames and constants are
compatibility names for this transaction; there is no persistent LRV3 record
directory, style canvas, carry set or manifest on the live Plain path.

C6 captures the one-edit certificate before mutation and derives a
non-authoritative physical-row hint afterward. R25 frame 18 independently
checks Plain capabilities, source length, revision, epochs, width, the selected
`se_v_rows` start and following anchor, the CR/EOF terminator and edit bounds.
It accepts only insert/backspace edits that leave one physical row shorter than
the active width. It writes the selected start, length, flags, row and caret
inputs into the private `$8D00` transaction area and publishes `PREPARED` last.
No parser, style planner or REU directory publication occurs.

C33 frame 1 consumes the transaction only while `PREPARED` and its exact R25
image and editor witnesses remain current. With no prepared edit it keeps the
ordinary warm-caret route. The consumer rebuilds and paints the single affected
row, updates the following resident anchors by `+1` or `-1`, commits the native
60/80-column row packet when applicable, then retires the transaction. CR edits,
wrap changes, selection, folds, styled modes, stale state and any failed check
use the established complete-render fallback.

Current linked sizes are C6 `3570`, R25 `3231` and C33 `3784` bytes before its
fixed native-font segment, with 56 bytes free before `$BF00`. Resident `main.o`
is `271` bytes, three bytes smaller than its comparison build. The exact ledger
is 2,794 replacement bytes against 5,220 retired bytes, for 2,426 bytes of net
deletion. No BSS or zero-page bytes were added.

Static 6510 probes pass 23 edit-certificate cases, 12 row-hint boundary cases,
and stale `PREPARED` retirement. The actual-product Peddle gate passes exact
source, pixels, attributes, row anchors and caret. Insert/delete instruction
counts are `10548/10243`, `87619/87345` and `50689/50460` in 40/60/80 columns;
ordinary Plain edits meet the 30K/100K instruction targets. The same operations
use `3/3`, `6/6`, `6/6` loads and `6/6`, `8/8`, `8/8` calls, leaving the wide
load target open. Warm caret costs `5179/33698/34859`; CR and wrap refusal
fallbacks cost `317297` and `426997`.

Native PAL VICE passes exact source and screenshot checks. The 60-column
insert/delete path publishes at `364043/363415` cycles and settles at
`364191/363520`; the 80-column path publishes at `218387/217945` and settles at
`218492/218050`. Each uses one draw sequence, six loads, eight calls, nine DMAs
and 23,072 DMA bytes, with no unexpected later group. The tracked timing test
issues `syntax plain` after opening the fixture so this is a real Plain result.
NTSC and physical-hardware timing remain pending.

Current evidence and next gates are in `agentsworking/STATUS.md` and
`docs/OPTIMIZATION_PLAN.md`.
