# Private C19 resource-pressure recovery

Released private source; no canonical source, allocator, Makefile or resident
changes. Frozen input: `build/cache-editor-product/20261026T052628862819Z/fixture`.

The original full fold suite fails after CUT with `$35`: current source/history,
the old published fold map, clipboard and optional semantic arena consume seven
objects; retention temporarily needs both a hint and a new map. The same failure
occurs on the preceding045019 build. This is not an R21 regression.

`coordinator.s` and `retain.s` are frozen source copies with only an import and
their one `JSR se_object_create` replaced by `JSR ec_create_fold`. `create.s`
first performs the original CREATE unchanged. Only actual resource errors `$35`
(object catalog full) or `1` (provider logical/physical banks full) may attempt
retirement. `$99` is not this provider's exhaustion contract. All other failures
return unchanged. Successful ordinary CREATE retains its A/X/Y/carry result.

Retirement requires foreground owner3, no ACTIVE/MUTATING job, the actual
generational/epoch token, type53, and the full logical/physical extent graph.
The existing object release service revalidates every extent before freeing.
Only after success does the helper clear the five-byte arena capability, clear
ARMED/PAGE, and set LOST. Ticket, incarnation, head/tail/count, all96 ring bytes
and TRIED16 survive. The helper neither reads nor writes BC_FRAME. Its only phase
input is the existing `se_ec_banks` outside BC_FRAME; no new state or ZP exists.
It retries actual type46 CREATE once with that bank count. If reclaiming the
arena still cannot satisfy the request, it returns the genuine retry error.

Keeping TRIED matches C12 and avoids automatic allocation/reparse thrashing
under pressure. The semantic cache remains unavailable until a later explicit
baseline policy or new document incarnation resets admission. Required fold
operations continue through the ordinary parser. This is a deliberate cache
retry limitation, not loss of source or stored fold choices.

Private link: normal C19 entry + cloned coordinator/retain + frozen reader
dispatch + create.s + one generated module-bindings object, using the frozen
fold-editor-control.cfg. `build.py` rebinds from the supplied immutable resident,
never current shared labels. 1469B versus1370B control: **+99B**, no BSS/ZP.

Run:

```
python3 -u tests/test_cache_fold_pressure.py --fixture build/cache-editor-product/20261026T052628862819Z/fixture
```

Final run: `build/cache-fold-pressure/20261026T054407141226Z`.

* Original28 independent fold/source/history/clipboard/pixel/map frames pass,
  including CUT/Undo, retained pending edits, changed opener, navigation,
  wrapped opener and summary above64KiB. Only the prior obsolete transport
  allowance changes, with exact observed typed46/FE/first53 DMA byte masks.
  Existing53 is immutable except the authenticated, observed retirement.
* Fourteen actual loaded-C19 helper cases: ordinary CREATE; real35 and real1
  success; insufficient reclaimed banks (one retry, error1); ACTIVE, MUTATING,
  stale generation/epoch, foreign type, logical/physical/map faults, foreign
  phase and nonresource36 refusal. Every helper case preserves all16MiB REU
  bytes and the complete1152B phase union, source/history and shim. Full64KiB
  guards allow only declared allocator/request/catalog/provider/BCcap+flags
  temporaries and stack. Refusal preserves all object/provider publication.
* Six representative CPU PNGs directly reviewed; no native/timing claim.

The tests use documented CPU IEC/font fixture transports. The only executable
substitution is a sealed private C19 against the unchanged frozen resident and
other53 assets. Canonical integration and native qualification remain separate.
