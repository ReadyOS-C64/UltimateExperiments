# Optional confirmed-empty inline hint

Release: compile the replacement fast-entry.s with `-D BCQ_EMPTY_INLINE_HINT=1` only for C37. Without the flag its 3491-byte sealed SEO is byte-identical to the original; enabled payload is 3528 bytes (+37), no BSS/ZP. C35 remains unchanged (same selector would overflow to 4118 bytes).

After real checked semantic CR/source validation, eligible kinds below 4 publish INLINE=0 only for FINISH-complete bit4, 24-bit event count zero, and canonical FFFFFFFF INLINE reference. Every inconsistency retains conservative INLINE=1. The original kind accumulator is restored before subsequent class/role dispatch.

Runtime proof: 26 actual-render frames, six fault groups, 1920 local-predicate whole64KiB cases. The full runtime gate used the prior unguarded hint binary; independently assembled flag-on sealed SEO is exactly byte-identical. Flag-off assembly proves old sealed binary identity. Local predicate host inputs are explicitly a pure bytecode predicate seam, not authenticated source records. All public rendering inputs, semantic arenas and pending edits were actual editor-produced. Includes 256 inline events, unmatched markers, real PETSCII $5C escapes, nested styles, Full/Markdown/Plain, valid-CRC malformed hints, source revision changes and foreign owners.

Reproduce `python3 tests/test_cache_inline_hint.py` (see --help for fixture options); builder is build.py and narrow promotion diff is ready.patch. No canonical source/build changes were made by this lane. Exact full16MiB comparison excludes only enumerated derived FE spans; no whole-bank mask. CPU instruction savings are not native cycle claims. This hint does not close the general editor performance goal.
