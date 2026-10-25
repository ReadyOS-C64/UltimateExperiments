# Fold editor leaves

Actual operation-sized C17 `foldparse`, C18 `foldfinish`, R18 `foldcore`.
No root/UI integration is implied. Existing foundation/builder/parser objects
are compiled unchanged; no private leaf calls another command leaf.

`api.inc` defines the exact frame opcodes. Root owns `se_f_owner`; every entry
refuses non3 with B2 before any phase read. C17 op0 BEGIN, op1 STEP phases1..3,
op2 CANCEL. C18 op1 STEP phases4..9, op2 CANCEL; BEGIN refused. Wrong op/phase
returns B0 before touching phase state. C success returns Cclear/A2 pending or
A0 complete; errors Cset/Aerror. CANCEL is idempotent. No entry claims ownership
or allocates/releases the map object. Caller supplies owner46 token/capacity.
Editor-source BEGIN still refuses old_valid1; flat-object retention is insufficient.

R18 exposes foundation operations0..13; FAIL's primary A must be copied into
frame+1. Core operations retain the original foundation return semantics, not
C pending2 semantics. Ops14/15/16 invoke the bounded locator begin/step/cancel. A core entry does not acquire a source lease.

State geometry (all aliases to caller phase, no additive resident BSS/ZP):
foundation197 at8D00; existing SM block79 at8E11; builder89 at8E60; common record32
at8EB9; existing FS86 at8EE0; source128 at8F36; old-record32 at8FB6. Total643B,
with gaps enclosing726B through8FD5. No phase pointer escapes a returned call.

Root calls C17 until a completed STEP publishes phase4, then C18 on the next pump.
C bridges enter R18, and the existing source bridge enters R14 sequentially.
R slot contents are never assumed to survive the other bridge. Foundation is
entirely within R18, using only resident object/DMA services. C18's unreachable
SM stubs and C17's unreachable filter stubs reject; entry guards prevent reaching
them through supported operations. The full unchanged builder control object is
intentionally duplicated between C leaves.

Resident `se_fs_end` is an epoch/token-safe emergency exit even when either C
or R leaf cannot load. Root must gate owner3 first, preserve the primary error,
call END, invalidate candidate/job state and then release owner3. If source BEGIN
refuses another active client, it acquires nothing; caller must not blindly END
that client's lease. A missing top-level leaf has run no cleanup itself.

Build/link order: entry first, unchanged code components, bridges/stubs, then
state objects, then exactly ONE generated tools/module_bindings.py alias object.
`tests/test_fold_leaves.py` exports reusable `build(out,base)` to seal against a
verified immutable resident fixture. It uses the existing reader-dispatch.s27B.
The generated editor-api.inc declares overlay frame/call imports and binding
macro only; it does not duplicate generated resident alias exports.

Measured on0659: C17 3244B, C18 3177B, R18 3015B (includes16-byte binding each).
R18 includes the released403B bounded locator and has1081B free. All linkers assert4KiB area fit and fixed
phase placements. No shared Makefile, root, foundation or source-reader files
were changed by this lane.
