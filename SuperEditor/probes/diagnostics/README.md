# Read-only diagnostic services (separate integration candidate)

Run from SuperEditor:

```
make -f probes/diagnostics/Makefile test
```

All objects, labels, emitted binaries, private Peddle runtime and results stay
under `build/diagnostics/`. This links the actual REU provider, object allocator,
document import/reader/lease and resident CRC implementations. Tiny fixture
symbols stand in for editor phase/dirty/revision/telemetry fields; it does not
run the editor, overlay admission, menus, VICE or video. The one-MiB original
is imported by assembler object transfers. Fragmented graphs and pending gaps
are independently host-built consumer fixtures. These tests do not close M2.

`src/diagnostics/` is operation-sized: `state.s`, `snapshot.s` (BEGIN),
`context.s` (validation), `scan.s` (STEP), `cancel.s` (resident cleanup).
Only link what the consumer needs. Compile snapshot/context/scan into one command
overlay, with its own ordinary SEO2 binding/entry wrapper. Keep state/cancel
resident so a failed overlay reload can still release the lease. The probe
places the service body at `$B000` and proves a linker-enforced 4-KiB limit;
it does not supply or claim an admitted production overlay. The services use
the existing shared resident `text_ptr`; they allocate no ZP. Their persistent
frame is28 bytes, asserted at most48. No new permanent source/cache buffer or
REU allocation is required.

The resident CRC implementation is CRC16/CCITT-FALSE (poly `$1021`, initial
`$FFFF`, no reflection, no final XOR). Snapshot hash type1 explicitly names this
algorithm, and the versioned descriptor never calls it a cryptographic hash.
The job saves its CRC between calls and restores it only immediately before
hashing. Overlay admission/other clients may freely clobber `se_crc_value`
between slices. Both existing resident CRC variants preserve Y and are suitable.

## API and lifetime

Set `se_diag_buffer[2]` to the start of an exclusively caller-owned128-byte
buffer wholly within `$8800-$8BFF` (valid starts `$8800-$8B80`). Set
`se_diag_cursor[3]` to the current visible caret, at most merged EOF. Call
`se_diag_begin`: carry clear/A1 means scanning. An empty source still starts a
job and completes on its first STEP, with CRC `$FFFF`.

Call `se_diag_step` until carry clear/A0 (complete); carry clear/A1 means more
work. Each STEP hashes at most128 native bytes. A committed slice delegates to
`se_doc_read_some`, so it visits at most eight source-piece spans, with that
reader's documented root/leaf seek and bank-split costs. A gap slice stops at
the prefix/suffix boundary. This is a finite operation budget, not a raster,
cycle or responsiveness guarantee. No slot/cache/hot-buffer pointers persist
between calls. Source bytes are consumed directly, with no PETSCII conversion.

`se_diag_cancel` is resident, idempotent and returns carry clear/A0. It releases
only the read lease this job acquired, and only when its saved epoch matches
both provider and document epochs. New-provider leases and foreign same-epoch
lease counts are preserved. `se_diag_abort` is the resident failure cleanup
entry: A error -> carry set/A same error, with a failed descriptor. A dispatcher
must call it after a failed overlay reload while a job is active.

The coordinator must serialize use of COW scratch, and must never start a
writer or hand `$8800-$8BFF` to another service during the job. BEGIN refuses
active document mutation, hot load/flush, history, block, clipboard or snapshot
work; its owned document read lease prevents ordinary COW publication across
slices. It validates every hot bound and token before reading the gap. STEP
checks full source tokens, committed generation/length, provider epoch, hot
state/bounds/tokens and visible edit revision before continuing. A same-length
pending edit is caught by the existing editor's `se_r_revision`. A new consumer
must maintain that revision after each successful local mutation, as the editor
does. Conservative refusal after a gap/cursor rearrangement is permitted.

The caller must not change the admitted output buffer or resident private frame
while active. BEGIN captures the request pointer; request fields may then be
reused. It captures cursor, dirty state and telemetry at BEGIN; cursor movement
and overlay telemetry need not be frozen during the scan. Output expires when
the caller relinquishes the COW scratch (typically before the next mutation).
No claim is made that this buffer is permanent editor storage.

Carry-set errors: `$78` no active job/competing job or busy consumer; `$79`
source context changed; `$7A` invalid buffer/caret; `$7B` malformed gap bounds.
Lower provider/object/document errors propagate. Failed admission leaves output
and leases unchanged; STEP failure writes status4/error and releases its lease.
An already-active repeated BEGIN refuses without disturbing its job.

## Snapshot descriptor

`src/diagnostics/api.inc` is the complete offset definition. All integers are
little endian. The128-byte descriptor starts `DGS1`, ABI1, size128. Status1
means scanning,2 complete,3 cancelled,4 failed. The CRC is authoritative only
at status2; scanned24 reports progress. The descriptor includes visible merged
length, committed generation, supplied visible caret, pending, history dirty,
combined dirty, provider epoch, original/append/metadata tokens, hot context,
and the BEGIN overlay loads/hits/calls (modulo16bit).

Offsets34/36/38 point to the provider's live256-byte logical map, logical-owner
and physical-owner arrays. These are read-only borrowed descriptors, valid only
for the captured provider epoch and while the foreground coordinator prevents
allocation changes during inspection. They are explicitly **not copied table
snapshots** and must never be retained as an archival allocation snapshot.
Offsets40/42 are BEGIN counts of allocated logical owners1..254 (includes the
control bank) and free physical owner0. The provider's bank count and retired
flag are also captured. Owner0 is free,1 control,2 overlays,3 document metadata,
4 document sources,5 clipboard, other owner codes follow their owning service,
and255 is unavailable. Logical handles and physical banks are separate domains.

All source/REU data, hot bytes, view/index frames and `$C600-$C9FF` are preserved.
Ordinary document I/O/cache and shared request frames/CRC/ZP are transient and
may change; the exact exceptions follow the existing document reader ABI.
