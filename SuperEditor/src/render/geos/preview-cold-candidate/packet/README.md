Private feasibility component only: actual R14 bounded packet encoder/sink.
It is NOT a staged preview controller, layout engine, consumer or speedup.
Released prepare.inc in the parent directory remains unchanged.

`tests/test_geos_preview_packet_candidate.py` links unchanged actual R14 source
adapter with three additional private operations:3BEGIN,4STEP,5CANCEL.
Control2331B is byte-identical to coherent101910272004Z R14. Candidate3341B
adds1010 and leaves755bytes. No residentBSS/ZP/catalog asset.

The source producer must have its OWN canonical24-bit cursor. PP_POSITION,
PP_X/Y/HEIGHT and row anchors belong to the paint consumer and may advance only
through actual font metrics and hidden-control consumption. Advancing a source
producer by a contiguous raw160B packet is safe only as source lookahead; it is
never a viewport row/page boundary. A bounded batch may end before enough
visible glyphs to fill the page, or may contain unused source suffix after the
consumer reaches the real bottom. It must support another source batch or
throw away suffix. No constant source-byte count predicts viewport geometry.

Wire packet534B:
0..15 canonical GSEM KIND/LANG/LEVEL/MARKER/START/END/BODY/ROLE/REVERSE/HEIGHT;
16..18 canonical raw window query;19 count0..160;20..22 raw anchor;
23..29 selected logical-line base profile7;30 profile index;
31 bit0native-code-body,bit7first-band(metrics/anchor allocation stillneeded);
32..191 native source160;192..351 inline styles160;352..511 roles160;
512..531 matched-control hiddenmask20;532..533 CRC16-CCITT-FALSE littleendian.
Inactive raw/style/role slots are zero. Code styles/hidden are zero, roles are
actual C25 output, not an old C26 packet. Prose arrays come from actual C26.
Source/font geometry is not precomputed or invented by this encoder.

The caller initializes the private phase frame (tests poison then explicitly
initialize ACTIVE0). K=CC50..CC60; destination wordCC59 is input. Scratch9000..901F
holds header below retained source context9040. Buffer8880..88FF is dead CG
output before the next font operation; no glyph may be live during the sink.
All source/style/role/hidden input arrays remain immutable until DONE/CANCEL.
Owner4 is checked before phase reads. BEGIN validates count/canonical ranges,
full current59B R14 source identity and64settings against C27's captured key,
actual typed FE bank/epoch and destination[B200,E568). It owns a fresh counted
source lease and retains GS_FS for normal resident cleanup. Each STEP guards
source/key/FE binding and writes<=128payloadbytes; last step also writesCRC2.
Source/representation is never changed. DONE is only a caller-owned completion
witness, NOT a durable published batchVALID. A controller must clear image/
source-cache/edit-cache validity before the first stage write and publish a
checked full batch descriptor VALID-last before any consumer can read it.

Measured actual public-worker interception:11diverse259B packets plus7long
source packets, including160B emphasis/hidden-control windows,160B BASIC string
and continuation, emptyEOF. Each packet:5STEPs plusBEGIN,29,492..30,194 actual
CPU instructions, maximum single call6505, ZERO additional cold overlay loads
because R14 was already active after C25/C26 END. Independent canonical host
parser/inline/lexer produces every packet byte and CRC. Each sink preserves
all67bytes of current PP geometry, bitmap/attributes, source/history/catalog/
ReadyOS shim and all16MiB REU outside its exact534B destination. Full normal
preview continued after every sink and matched the independent raster oracle.

This prototype ADDS work to the unchanged row-at-a-time pipeline. No end-to-end
speedup is claimed. Promoting a larger R14 alone also increases every cold R14
admission's CRC cost. Its usefulness depends on batching enough source work to
remove the subsequent R14/R23 swaps; individual packet staging without batching
is not an optimization.

Headroom feasibility, separately LINK-ONLY:
C27's existing `window`+`read_window` block can be replaced by a future sequential
C24 op3 request, reusing the proven preparation/READ implementation. Removing
that code and its dead phase2 branch links C27 at3843B versus4044 (253free).
No C24op3/consumer is implemented or runtime-proven in that link probe. A new
consumer must fit there, fetch completed packets with resident checked DMA so
R23 stays loaded, authenticate source/settings/provider/FE/batch CRC and bound
all lengths before use. Fetching each paint packet through R14 would reproduce
the original swap bottleneck. Snapshot/restore font-stage validity and the
semantic checkpoint/producer cursor across any paint batch are still required.

A24packet batch=12,816B (not12,768: now includes per-packetCRC2) fits FE
B200..E567(13,160B), preserves typing-font cache E568..EA87. Metadata source key
must remain live until full page completion. Warm preview capture overwrites
this same scratch afterward. Folded projection is deliberately rejected by the
prototype; integrating hidden fold jumps/summary metadata is another component.

The253B consumer headroom is NOT proof of a complete guarded consumer fit.
Source identity/lease lifetime must be solved without calling R14 on every
paint packet. A534B bounce at8D00 would overwrite the actual FS context8EE0;
that is unsafe while an own source lease is retained. One candidate bounce is
8400..8615, with explicit se_doc_invalidate before borrowing the cached leaf,
then decode arrays before overlapping code-role output8400. That preserves FS
and GS_FS but still needs full batch/source guard and measured code size.
Existing warm-cache pc_context compares the captured FS identity; it is not a
substitute for checking the current source after arbitrary external mutation.
Do not quietly reuse it as a weaker stage guard. The full guarded consumer,
batchVALID/CRC/readback, source cancellation/epoch/capability fault matrix and
actual stage/paint alternation remain open. No final architecture feasibility
or benefit has been asserted beyond the measured sink and link-only headroom.
