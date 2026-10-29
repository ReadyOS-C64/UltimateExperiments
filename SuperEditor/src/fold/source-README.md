# Pending-aware editor source callback ABI1

Optional actual6510 source adapter for parser/fold/style consumers. It is not
wired into the editor job/UI or given a production placement yet. Build/verify:

```
python3 tests/test_fold_editor_source.py
```

This CPU test links only a private capsule against the immutable2f6d editor
resident bindings. It exercises the real document reader, public splices and
hot-window calls. It restores product overlay bytes **and1152B LINEINDEX** before
calling any editor overlay operation, preserving the capsule's caller phase
separately. Probe addresses are not product memory grants. No VICE/native/video/
physical-keyboard or ReadyOS lifecycle integration is claimed.

## Generic callbacks

All calls are foreground, D=0, nonreentrant per caller context, clobber A/X/Y/P
and existing `text_ptr`. No new zero-page bytes are allocated. No pointer into
shared reader or VIEW caches survives a call. The caller owns the phase context
and output buffers for the full operation; these callbacks do not establish
ownership merely because an address is legal to the object/DMA provider.

|Call|Inputs|Outputs|
|---|---|---|
|`se_fs_begin`|Stable actual document/hot state, idle competing mutation phases|Own counted read lease; `se_fs_length[3]`, `se_fs_revision[4]`; Cclear/A0|
|`se_fs_guard`|Existing active/owned context|Cclear/A0 if full identity still matches; Cset/Aerror otherwise|
|`se_fs_read`|Absolute `se_fs_offset[3]`, requested `se_fs_count`1..128, `se_fs_buffer[2]`|Cclear/A0 and `se_fs_done`0..128 actual bytes copied;0 only at EOF on success|
|`se_fs_end`|Possibly active/owned context|Idempotently release exactly the owned lease if lifetime still matches; Cclear/A0|

`READ` accepts random restarts, including known block/body anchors for a second
inline pass. It preserves its offset input. A short read is normal before EOF;
advance only by `done`, never by requested count. Error returns may also have
`done=0`; check carry first. Offset greater than EOF, zero/oversized request and
unsafe buffers fail. The output argument can change between calls.

Complete requested output spans must fit **one** explicit owned range:
`$8880-$8BFF` (preserving diagnostic `$8800-$887F`) or the caller-owned phase
union `$8D00-$917F`. `$8C00-$8CFF` VIEW, `$9180-$91FF` NAV, hot RAM, shim, wrap/
overflow and overlap with this adapter's own context are rejected before DMA.
The caller layout must additionally keep its other controller/parser state out
of the chosen output span. This is not permission to overwrite a live file or
index phase. Root job/phase ownership remains an integration requirement.

## Exact identity and source shape

The explicit86B context includes59 captured identity bytes: provider epoch,
document epoch/generation, complete metadata/original/append tokens, committed
length/root count,32-bit visible-source render revision, hot ready/pending/phase/
owned/fault/epoch/generation/tokens/base/old length/new length/left/right. Each
operation revalidates current document state, full token generations and every
provider extent mapping. Root counts and16-bit generation alone are insufficient
source identity. The complete monotonic revision and logical-token lifetimes
remain required at editor publication boundaries.

Admission rejects active doc/hot/history/block/clipboard/snapshot phases. It
validates `0<=left<=right<=2048`, `length=left+2048-right`, old length<=2048,
old span contained in committed source and nonoverflowing24-bit merged length /
hot end. A loaded window must match document tokens/generation/provider lifetime;
unloaded hot state is allowed only with no pending bytes. No unchecked hot-RAM
indexing occurs. A later hot-cache load/move/edit or source publication invalidates
the captured context, even when visible bytes might coincidentally be equal.

`BEGIN` acquires its own counted document read lease, preserving existing foreign
leases. It captures identity after successful admission. A failed/repeated BEGIN
never releases another client's lease. `GUARD`/`READ` errors require caller END;
the fold builder's optional wrapper supplies that cleanup automatically.
`END` decrements only if its owned flag, provider/document epoch and all three
current document tokens still match the captured lifetime. On a newly current
epoch or graph, it forgets its stale flag without touching that graph's counter.
A missing/zero counter is never decremented. Pending typing can change the RAM
view without committed mutation; context rejection then releases exactly this
client's still-current committed lease. END is a separate105B cleanup operation
so later integration can keep it callable after failed source-overlay admission.

## Bounded merged reads

Committed spans call actual `se_doc_read_some`, at most8 source descriptors and
128 requested bytes, using the existing `$8000-$83FF` reader scratch and
`$8400-$87FF` leaf cache. The actual returned count is copied to the caller's
owned buffer before return. Requests are refreshed on every call; another reader
may evict the leaf/cache between callbacks safely. No shared VIEW state changes.

Pending-prefix/suffix runs copy directly from validated HOT_FIRST RAM and stop
at the logical prefix/suffix/page boundary. Eight static source-page loops reuse
one existing destination pointer, avoiding a second ZP pointer or self-modified
continuation. Committed offsets after the hot span are translated as
`visible offset -new hot length +old committed length`. No whole document is
flattened, cloned or flushed to obtain the merged stream. The builder still
feeds at most32 bytes per STEP; a source fetch may perform the real bounded
piece-reader transfers, so the direct-object probe's two-DMA bound does not apply
to this adapter. Source byte/descriptor bounds remain explicit.

## Optional fold hook and placement

Compile only `builder.s` with `SE_FOLD_EDITOR_SOURCE` and link these modules. Its
BEGIN copies authoritative callback length/revision into the fold context before
binding; refill accepts actual short counts; every STEP guards source identity;
success/error/cancel call END. Callback BEGIN failure returns directly, preserving
an already active independent source client. Direct-object default builds are
byte-identical to the frozen37ad0e49…bd18c builder.

The old direct-object retention proof is only5B source token +length/revision;
it cannot describe a piece graph and pending gap. Therefore this optional hook
rejects `se_fb_old_valid!=0`. New editor-source candidates start expanded until
a complete captured-identity retention proof is designed. It never silently
reuses a coincidentally equal source position or a short hash.

Measured code:2289B source context/shape/random-read, plus105B END cleanup;
caller state86B, no extra ZP. Full fold builder+parser+adapter phase is643B.
The callback request/output fields contain explicit caller C64 buffer addresses;
no shared-cache pointer is retained. Checkpoints preserve the caller layout, or
rebind the output argument before the next READ after an idle relocation.
These are caller-owned/REU-checkpointable contexts, not additional resident BSS.
The style planner cannot assume this code fits its remaining~500B; the parent
must choose a shared operation slot/resident-mediated callback route and explicit
phase placement. Production overlay dispatch, suspend/resume, real job wiring
and old-map retention remain separate work.
