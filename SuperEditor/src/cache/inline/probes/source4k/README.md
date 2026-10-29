# Private v3: conservative cached SOURCE admission

This is a qualified **private component/frontend**, not a main-editor or native
feature. Actual C20 is byte-identical and continues requesting C26 SOURCE3.
Optional `SE_EDITOR_CACHED_INLINE_SOURCE=1` adds the read-only gate in`gate.inc`;
flag absent reassembles the modified C26 byte-identically to its packaged3327B
control. Enabled C26 is3436B. The SOURCE_ONLY C39 entry is4093B, with no BSS/ZP,
object, bank, resident-code growth or new C20 operation. These private builds
use the frozen bf15 resident; main rebinding/integration remains a separate gate.

## Runtime contract and lifetime

Owner4 is checked before phase access. C26 SOURCE3 delegates only if the source
controller is inactive, C20 continuation167 is1, GSEM is inactive, ARMED/PAGE_PROOF
are present without LOST/MUTATING/ACTIVE, queue is empty, count/role/kind are in
range, actual inline hint is nonzero, and unsigned24-bit END-BODY>=4096. Negative
or other inapplicable inputs take unchanged legacy validation. Registers hold
subtraction temporaries; no phase clear, parser, allocation or source lease occurs
before handoff. This cheap decision is not cache authority: C39 still checks
full59 source/13 authority, typed ownership/map/epoch, complete CR-page/own CRC,
CR schema and context. Only its authenticated actual event count<=8 proceeds to
complete INL directory/header/payload CRC and event validation. Larger counts
END the owned query and request26/5/A1. SOURCE_FALLBACK5 bypasses the gate, so
misses cannot loop. Success ENDs and requests20/1/A1. Other errors remain carry
errors, and cancellation never resumes C20. Opcode5 exists only in this runtime
profile. Normal legacy C26 APIs stay available; no normal C21 PS8 hook changes.

The real GL is832B at8D00..903F. C20's existing SOURCE bridge saves its110B live
core,324B map,59B source identity and32B native packet at45E6..47FF;4400..45E5 is
its live source ledger/certificate. C39 query576 overwrites GL. Its343B staging
at8880..89D6 and control through89F0 borrow inactive R21/glyph work, not live GL.
C39 preserves ledger and backup. After the return, actual C20 inline_resume
restores core/map/packet, reacquires R14 and compares all59 old identity bytes
before measurement. Source revision change there returns74. First10 role bytes
alias query IO while pending and are not consumable; only successful END permits
publication. All21 hidden-mask bytes publish; count styles/roles publish only.

Actual root dispatch must retain odd39's worker-owned OP0/1 and C39 miss26/5.
This verifier follows actual REQUEST/OP sequentially; no resident dispatch,
registered asset, complete raster or native-latency claim is made.

## Reproduction and integration recipe

Run`python3 tests/test_cache_inline_source4k.py` from the repository root.
The test builds original/default/enabled actual C26 from the immutable source ZIP,
compares both default copies with packaged C26, and imports the selected image
through the real manager at cold fixture setup. C39 links this`entry.s` with the
released inline query/source/records plus source-adapter seed/core/page. It
uses real producer→writer→C35→empty-hint C37→C20/C26/C39, not host parser events.
Private state bindings9FB5..9FC5 are an explicit old-fixture seam; production must
resolve the actual`se_bc_*` symbols from its current resident report instead.
The supplied`inline.patch` is a minimal merge guide, not an overwrite of current
canonical C26. Copy/rehome the includes and use the optional flag; C20 is unchanged.
Use ordinary imports-only editor-api/module_bindings once per image.

The final gate has59 SOURCE cases and11124 per-call RAM checks, plus64 exact
read-only admission cases. Independent whole-source style/geometry oracles check
all anchors and every map boundary. Full16MiB, canonical roots/hot/history and
shim are exact; legitimate document-read request/cache/ZP scratch is named
explicitly. It covers pending source, source change before restore, bad cert,
actual foreign owners/CONT tags/COUNT0, real checked fallback, >64KiB, nested
emphasis/code/escape and a legitimate packed255-slot INLpage. Resealed count
metadata0/high24-bit rejects C2; a false8-event short stream preserves the existing
C0 error;9..65535 safely declines before INL reads. No failed result publishes or
resumes C20. The previously released generic34-window/11-fault output gate is
ancestry for unchanged query/source/records; it is not rerelabeled as a generic
SOURCE_ONLY A0/A2 entry proof.

## Actual measured cost

Totals below cover actual C20+workers+overlay admission/DMA, excluding common
baseline and classification. They are CPU instructions, not PAL cycles.

| Case | Legacy | Candidate | Change | DMA old/new | Loads old/new |
|---|---:|---:|---:|---:|---:|
| 4KiB,1 event |914312|264655|-71.1%|101/12|3/4|
| 4KiB,4 events |926305|328394|-64.5%|101/15|3/4|
| 4KiB,8 events |940743|410456|-56.4%|101/19|3/4|
| 5KiB,8 events |1127991|410416|-63.6%|133/19|3/4|
| 4KiB nested/code/escape |923865|308183|-66.6%|101/14|3/4|
| Packed255-slot page,4KiB1 |932528|366551|-60.7%|135/33|3/4|
| Packed255-slot page,5KiB8 |1146413|524186|-54.3%|167/40|3/4|
| 66004B body/query65900 |11990155|257081|-97.9%|2038/14|3/4|

Ordinary tiny inline rows never load39 and retain the same DMA/load counts;
the larger C26 CRC/check adds about1.0% instructions. The dense1800B/300-event
case stays legacy (1037502→1039806,+0.22%,32 DMA/3 loads unchanged). Admission
with>8 events on a genuinely large body still pays bounded CR lookup and fallback
swaps; no universal speedup is claimed. The rejected512-byte v1/v2 experiments
remain separately archived rather than being called equivalent to this threshold.

The initial integration scope is long, sparsely marked logical bodies. It does
not solve general typing/preview performance or reuse INLINE outside this SOURCE
handoff. Actual main C39 registration, source/render pixels, missing-outer cleanup,
resident routing, static stack and native timing still require parent gates.
