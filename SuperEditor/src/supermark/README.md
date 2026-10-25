# SuperMark streaming services

These are actual ca65/6510 semantic modules, independently CPU-tested, ready
for editor integration. They do not yet implement editor styling, a fold tree,
rendered editing, or dialogs. No parser byte is sent to CHROUT or rewritten.

Build and verify from the SuperEditor directory:

```
make -C probes/supermark test
```

The standalone CPU fixture links block/inline/lexer code at $8000/$9000/$A000
and contexts at $C000. Those are **probe addresses**, not new editor memory
reservations. Each code segment is independently below 4 KiB. Link only the
operation needed; place its context in caller-owned RAM and checkpoint it in
logical REU storage when useful. No zero-page allocation, DMA, VIC, KERNAL,
resident editor symbol, or overlay call is required. The existing overlay
binding/header/trampoline still needs to wrap any eventual editor-side consumer.

All calls are foreground, nonreentrant for a given context, clobber A/X/Y and
flags, and require binary arithmetic (D=0). Absolute 24-bit source positions
are little endian. Caller ensures they do not overflow and supplies only bytes
inside its document range. Context layout version is `SM_ABI_VERSION=1`.
`se_sm_state`, `se_si_state`, `se_sl_state` and corresponding `_state_size`
exports identify complete pointer-free contexts. Copy the entire context for
checkpoints; no stack/ZP/self-modified code is part of a checkpoint. Every input
call accepts one byte; boundaries between host/REU chunks have no semantics.

## Block classification

Call `se_sm_init`. Origin is zero; for another source line boundary, write
`se_sm_pos[3]`, then call `se_sm_at_line` immediately after init. Feed each byte
to `se_sm_feed` in A, including CR $0D. Consume the event when `se_sm_ready=1`
before feeding the next byte. `se_sm_finish` emits a final nonempty line without
CR; it does not manufacture a blank line after a terminal CR. Feed/finish return
carry clear. Initialization is a new parser context, not a document mutation.

The event contains:

| Field | Meaning |
| --- | --- |
| `kind` | 0 prose, 1 empty, 2 heading, 3 list, 4 fence open, 5 code line, 6 fence close, 7 region open, 8 region close |
| `start[3]`, `end[3]` | Entire line source interval, excluding CR |
| `body[3]` | Source boundary after the structural prefix; end for fence lines |
| `level` | Heading 1–6 or list nesting 0–3 |
| `language` | 0 plain, 1 BASIC V2, 2 assembler; meaningful for code events |
| `fence` | Active exact closing-colon length after the event, zero outside code |
| `regions` | Recognized explicit-region depth after the event, maximum16 |
| `marker` | Advisory prefix length; 0 for list prefixes exceeding255 bytes—use `body-start` |
| `end_state` | 1 on an exact code-fence close, otherwise0 |

Classification waits for CR/EOF, so a closing fence is exact rather than a
premature match on a prefix. At most32 source-prefix bytes are cached. Heading
markers, fence labels and region introducers fit this window. A separate
bounded state machine accepts arbitrarily long ordered-list numerals, retaining
the exact body anchor. No complete line buffer is allocated.

Column zero is required for headings and fences. Heading needs a space, levels
1–6. Lists permit exactly0/2/4/6 leading spaces, then `- `, `* `, or one or more
digits followed by `. `. Supplied numbers are untouched. Empty means a zero-byte
line; a whitespace-only line is ordinary prose. Code has precedence over all
other structure. Fences require3–15 colons and a nonempty label, and close only
on the exact number of colons with no suffix. Known `basic`/`asm` labels select
lexers; `text`, unknown labels, and labels with trailing text select plain code.
Labels compare native case-insensitively. A bare closing fence outside code is
literal. A16-colon opener is literal, as specified by the bounded grammar.

`:::region` accepts an optional space/title; `:::end` must be exact and is
literal without an open region. Region depth beyond16 and its matching ends
remain literal; the overflow counter prevents the extra end from closing a
recognized outer region. Markers inside code never affect region depth.
Heading and code/region events provide source anchors for a fold-tree consumer;
this service does not retain a tree, collapse flags, or transformed edit anchors.

## Inline matched-pair events

Call `se_si_init`, optionally set `se_si_pos[3]` to the source origin, and feed
bytes with `se_si_feed`. Consume `ready` events before the next feed. Call
`se_si_finish` at EOF. For a recognized heading/list/region-title body, first set pos to its body
origin and call `se_si_at_body` with A/X/Y = skipped prefix length (low/mid/high).
This excludes the structural marker and retains the original logical column.
For ordinary prose, scan the whole line after init. CR automatically ends all inline constructs; no emphasis
or inline-code delimiter spans a CR. The parser emits no event for an unmatched
opening delimiter, so literal source is always the safe initial presentation.

| Event field | Meaning |
| --- | --- |
| `kind=1` | A matched pair |
| `style` | Mask1 emphasis, mask2 strong, value3 combined; value4 exclusive inline code |
| `width` | Exact opening/closing delimiter width |
| `open[3]`, `close[3]` | First byte of each delimiter |
| `kind=2` | A confirmed pound escape; open points at £ and close at the escaped byte; width1/style0 |

