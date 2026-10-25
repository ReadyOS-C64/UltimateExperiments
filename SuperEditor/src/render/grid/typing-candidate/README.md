# Private source-grid local typing capsule

This is a private measured prototype, not canonical production. `build.py` emits
sealed replacement C33 (`grid`) and R25 (`geostail`) against an immutable editor
report. It never edits the shared build, resident, startup, Makefile or catalog.
No new asset, resident bytes, BSS or zero-page storage is needed.

C33 keeps its existing CAPTURE0, TRY1 and PLAN2 APIs. Its unchanged source/caret
case uses the original algorithms. Typed-cache admission, field comparison,
CRC and DMA routines move to the existing R25 spare space (private ops2..13).
New R25 ops14/15 prepare/commit the single-row transaction; neither calls a
second R leaf. C33 calls R16/17 sequentially to repaint one complete physical
row and its existing14 dynamic status cells. Original R25 tail ops0/1 remain.

Build R25 first. Its generated exact payload length and CRC become
`helper-witness.inc` consumed by C33. A new C33 declines an old R25 even with
the same resident seal. Catalog authentication occurs once per uninterrupted
foreground C33 operation; actual overlay admission/DMA still performs the
existing epoch, ownership and executable validation on each call. No yield,
IEC, provider/object mutation, or catalog writer occurs inside this operation.
The old C33 remains compatible with the new R25.

## Deliberately narrow eligibility

The old NC version1 header is unchanged: it still certifies exact rendered row
inputs, the complete source graph/key, full style descriptor, font/catalog/FE
ownership, row anchors and publication sequence. It is never manufactured from
validbits alone. A typing candidate requires exactly one nonwrapping revision,
one-byte length/hot-length change, insert/Backspace caret delta, the proper
hot-delete count, unchanged source tokens/generation/epochs and all other
header fields. Real typed source objects and the selected font leaf are checked.

Target row must be a complete short CR/EOF logical line, starting with a native
letter, with no inline `*`, `@` or pound escape anywhere. Its whole new source
row is read and compared with the old authenticated packet, except exactly one
alphanumeric inserted/deleted byte. Selection, fold, pan, manual pan, pending
jobs, owner conflicts, stale/corrupt capability/cache, structural edits,
soft-wrap geometry changes and unready semantic plans decline.

Palette role0 alone is **not** semantic authority. Before admission the module
reads actual source from BOF to the target line start (at most127 bytes), refuses
any earlier colon, and refuses longer prefixes. The real SuperMark block
classifier can only enter code or regions via colon-leading fences. With no
prior colon and a letter-leading target, no code/region carry is possible.
Single interior alphanumeric changes and absence of inline delimiters then
preserve the target's prose classification. Closed fences and harmless prior
colons conservatively decline too. This restriction is intentional; expanding
it needs an authenticated parser/carry witness, not color inference.

On success the module paints one row using the actual narrow-font renderer,
updates only that owned FE240B packet plus NC256B header, rebases later viewport
anchors by the certified one-byte delta, rekeys the unchanged published semantic
plan, and invalidates its source checkpoint. Root uses the existing successful
TRY publication route, so there is no second full CAPTURE or deferred restyle.
Subsequent motion may flush pending source, correctly invalidating the witness
and causing one ordinary full publication before later caret hits.

R25 may overwrite AC00. This prototype never assumes its font survives: actual
R16/17 admission/row/status calls reload and authenticate it as necessary.
The status path remains the existing cell renderer, not a direct retained-font
shortcut. Scratch stays in existing foreground8880..8BFF. Shared phase8D00..917F,
source/history/clipboard objects and C600..C9FF are untouched.

## Reproduce

```
python3 tests/test_grid_typing_candidate.py
python3 tests/test_grid_typing_candidate_vice.py
```

The CPU gate compares complete independent pixels/attributes and actual full
rendering, whole64KiB with explicit argument/view scratch exclusions, whole16MiB
outside the owned packet/header, read-only failures, and mixed generation pairs.
The native wrapper uses actual IRQ input, .NET VICE PAL/traps/warp, a copied D81,
owned8100/text8200 ports and tracked PID. First publication and settled idle are
reported separately. Timing numbers are PAL emulated cycles, not host warp time
or Ultimate acceleration. Native uses original source/catalog/shim/font/stack
and full-VIC-pixel checks; its catalog/pending-source REU checks do not substitute
for the CPU gate's byte-exact whole16MiB proof.
