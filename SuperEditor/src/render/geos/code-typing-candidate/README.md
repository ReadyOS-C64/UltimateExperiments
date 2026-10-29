# Private native8 code typing transaction

Released for parent review/promotion; not yet a packaged editor feature or native timing claim.

`build-worker.py OUTPUT IMMUTABLE_FIXTURE` compiles both sealed images against that fixture's **current** `editor-report.json` and binding digest. It first links C31, emits `stage-constants.inc` with exact image/raw lengths and CRC16 values, then compiles R31 using those constants. There is no frozen old binding in the sources. Rebuild both images whenever the resident binding or staged sources change.

- R31: `worker.s`, `guard.s`, `admit.s`, `stage-guard.s`, `transport.s`, existing `typing/status-normal.s` and `typing/status-raster.s`; imports-only `editor-api.inc` and one generated module binding object. `capsule.cfg` places CODE/RODATA at A000. Entry binding16 then opcode3. Root opcode3 is owner0 only; foreign owners return A2/Cclear without touching phase/font descriptors. Claim4, complete one bounded <=39-byte row transaction, releaseowner0 on every return. A0/Cclear completed, A2/Cclear readonly eligibility miss, Cset genuine provider/staged-image error. Root must call its normal publication once on A0.
- C31: `stage-entry.s`, `lex-paint.s`, the unchanged actual `lexer.s` twice (`SE_SM_CODE_ONLY` and `SE_SM_STATE_ONLY`), one generated binding object. `stage.cfg` places binding/header B000..B01F and immutable code payload linked-run5000/loadB020. The SM_STATE60B is caller-owned8D00..8D3B, never resident allocation. Source `lexer.s` is byte-identical to the frozen production source's pure SuperMark lexer.
- Current exact payloads are reported by generated `worker-budget.json` and `stage.json`. Both fit4096 without resident BSS or new ZP.

## C21 production publication hook

The only publisher change needed is at `page.s:prepare_line`, after actual C24 completed, before clearing/preparing C20:

```asm
lda GSEM_FRAME+GSEM_LANG
sta GP_RECORD+30
eor #$FF
sta GP_RECORD+31
```

Byte30 is actual BASIC1/assembler2 language and31 its complement. R31 refuses old zero/default prefixes. `build-page.py` demonstrates only this five-instruction private change from the immutable production ZIP. Do not replace current production C21 or C24 with the extracted private copies.

## Cold and warm executable protocol

A normal actual mutation already leaves C6 in its C slot. Calling R31 loads only the R slot. **Never call C31 from R31**, and no invalid-opcode or dummy C6 operation is necessary. R31 directly obtains C31's immutable catalog backing:

1. Validate provider epoch, asset epoch, all four allocated logical asset owners2, selected logical-to-physical map and physical owner2; find catalog slot1/ID31 with exact generated size/image CRC.
2. DMA the authoritative binding16 to8080 and compare R31's current A000 binding.
3. DMA raw offset32/length to5000, verify generated sealed CRC16, then publish shared font-window `GF_FACE=$FF`, `GF_VALID=$41` last. Only then may5000/5003 execute.
4. Warm reuse validates the same capabilities and stamp at5C80..5C84. It relies on the existing **all legitimate5000 writers clear GF_VALID before writing** contract, including failed overlay CRC admission, font fetch and preview/resume. `se_overlay_loads` is recorded for diagnostics but its16-bit wrap is not authority. Any legal stage/font overwrite forces re-prime. This does not claim detection of unauthorized arbitrary RAM writes after a valid stamp, just as an already admitted executable overlay is not CRC-scanned on each instruction.

Jump5000 is actual fresh lexer ->40 palette roles8300; jump5003 renders all40 native8 cells of one aligned physical row. Raw payload/CRC include both jump addresses, actual lexer and adapter; offsets are never guessed from previous builds. Font4800 is the same real native128glyph font authority used by existing R27 UI. Inverse screen aliases use the high bit; all256 native inputs pass the component oracle.

## Authority and transaction

Only literal GEOS, wrap mode with zero pan, normal UI0, no selection/fold/provider/history fault. Old and new code row must be complete CR/EOF, kind1/height8/alignedY16..184, <=39glyphs; raw source bytes are one native8 glyph each. Existing full source graph/generation/epoch/revision+1/mergedlength/GEC/GCC draw witnesses are checked independently. Typed FE header, row geometry, language, canonical start/end/next and preceding CR are checked. First nonspace alpha/digit must be unchanged and strictly precede the edit, so an ordinary edit cannot create/remove a code fence. Controls/CR, wrapped/long rows, empty-leading edits and non-alpha/digit prefixes fall back.

The actual unchanged pure lexer recomputes the **entire new row**; no copied old roles or fake lexer. Whole new characters are compared to actual merged source and final CR/EOF before any FE/bitmap mutation. An eligibility miss retains GCC/GEC for existing R28/full fallback. Accepted phase invalidates the sparse index before touching lexer phase8D00.

READY-last: invalid FEheader/GCC -> caret-free native row -> save320bitmap+40attributes into existing FEbase -> restore real caret -> write842B live row -> guarded following32B canonical-prefix rebases -> header/new source/viewport/GCC witnesses + status. Partial transaction failure invalidates derived certificates; canonical source/history/clipboard remain untouched. Cached base is **body authoritative**, not a promise of current status/chrome cache bytes.

Caller scratch is8B40..8B4E,8B60..63,8B80..8B8C,8BF0..F4; lexer8D00..8D3B; packet8D3C..9085; header90CA..9109; existing GP_IO9178..7D; CPU bounce8000..813F and8400..8427; the shared legitimate5000 window and CBC0 font descriptor. No leases, allocations, source object writes, new BSS or ZP. Existing foreground text_ptr/screen_ptr are borrowed. Source cache8000 is explicitly invalidated before bounce writes. ShimC600..C9FF untouched.

## Reproduce

```sh
python3 tests/test_geos_code_typing.py
python3 tests/test_geos_code_typing_transaction.py
```

The transaction gate executes the actual immutable packaged C6 and actual C24-backed private C21 publisher, then an explicit R31 root-call seam. It compares every VIC bitmap/attribute byte against independent semantic/font models and actual R28/full renderer, all live packet/header fields, the whole caret-free body base, canonical/history state, every foreign REU byte and shim. Component tests separately guard whole64KiB RAM and all16MiB REU.

No production router, catalog changes, D81/native run, physical key or latency claim is made here. Parent owns promotion, routing, cold names (`code`/`clex` suggested), shared builds and native acceptance.
