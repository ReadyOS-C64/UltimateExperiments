# Private retained lexical-page vertical slice

This is a CPU-qualified component, not an installed editor feature. It does not
change a semantic root, CR lexical reference, or existing baseline completeness.
The test replaces unused C29/R26 images only in a private frozen fixture and uses
the real overlay loader, R14 source provider, lexer, typed object services and
arena page reader. No host parser events feed either worker.

Run from the repository root:

```sh
python3 tests/test_cache_lexical.py --fixture build/cache-editor-product/20261026T035310363807Z/fixture
```

`--build-only` measures linkage without running the fixture. Current linked
capsules are C3993 bytes (controller1143 + unchanged lexer2850) and R3917 bytes
(entry2712 + arena core233 + reader972), including their binding headers. There
is no new BSS, ZP, object or bank. Existing owner4 BC_FRAME576 holds all state.
The actual lexer60 occupies +94; counted R14 reader86 +173; input32 +259; real
CR96 +291; arena control61 +387; IO128 +448. Header/output aliases are explicit
in api.inc and page.inc. Output roles8200..827F are provisional caller scratch.

## Component protocol

The C worker accepts only a completed real C35 classification: full source59,
captured authority13 and genuine CR96. It checks CR format/CRC, code kind5 and
language BASIC1 or assembler2, then begins a real counted R14 lease and compares
all59 source fields. It feeds each canonical BODY byte exactly once. STEP feeds
at most32 bytes and performs at most one32-byte source read. READY1 exposes a
span7 (`role,START24,END24`); repeated STEP holds it unchanged. ACK follows a
successful append. READY2 is a finish barrier, retaining the lease until the
publisher completes and terminal ACK releases it. CANCEL is idempotent and
preserves foreign/stale-epoch leases. Consumer reopen uses a fresh real lease.

The R worker finds an allzero directory entry in the actual typed53 allocation;
it does not infer a physical bank. It stages at most562 span7 records in one
page. Descriptor96 + spans fit4030 payload bytes. It seals payload CRC, page
header, page VALID, directory CRC and finally the one-byte directory VALID.
The returned page/generation is the only reference the test passes to a reader.
STREAM on the563rd span returns A3; no lexical completeness is published.
Cancellation may leave unreachable staging bytes in that unused candidate page
or a directory entry whose VALID remains0. Existing root A/B, CR/INLINE pages,
source/history and foreign REU remain exact. This is not whole-bank rollback.

The LXC1 descriptor binds ABI1, language, BODY/END24, authority13, actual source59
and span count. Consumer READ_BEGIN takes a canonical24-bit position and count
1..128. Its dimensions remain immutable while pending. The existing arena
reader checks directory, header and the entire payload CRC before interpreting
the descriptor. Role4 fills uncovered bytes; stored ordered spans override it.
Each STEP paints at most32 output role bytes. READY is published only at final
success. A161-glyph caller would require two bounded windows. Plain and Markdown
BEGIN return A2 without source lease, frame writes or lexer feeds; Full is3.

## Measured admission policy

These are actual6510 instruction counts including overlay admission, binding,
CRC and source guards, not native cycles. Initial semantic C35 classification
is common setup and is reported separately. All roles match both the independent
host lexer oracle and the original packaged C25, byte for byte.

* BASIC25-byte BODY: build206580; three hits102663 versus original C25 windows
  95701. Both build and hits lose. ASM24-byte BODY also loses. Do not admit all
  code lines unconditionally.
* Sparse BASIC1007-byte BODY crossing65536: build380779; six hits169137; total
  549916 versus original C25 windows1289973 (57.4% fewer instructions). The
  cached windows include a128-byte query crossing65536 and execute zero actual
  lexer feed entries. Build uses9 overlay loads; each later window uses1 or2.

This supports a future conservative opt-in for longer, revisited logical BODYs.
It does not establish a universal length threshold or predict native latency.
Font/palette values are absent from the lexical key because stored role IDs
encode grammar, not color; actual renderer application remains a later gate.

## Subsequent promotion ABI proposal — not implemented

1. Keep cold producer and page transport as separate operation-sized leaves;
   coordinate catalogue/slot/headroom before adding registrations. No new bank
   is required if an existing53 arena has a free page; pressure safely declines.
2. Add an explicit versioned root lexical capability and checked CR lexref only
   after a page is fully committed. Existing root ABI0/CR NIL must remain valid
   and safely miss. Never install a fabricated ref or overwrite a live CR page
   in place: a new directory/root transaction must publish reachability last.
3. Consumer admission must bind arena/ticket/incarnation, full live FS59, grammar
   language and BODY boundaries, then use the actual returned ref plus full CRC.
   Source edits or W_LOAD representation changes currently miss; no numeric
   epoch/content-equivalence shortcut is licensed by this proof.
4. Preserve old reachable baseline on STREAM/error/cancel. Allocation pressure,
   missing module, policy bypass and unsupported/multi-page BODYs use real C25.
   Do not publish partial-role completeness. A future root lifecycle must revoke
   lexical refs together with existing source/arena authority.
5. Integration must prove public code-render windows, cancellation/missing assets,
   observer drain/rebase and lifecycle, then compare full cold+revisit cost with
   the same packaged C25 input before choosing a production admission policy.

The component test also covers foreign-owner opacity; Plain/Markdown bypass;
CR/root-source mismatch; source/ticket/incarnation/map faults; eight cancellation
points; stale held-epoch cleanup; dense real-span STREAM; immutable consumer
dimensions and published-payload corruption. FullRAM checks protect regions
outside explicit service/scratch ranges, and wholeREU checks allow only the
actual candidate page and its directory8 during construction. Read hits are
entirely REU-read-only. There is no native, root/CR linkage, persistent lexical
discovery, editor consumer or complete end-to-end cache claim.
