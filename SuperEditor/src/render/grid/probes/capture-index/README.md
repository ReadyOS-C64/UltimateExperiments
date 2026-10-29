# C33 capture / persistent navigation index lifetime

`tests/test_grid_capture_index.py` qualifies exact packaged59 images. It does
not rebuild or replace product capsules. The C33 change is parent-owned.

Bad: `build/cache-editor-product/20261026T180419392911Z/fixture`, C33
`91a51068dbebaefc763379a5f6225a9cf0ddaabc098f6b219d2cd7a01eb31f2e`.
Fixed: `build/capture-index-fixed/20261026T183928480377Z/fixture`, C33
`ab86a6aca6a054e7de24c48916856b1393438ef5846f693ff03493fce83d0fbb`.
Resident `93832107...dd76b` and all other58 capsules are identical. Every run
checks the actual D81/resident/all59 capsules/binding/CRC, then uses only the
resident loader to admit modules.

## Reproduction and acceptance

```sh
python3 tests/test_grid_capture_index.py --expect-bad --file-open
python3 tests/test_grid_capture_index.py --fixture build/capture-index-fixed/20261026T183928480377Z/fixture --file-open --extended
python3 tests/test_grid_capture_index.py --fixture build/capture-index-fixed/20261026T183928480377Z/fixture --file-open --reverse --extended
python3 tests/test_grid_capture_index.py --fixture build/capture-index-fixed/20261026T183928480377Z/fixture --far --extended
python3 tests/test_grid_capture_index.py --fixture build/capture-index-fixed/20261026T183928480377Z/fixture --crc
```

Public flow: actual File/Open DIVERSE, typed `syntax plain`, mode60, typed
`goto 2`, six RIGHT, then RIGHT/LEFT/DOWN/UP; mode80 and another `goto 2`.
The bad image genuinely fails the second GOTO with `$7B`. No index bytes or
cache authority are fabricated. The fixed image passes both mode orders and
GOTO1/3/14/20/26/2, including offsets above255. A separate source-seeded66222B
case uses public GOTO9402 and subsequent anchors beyond65536; it is not a
large-file IEC admission claim. File tests model only existing KERNAL/DOS ROM
boundaries; they do not prove native IEC, actual disk writes or physical keys.

All54 fixed primary frames have independent full bitmap/attributes, canonical
source/history/clipboard/selection, catalog and1024B ReadyOS-shim checks.
Every measured mode/GOTO/local-caret interval preserves the whole16MiB outside
exact actual typed-owner validated DMA spans; no whole-FE mask is used.
Canonical caret anchors and the four raw movement endpoints are independently
specified. Bad error-state RAM/REU are retained after checking unchanged canonical source.

The separate internal CRC component first admits actual C33 through its real
resident entry, verifies exact executable bytes, then invokes its sealed
labels. Expanding the256-word table may change ONLY `$8D00..$8EFF`, stack,
and the three actual authority bytes `se_i_ready`, `se_i_count`,
`se_n_cache_count`. All three must become zero.132 packet CRCs independently
match CCITT-FALSE with ONLY CRC2+stack writes. All64KiB RAM and16MiB REU are
checked. This component explicitly supplies arithmetic inputs; it is separate
from the public capture/owner-admission proof.

## Alias audit

* `src/nav/state.s` LINEINDEX is `$8D00..$917F`; CRC tables overwrite its first
 512B. Token/generation matching cannot authenticate these overwritten data.
 `src/overlays/navigation.s:index_context` tests `se_i_ready/count` before using
 the index; `index_reset` reconstructs the first record and resets contiguous
 line-cache count. Clearing all three retained authority bytes before the
 first table store makes this invalidation explicit.
* The copied FS frame at `$8EE0` is within that phase. CAPTURE is admitted only
 with owner0 before claim4, no job/draw/error/hot phase/navigation busy/document
 busy/read locks. Its capture path uses resident `se_view_peek` and R25 pure
 helpers, not R14/FS. A live source lease therefore cannot be overwritten on
 the admitted path. FS bytes after capture are scratch, not a valid FS context;
 later phase clients must initialize their own FS flags before BEGIN. Existing
 style claim clears its reader state, layout-fold explicitly clears FS flags,
 and fold coordination clears the full union. No new FS authority is minted.
* The persistent contiguous line cache lives beyond the overwritten table and
 is separately revoked by `se_n_cache_count=0`. Preferred-column state is not
 index authority and stays intact. The exact CRC component rejects any other
 persistent RAM write.

No broader phase-alias, all-mode native, lifecycle/ReadyOS or hardware claim.
The prior registered raw44/fault24/CRC132 release remains unchanged.
