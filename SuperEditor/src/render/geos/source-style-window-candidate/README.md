# Current C20 output certificate — private released candidate

This preserves the literal editor's existing C20 source reads and 32-byte C26
queries. It retains their style/role output for the first 161 canonical source
bytes of the current C20 line, so C21 need not parse the same logical body again.
It is not a cross-job style cache, source checkpoint, prefetch or rendered map.

## Promotion recipe

`ready.patch` is against the exact sources frozen in
`build/geos-preflush-product/20261025T193429355750Z/fixture`.
Apply its three existing-file changes and three NEW helpers to canonical
`src/render/geos/`. Do not copy the historical `page.s` in this directory.
`page-current.s` is the complete rebased C21 for inspection only; the only
coordinator change is one include and a 14-byte routing hook. All preflush and
semantic checkpoint hooks remain unchanged. Add helper files to source-line
build dependencies if desired; object list, flags, cfg, catalog, resident and
root scheduler are unchanged.

C20 remains compiled with `SE_EDITOR_GEOS_INLINE=1`. The generic non-inline
source-line image is byte-identical (494 bytes with common bound service seams).
The opt-in implementation rejects `SE_EDITOR_GEOS_RENDERED`, whose canonical
ledger would conflict with the certificate. It does not implement hidden markup.

Measured on binding `35abf057d66aedcd5ce2f1958280eaf0`:

| leaf | before | after | sidecar SHA256 |
| --- | ---: | ---: | --- |
| C20 geosline | 3461 | 3904 | `72bb9747c1dce84ac2dfbeb92b5915b8d86bc084011deca53eb27f5cd85af2c0` |
| C21 geospage | 4048 | 4062 | `0b32e317decf2043e42fb6d793c884d93c3265e9a24eec08ba87efc88c7b030f` |

No new BSS, ZP, resident bytes, asset, REU handle or bank. Root's existing worker
completion routing suffices. C20 editor op7 (`SC_CONSUME`) returns A0 on a hit;
a miss hands normal C26 BEGIN0/WIDE4 to root and returns A1. All entry paths check
owner4 before reading phase or certificate. It requires inactive C20 context.
The operation copies at most161 style/role pairs in one bounded call; it feeds
no source bytes. Original BEGIN/STEP source-feed32/read-one budgets are unchanged.

## Authority and lifetime

* GS_BEGIN clears VALID. Only outputs returned by actual C26 and accepted by
  C20's original fresh-lease full59-byte identity comparison are accumulated.
* Each appended chunk matches the full59-byte identity, logical
  START/END/BODY/ROLE, and contiguous current GL_START-relative offset.
* Only actual line completion publishes VALID2; cancel/error clears it. C21
  compares the completed identity, context and exact requested FIRST/count.
* C21 still checks actual source/FE authority on every entry, including after
  op7 and before consuming outputs. Source changes across either side of op7
  are rejected before pixels. The saved identity comparison is not substituted
  for those existing guards.
* A miss takes the original C26 path. Pan beyond the cached first161 safely
  falls back. No source provider invocation or source read is skipped in C20.
* Successful consumption clears the inactive aliased `se_fs_owned` byte, just
  as the old C26 publication did. No lease is released there: GS context is
  already inactive, and real counted read leases remain unchanged. GL X-map is
  already persisted by C21 before this operation.

Ownership: 4400..458B (396 bytes); untouched ledger suffix458C..45E5 (90 bytes).
Packed C20 continuation45E6..47F2 and untouched13-byte tail47F3..47FF retain
all prior guards. Temporary9131..9133 is below parent9134 and only used inside
C20 calls. C26/GL alias phase can be overwritten only after source completion.

## Executable gates and measurements

`tests/test_geos_style_certificate_candidate.py --base <fixture> --suite`
`fit|inline|fold|incremental|capacity|profile`; add `--control` for the profile.
`tests/test_geos_style_certificate_faults.py --base <fixture>` retains the
original bridge recovery suite and adds op7 seam changes, STOP, fallback and
six foreign owners with complete phase/certificate/16MiB unchanged checks.
These are private CPU substitutions, not a packaged D81 or native claim.

Current-checkpoint fair whole-page CPU instructions, exact independent pixels,
source/history/catalog/shim and typed16MiB write guards:

| source | control | candidate | saved |
| --- | ---: | ---: | ---: |
| diverse422 | 2,606,084 | 2,520,019 | 3.30% |
| inline406 | 4,244,711 | 3,754,049 | 11.56% |
| long styled863 | 15,246,872 | 12,218,884 | 19.86% |

Duplicate C21 C26 queries3/8/18 become0; C20 queries6/14/38 remain unchanged.
R14 calls65/130/1581 become60/99/1095. Requested C26 source bytes are not DMA
bytes (adapter may short-read/clamp). These are CPU instruction measurements,
not PAL cycles or first-visible/key latency. Long-line C20 repeated lookahead
remains a material cost; this certificate does not solve it.
