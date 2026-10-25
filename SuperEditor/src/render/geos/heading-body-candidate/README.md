# Complete heading-body dirty-row candidate

Private R28 implementation only; no production/shared build changes. The preferred
append-capable release is **`append-edit-cache.s`**, SHA256
`22f4543d4ad5ff04f1bc842bf1baf315cdd2b2c35aa827983dc09d598183f13b`.
It is **4096 bytes**, +45 over the byte-identically reassembled 4051-byte control.
No new resident/phase BSS, zero page, overlay slot, opcode, or helper call.
The cache-warm component remains 664 bytes. The earlier interior-only
`edit-cache.s` is retained unchanged, SHA256
`d00e7bc3c74629c0c3c77d2434882691df19568bdf1b4a643413c601032b929d`;
it also fits4096 but retains the old POSITION<END append limitation.

## Admission and publication

New internal `GEX_CLASS=4` accepts a single authoritative alphanumeric INSERT or
BACK strictly after the old heading prefix. Forward Delete, whitespace/control
or punctuation edits and prefix edits refuse this class. PETSCII alphabetic
high-case bytes use the existing bit7 folding; digits0..9 are included.

The old row must have kind0, exact heading flags1, all role bytes2, a checked
literal prefix of1..6 hashes followed by space, START=FIRST, a complete CR/EOF
reason, source-count agreement and height9. Its TOP/HEIGHT must match the saved
painted-caret `GCC_Y/GCC_HEIGHT`. The old caret-row witness, full canonical
source/capability/provider/epoch/revision/length/sequence keys, no selection,
no folded projection, no pan/no-wrap/preview/modal, current pending shape,
previous-CR and authoritative old/new byte checks are retained. Styles may be
nonzero: headings with emphasis/strong retain role2, and actual C26 rebuilds
the entire new row. Inline-code role4 deliberately falls back.

The position-minus-START comparison uses the low byte only after full24-bit
containment and the <=161-byte complete-row proof; its mathematical result is
therefore0..161, even across a256-byte address boundary. It cannot truncate a
far source address. Hash+space length is compared before accepting the edit.

C21 sees nonzero class4 and runs its existing **real C24/C20/C26** row rebuild.
The existing VERIFY comparison already expects heading flags1 for class>=3.
It verifies new kind/height/TOP/START/FIRST, identical CR/EOF reason, and exact
END/NEXT plus or minus one before any dirty pixels publish. A new wrap abandons
the staged transaction and forces full rendering. Existing suffix rebasing and
the physical shared-strip majority-color producer remain unchanged.

A heading remains a heading after a body-only alphanumeric edit. Its unchanged
raw prefix cannot become a fence/region directive, and headings change no
following fence/language/region carry. Both old-prefix proof and actual new C24
classification are mandatory. This is not arbitrary parser-carry reuse.

## Append-capable variant and fitting

The preferred variant additionally considers POSITION==END only for a row with
its heading flag bit set. Exact flags1, saved caret-row, kind, complete CR/EOF,
prefix, operation and all geometry checks still follow. Thus CR/EOF appending
is supported; a softwrap equality with caret in the next row refuses. Deleting
the real CR is rejected by the existing ordinary-byte guard.

To fit, it removes only the redundant initial CLASS clear: every accepted START
or interior branch assigns CLASS before use; misses invalidate PHASE/GEC/GCC,
and C21 reads CLASS only after an accepted FAST_PAINT transaction. It uses
`TXA/ORA#2` for the already-validated operation0/1 and `EOR#1/ORA#8` only where
old KIND is already proved0/1. The new-row VERIFY mapping remains unchanged.
A zero-hash test uses TYA rather than CPY#0. Nearby long branches are shortened
to the exact same existing rejection trampoline. No rejection predicate or
source/provider guard is removed. The earlier interior-only source remains an
independent immutable release if already copied by the parent.

## Proof and limits

Append candidate and unchanged control each pass **72 public frames**; all72
PNG files are byte-identical. Each frame compares independent canonical
SuperMark/expanded-font pixels with actual forced full renderer output,
attributes, every START/END/NEXT/FIRST/count/TOP/HEIGHT and bottom, canonical
source/history/catalog/leases and the complete1KiB ReadyOS shim. Full16MiB
comparisons allow only authenticated FE body/transaction spans; the real folded
fallback additionally audits exact observed typed46 metadata writes.

Coverage includes heading levels1..6, insertion/BACK/digits/highPETSCII,
first-body and CR/EOF append, corrective BACK, 256-byte crossing and >64KiB,
following BASIC fences, surrounding regions, inline styles, published pending
baselines, two-unpainted-edit refusal, old/new wrap, exact soft boundary,
selection, real collapsed folds,12 malformed metadata cases and six opaque
owner/operation groups. Original ordinary15, forward37 and corrective-BACK35
suites also pass. Only explicitly recorded historical expected-path predicates
change; their source, pixel, forced-full and REU checks remain intact.

| Case | Original render instructions | Candidate | Forced full | Loads original→candidate |
| --- | ---: | ---: | ---: | ---: |
| Heading body INSERT | 829761 | 387095 | 797051 |24→17|
| Heading body BACK |817543|375064|784838|24→17|
| Diverse422 heading body |3125703|606550|3092993|120→17|
| Append at CR |844025|408361|810864|24→17|
| Append at EOF |627627|340280|594934|16→17|
| Heading beyond64KiB |11956807|11521743|11924096|24→17|

These count actual instructions **inside render after input has settled**,
not whole-interaction cycles. EOF may increase loads despite lower instructions.
Far source remains dominated by real C24 canonical-prefix parsing; this does
not make all far edits fast. Native cycles and production stack qualification
are the parent's gates.

An initial >64KiB setup hit the inherited25000-total-service harness limit in
cold job12, error0, before the new edit or R28 admission. That failed RAM/REU
snapshot is retained. Candidate and baseline control pass with200000 total
steps while preserving every actual per-service call, error and lease check.
No product timeout or cancellation behavior was changed.

## Reproduce

```
python3 tests/test_geos_heading_body_candidate.py --append --diverse
python3 tests/test_geos_heading_body_candidate.py --append --diverse --variant control
python3 tests/test_geos_heading_body_candidate_regressions.py --fixture PRIVATE_FIXTURE --suite ordinary --packaged
python3 tests/test_geos_heading_body_candidate_regressions.py --fixture PRIVATE_FIXTURE --suite forward --packaged
python3 tests/test_geos_heading_body_candidate_regressions.py --fixture PRIVATE_FIXTURE --suite back --packaged
```

The private fixture seals/packages only R28 and updates its matching source ZIP.
All other D81 file bytes and sector chains are checked equal. Preferred fixture:
`build/geos-heading-body/20261025T163902774632Z/fixture`, private D81SHA256
`dcd035013f8304261c52b8a0d929dede804ba87bda44ce8e92a627faa78c9f39`.