A matched-pair consumer hides `[open,open+width)` and
`[close,close+width)`, and applies style to `[open+width,close)`. Escape consumers
hide only the pound byte. Every visible glyph remains mapped to its original
source byte; do not delete source markers as part of rendering. Nested emphasis
spans combine their bits. Inline code overrides enclosing emphasis.

Exact runs of1/2/3 asterisks represent emphasis/strong/both. Runs of4 or more
are literal. Matching is properly nested with a maximum8 openings; excess
openings remain literal. Exact `@@` opens/closes inline code; other @ runs are
literal. Emphasis and escaping are disabled inside inline code. Unclosed inline
code remains entirely literal, including its interior markup. The parser emits
descriptors after closure, so a consumer must collect/apply spans before drawing
a line or invalidate earlier rows when a deferred event completes.

The native pound is $5C. `£*`, `£@`, and `££` are inline escapes. Block-only
escapes require syntax to be possible: at column zero, `£#{1..6} ` and
`£:{3..15}label`; at valid list indentation, `£- ` or digits followed by `£. `.
Those events wait for confirming lookahead, across chunks if necessary.
`£5`, `word £#`, `£#no-space`, `£-no-space`, `£:one-colon`, seven hashes, and
deeper/odd list indentation retain £ literally. Block scanning must see the
original bytes, so the leading £ prevents an escaped block marker from becoming
structure. Normal document typing does not generate an ASCII backslash escape.

## BASIC/assembler lexer

Call `se_sl_init` with A=0 plain,1 BASIC,2 assembler; other values select plain.
Optionally set `se_sl_pos[3]`. Feed A bytes to `se_sl_feed`. After each accepted
byte, drain `se_sl_next` until carry set. A successful `next` returns a semantic
span in `se_sl_start[3]`, `se_sl_end[3]`, `se_sl_style`. `se_sl_count` is0–2.
If unread spans remain, feed/finish returns carry set/A=1 without consuming
input, so output cannot silently overflow. `se_sl_finish` flushes the final token;
drain again. Feed/finish otherwise return carry clear. Returned spans are source
intervals; the default for unreturned bytes is plain code.

Styles are keyword7, number8, string9, comment10, directive11, label12,
operator13. These are semantic protocol values, never C64 color numbers. Map
them through the renderer theme and the bitmap8×8 attribute conflict policy.

BASIC recognizes the documented full BASIC V2 text keywords/functions, including
adjacent forms such as `10PRINT"X":GOTO10`. `REM` consumes the rest of the line.
`DATA` suppresses keyword/number/operator highlighting until a colon outside
quotes; a quoted colon cannot terminate DATA. Strings, line numbers, decimal
numbers, leading fractions and exponent forms have separate styles. Keywords
inside strings, REM, DATA or shifted abbreviations are never invented. Abbreviated
shifted BASIC entry such as native `pR` remains literal; use full keywords. This
is text highlighting, not tokenized PRG decoding or BASIC validation. A separate
`GO TO` spelling is outside this subset; `GOTO`/`GOSUB` are recognized. INPUT# /
PRINT# color the keyword and # operator separately. Embedded unsupported controls
are source data and have no terminal effect.

Assembler recognizes official6502 mnemonic spellings, an explicit ca65-oriented
directive table (see `lexer.s`), identifiers ending in a single colon as labels,
$hex, %binary, decimal, #/operators, single/double quoted strings and semicolon
comments. Unknown words/directives remain plain. Identifier bytes are native
letters, digits after the first byte, `_`, `@`, and `.`. The scanner does not
validate addressing modes, macro expansion, scoped-name semantics, numbers, or
expressions and does not interpret string escapes. A malformed/unclosed string
is styled to CR/EOF and then resets. It does not alter or reject source.

Case folding recognizes native $41–$5A and $C1–$DA only. Host ASCII lowercase
$61–$7A is PETSCII graphics, not a third spelling of letters. Host fixtures use
an explicit transcription converter and include controls, both native cases and
graphics to keep those byte types distinct.

## Integration and evidence limits

A bounded consumer can classify a line, then read its unchanged source again
through the existing chunk reader for inline/lexical spans. Checkpoint state at
source anchors. An edit invalidates from a preceding valid checkpoint until
parser state converges; document identity/generation and checkpoint ownership
are caller responsibilities. Fold-tree maintenance, stable anchors, source/
rendered caret affinity, color application and rendering remain separate work.
Do not interpret this probe as M5 or the full editor being complete.

`build/supermark/result.json` records exact source/probe hashes, per-module sizes,
whole-input independent comparisons, malformed/native cases, incremental edits,
fresh-CPU context transfers, backpressure and protected RAM. Instruction totals
are CPU-test observations, not PAL/NTSC frame latency or VIC/video proof. No VICE
instance, D81 or physical keyboard was used by this probe.
