# Private narrow caret transaction

This is a CPU-tested candidate, not a production route or a native timing claim.
`build.py OUT IMMUTABLE_FIXTURE` links a sealed C33 command leaf; it adds no
resident, BSS or zero-page reservation. The current 47-asset fixture accepts it
as the 48th catalog image through the real import API, using the existing three
logical asset banks. This private fixture does not change the production cold
startup's 47 imports or D81.

## Coordinator seam

- Operation 0 CAPTURE is trusted **only after** a successful full narrow frame
  and its real publication. UI/menu/job/draw state must be idle. It does not
  allocate. It seals the actual 22 cached input packets, source/context fields,
  published anchors, styles, selection/folds, font capability and draw sequence.
- Operation 1 TRY runs before the normal 60/80 root render. `A=0/C=0` means the
  transaction painted its rows/status and updated the retained witness; the
  resident caller must clear redraw and call the existing publication exactly
  once. `A=2/C=0` means use the normal full path. Wrong phase owners return this
  miss without inspecting/writing the private frame. The outer loader can still
  return its strict transport error before C33 executes (for example epoch18).
- No C-to-C nesting. C33 uses only the existing R16/R17 admission/row/native-cell
  operations. It leaves the caller phase union $8D00-$917F untouched.

`api.inc` defines the exact byte layout. Caller RAM is $8880-$8BFF, excluding
$8800-$887F diagnostics, VIEW, NAV, HOT and the ReadyOS reservation. Existing
FE grid row inputs occupy $0000-$149F. The new header is $1500-$15FF in that
same typed logical allocation, and its use requires the width identity60/80.
The interpretation is mutually exclusive with the GEOS FE page cache.

The header uses CRC16/CCITT-FALSE for itself and every 240-byte row input. It
binds the full 28-byte canonical source key, pending window identity, all 23
anchors, layout/pan, the complete 37-byte published style descriptor, selected
anchor, typed fold identity/projection, actual R16/R17 catalog size/CRC/provider
mapping and exact publication sequence. Valid bits are an additional condition,
never a source-revision certificate. Source bytes are not rewalked on TRY;
resident document/view capability validation remains mandatory. Header/row CRC
is a derived-cache integrity check, not a replacement for source ownership.

TRY reconstructs flags from canonical ownership and the authenticated role/char
packets. It paints at most the old and new row plus 14 changed native status
cells. Marked moves require adjacent visible rows; other changes fall back.
Ordinary local movement commits a pending group in current production: the
changed document generation deliberately misses, then a real full publication
can be captured again. Pending source itself is supported if its identity and
geometry remain unchanged. Manual-pan changes and off-viewport movement also
fall back rather than manufacturing a new layout.

## Memory and promotion budget

The current leaf is 3606 bytes (490 spare), no BSS/ZP. A new catalog entry uses
no additional logical bank. A production table entry needs three cold bytes;
`GRID` can alias the existing `GRIDEDIT` filename prefix, but current cold end
$0EFD provides only two bytes before the fixed $0F00 probe. At least one cold
byte still needs measured recovery. The two resident hooks need approximately
55-60 bytes; current resident has two free bytes, so this is **not** a complete
production fit. Root must relocate/compact code and measure the final link.
A C16-to-C33 call is forbidden; CAPTURE must return to resident first, or be
reworked as an explicit root continuation. C16 stays4096 unchanged here.

The managed loader's sticky stage/font invalidation policy is unchanged. The
candidate records the full font asset capability/CRC and admits that leaf
before any painting. It does not rely on a wrapping load counter. Checked asset
writes revoke managed tags; silent external raw REU/font mutation remains
outside that managed contract. No source/history/clipboard writes, allocation,
phase-union writes, shim writes or catalog-policy relaxation is introduced.

## Reproduce

`python3 tests/test_grid_caret_candidate.py` creates only private build output.
The CPU gate calls actual source/edit/navigation commands and actual leaf
imports. Successful TRY uses one disclosed future-root seam: clear redraw and
call real `se_er_published`; it does not seed source, geometry, row packets or
pixels. Reference is the actual completed full renderer plus an independent
font/style/selection/fold oracle, with all 64k bitmap pixels/1000 attrs checked.
Whole16MiB REU is unchanged outside two exact 240-byte row packets and the
256-byte header. Failure injection is explicit and preserves the source,
history, clipboard, phase union, bitmap, attributes and entire REU.
